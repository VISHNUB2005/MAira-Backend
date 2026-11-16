import React from 'react';
import Logo from '../common/Logo';
import { Sparkles, MessageSquare } from 'lucide-react';

export default function AuthLeftBanner({ variant = 'screen2' }) {
  const isScreen2 = variant === 'screen2';

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '40px 48px',
        maxWidth: '560px',
      }}
    >
      <div>
        <Logo
          badge={isScreen2 ? 'AI Workspace' : null}
          subtitle={!isScreen2 ? 'Intelligent Workspace' : null}
          size="large"
        />

        <div style={{ marginTop: '56px' }}>
          <h1
            style={{
              fontSize: '2.75rem',
              fontWeight: 800,
              lineHeight: 1.15,
              color: '#FFFFFF',
              letterSpacing: '-0.03em',
              marginBottom: '20px',
            }}
          >
            Your intelligent<br />
            workspace,<br />
            powered by AI.
          </h1>

          <p
            style={{
              fontSize: '1.02rem',
              color: '#94A3B8',
              lineHeight: 1.6,
              maxWidth: '460px',
            }}
          >
            {isScreen2
              ? "Streamline your team's knowledge, automate repetitive workflows, and collaborate seamlessly with autonomous conversational agents designed for everyday productivity."
              : "Ground natural conversational intelligence across documents, collaborative data, and everyday creative workflows with effortless simplicity."}
          </p>
        </div>
      </div>

      <div style={{ marginTop: '48px' }}>
        {isScreen2 ? (
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(26, 36, 60, 0.5))',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              borderRadius: '16px',
              padding: '22px 24px',
              backdropFilter: 'blur(16px)',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.4)',
              display: 'flex',
              gap: '16px',
              alignItems: 'flex-start',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'rgba(59, 130, 246, 0.2)',
                border: '1px solid rgba(59, 130, 246, 0.35)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                color: '#60A5FA',
              }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <h4 style={{ fontSize: '0.92rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '6px' }}>
                Instant setup for high-performing teams
              </h4>
              <p style={{ fontSize: '0.82rem', color: '#94A3B8', lineHeight: 1.5 }}>
                Verify your corporate account to connect project repositories, documents, and messaging channels in one unified conversational hub.
              </p>
            </div>
          </div>
        ) : (
          <div
            style={{
              background: 'linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(26, 36, 60, 0.5))',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              borderRadius: '16px',
              padding: '22px 24px',
              backdropFilter: 'blur(16px)',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.72rem',
                fontWeight: 600,
                color: '#60A5FA',
                letterSpacing: '0.04em',
                marginBottom: '10px',
              }}
            >
              <span className="status-dot blue" style={{ width: '6px', height: '6px' }} />
              CONVERSATIONAL AI PREVIEW
            </div>
            <p style={{ fontSize: '0.86rem', color: '#E2E8F0', fontStyle: 'normal', lineHeight: 1.5, marginBottom: '14px' }}>
              <strong style={{ color: '#93C5FD' }}>mAIra Assistant:</strong> &ldquo;I've synthesized your team's project notes and prepared the upcoming briefing draft whenever you're ready.&rdquo;
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span
                style={{
                  fontSize: '0.72rem',
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  background: 'rgba(30, 41, 59, 0.8)',
                  color: '#94A3B8',
                  border: '1px solid rgba(51, 65, 85, 0.6)',
                }}
              >
                Document Insights
              </span>
              <span
                style={{
                  fontSize: '0.72rem',
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  background: 'rgba(30, 41, 59, 0.8)',
                  color: '#94A3B8',
                  border: '1px solid rgba(51, 65, 85, 0.6)',
                }}
              >
                Workflow Automation
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
