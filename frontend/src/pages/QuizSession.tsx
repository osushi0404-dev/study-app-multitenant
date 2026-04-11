import React, { useState, useEffect, useLayoutEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Radio,
  RadioGroup,
  FormControlLabel,
  LinearProgress,
  Chip,
  Alert,
  Checkbox,
  FormGroup,
  TextField,
  CircularProgress,
  Container,
} from '@mui/material';
import {
  CheckCircle,
  Cancel,
  NavigateNext,
  Home,
  Refresh,
  School,
  CheckCircleOutline,  // 追加: 正解マーカー用
} from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import apiClient from '../services/api';
import {
  QuizSession,
  Problem,
  QuizResult,
} from '../types/quiz';
import { useQuizDisplayStats } from '../hooks/useQuizDisplayStats';
import ImageModal from '../components/ImageModal';

const QuizSessionPage: React.FC = () => {
  const [session, setSession] = useState<QuizSession | null>(null);
  const [currentProblem, setCurrentProblem] = useState<Problem | null>(null);
  const [selectedChoices, setSelectedChoices] = useState<string[]>([]);
  const [textAnswer, setTextAnswer] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [startTime, setStartTime] = useState<number>(Date.now());
  const [totalProblemsInSubject, setTotalProblemsInSubject] = useState<number>(0);  // 追加
  const [imageModalOpen, setImageModalOpen] = useState<string>('');  // 画像拡大表示用
  const [isReviewMode, setIsReviewMode] = useState<boolean>(false);  // 追加
  const isReviewModeRef = useRef(isReviewMode);
  useLayoutEffect(() => { isReviewModeRef.current = isReviewMode; }, [isReviewMode]);

  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const subjectId = searchParams.get('subject');

  // カスタムフック使用：表示用統計値を計算（React Hooksルールに従いトップレベルで呼び出す）
  const stats = useQuizDisplayStats(session, showResult, result, totalProblemsInSubject);

  const loadNextProblem = useCallback(async (sessionId: string) => {
    try {
      setLoading(true);
      setShowResult(false);
      setResult(null);
      setSelectedChoices([]);
      setTextAnswer('');

      const response = await apiClient.get(`/api/quiz/${sessionId}/next_problem/`);

      if (response.data && response.data.id) {
        setCurrentProblem(response.data);
        setStartTime(Date.now());

        // 科目の総問題数と復習モードフラグを設定
        if (response.data.total_problems_in_subject) {
          setTotalProblemsInSubject(response.data.total_problems_in_subject);
        }
        if (response.data.is_review_mode !== undefined) {
          // 復習モード開始時にトースト通知
          if (response.data.is_review_mode && !isReviewModeRef.current) {
            toast.success('全問題を解き終えました。既出問題から再度出題しています。');
          }
          setIsReviewMode(response.data.is_review_mode);
        }
      } else {
        console.error('Invalid problem data:', response.data);
        toast.error('問題の読み込みに失敗しました');
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        // 問題が1問もない科目
        toast.error('この科目には問題が登録されていません');
        navigate('/dashboard');
      } else {
        console.error('Error loading problem:', error);
        toast.error('問題の読み込みに失敗しました');
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const createNewSession = useCallback(async () => {
    try {
      setLoading(true);
      const sessionData: any = {};

      if (subjectId) {
        sessionData.subject = subjectId;
      }
      // problem_count パラメータは送信しない（バックエンドが全問題数を設定）

      const response = await apiClient.post('/api/quiz/', sessionData);
      setSession(response.data);

      // 最初の問題を取得
      await loadNextProblem(response.data.id);
    } catch (error) {
      console.error('Error creating session:', error);
      toast.error('クイズセッションの作成に失敗しました');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  }, [subjectId, navigate, loadNextProblem]);

  const loadSession = useCallback(async (sessionId: string) => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/quiz/${sessionId}/`);
      setSession(response.data);

      if (response.data.is_active) {
        // アクティブなセッションの場合、次の問題を取得
        await loadNextProblem(sessionId);
      } else {
        // 完了したセッションの場合、結果を表示
        setSessionComplete(true);
      }
    } catch (error) {
      console.error('Error loading session:', error);
      toast.error('セッションの読み込みに失敗しました');
      navigate('/dashboard');
    } finally {
      setLoading(false);
    }
  }, [navigate, loadNextProblem]);

  const handleSubmitAnswer = useCallback(async (): Promise<void> => {
    if (!session || !currentProblem) return;

    // 回答のバリデーション
    if (currentProblem.problem_type === 'text' && !textAnswer.trim()) {
      toast.error('回答を入力してください');
      return;
    }

    if (currentProblem.problem_type !== 'text' && selectedChoices.length === 0) {
      toast.error('選択肢を選んでください');
      return;
    }

    try {
      setSubmitting(true);
      const timeTaken = Math.floor((Date.now() - startTime) / 1000); // 秒単位

      const answerData: any = {
        problem_id: currentProblem.id,
        time_taken: timeTaken,
      };

      if (currentProblem.problem_type === 'text') {
        answerData.text_answer = textAnswer;
      } else {
        answerData.selected_choice_ids = selectedChoices;
      }

      const response = await apiClient.post(
        `/api/quiz/${session.id}/submit_answer/`,
        answerData
      );

      setResult(response.data);
      setShowResult(true);

      // セッション情報を更新
      if (response.data.session) {
        setSession(response.data.session);
      }
    } catch (error) {
      console.error('Error submitting answer:', error);
      toast.error('回答の送信に失敗しました');
    } finally {
      setSubmitting(false);
    }
  }, [session, currentProblem, selectedChoices, textAnswer, startTime]);

  useEffect(() => {
    if (id) {
      // 既存のセッションを取得
      loadSession(id);
    } else {
      // 新しいセッションを作成
      createNewSession();
    }
  }, [id, loadSession, createNewSession]);

  // 単一選択問題の即時回答機能（UX改善）
  useEffect(() => {
    if (
      currentProblem?.problem_type === 'single_choice' &&
      selectedChoices.length === 1 &&
      !submitting &&
      !showResult
    ) {
      handleSubmitAnswer();
    }
  }, [selectedChoices, currentProblem, submitting, showResult, handleSubmitAnswer]);

  const handleNextQuestion = (): void => {
    if (session) {
      loadNextProblem(session.id);
    }
  };

  const handleChoiceSelect = (choiceId: string): void => {
    if (currentProblem?.problem_type === 'single_choice') {
      setSelectedChoices([choiceId]);
    } else if (currentProblem?.problem_type === 'multiple_choice') {
      setSelectedChoices(prev => {
        if (prev.includes(choiceId)) {
          return prev.filter(id => id !== choiceId);
        } else {
          return [...prev, choiceId];
        }
      });
    }
  };

  const getDifficultyColor = (difficulty: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (difficulty) {
      case 'easy': return 'success';
      case 'medium': return 'warning';
      case 'hard': return 'error';
      default: return 'default';
    }
  };

  const getDifficultyLabel = (difficulty: string): string => {
    switch (difficulty) {
      case 'easy': return '初級';
      case 'medium': return '中級';
      case 'hard': return '上級';
      default: return difficulty;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (sessionComplete && session) {
    const accuracy = session.total_problems > 0
      ? Math.round((session.correct_answers / session.total_problems) * 100)
      : 0;

    return (
      <Container maxWidth="md">
        <Card>
          <CardContent>
            <Box textAlign="center" py={3}>
              <Typography variant="h4" gutterBottom>
                クイズ完了！
              </Typography>

              <Box my={4}>
                <Typography variant="h2" color="primary" gutterBottom>
                  {accuracy}%
                </Typography>
                <Typography variant="h6" color="textSecondary">
                  正答率
                </Typography>
              </Box>

              <Box display="flex" justifyContent="center" gap={4} my={3}>
                <Box>
                  <Typography variant="h4">
                    {session.correct_answers}
                  </Typography>
                  <Typography color="textSecondary">
                    正解
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="h4">
                    {session.total_problems - session.correct_answers}
                  </Typography>
                  <Typography color="textSecondary">
                    不正解
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="h4">
                    {session.total_problems}
                  </Typography>
                  <Typography color="textSecondary">
                    問題数
                  </Typography>
                </Box>
              </Box>

              <Box display="flex" justifyContent="center" gap={2} mt={4}>
                <Button
                  variant="contained"
                  startIcon={<Refresh />}
                  onClick={createNewSession}
                >
                  もう一度挑戦
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Home />}
                  onClick={() => navigate('/dashboard')}
                >
                  ダッシュボードへ
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      </Container>
    );
  }

  if (!currentProblem || !session) {
    return (
      <Container maxWidth="md">
        <Alert severity="info">
          問題を読み込んでいます...
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box mb={3}>
        {/* Progress Bar */}
        <Box mb={2}>
          {/* 復習モード通知 */}
          {isReviewMode && (
            <Alert severity="info" sx={{ mb: 1 }} icon={<Refresh />}>
              全{totalProblemsInSubject}問を解き終えました。既出問題から再度出題しています。
            </Alert>
          )}

          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="body2" color="textSecondary">
                問題 {stats.problemInRound} / {totalProblemsInSubject || session.total_problems}
              </Typography>
              {stats.currentRound > 1 && (
                <Chip
                  label={`${stats.currentRound}周目`}
                  size="small"
                  color="primary"
                  sx={{ height: 20, fontSize: '0.75rem' }}
                />
              )}
            </Box>
            <Typography variant="body2" color="textSecondary">
              正解: {stats.displayCorrectAnswers} / 総回答: {stats.displayAnsweredProblems}
            </Typography>
          </Box>

          <LinearProgress
            variant="determinate"
            value={stats.progressPercentage}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>

        {/* Problem Card */}
        <Card>
          <CardContent>
            {/* Problem Info */}
            <Box display="flex" gap={1} mb={2}>
              {currentProblem.subject_name && (
                <Chip
                  icon={<School />}
                  label={currentProblem.subject_name}
                  size="small"
                />
              )}
              <Chip
                label={getDifficultyLabel(currentProblem.difficulty)}
                color={getDifficultyColor(currentProblem.difficulty) as any}
                size="small"
              />
            </Box>

            {/* Question */}
            <Typography variant="h6" gutterBottom>
              {currentProblem.question_text}
            </Typography>

            {/* 問題画像 - 条件付きレンダリング */}
            {currentProblem.question_image && (
              <Box mt={2}>
                <img
                  src={`${process.env.REACT_APP_API_BASE_URL}${currentProblem.question_image}`}
                  alt="問題画像"
                  style={{
                    maxWidth: '100%',
                    borderRadius: '8px',
                    cursor: 'pointer'
                  }}
                  onClick={() => setImageModalOpen(`${process.env.REACT_APP_API_BASE_URL}${currentProblem.question_image}`)}
                  loading="lazy"
                />
              </Box>
            )}

            {/* Answer Input */}
            <Box mt={3}>
              {currentProblem.problem_type === 'text' ? (
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  variant="outlined"
                  placeholder="回答を入力してください"
                  value={textAnswer}
                  onChange={(e) => setTextAnswer(e.target.value)}
                  disabled={showResult}
                />
              ) : currentProblem.problem_type === 'single_choice' ? (
                <RadioGroup
                  value={selectedChoices[0] || ''}
                  onChange={(e) => handleChoiceSelect(e.target.value)}
                >
                  {currentProblem.choices.map((choice) => {
                    const isCorrectChoice = showResult && result?.correct_choices?.some((c: any) => c.id === choice.id);
                    const isSelectedWrong = showResult && selectedChoices.includes(choice.id) && !result?.is_correct;

                    return (
                      <Box key={choice.id} sx={{ position: 'relative', mb: 1 }}>
                        <FormControlLabel
                          value={choice.id}
                          control={<Radio />}
                          label={
                            <Box display="flex" alignItems="center" gap={1}>
                              {choice.text}
                              {isCorrectChoice && (
                                <CheckCircleOutline
                                  sx={{ color: 'success.main', fontSize: 20 }}
                                />
                              )}
                            </Box>
                          }
                          disabled={showResult}
                          sx={{
                            width: '100%',
                            '& .MuiFormControlLabel-label': {
                              color: isCorrectChoice
                                ? 'success.main'
                                : isSelectedWrong
                                ? 'error.main'
                                : 'inherit',
                              fontWeight: isCorrectChoice ? 600 : 400,
                            }
                          }}
                        />
                      </Box>
                    );
                  })}
                </RadioGroup>
              ) : (
                <FormGroup>
                  {currentProblem.choices.map((choice) => {
                    const isCorrectChoice = showResult && result?.correct_choices?.some((c: any) => c.id === choice.id);
                    const isSelectedWrong = showResult && selectedChoices.includes(choice.id) &&
                                            !result?.correct_choices?.some((c: any) => c.id === choice.id);

                    return (
                      <Box key={choice.id} sx={{ position: 'relative', mb: 1 }}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={selectedChoices.includes(choice.id)}
                              onChange={() => handleChoiceSelect(choice.id)}
                              disabled={showResult}
                            />
                          }
                          label={
                            <Box display="flex" alignItems="center" gap={1}>
                              {choice.text}
                              {isCorrectChoice && (
                                <CheckCircleOutline
                                  sx={{ color: 'success.main', fontSize: 20 }}
                                />
                              )}
                            </Box>
                          }
                          sx={{
                            width: '100%',
                            '& .MuiFormControlLabel-label': {
                              color: isCorrectChoice
                                ? 'success.main'
                                : isSelectedWrong
                                ? 'error.main'
                                : 'inherit',
                              fontWeight: isCorrectChoice ? 600 : 400,
                            }
                          }}
                        />
                      </Box>
                    );
                  })}
                </FormGroup>
              )}
            </Box>

            {/* Result */}
            {showResult && result && (
              <Box mt={3}>
                <Alert
                  severity={result.is_correct ? 'success' : 'error'}
                  icon={result.is_correct ? <CheckCircle /> : <Cancel />}
                >
                  {result.is_correct ? '正解です！' : '不正解です'}
                </Alert>

                {/* 解説ボックス: 解説文または解説画像がある場合に表示 */}
                {(result.explanation || result.explanation_image) && (
                  <Box mt={2} p={2} bgcolor="grey.100" borderRadius={1}>
                    {result.explanation && (
                      <>
                        <Typography variant="subtitle2" gutterBottom>
                          解説:
                        </Typography>
                        <Typography variant="body2">
                          {result.explanation}
                        </Typography>
                      </>
                    )}

                    {/* 解説画像 - 条件付きレンダリング */}
                    {result.explanation_image && (
                      <Box mt={result.explanation ? 2 : 0}>
                        <img
                          src={`${process.env.REACT_APP_API_BASE_URL}${result.explanation_image}`}
                          alt="解説画像"
                          style={{
                            maxWidth: '100%',
                            borderRadius: '8px',
                            cursor: 'pointer'
                          }}
                          onClick={() => setImageModalOpen(`${process.env.REACT_APP_API_BASE_URL}${result.explanation_image}`)}
                          loading="lazy"
                        />
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            )}

            {/* Actions */}
            <Box display="flex" justifyContent="flex-end" gap={2} mt={3}>
              {!showResult ? (
                <>
                  <Button
                    variant="outlined"
                    onClick={() => navigate('/dashboard')}
                  >
                    中断
                  </Button>
                  {/* 単一選択問題は即時回答のため「回答する」ボタンを非表示 */}
                  {currentProblem.problem_type !== 'single_choice' && (
                    <Button
                      variant="contained"
                      onClick={handleSubmitAnswer}
                      disabled={submitting}
                      startIcon={submitting ? <CircularProgress size={16} /> : null}
                    >
                      回答する
                    </Button>
                  )}
                </>
              ) : (
                <>
                  <Button
                    variant="outlined"
                    startIcon={<Home />}
                    onClick={() => navigate('/dashboard')}
                  >
                    終了
                  </Button>
                  {session.answered_problems < session.total_problems && (
                    <Button
                      variant="contained"
                      endIcon={<NavigateNext />}
                      onClick={handleNextQuestion}
                    >
                      次の問題
                    </Button>
                  )}
                </>
              )}
            </Box>
          </CardContent>
        </Card>
      </Box>

      {/* 画像拡大表示モーダル */}
      <ImageModal
        imageUrl={imageModalOpen}
        open={!!imageModalOpen}
        onClose={() => setImageModalOpen('')}
      />
    </Container>
  );
};

export default QuizSessionPage;
