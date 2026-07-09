import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Box, CircularProgress, Alert } from '@mui/material';

interface OrgAdminRouteProps {
  children: React.ReactNode;
}

/**
 * 組織管理者（role === 'admin'）専用ルートガード（I102）。
 *
 * 既存の AdminRoute は is_staff / is_superuser（プラットフォーム staff）判定のため、
 * BE の IsOrgAdmin（role === 'admin'）と概念が異なる。role と is_staff は独立フィールドで、
 * org admin（role='admin' かつ is_staff=false）が AdminRoute では締め出されてしまう。
 * そのため問題管理など「組織管理者」向け画面には本ガードを使う（BE と概念を統一）。
 */
const OrgAdminRoute: React.FC<OrgAdminRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== 'admin') {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          このページにアクセスする権限がありません。管理者権限が必要です。
        </Alert>
      </Box>
    );
  }

  return <>{children}</>;
};

export default OrgAdminRoute;
