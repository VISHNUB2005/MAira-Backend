import React from 'react';
import { Link } from 'react-router-dom';
import logoImg from '../../assets/logo.png';

export default function Logo({ badge = null, subtitle = null, size = 'default' }) {
  const isLarge = size === 'large';
  const iconSize = isLarge ? 40 : 30;

  return (
    <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
      <div
        style={{
          position: 'relative',
          width: `${iconSize}px`,
          height: `${iconSize}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <img
          src={logoImg}
          alt="mAIra Logo"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            filter: 'drop-shadow(0 0 10px rgba(56, 189, 248, 0.4))',
          }}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: isLarge ? '1.5rem' : '1.25rem',
              fontWeight: 700,
              letterSpacing: '-0.02em',
              color: '#FFFFFF',
              lineHeight: 1.1,
            }}
          >
            mAIra
          </span>

          {badge && (
            <span
              style={{
                fontSize: '0.65rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                padding: '2px 8px',
                borderRadius: '9999px',
                background: badge === 'ENTERPRISE' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                color: badge === 'ENTERPRISE' ? '#60A5FA' : '#94A3B8',
                border: badge === 'ENTERPRISE' ? '1px solid rgba(59, 130, 246, 0.35)' : '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              {badge}
            </span>
          )}
        </div>

        {subtitle && (
          <span style={{ fontSize: '0.72rem', color: '#64748B', fontWeight: 400, marginTop: '1px' }}>
            {subtitle}
          </span>
        )}
      </div>
    </Link>
  );
}
