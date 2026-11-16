import React from 'react';
import Logo from '../common/Logo';

export default function AuthCard({ children, showLogo = true, logoSize = 'default', footer = null, maxWidth = '460px' }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        padding: '40px 20px',
        background: 'radial-gradient(ellipse at 50% 25%, rgba(29, 78, 216, 0.12) 0%, #070A12 70%)',
        overflow: 'hidden',
      }}
    >
      {/* Background ambient lighting */}
      <div
        style={{
          position: 'absolute',
          top: '15%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '600px',
          height: '400px',
          background: 'radial-gradient(circle, rgba(59, 130, 246, 0.08) 0%, rgba(124, 58, 237, 0.05) 50%, transparent 80%)',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          width: '100%',
          maxWidth: maxWidth,
          background: 'rgba(15, 22, 38, 0.88)',
          border: '1px solid rgba(59, 130, 246, 0.22)',
          borderRadius: '20px',
          padding: '36px 36px',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.7), 0 0 30px rgba(59, 130, 246, 0.1)',
          position: 'relative',
          zIndex: 10,
        }}
      >
        {showLogo && (
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '22px' }}>
            <Logo size={logoSize} />
          </div>
        )}

        {children}
      </div>

      {footer && (
        <div
          style={{
            marginTop: '36px',
            textAlign: 'center',
            fontSize: '0.74rem',
            color: '#64748B',
            zIndex: 10,
          }}
        >
          {footer}
        </div>
      )}
    </div>
  );
}
