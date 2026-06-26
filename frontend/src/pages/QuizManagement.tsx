import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Grid,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Fab,
  CircularProgress,
  FormControlLabel,
  RadioGroup,
  Radio,
  Checkbox,
  FormLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
  TablePagination,
} from '@mui/material';
import ImageUploadArea from '../components/ImageUploadArea';
import {
  Add,
  Edit,
  Delete,
  Preview,
  Save,
  AutoAwesome,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { toast } from 'react-hot-toast';
import AIQuestionGenerator from '../components/AIQuestionGenerator';
import ProblemPreview from '../components/ProblemPreview';
import axios from 'axios';
import { Subject, Problem, EditableImage } from '../services/types';
import apiClient from '../services/api';
import quizService from '../services/quiz.service';

/** API（DRF）のバリデーションエラーから表示用メッセージを抽出（イシュー#073） */
const extractApiErrorMessage = (error: unknown, fallback: string): string => {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data;
    if (typeof data === 'string') return data;
    if (Array.isArray(data)) return data.map((v) => String(v)).join(' ');
    if (typeof data === 'object') {
      const parts = Object.values(data).flat().map((v) => String(v));
      if (parts.length > 0) return parts.join(' ');
    }
  }
  return fallback;
};


const problemSchema = yup.object({
  question_text: yup.string().required('問題文は必須です'),
  subject: yup.string().required('科目は必須です'),
  difficulty: yup.string().oneOf(['easy', 'medium', 'hard']).required('難易度は必須です'),
  problem_type: yup.string().oneOf(['single_choice', 'multiple_choice']).required('問題タイプは必須です'),
  explanation: yup.string().required('解説は必須です'),
  choices: yup.array().when('problem_type', ([problemType], schema) => {
    if (problemType === 'single_choice' || problemType === 'multiple_choice') {
      return schema.of(
        yup.object({
          text: yup.string().required('選択肢のテキストは必須です'),
          is_correct: yup.boolean().required(),
        })
      ).min(2, '選択肢は最低2つ必要です').test(
        'has-correct-answer',
        '正解を少なくとも1つ選択してください',
        (choices) => choices?.some(choice => choice.is_correct) || false
      );
    }
    return schema;
  }),
});

type ProblemFormData = yup.InferType<typeof problemSchema>;

