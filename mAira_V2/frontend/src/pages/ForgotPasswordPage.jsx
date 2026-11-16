import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import AuthCard from '../components/auth/AuthCard';
import '../styles/auth.css';

export default function ForgotPasswordPage() {
  return (
    <AuthCard maxWidth="460px">
      <div style={{ textAlign: 'center', marginBottom: '22px' }}>
        <h2 className="auth-form-title">Password Recovery</h2>
        <p className="auth-form-subtitle">
          Self-service password recovery is not included in Phase 1. Please contact your institutional administrator for assistance.
        </p>
      </div>
      <div style={{ textAlign: 'center', marginTop: '18px' }}>
        <Link to="/" className="auth-back-link"><ArrowLeft size={14} /> Back to email</Link>
      </div>
    </AuthCard>
  );
}
