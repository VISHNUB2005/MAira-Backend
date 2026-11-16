import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AuthCard from '../components/auth/AuthCard';
import OtpInput from '../components/common/OtpInput';
import { Mail, ArrowRight, ArrowLeft, RefreshCw } from 'lucide-react';
import '../styles/auth.css';

export default function RecoveryVerifyPage() {
  const navigate = useNavigate();
  const [otp, setOtp] = useState(['', '', '', '', '', '']);

  const handleVerify = (e) => {
    e.preventDefault();
    navigate('/recovery/new-password');
  };

  return (
    <AuthCard
      showLogo={true}
      maxWidth="440px"
      footer={<div>© 2025 mAIra AI Systems</div>}
    >
      <div style={{ textAlign: 'center', marginBottom: '18px' }}>
        <h2 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
          Enter recovery code
        </h2>
        <p style={{ fontSize: '0.82rem', color: '#94A3B8', lineHeight: 1.5 }}>
          Enter the 6-digit code sent to your selected<br />
          recovery method.
        </p>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          background: 'rgba(13, 19, 34, 0.75)',
          border: '1px solid #1E293B',
          borderRadius: '20px',
          padding: '6px 14px',
          width: 'fit-content',
          margin: '0 auto 20px',
          fontSize: '0.8rem',
          color: '#CBD5E1',
        }}
      >
        <Mail size={14} color="#60A5FA" />
        <span>k*****@gmail.com</span>
      </div>

      <form onSubmit={handleVerify}>
        <OtpInput value={otp} onChange={setOtp} />

        <button
          type="submit"
          className="btn-primary-gradient"
          style={{ width: '100%', height: '46px', marginTop: '14px' }}
        >
          <span>Verify Code</span>
          <ArrowRight size={16} />
        </button>
      </form>

      <div style={{ textAlign: 'center', marginTop: '18px', fontSize: '0.78rem', color: '#94A3B8' }}>
        <p style={{ marginBottom: '10px' }}>
          Didn't receive the code?{' '}
          <button
            type="button"
            onClick={() => alert('Recovery code resent to your email.')}
            style={{ color: '#60A5FA', cursor: 'pointer', background: 'none', border: 'none' }}
          >
            Resend code
          </button>
        </p>

        <p style={{ marginBottom: '14px' }}>
          <Link
            to="/forgot-password"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#94A3B8' }}
          >
            <RefreshCw size={12} />
            <span>Use another recovery method</span>
          </Link>
        </p>

        <Link to="/?tab=login" className="auth-back-link">
          <ArrowLeft size={14} />
          <span>Back to Login</span>
        </Link>
      </div>
    </AuthCard>
  );
}
