import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Eye, EyeOff, Lock } from 'lucide-react';
import AuthCard from '../components/auth/AuthCard';
import { api, authStore } from '../services/api';
import '../styles/auth.css';

export default function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email || '';
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!email) navigate('/', { replace: true });
  }, [email, navigate]);

  const continueToWorkspace = (user) => {
    authStore.saveSession({ ...user, user: user.user });
    navigate(user.user?.role === 'ADMIN' ? '/admin' : '/dashboard', { replace: true });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!email) {
      navigate('/', { replace: true });
      return;
    }
    setBusy(true);
    setError('');
    try {
      const result = await api.login(email, password);
      if (result.mfa_required && result.mfa_token) {
        navigate('/register/verify', {
          state: { email, mode: 'mfa', mfaToken: result.mfa_token, expiresIn: result.expires_in_seconds },
        });
      } else {
        continueToWorkspace(result);
      }
    } catch (err) {
      setError(err.message || 'Unable to sign in. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard maxWidth="460px">
      <div style={{ textAlign: 'center', marginBottom: '22px' }}>
        <h2 className="auth-form-title">Welcome Back</h2>
        <p className="auth-form-subtitle">Enter your password to continue.</p>
      </div>

      <div className="auth-email-box">
        <span>{email}</span>
        <Link to="/" className="auth-change-link">Change</Link>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="auth-input-group">
          <div className="auth-input-header">
            <label className="auth-label" htmlFor="login-password">Password</label>
            <Link to="/forgot-password" className="auth-forgot-link">Forgot Password?</Link>
          </div>
          <div className="auth-input-wrapper">
            <Lock size={16} className="auth-input-icon" />
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              className="auth-input"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
            <button type="button" className="auth-toggle-pwd" onClick={() => setShowPassword((value) => !value)}>
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {error && <p className="auth-login-error" role="alert">{error}</p>}
        <button type="submit" className="btn-primary-gradient" style={{ width: '100%', height: '46px', marginTop: '12px' }} disabled={busy}>
          <span>{busy ? 'Verifying...' : 'Continue'}</span>
          <ArrowRight size={16} />
        </button>
      </form>

      <div style={{ textAlign: 'center', marginTop: '18px' }}>
        <Link to="/" className="auth-back-link"><ArrowLeft size={14} /> Back to email</Link>
      </div>
    </AuthCard>
  );
}
