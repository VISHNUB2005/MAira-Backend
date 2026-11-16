import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import AuthLeftBanner from '../components/auth/AuthLeftBanner';
import OtpInput from '../components/common/OtpInput';
import { Mail, ArrowRight, ArrowLeft } from 'lucide-react';
import { api, authStore } from '../services/api';
import '../styles/auth.css';

export default function RegisterVerifyPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const mode = location.state?.mode || 'register';
  const rawEmail = location.state?.email || '';
  const mfaToken = location.state?.mfaToken;
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [secondsLeft, setSecondsLeft] = useState(location.state?.expiresIn || 300);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!rawEmail || (mode === 'mfa' && !mfaToken)) navigate('/', { replace: true });
  }, [rawEmail, mode, mfaToken, navigate]);

  useEffect(() => {
    if (secondsLeft <= 0) return undefined;
    const timer = setTimeout(() => setSecondsLeft((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [secondsLeft]);

  const maskEmail = (mail) => {
    if (!mail || !mail.includes('@')) return mail || '';
    const [name, domain] = mail.split('@');
    return `${name.slice(0, 1)}${'*'.repeat(Math.max(2, name.length - 1))}@${domain}`;
  };

  const handleVerify = async (event) => {
    event.preventDefault();
    const code = otp.join('');
    if (code.length !== 6) {
      setError('Enter the complete 6-digit code.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      if (mode === 'mfa') {
        const result = await api.verifyMfa(mfaToken, code);
        authStore.saveSession(result);
        navigate(result.user?.role === 'ADMIN' ? '/admin' : '/dashboard', { replace: true });
      } else {
        const result = await api.verifyRegistrationOtp(rawEmail, code);
        navigate('/register/create-password', {
          state: { email: rawEmail, registrationTicket: result.registration_ticket },
        });
      }
    } catch (err) {
      setError(err.message || 'The verification code could not be validated.');
    } finally {
      setBusy(false);
    }
  };

  const handleResend = async () => {
    if (mode !== 'register' || resending) return;
    setResending(true);
    setError('');
    try {
      const result = await api.initiateRegistration(rawEmail);
      setSecondsLeft(result.expires_in_seconds || 300);
      setOtp(['', '', '', '', '', '']);
    } catch (err) {
      setError(err.message || 'Unable to resend the verification code.');
    } finally {
      setResending(false);
    }
  };

  const formattedTimer = `${String(Math.floor(secondsLeft / 60)).padStart(2, '0')}:${String(secondsLeft % 60).padStart(2, '0')}`;
  const isMfa = mode === 'mfa';

  return (
    <div className="auth-split-container">
      <div className="auth-split-wrapper">
        <AuthLeftBanner variant="screen2" />
        <div className="auth-form-card">
          <div className="auth-step-row">
            <span className="auth-step-text">{isMfa ? 'Login • Multi-Factor Authentication' : 'Step 2 of 3 • Email Verification'}</span>
            <div className="auth-step-bars">
              <div className="auth-step-bar active" />
              <div className="auth-step-bar active" />
              <div className="auth-step-bar" />
            </div>
          </div>

          <h2 className="auth-form-title">{isMfa ? 'Verify Your Login' : 'Verify Your Email'}</h2>
          <p className="auth-form-subtitle">
            {isMfa ? 'Enter the 6-digit code sent to your registered email to finish signing in.' : 'We sent a 6-digit code to your institutional email address.'}
          </p>

          <div className="auth-email-box">
            <div className="auth-email-left"><Mail size={16} color="#60A5FA" /><span>{maskEmail(rawEmail)}</span></div>
            <button type="button" className="auth-change-link" onClick={() => navigate(isMfa ? '/login/password' : '/', { state: { email: rawEmail } })}>Change</button>
          </div>

          <form onSubmit={handleVerify}>
            <div className="otp-header-row">
              <span>Enter 6-digit code</span>
              <span style={{ color: '#64748B' }}>Numeric code</span>
            </div>
            <OtpInput value={otp} onChange={setOtp} />
            {error && <p className="auth-login-error" role="alert">{error}</p>}
            <button type="submit" className="btn-primary-gradient" style={{ width: '100%', height: '46px', marginTop: '12px' }} disabled={busy}>
              <span>{busy ? 'Verifying...' : isMfa ? 'Verify & Sign In' : 'Verify Email'}</span>
              <ArrowRight size={16} />
            </button>
          </form>

          <div className="auth-card-footer-actions">
            <div>
              <div>{isMfa ? 'Code expires in' : "Didn't receive the code?"}</div>
              <div style={{ marginTop: '2px' }}>
                {isMfa ? <span className="auth-resend-time">{formattedTimer}</span> : secondsLeft > 0
                  ? <>Resend code in <span className="auth-resend-time">{formattedTimer}</span></>
                  : <button type="button" className="auth-change-link" onClick={handleResend} disabled={resending}>{resending ? 'Sending...' : 'Resend code'}</button>}
              </div>
            </div>
            <Link to="/" className="auth-back-link"><ArrowLeft size={14} /><span>Back to email</span></Link>
          </div>
        </div>
      </div>
    </div>
  );
}