const QuizManagement: React.FC = () => {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSubject, setFilterSubject] = useState('');
  const [filterDifficulty, setFilterDifficulty] = useState('');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingProblem, setEditingProblem] = useState<Problem | null>(null);
  const [previewProblem, setPreviewProblem] = useState<Problem | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState<string | null>(null);
  const [aiGeneratorOpen, setAiGeneratorOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  // 画像アップロード用の状態（イシュー#031/#073対応: 既存＋新規を1リストで管理）
  const [questionImageItems, setQuestionImageItems] = useState<EditableImage[]>([]);
  const [explanationImageItems, setExplanationImageItems] = useState<EditableImage[]>([]);

  const navigate = useNavigate();

  const {
    control,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ProblemFormData>({
    resolver: yupResolver(problemSchema),
    defaultValues: {
      question_text: '',
      subject: '',
      difficulty: 'medium',
      problem_type: 'single_choice',
      explanation: '',
      choices: [
        { text: '', is_correct: false },
        { text: '', is_correct: false },
        { text: '', is_correct: false },
        { text: '', is_correct: false },
      ],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'choices',
  });

  const problemType = watch('problem_type');

  useEffect(() => {
    fetchProblems();
    fetchSubjects();
  // fetchProblems・fetchSubjects はコンポーネント内関数のためマウント時のみ実行（deps に追加すると無限ループになる）
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // フィルタ変更時に問題を再取得し、ページをリセット
  useEffect(() => {
    if (subjects.length > 0) {  // 科目データが読み込まれた後のみ実行
      setPage(0);  // ページを1ページ目にリセット
      fetchProblems();
    }
  // fetchProblems はコンポーネント内関数のためフィルタ値のみを deps に指定（追加すると無限ループになる）
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterSubject, filterDifficulty]);

  const fetchProblems = async () => {
    try {
      setLoading(true);

      // クエリパラメータの構築
      const params = new URLSearchParams();
      if (filterSubject) {
        params.append('subject', filterSubject);
      }
      if (filterDifficulty) {
        params.append('difficulty', filterDifficulty);
      }

      const url = params.toString()
        ? `/api/problems/?${params.toString()}`
        : '/api/problems/';

      const response = await apiClient.get(url);
      // ページネーション形式のレスポンスの場合はresultsを使用
      const problemsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setProblems(problemsData);
    } catch (error) {
      toast.error('問題の取得に失敗しました');
      console.error('Error fetching problems:', error);
      setProblems([]); // エラー時は空配列をセット
    } finally {
      setLoading(false);
    }
  };

  const fetchSubjects = async () => {
    try {
      const response = await apiClient.get('/api/organizations/subjects/');
      // ページネーション形式のレスポンスの場合はresultsを使用
      const subjectsData = Array.isArray(response.data) ? response.data : response.data.results || [];
      setSubjects(subjectsData);
    } catch (error) {
      console.error('Error fetching subjects:', error);
      setSubjects([]); // エラー時は空配列をセット
    }
  };

  // クライアント側フィルタリングは不要（サーバー側でフィルタリング済み）
  // const filteredProblems = problems.filter(problem => {
  //   if (filterSubject && problem.subject !== filterSubject) return false;
  //   if (filterDifficulty && problem.difficulty !== filterDifficulty) return false;
  //   return true;
  // });

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'success';
      case 'medium': return 'warning';
      case 'hard': return 'error';
      default: return 'default';
    }
  };

  const getDifficultyLabel = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return '初級';
      case 'medium': return '中級';
      case 'hard': return '上級';
      default: return difficulty;
    }
  };

  const getProblemTypeLabel = (type: string) => {
    switch (type) {
      case 'single_choice': return '単一選択';
      case 'multiple_choice': return '複数選択';
      default: return type;
    }
  };

  const handleCreateProblem = async (data: ProblemFormData) => {
    try {
      // multipart/form-dataでのリクエスト送信（イシュー#031対応）
      const formData = new FormData();

      // 問題データをJSONフィールドとして追加
      formData.append('question_text', data.question_text);
      formData.append('subject', data.subject);
      formData.append('difficulty', data.difficulty);
      formData.append('problem_type', data.problem_type);
      formData.append('explanation', data.explanation || '');

      // 選択肢データを個別に追加（エラーハンドリング付き）
      if (data.choices && data.choices.length > 0) {
        try {
          data.choices.forEach((choice, index) => {
            try {
              formData.append('choices', JSON.stringify(choice));
            } catch (error) {
              console.error(`Failed to stringify choice ${index}:`, error);
              throw new Error(`選択肢${index + 1}のデータが不正です`);
            }
          });
        } catch (error) {
          toast.error('選択肢のデータ形式に問題があります');
          console.error('Error creating problem:', error);
          return;
        }
      }

      // 問題用画像の追加（作成は新規Fileのみ・positional命名）
      let qi = 0;
      questionImageItems.forEach((item) => {
        if (item.kind === 'new') {
          qi += 1;
          formData.append(`question_image_${qi}`, item.file);
        }
      });

      // 解説用画像の追加（作成は新規Fileのみ・positional命名）
      let ei = 0;
      explanationImageItems.forEach((item) => {
        if (item.kind === 'new') {
          ei += 1;
          formData.append(`explanation_image_${ei}`, item.file);
        }
      });

      await apiClient.post('/api/problems/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success('問題を作成しました');
      setCreateDialogOpen(false);
      reset();
      // 画像状態をクリア
      setQuestionImageItems([]);
      setExplanationImageItems([]);
      fetchProblems();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, '問題の作成に失敗しました'));
      console.error('Error creating problem:', error);
    }
  };

  /**
   * 編集時の画像差分を FormData に積む（イシュー#073）。
   * 最終並び順を *_images_order（{existing}|{new}）として送信し、新規ファイルを添付する。
   */
  const appendImageOrder = (
    formData: FormData,
    kind: 'question' | 'explanation',
    items: EditableImage[],
  ) => {
    const order: Array<{ existing: string } | { new: string }> = [];
    let newIdx = 0;
    items.forEach((item) => {
      if (item.kind === 'existing') {
        order.push({ existing: item.assetId });
      } else {
        newIdx += 1;
        const key = `${kind}_image_${newIdx}`;
        formData.append(key, item.file);
        order.push({ new: key });
      }
    });
    formData.append(`${kind}_images_order`, JSON.stringify(order));
  };

  /** 画像アイテムを delta（-1=上 / +1=下）方向へ移動した新配列を返す（イシュー#073） */
  const moveItem = (items: EditableImage[], index: number, delta: number): EditableImage[] => {
    const target = index + delta;
    if (target < 0 || target >= items.length) return items;
    const next = [...items];
    const [moved] = next.splice(index, 1);
    next.splice(target, 0, moved);
    return next;
  };

  const handleUpdateProblem = async (data: ProblemFormData) => {
    if (!editingProblem) return;

    try {
      // multipart PUT で画像差分（order配列＋新規ファイル）を送信（イシュー#073）
      const formData = new FormData();
      formData.append('question_text', data.question_text);
      formData.append('subject', data.subject);
      formData.append('difficulty', data.difficulty);
      formData.append('problem_type', data.problem_type);
      formData.append('explanation', data.explanation || '');

      if (data.choices && data.choices.length > 0) {
        data.choices.forEach((choice) => {
          formData.append('choices', JSON.stringify(choice));
        });
      }

      appendImageOrder(formData, 'question', questionImageItems);
      appendImageOrder(formData, 'explanation', explanationImageItems);

      await quizService.updateProblem(editingProblem.id, formData);
      toast.success('問題を更新しました');
      setEditingProblem(null);
      reset();
      setQuestionImageItems([]);
      setExplanationImageItems([]);
      fetchProblems();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, '問題の更新に失敗しました'));
      console.error('Error updating problem:', error);
    }
  };

  const handleDeleteProblem = async (problemId: string) => {
    try {
      await apiClient.delete(`/api/problems/${problemId}/`);
      toast.success('問題を削除しました');
      setDeleteConfirmOpen(null);
      fetchProblems();
    } catch (error) {
      toast.error('問題の削除に失敗しました');
      console.error('Error deleting problem:', error);
    }
  };

  const openEditDialog = (problem: Problem) => {
    setEditingProblem(problem);
    reset({
      question_text: problem.question_text,
      subject: problem.subject,
      difficulty: problem.difficulty,
      // 'text'タイプは問題管理画面では未対応のため型アサーション
      problem_type: problem.problem_type as 'single_choice' | 'multiple_choice',
      explanation: problem.explanation || '',
      choices: problem.choices.map(c => ({
        text: c.text,
        is_correct: c.is_correct,
      })),
    });
    // 既存画像を1リストに読み込む（イシュー#073）
    const toExisting = (assets?: { id: string; url: string; original_filename: string }[]): EditableImage[] =>
      (assets ?? []).map(a => ({
        kind: 'existing',
        assetId: a.id,
        url: a.url,
        filename: a.original_filename,
      }));
    setQuestionImageItems(toExisting(problem.question_images));
    setExplanationImageItems(toExisting(problem.explanation_images));
  };

  const closeEditDialog = () => {
    setEditingProblem(null);
    reset();
    // 画像状態をクリア（イシュー#031/#073対応）
    setQuestionImageItems([]);
    setExplanationImageItems([]);
  };

  const closeCreateDialog = () => {
    setCreateDialogOpen(false);
    reset();
    // 画像状態をクリア（イシュー#031/#073対応）
    setQuestionImageItems([]);
    setExplanationImageItems([]);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleChoiceCorrectToggle = (index: number) => {
    const currentChoices = watch('choices');
    if (!currentChoices || !Array.isArray(currentChoices)) return;

    if (problemType === 'single_choice') {
      // For single choice, uncheck all others
      const newChoices = currentChoices.map((choice, i) => ({
        ...choice,
        is_correct: i === index,
      }));
      setValue('choices', newChoices);
    } else {
      // For multiple choice, toggle the selected one
      const newChoices = [...currentChoices];
      // eslint-disable-next-line security/detect-object-injection
      newChoices[index].is_correct = !newChoices[index].is_correct;
      setValue('choices', newChoices);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">問題管理</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            color="success"
            startIcon={<Preview />}
            onClick={() => navigate('/quiz')}
          >
            クイズを実行
          </Button>
          <Button
            variant="outlined"
            startIcon={<AutoAwesome />}
            onClick={() => setAiGeneratorOpen(true)}
            color="secondary"
          >
            AI問題生成
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateDialogOpen(true)}
          >
            問題を作成
          </Button>
        </Box>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            フィルター
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>科目</InputLabel>
                <Select
                  value={filterSubject}
                  label="科目"
                  onChange={(e) => setFilterSubject(e.target.value)}
                >
                  <MenuItem value="">すべて</MenuItem>
                  {subjects.map(subject => (
                    <MenuItem key={subject.id} value={subject.id}>
                      {subject.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>難易度</InputLabel>
                <Select
                  value={filterDifficulty}
                  label="難易度"
                  onChange={(e) => setFilterDifficulty(e.target.value)}
                >
                  <MenuItem value="">すべて</MenuItem>
                  <MenuItem value="easy">初級</MenuItem>
                  <MenuItem value="medium">中級</MenuItem>
                  <MenuItem value="hard">上級</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Problems Table */}
      <TableContainer component={Paper} sx={{ mb: 3 }}>
        <Table sx={{ minWidth: 650 }} aria-label="問題一覧">
          <TableHead>
            <TableRow sx={{ backgroundColor: 'action.hover' }}>
              <TableCell sx={{ fontWeight: 'bold', minWidth: 300 }}>問題文</TableCell>
              <TableCell sx={{ fontWeight: 'bold', minWidth: 120 }}>科目</TableCell>
              <TableCell sx={{ fontWeight: 'bold', minWidth: 100 }}>難易度</TableCell>
              <TableCell sx={{ fontWeight: 'bold', minWidth: 100 }}>形式</TableCell>
              <TableCell sx={{ fontWeight: 'bold', minWidth: 100 }}>作成日</TableCell>
              <TableCell align="center" sx={{ fontWeight: 'bold', minWidth: 150 }}>アクション</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {problems
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((problem) => (
              <TableRow
                key={problem.id}
                sx={{
                  '&:hover': { backgroundColor: 'action.hover' }
                }}
              >
                <TableCell>
                  <Tooltip title={problem.question_text}>
                    <Typography variant="body2" sx={{
                      maxWidth: 300,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {problem.question_text}
                    </Typography>
                  </Tooltip>
                </TableCell>
                <TableCell>
                  <Chip
                    label={problem.subject_name || problem.subject}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={getDifficultyLabel(problem.difficulty)}
                    size="small"
                    color={getDifficultyColor(problem.difficulty) as any}
                  />
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {getProblemTypeLabel(problem.problem_type)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {new Date(problem.created_at).toLocaleDateString('ja-JP')}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Box display="flex" justifyContent="center" gap={0.5}>
                    <Tooltip title="プレビュー">
                      <IconButton
                        size="small"
                        color="info"
                        onClick={() => setPreviewProblem(problem)}
                      >
                        <Preview />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="編集">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => openEditDialog(problem)}
                      >
                        <Edit />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="削除">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => setDeleteConfirmOpen(problem.id)}
                      >
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {problems.length === 0 && (
          <Box textAlign="center" py={4}>
            <Typography variant="h6" color="text.secondary">
              問題が見つかりません
            </Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setCreateDialogOpen(true)}
              sx={{ mt: 2 }}
            >
              最初の問題を作成
            </Button>
          </Box>
        )}

        {problems.length > 0 && (
          <TablePagination
            rowsPerPageOptions={[5, 10, 25, 50]}
            component="div"
            count={problems.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={handleChangePage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            labelRowsPerPage="1ページあたりの行数:"
            labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}件`}
          />
        )}
      </TableContainer>

      {/* Create/Edit Dialog */}
      <Dialog
        open={createDialogOpen || !!editingProblem}
        onClose={editingProblem ? closeEditDialog : closeCreateDialog}
        maxWidth="md"
        fullWidth
      >
        <form onSubmit={handleSubmit(editingProblem ? handleUpdateProblem : handleCreateProblem)}>
          <DialogTitle>
            {editingProblem ? '問題を編集' : '新しい問題を作成'}
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12}>
                <Controller
                  name="question_text"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      fullWidth
                      multiline
                      rows={3}
                      label="問題文"
                      error={!!errors.question_text}
                      helperText={errors.question_text?.message}
                    />
                  )}
                />
              </Grid>

              {/* 問題用画像アップロード欄（イシュー#031対応） */}
              <Grid item xs={12}>
                <ImageUploadArea
                  label="問題用画像"
                  items={questionImageItems}
                  onImagesAdd={(files) => setQuestionImageItems([
                    ...questionImageItems,
                    ...files.map(f => ({ kind: 'new' as const, file: f })),
                  ])}
                  onRemove={(index) => setQuestionImageItems(
                    questionImageItems.filter((_, i) => i !== index))}
                  onMoveUp={(index) => setQuestionImageItems(moveItem(questionImageItems, index, -1))}
                  onMoveDown={(index) => setQuestionImageItems(moveItem(questionImageItems, index, 1))}
                  maxImages={5}
                />
              </Grid>

              <Grid item xs={12} sm={4}>
                <Controller
                  name="subject"
                  control={control}
                  render={({ field }) => (
                    <FormControl fullWidth error={!!errors.subject}>
                      <InputLabel>科目</InputLabel>
                      <Select {...field} label="科目">
                        {subjects.map(subject => (
                          <MenuItem key={subject.id} value={subject.id}>
                            {subject.name}
                          </MenuItem>
                        ))}
                      </Select>
                      {errors.subject && (
                        <Typography variant="caption" color="error">
                          {errors.subject.message}
                        </Typography>
                      )}
                    </FormControl>
                  )}
                />
              </Grid>

              <Grid item xs={12} sm={4}>
                <Controller
                  name="difficulty"
                  control={control}
                  render={({ field }) => (
                    <FormControl fullWidth error={!!errors.difficulty}>
                      <InputLabel>難易度</InputLabel>
                      <Select {...field} label="難易度">
                        <MenuItem value="easy">初級</MenuItem>
                        <MenuItem value="medium">中級</MenuItem>
                        <MenuItem value="hard">上級</MenuItem>
                      </Select>
                    </FormControl>
                  )}
                />
              </Grid>

              <Grid item xs={12}>
                <Controller
                  name="problem_type"
                  control={control}
                  render={({ field }) => (
                    <FormControl error={!!errors.problem_type}>
                      <FormLabel>問題タイプ</FormLabel>
                      <RadioGroup {...field} row>
                        <FormControlLabel
                          value="single_choice"
                          control={<Radio />}
                          label="単一選択"
                        />
                        <FormControlLabel
                          value="multiple_choice"
                          control={<Radio />}
                          label="複数選択"
                        />
                      </RadioGroup>
                    </FormControl>
                  )}
                />
              </Grid>

              {(problemType === 'single_choice' || problemType === 'multiple_choice') && (
                <>
                  <Grid item xs={12}>
                    <Typography variant="subtitle1" sx={{ mb: 1 }}>
                      選択肢
                    </Typography>
                    {fields.map((field, index) => (
                      <Box key={field.id} sx={{ mb: 2 }}>
                        <Grid container spacing={1} alignItems="center">
                          <Grid item xs={1}>
                            {problemType === 'single_choice' ? (
                              <Radio
                                checked={watch(`choices.${index}.is_correct`)}
                                onChange={() => handleChoiceCorrectToggle(index)}
                              />
                            ) : (
                              <Checkbox
                                checked={watch(`choices.${index}.is_correct`)}
                                onChange={() => handleChoiceCorrectToggle(index)}
                              />
                            )}
                          </Grid>
                          <Grid item xs={9}>
                            <Controller
                              name={`choices.${index}.text`}
                              control={control}
                              render={({ field }) => (
                                <TextField
                                  {...field}
                                  fullWidth
                                  size="small"
                                  label={`選択肢 ${String.fromCharCode(65 + index)}`}
                                  // eslint-disable-next-line security/detect-object-injection
                                  error={!!errors.choices?.[index] && errors.choices[index] && typeof errors.choices[index] === 'object' && 'text' in errors.choices[index]!}
                                  // eslint-disable-next-line security/detect-object-injection
                                  helperText={errors.choices?.[index] && errors.choices[index] && typeof errors.choices[index] === 'object' && 'text' in errors.choices[index]! ? (errors.choices[index] as any).text?.message : ''}
                                />
                              )}
                            />
                          </Grid>
                          <Grid item xs={2}>
                            {fields.length > 2 && (
                              <IconButton
                                size="small"
                                onClick={() => remove(index)}
                              >
                                <Delete />
                              </IconButton>
                            )}
                          </Grid>
                        </Grid>
                      </Box>
                    ))}
                    {fields.length < 6 && (
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<Add />}
                        onClick={() => append({ text: '', is_correct: false })}
                      >
                        選択肢を追加
                      </Button>
                    )}
                    {errors.choices && (
                      <Typography variant="caption" color="error" display="block" sx={{ mt: 1 }}>
                        {errors.choices.message || (errors.choices as any)?.root?.message}
                      </Typography>
                    )}
                  </Grid>
                </>
              )}

              <Grid item xs={12}>
                <Controller
                  name="explanation"
                  control={control}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      fullWidth
                      multiline
                      rows={2}
                      label="解説"
                      error={!!errors.explanation}
                      helperText={errors.explanation?.message}
                    />
                  )}
                />
              </Grid>

              {/* 解説用画像アップロード欄（イシュー#031対応） */}
              <Grid item xs={12}>
                <ImageUploadArea
                  label="解説用画像"
                  items={explanationImageItems}
                  onImagesAdd={(files) => setExplanationImageItems([
                    ...explanationImageItems,
                    ...files.map(f => ({ kind: 'new' as const, file: f })),
                  ])}
                  onRemove={(index) => setExplanationImageItems(
                    explanationImageItems.filter((_, i) => i !== index))}
                  onMoveUp={(index) => setExplanationImageItems(moveItem(explanationImageItems, index, -1))}
                  onMoveDown={(index) => setExplanationImageItems(moveItem(explanationImageItems, index, 1))}
                  maxImages={5}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={editingProblem ? closeEditDialog : closeCreateDialog}>
              キャンセル
            </Button>
            <Button type="submit" variant="contained" startIcon={<Save />} disabled={isSubmitting}>
              {editingProblem ? '更新' : '作成'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Preview Dialog - イシュー#033対応: ProblemPreviewコンポーネント使用 */}
      <Dialog
        open={!!previewProblem}
        onClose={() => setPreviewProblem(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>問題プレビュー</DialogTitle>
        <DialogContent>
          {previewProblem && (
            <ProblemPreview
              problem={previewProblem}
              showCorrectAnswer={true}
              showExplanation={true}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewProblem(null)}>閉じる</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(null)}
      >
        <DialogTitle>問題を削除</DialogTitle>
        <DialogContent>
          <Typography>
            この問題を削除してもよろしいですか？この操作は取り消せません。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirmOpen(null)}>
            キャンセル
          </Button>
          <Button
            onClick={() => deleteConfirmOpen && handleDeleteProblem(deleteConfirmOpen)}
            color="error"
            variant="contained"
          >
            削除
          </Button>
        </DialogActions>
      </Dialog>

      {/* AI Question Generator Dialog */}
      <AIQuestionGenerator
        open={aiGeneratorOpen}
        onClose={() => setAiGeneratorOpen(false)}
        subjects={subjects}
        onProblemGenerated={fetchProblems}
      />

      {/* Floating Action Button */}
      <Fab
        color="primary"
        aria-label="add"
        sx={{ position: 'fixed', bottom: 16, right: 16 }}
        onClick={() => setCreateDialogOpen(true)}
      >
        <Add />
      </Fab>
    </Box>
  );
};

export default QuizManagement;
