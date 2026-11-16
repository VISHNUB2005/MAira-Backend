import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterVerifyPage from './pages/RegisterVerifyPage';
import RegisterPasswordPage from './pages/RegisterPasswordPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import RecoverySuccessPage from './pages/RecoverySuccessPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import UserDashboardPage from './pages/UserDashboardPage';
import { authStore } from './services/api';

function ProtectedRoute({ children, requiredRole }) {
  const location = useLocation();
  const token = authStore.getAccessToken();
  const user = authStore.getUser();
  if (!token || !user) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  if (requiredRole === 'ADMIN' && user.role !== 'ADMIN') return <Navigate to="/dashboard" replace />;
  if (requiredRole === 'USER' && user.role === 'ADMIN') return <Navigate to="/admin" replace />;
  return children;
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="/login/password" element={<LoginPage />} />
        <Route path="/register" element={<Navigate to="/" replace />} />
        <Route path="/register/verify" element={<RegisterVerifyPage />} />
        <Route path="/register/create-password" element={<RegisterPasswordPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/recovery/success" element={<RecoverySuccessPage />} />
        <Route path="/register/success" element={<RecoverySuccessPage />} />
        <Route path="/admin" element={<ProtectedRoute requiredRole="ADMIN"><AdminDashboardPage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute requiredRole="USER"><UserDashboardPage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
