import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Typography,
  Button,
  IconButton,
  Chip,
  Box,
  TextField,
  InputAdornment,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Search as SearchIcon,
  VpnKey as KeyIcon,
  Block as BlockIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/api';

interface User {
  id: string;
  email: string;
  user_id: string;
  first_name?: string;
  last_name?: string;
  role: string;
  is_active: boolean;
  is_admin: boolean;
  is_superuser: boolean;
  is_email_verified: boolean;
  last_login?: string;
  created_at: string;
  failed_login_attempts: number;
}

const UserManagement: React.FC = () => {
  const navigate = useNavigate();
  const [users, setUsers] = useState<User[]>([]);
  const [, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [resetPasswordDialog, setResetPasswordDialog] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState('');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/admin/users/');
      // ページネーションレスポンスの場合はresultsキーからデータを取得
      const userData = response.data.results || response.data;
      setUsers(userData);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      setSnackbar({ open: true, message: 'ユーザー一覧の取得に失敗しました', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleToggleActive = async (user: User) => {
    try {
      const response = await apiClient.post(
        `/api/admin/users/${user.id}/toggle_active/`,
        {}
      );
      
      setSnackbar({ 
        open: true, 
        message: response.data.message, 
        severity: 'success' 
      });
      
      fetchUsers();
    } catch (error) {
      console.error('Failed to toggle user status:', error);
      setSnackbar({ 
        open: true, 
        message: 'ステータスの変更に失敗しました', 
        severity: 'error' 
      });
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser) return;
    
    try {
      const response = await apiClient.post(
        `/api/admin/users/${selectedUser.id}/reset_password/`,
        {}
      );
      
      setTemporaryPassword(response.data.temporary_password);
      setSnackbar({ 
        open: true, 
        message: response.data.message, 
        severity: 'success' 
      });
    } catch (error) {
      console.error('Failed to reset password:', error);
      setSnackbar({ 
        open: true, 
        message: 'パスワードリセットに失敗しました', 
        severity: 'error' 
      });
    }
  };

  const filteredUsers = users.filter(user =>
    (user.email && user.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (user.user_id && user.user_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (user.first_name && user.first_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (user.last_name && user.last_name.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const paginatedUsers = filteredUsers.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          ユーザー管理
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/admin/users/new')}
        >
          新規ユーザー作成
        </Button>
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2 }}>
          <TextField
            fullWidth
            variant="outlined"
            placeholder="検索（メール、ユーザーID、名前）"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
          />
        </Box>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ユーザーID</TableCell>
              <TableCell>メール</TableCell>
              <TableCell>名前</TableCell>
              <TableCell>役割</TableCell>
              <TableCell>ステータス</TableCell>
              <TableCell>最終ログイン</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedUsers.map((user) => (
              <TableRow key={user.id}>
                <TableCell>{user.user_id}</TableCell>
                <TableCell>
                  {user.email}
                  {user.is_email_verified && (
                    <CheckCircleIcon 
                      sx={{ ml: 1, fontSize: 16, color: 'success.main', verticalAlign: 'middle' }} 
                    />
                  )}
                </TableCell>
                <TableCell>
                  {user.first_name || user.last_name
                    ? `${user.last_name || ''} ${user.first_name || ''}`.trim()
                    : '-'}
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 0.5 }}>
                    {user.is_superuser && (
                      <Chip label="スーパーユーザー" size="small" color="error" />
                    )}
                    {user.is_admin && !user.is_superuser && (
                      <Chip label="管理者" size="small" color="warning" />
                    )}
                    {!user.is_admin && !user.is_superuser && (
                      <Chip label="一般" size="small" />
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={user.is_active ? '有効' : '無効'}
                    size="small"
                    color={user.is_active ? 'success' : 'default'}
                  />
                  {user.failed_login_attempts >= 5 && (
                    <Chip
                      label="ロック中"
                      size="small"
                      color="error"
                      sx={{ ml: 0.5 }}
                    />
                  )}
                </TableCell>
                <TableCell>
                  {user.last_login
                    ? new Date(user.last_login).toLocaleString('ja-JP')
                    : '未ログイン'}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => navigate(`/admin/users/${user.id}/edit`)}
                    title="編集"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => {
                      setSelectedUser(user);
                      setResetPasswordDialog(true);
                    }}
                    title="パスワードリセット"
                  >
                    <KeyIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleToggleActive(user)}
                    title={user.is_active ? '無効化' : '有効化'}
                  >
                    <BlockIcon color={user.is_active ? 'error' : 'disabled'} />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredUsers.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="表示件数:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} / ${count}件`}
        />
      </TableContainer>

      <Dialog open={resetPasswordDialog} onClose={() => setResetPasswordDialog(false)}>
        <DialogTitle>パスワードリセット</DialogTitle>
        <DialogContent>
          {temporaryPassword ? (
            <Box>
              <Alert severity="success" sx={{ mb: 2 }}>
                パスワードがリセットされました。
              </Alert>
              <Typography variant="body2" gutterBottom>
                仮パスワード:
              </Typography>
              <Typography variant="h6" sx={{ fontFamily: 'monospace', p: 2, bgcolor: 'grey.100' }}>
                {temporaryPassword}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                このパスワードをユーザーに伝えてください。
              </Typography>
            </Box>
          ) : (
            <Typography>
              {selectedUser?.email} のパスワードをリセットしますか？
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setResetPasswordDialog(false);
            setTemporaryPassword('');
            setSelectedUser(null);
          }}>
            閉じる
          </Button>
          {!temporaryPassword && (
            <Button onClick={handleResetPassword} variant="contained" color="primary">
              リセット
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default UserManagement;