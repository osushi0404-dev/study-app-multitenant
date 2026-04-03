import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Alert,
  Tooltip,
  Divider,
} from '@mui/material';
import { ArrowBack, Edit } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { Subject } from '../services/types';
import apiClient from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const SubjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isOrgAdmin = user?.role === 'admin';

  const [subject, setSubject] = useState<Subject | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!isOrgAdmin) {
      setLoading(false);
      return;
    }
    fetchSubject();
  }, [id, isOrgAdmin]);

  const fetchSubject = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/api/subjects/${id}/`);
      setSubject(response.data);
    } catch (e: any) {
      if (e?.response?.status === 404) {
        setNotFound(true);
      } else {
        toast.error('科目情報の取得に失敗しました');
      }
    } finally {
      setLoading(false);
    }
  };

  if (!isOrgAdmin) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">このページには組織管理者のみアクセスできます。</Alert>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (notFound || !subject) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          科目が見つかりません。
        </Alert>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate('/subject-management')}
        >
          科目一覧に戻る
        </Button>
      </Box>
    );
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '─';
    return new Date(dateStr).toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  };

  return (
    <Box sx={{ p: 3 }}>
      <Button
        startIcon={<ArrowBack />}
        onClick={() => navigate('/subject-management')}
        sx={{ mb: 2 }}
      >
        科目一覧に戻る
      </Button>

      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <Typography variant="h5" gutterBottom>
          {subject.name}
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              説明
            </Typography>
            <Typography variant="body1">
              {subject.description || '─'}
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary">
              問題数
            </Typography>
            <Typography variant="body1">
              {subject.problem_count ?? '─'} 件
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary">
              登録日
            </Typography>
            <Typography variant="body1">
              {formatDate(subject.created_at)}
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary">
              更新日
            </Typography>
            <Typography variant="body1">
              {formatDate(subject.updated_at)}
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
          <Tooltip title="この機能は近日対応予定です">
            <span>
              <Button
                variant="outlined"
                startIcon={<Edit />}
                disabled
                aria-label="編集"
              >
                編集
              </Button>
            </span>
          </Tooltip>
        </Box>
      </Paper>
    </Box>
  );
};

export default SubjectDetail;
