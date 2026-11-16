import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import AuthCard from '../components/auth/AuthCard';
import { Check, ArrowRight } from 'lucide-react';
import '../styles/auth.css';

export default function RecoverySuccessPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const registrationComplete = Boolean(location.state?.registrationComplete);

  return (
    <AuthCard
      showLogo={true}
      maxWidth="420px"
      footer={<div>© 2025 mAIra. All rights reserved.</div>}
    >
      <div style={{ textAlign: 'center', padding: '10px 0' }}>
        <div className="success-icon-badge">
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: '#3B82F6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              boxShadow: '0 0 12px rgba(59, 130, 246, 0.8)',
            }}
          >
            <Check size={20} strokeWidth={3} />
          </div>
        </div>

        <h2 style={{ fontSize: '1.38rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
          {registrationComplete ? "Registration completed successfully" : "Password updated successfully"}
        </h2>
        <p style={{ fontSize: '0.84rem', color: '#94A3B8', lineHeight: 1.5, marginBottom: '24px' }}>
          {registrationComplete
            ? 'Your account is now registered. You can sign in using your email and password.'
            : 'Your password has been changed successfully. You can now log in with your new password.'}
        </p>

        <button
          type="button"
          className="btn-primary-gradient"
          style={{ width: '100%', height: '46px' }}
          onClick={() => navigate('/')}
        >
          <span>Continue to Sign In</span>
          <ArrowRight size={16} />
        </button>
      </div>
    </AuthCard>
  );
}
