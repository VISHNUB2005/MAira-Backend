import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AuthCard from '../components/auth/AuthCard';
import PasswordRequirements from '../components/common/PasswordRequirements';
import { Eye, EyeOff, ArrowRight, ArrowLeft } from 'lucide-react';
import '../styles/auth.css';

export default function RecoveryPasswordPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    navigate('/recovery/success');
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Top Header Row matching Screen 6 */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: 0,
          right: 0,
          textAlign: 'center',
          fontSize: '0.74rem',
          color: '#64748B',
          zIndex: 20,
        }}
      >
        <a href="#privacy" style={{ color: '#64748B' }}>Privacy</a>
        {' • '}
        <a href="#terms" style={{ color: '#64748B' }}>Terms</a>
        {' • '}
        <span>© 2025 mAIra. All rights reserved.</span>
      </div>

      <AuthCard showLogo={true} maxWidth="460px">
        <div style={{ textAlign: 'center', marginBottom: '22px' }}>
          <h2 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#FFFFFF', marginBottom: '6px' }}>
            Create a new password
          </h2>
          <p style={{ fontSize: '0.82rem', color: '#94A3B8' }}>
            Create a new password for your account.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="auth-input-group">
            <div className="auth-input-header">
              <label className="auth-label">New Password</label>
            </div>
            <div className="auth-input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                style={{ paddingLeft: '14px' }}
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="auth-toggle-pwd"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <PasswordRequirements password={password} variant="two-column" />

          <div className="auth-input-group">
            <div className="auth-input-header">
              <label className="auth-label">Confirm New Password</label>
            </div>
            <div className="auth-input-wrapper">
              <input
                type={showConfirm ? 'text' : 'password'}
                className="auth-input"
                style={{ paddingLeft: '14px' }}
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
              <button
                type="button"
                className="auth-toggle-pwd"
                onClick={() => setShowConfirm(!showConfirm)}
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn-primary-gradient"
            style={{ width: '100%', height: '46px', marginTop: '14px' }}
          >
            <span>Update Password</span>
            <ArrowRight size={16} />
          </button>

          <div style={{ textAlign: 'center', marginTop: '18px' }}>
            <Link to="/?tab=login" className="auth-back-link">
              <ArrowLeft size={14} />
              <span>Back to Login</span>
            </Link>
          </div>
        </form>
      </AuthCard>
    </div>
  );
}
