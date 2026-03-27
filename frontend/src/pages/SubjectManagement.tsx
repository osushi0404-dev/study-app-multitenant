import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Paper,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import { Subject } from '../services/types';
import apiClient from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const SubjectManagement: React.FC = () => {
  const { user } = useAuth();
  const isOrgAdmin = user?.role === 'admin';

  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [newSubjectName, setNewSubjectName] = useState('');
  const [loading, setLoading] = useState(true);
  const [addingSubject, setAddingSubject] = useState(false);

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

  const handleAddSubject = async () => {
    const name = newSubjectName.trim();
    if (!name) {
      toast.error('科目名を入力してください');
      return;
    }
    setAddingSubject(true);
    try {
      await apiClient.post('/api/subjects/', { name });
      toast.success('科目を追加しました');
      setNewSubjectName('');
      await fetchSubjects();
    } catch (e: any) {
      toast.error(e?.response?.data?.error || '科目追加に失敗しました');
    } finally {
      setAddingSubject(false);
    }
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
      <Typography variant="h5" gutterBottom>
        科目管理 — {user?.organization_name ?? ''}
      </Typography>
      <Paper sx={{ p: 2, maxWidth: 480 }}>
        {loading ? (
          <CircularProgress size={24} />
        ) : (
          <List dense>
            {subjects.map(s => (
              <ListItem key={s.id}>
                <ListItemText primary={s.name} />
              </ListItem>
            ))}
          </List>
        )}
        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
          <TextField
            size="small"
            label="科目名"
            value={newSubjectName}
            onChange={e => setNewSubjectName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddSubject()}
          />
          <Button
            variant="contained"
            size="small"
            disabled={addingSubject}
            onClick={handleAddSubject}
            startIcon={<Add />}
          >
            追加
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default SubjectManagement;
