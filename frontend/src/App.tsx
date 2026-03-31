import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider as CustomThemeProvider } from './contexts/ThemeContext';
import { NotificationProvider } from './contexts/NotificationContext';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import Layout from './components/Layout';
import NavigationLogger from './components/NavigationLogger';

// Accessibility
import AccessibilityProvider from './components/AccessibilityProvider';
import './styles/accessibility.css';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import QuizManagement from './pages/QuizManagement';
import QuizSession from './pages/QuizSession';
import Statistics from './pages/Statistics';
import Settings from './pages/Settings';
import PasswordReset from './pages/PasswordReset';
import EmailVerification from './pages/EmailVerification';
import Monitoring from './pages/Monitoring';
import UserManagement from './pages/UserManagement';
import UserCreate from './pages/UserCreate';
import UserEdit from './pages/UserEdit';
import SubjectManagement from './pages/SubjectManagement';
import SubjectDetail from './pages/SubjectDetail';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <CustomThemeProvider>
        <AccessibilityProvider>
          <AuthProvider>
              <NotificationProvider>
              <Router>
              <NavigationLogger />
              <CssBaseline />
              <Toaster 
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: '#363636',
                    color: '#fff',
                  },
                }}
              />
              
              <Routes>
              {/* Public Routes - 組織別登録URLを先に配置 */}
              <Route path="/login" element={<Login />} />
              <Route path="/register/:organizationSlug" element={<Register />} />
              <Route path="/register" element={<Register />} />
              <Route path="/password-reset" element={<PasswordReset />} />
              <Route path="/verify-email" element={<EmailVerification />} />
              
              {/* Protected Routes */}
              <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="quiz-management" element={<QuizManagement />} />
                <Route path="quiz/:id?" element={<QuizSession />} />
                <Route path="statistics" element={<Statistics />} />
                <Route path="settings" element={<Settings />} />
                <Route path="monitoring" element={<Monitoring />} />
                <Route path="subject-management" element={<SubjectManagement />} />
                <Route path="subject-management/:id" element={<SubjectDetail />} />

                {/* Admin Routes */}
                <Route path="admin/users" element={<AdminRoute><UserManagement /></AdminRoute>} />
                <Route path="admin/users/new" element={<AdminRoute><UserCreate /></AdminRoute>} />
                <Route path="admin/users/:id/edit" element={<AdminRoute><UserEdit /></AdminRoute>} />
              </Route>
              
              {/* Catch all route */}
              <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
              </Router>
              </NotificationProvider>
            </AuthProvider>
        </AccessibilityProvider>
      </CustomThemeProvider>
    </QueryClientProvider>
  );
}

export default App;