import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Layers, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export default function ScreenSwitcher() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const screens = [
    { id: 'p1-login', name: '1. Landing / Login', path: '/' },
    { id: 'p1-register', name: '1B. Landing / Register', path: '/?tab=register' },
    { id: 'p2-verify', name: '2. Register Email OTP', path: '/register/verify' },
    { id: 'p3-password', name: '3. Register Password', path: '/register/create-password' },
    { id: 'p4a-modal', name: '4A. Modal Email Verify', path: '/verify-modal' },
    { id: 'p4b-recovery', name: '4B. Forgot Password Method', path: '/forgot-password' },
    { id: 'p5-rec-otp', name: '5. Recovery Code Verify', path: '/recovery/verify-code' },
    { id: 'p6-rec-pass', name: '6. Recovery New Password', path: '/recovery/new-password' },
    { id: 'p7-rec-done', name: '7. Password Updated Success', path: '/recovery/success' },
    { id: 'p8-admin', name: '8. Enterprise Admin Dashboard', path: '/admin' },
    { id: 'p9-dashboard', name: '9. Authenticated Workspace', path: '/dashboard' },
  ];

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: 'rgba(8, 12, 20, 0.94)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid rgba(59, 130, 246, 0.25)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        fontFamily: 'Inter, sans-serif',
      }}
    >
      <div
        style={{
          maxWidth: '1440px',
          margin: '0 auto',
          padding: '6px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.78rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 8px',
              borderRadius: '4px',
              background: 'linear-gradient(135deg, rgba(37,99,235,0.3), rgba(124,58,237,0.3))',
              color: '#93C5FD',
              fontWeight: 700,
              fontSize: '0.74rem',
              letterSpacing: '0.04em',
            }}
          >
            <Layers size={13} />
            FIGMA FRAMES
          </span>
          <span style={{ color: '#64748B', display: collapsed ? 'none' : 'inline' }}>
            Jump to any verified Figma artboard:
          </span>
        </div>

        {!collapsed && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              overflowX: 'auto',
              padding: '2px 8px',
            }}
          >
            {screens.map((s) => {
              const currentFull = location.pathname + location.search;
              const isActive = s.path === currentFull || (s.path === '/' && location.pathname === '/' && !location.search && s.id === 'p1-login');
              return (
                <button
                  key={s.id}
                  onClick={() => navigate(s.path)}
                  style={{
                    padding: '3px 10px',
                    borderRadius: '6px',
                    fontSize: '0.74rem',
                    fontWeight: isActive ? 600 : 400,
                    whiteSpace: 'nowrap',
                    background: isActive ? 'linear-gradient(135deg, #2563EB, #7C3AED)' : 'rgba(30, 41, 59, 0.6)',
                    color: isActive ? '#FFFFFF' : '#94A3B8',
                    border: isActive ? '1px solid rgba(147, 197, 253, 0.4)' : '1px solid rgba(51, 65, 85, 0.4)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {s.name}
                </button>
              );
            })}
          </div>
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          style={{
            padding: '4px 8px',
            borderRadius: '4px',
            background: 'rgba(30, 41, 59, 0.5)',
            color: '#94A3B8',
            border: '1px solid rgba(51, 65, 85, 0.6)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '0.7rem',
          }}
        >
          {collapsed ? <><ChevronDown size={14} /> Show Nav</> : <><ChevronUp size={14} /> Minimize</>}
        </button>
      </div>
    </div>
  );
}
