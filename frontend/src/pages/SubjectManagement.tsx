import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import { Add, InfoOutlined, Edit, Delete } from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';
import { toast } from 'react-hot-toast';
import { Subject } from '../services/types';
import apiClient from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const schema = yup.object({
  name: yup
    .string()
    .required('科目名は必須です')
    .max(100, '100文字以内で入力してください'),
  description: yup
    .string()
    .max(500, '500文字以内で入力してください')
    .optional(),
});

type FormValues = yup.InferType<typeof schema>;

const DISABLED_TOOLTIP = 'この機能は近日対応予定です';

const SubjectManagement: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isOrgAdmin = user?.role === 'admin';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: yupResolver(schema),
    defaultValues: { name: '', description: '' },
  });

  useEffect(() => {
    if (isOrgAdmin) fetchSubjects();
    else setLoading(false);
  }, [isOrgAdmin]);

  const fetchSubjects = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get('/api/organizations/subjects/');
      const data = Array.isArray(response.data)
        ? response.data
        : response.data.results ?? [];
      setSubjects(data);
    } catch {
      toast.error('科目一覧の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenModal = () => {
    reset({ name: '', description: '' });
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
  };

  const onSubmit = async (values: FormValues) => {
    setSaving(true);
    try {
      await apiClient.post('/api/subjects/', {
        name: values.name,
        description: values.description ?? '',
      });
      toast.success('科目を追加しました');
      setModalOpen(false);
      await fetchSubjects();
    } catch (e: any) {
      toast.error(e?.response?.data?.error || e?.response?.data?.name?.[0] || '科目追加に失敗しました');
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '─';
    return new Date(dateStr).toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  };

  if (!isOrgAdmin) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">このページには組織管理者のみアクセスできます。</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          科目管理 — {user?.organization_name ?? ''}
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleOpenModal}
        >
          科目を追加
        </Button>
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : subjects.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            科目が登録されていません
          </Typography>
          <Button variant="contained" startIcon={<Add />} onClick={handleOpenModal}>
            最初の科目を追加
          </Button>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>科目名</TableCell>
                <TableCell>説明</TableCell>
                <TableCell align="center">問題数</TableCell>
                <TableCell>登録日</TableCell>
                <TableCell align="center">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {subjects.map(subject => (
                <TableRow
                  key={subject.id}
                  sx={{ '&:hover': { backgroundColor: 'action.hover' } }}
                >
                  <TableCell>
                    <Typography
                      component="span"
                      sx={{
                        cursor: 'pointer',
                        color: 'primary.main',
                        '&:hover': { textDecoration: 'underline' },
                      }}
                      onClick={() => navigate(`/subject-management/${subject.id}`)}
                    >
                      {subject.name}
                    </Typography>
                  </TableCell>
                  <TableCell
                    sx={{
                      maxWidth: 240,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    <Tooltip title={subject.description || ''} placement="top" disableHoverListener={!subject.description}>
                      <span>{subject.description || '─'}</span>
                    </Tooltip>
                  </TableCell>
                  <TableCell align="center">{subject.problem_count ?? '─'}</TableCell>
                  <TableCell>{formatDate(subject.created_at)}</TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                      <Tooltip title="詳細">
                        <IconButton
                          size="small"
                          color="info"
                          aria-label="詳細"
                          onClick={() => navigate(`/subject-management/${subject.id}`)}
                        >
                          <InfoOutlined fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title={DISABLED_TOOLTIP}>
                        <span>
                          <IconButton size="small" color="primary" aria-label="編集" disabled>
                            <Edit fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                      <Tooltip title={DISABLED_TOOLTIP}>
                        <span>
                          <IconButton size="small" color="error" aria-label="削除" disabled>
                            <Delete fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* 追加モーダル */}
      <Dialog open={modalOpen} onClose={handleCloseModal} maxWidth="sm" fullWidth>
        <DialogTitle>科目を追加</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="科目名"
                  required
                  fullWidth
                  error={!!errors.name}
                  helperText={errors.name?.message}
                  autoFocus
                />
              )}
            />
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="説明（任意）"
                  fullWidth
                  multiline
                  rows={3}
                  error={!!errors.description}
                  helperText={errors.description?.message}
                />
              )}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseModal}>キャンセル</Button>
          <Button
            variant="contained"
            onClick={handleSubmit(onSubmit)}
            disabled={saving}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SubjectManagement;
