import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AuthCard from '../components/auth/AuthCard';
import OtpInput from '../components/common/OtpInput';
import { Mail, ShieldCheck, Clock } from 'lucide-react';
import '../styles/auth.css';

export default function StandaloneVerifyPage() {
  const navigate = useNavigate();
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [secondsLeft, setSecondsLeft] = useState(30);

  useEffect(() => {
    if (secondsLeft <= 0) return;
    const interval = setInterval(() => {
      setSecondsLeft((s) => s - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [secondsLeft]);

  const handleVerify = (e) => {
    e.preventDefault();
    navigate('/dashboard');
  };

  const formattedTimer = `00:${secondsLeft < 10 ? '0' : ''}${secondsLeft}`;

  return (
    <AuthCard
      showLogo={true}
      maxWidth="440px"
      footer={
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '8px 14px' }}>
          <span>© 2025 mAIra Enterprise Suite. Data Sovereignty Assured.</span>
          <span>•</span>
          <a href="#privacy" style={{ color: '#94A3B8' }}>Privacy Policy</a>
          <span>•</span>
          <a href="#terms" style={{ color: '#94A3B8' }}>Terms of Service</a>
          <span>•</span>
          <a href="#security" style={{ color: '#94A3B8' }}>Security &amp; Compliance</a>
        </div>
      }
    >
      <div style={{ textAlign: 'center', marginBottom: '22px' }}>
        <h2 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '8px' }}>
          Verify your email
        </h2>
        <p style={{ fontSize: '0.82rem', color: '#94A3B8', lineHeight: 1.5 }}>
          We've sent a 6-digit verification code to your<br />
          authorized enterprise address.
        </p>
      </div>

      <div className="auth-email-box">
        <div className="auth-email-left">
          <Mail size={15} color="#60A5FA" />
          <span style={{ fontSize: '0.82rem' }}>sarah.chen@vanguard-ai.io</span>
        </div>
        <button
          type="button"
          className="auth-change-link"
          onClick={() => navigate('/?tab=login')}
        >
          Change Email
        </button>
      </div>

      <form onSubmit={handleVerify}>
        <div className="otp-header-row">
          <span style={{ color: '#CBD5E1' }}>Verification Code</span>
          <span style={{ color: '#64748B' }}>6-digit security token</span>
        </div>

        <OtpInput value={otp} onChange={setOtp} />

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.74rem',
            color: '#94A3B8',
            margin: '14px 0 20px',
          }}
        >
          <div>
            Didn't receive the code?{' '}
            <button
              type="button"
              onClick={() => setSecondsLeft(30)}
              style={{ color: '#60A5FA', cursor: 'pointer', background: 'none', border: 'none' }}
            >
              Resend Code
            </button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#CBD5E1' }}>
            <Clock size={13} color="#94A3B8" />
            <span>Resend in {formattedTimer}</span>
          </div>
        </div>

        <button
          type="submit"
          style={{
            width: '100%',
            height: '44px',
            borderRadius: '10px',
            background: 'rgba(37, 99, 235, 0.45)',
            border: '1px solid rgba(59, 130, 246, 0.5)',
            color: '#FFFFFF',
            fontSize: '0.88rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            cursor: 'pointer',
            boxShadow: '0 4px 14px rgba(37, 99, 235, 0.25)',
          }}
        >
          <ShieldCheck size={16} />
          <span>Verify Email</span>
        </button>
      </form>
    </AuthCard>
  );
}
