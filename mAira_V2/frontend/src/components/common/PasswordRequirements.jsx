import React from 'react';
import { CheckCircle2, Circle } from 'lucide-react';

export default function PasswordRequirements({ password = '', variant = 'compact' }) {
  const hasMinLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);

  if (variant === 'two-column') {
    // Screen 6 layout
    return (
      <div
        style={{
          background: 'rgba(13, 19, 34, 0.6)',
          border: '1px solid #1E293B',
          borderRadius: '10px',
          padding: '12px 14px',
          margin: '14px 0',
          fontSize: '0.78rem',
        }}
      >
        <div style={{ color: '#94A3B8', fontWeight: 500, marginBottom: '8px' }}>
          Password must contain:
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasMinLength ? '#34D399' : '#64748B' }}>
            {hasMinLength ? <CheckCircle2 size={13} color="#34D399" /> : <Circle size={13} />}
            <span>At least 8 characters</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasUpper ? '#34D399' : '#64748B' }}>
            {hasUpper ? <CheckCircle2 size={13} color="#34D399" /> : <Circle size={13} />}
            <span>One uppercase letter</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasLower ? '#34D399' : '#64748B' }}>
            {hasLower ? <CheckCircle2 size={13} color="#34D399" /> : <Circle size={13} />}
            <span>One lowercase letter</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasNumber ? '#34D399' : '#64748B' }}>
            {hasNumber ? <CheckCircle2 size={13} color="#34D399" /> : <Circle size={13} />}
            <span>One number</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: hasSpecial ? '#34D399' : '#64748B' }}>
            {hasSpecial ? <CheckCircle2 size={13} color="#34D399" /> : <Circle size={13} />}
            <span>One special character</span>
          </div>
        </div>
      </div>
    );
  }

  // Screen 3 layout
  const hasUpperLower = hasUpper && hasLower;
  const hasNumOrSym = hasNumber || hasSpecial;

  return (
    <div style={{ margin: '14px 0', fontSize: '0.8rem' }}>
      <div
        style={{
          color: '#64748B',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          fontSize: '0.7rem',
          marginBottom: '8px',
        }}
      >
        PASSWORD REQUIREMENTS
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: hasMinLength ? '#34D399' : '#64748B' }}>
          {hasMinLength ? <CheckCircle2 size={14} color="#34D399" /> : <Circle size={14} />}
          <span>At least 8 characters</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: hasUpperLower ? '#34D399' : '#64748B' }}>
          {hasUpperLower ? <CheckCircle2 size={14} color="#34D399" /> : <Circle size={14} />}
          <span>Upper &amp; lowercase letters</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: hasNumOrSym ? '#34D399' : '#64748B' }}>
          {hasNumOrSym ? <CheckCircle2 size={14} color="#34D399" /> : <Circle size={14} />}
          <span>At least one number or symbol</span>
        </div>
      </div>
    </div>
  );
}
