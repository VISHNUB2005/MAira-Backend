import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Logo from '../components/common/Logo';
import logoImg from '../assets/logo.png';
import {
  LayoutDashboard,
  MessageSquare,
  History,
  FolderClosed,
  Settings,
  Bell,
  User,
  Paperclip,
  ArrowUp,
  LogOut,
  X,
  Check,
} from 'lucide-react';
import '../styles/dashboard.css';
import { api, authStore } from '../services/api';

export default function UserDashboardPage() {
  const navigate = useNavigate();
  const [activeNav, setActiveNav] = useState('Dashboard');
  const [promptText, setPromptText] = useState('');
  const [toastMessage, setToastMessage] = useState(null);
  const [profile, setProfile] = useState(authStore.getUser());
  const [conversations, setConversations] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Popovers & Modals
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  const fileInputRef = useRef(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  useEffect(() => {
    let mounted = true;
    const loadWorkspace = async () => {
      try {
        const [me, history] = await Promise.all([api.profile(), api.listChats()]);
        if (!mounted) return;
        setProfile(me);
        setConversations(history.conversations || []);
      } catch (error) {
        if (mounted) showToast(error.message || 'Unable to load your workspace.');
      }
    };
    loadWorkspace();
    return () => { mounted = false; };
  }, []);

  const handleFileSelect = (event) => {
    event.target.value = '';
    showToast('File uploads are not available in Phase 1. Please send a text prompt.');
  };

  const handleSendClick = async (event) => {
    event?.preventDefault();
    const content = promptText.trim();
    if (!content || sending) {
      document.getElementById('user-chat-input')?.focus();
      return;
    }
    setSending(true);
    try {
      let sessionId = activeSessionId;
      if (!sessionId) {
        const created = await api.createChat();
        sessionId = created.chat_session_id;
        setActiveSessionId(sessionId);
        setConversations((items) => [created, ...items]);
      }
      setMessages((items) => [...items, {
        message_id: `local-${Date.now()}`,
        sender: 'USER',
        content,
        status: 'COMPLETED',
      }]);
      setPromptText('');
      const response = await api.sendMessage(sessionId, content);
      setMessages((items) => [...items, response]);
      const history = await api.listChats();
      setConversations(history.conversations || []);
    } catch (error) {
      showToast(error.message || 'Your message could not be sent.');
    } finally {
      setSending(false);
    }
  };

  const handleNewChat = async () => {
    setPromptText('');
    setMessages([]);
    setActiveNav('New Chat');
    try {
      const created = await api.createChat();
      setActiveSessionId(created.chat_session_id);
      setConversations((items) => [created, ...items.filter((item) => item.chat_session_id !== created.chat_session_id)]);
      showToast('New conversation created.');
      document.getElementById('user-chat-input')?.focus();
    } catch (error) {
      showToast(error.message || 'Unable to create a new conversation.');
    } finally {
      setActiveNav('Dashboard');
    }
  };

  const openConversation = async (conversation) => {
    setLoadingHistory(true);
    try {
      const detail = await api.getChat(conversation.chat_session_id);
      setActiveSessionId(conversation.chat_session_id);
      setMessages(detail.messages || []);
      setShowHistoryModal(false);
      setActiveNav('Dashboard');
    } catch (error) {
      showToast(error.message || 'Unable to open this conversation.');
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Clear the local session even if the network is unavailable.
    } finally {
      authStore.clear();
      navigate('/', { replace: true });
    }
  };

  return (
    <div
      className="user-dashboard-layout"
      onClick={() => {
        // Close open dropdowns when clicking outside
        if (showNotifications) setShowNotifications(false);
        if (showUserMenu) setShowUserMenu(false);
      }}
    >
      {/* Hidden real file input */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid rgba(59, 130, 246, 0.4)',
            color: '#FFFFFF',
            padding: '10px 18px',
            borderRadius: '8px',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.6)',
            zIndex: 10000,
            animation: 'fadeInMsg 0.2s ease',
          }}
        >
          <Check size={14} color="#34D399" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Sidebar */}
      <aside className="user-sidebar">
        <div>
          <Logo size="default" />

          <nav className="user-nav-list">
            <div
              className={`user-nav-item ${activeNav === 'Dashboard' ? 'active' : ''}`}
              onClick={() => setActiveNav('Dashboard')}
            >
              <LayoutDashboard size={17} />
              <span>Dashboard</span>
            </div>

            <div
              className={`user-nav-item ${activeNav === 'New Chat' ? 'active' : ''}`}
              onClick={handleNewChat}
            >
              <MessageSquare size={17} />
              <span>New Chat</span>
            </div>

            <div
              className={`user-nav-item ${activeNav === 'Conversation History' ? 'active' : ''}`}
              onClick={() => setShowHistoryModal(true)}
            >
              <History size={17} />
              <span>Conversation History</span>
            </div>

            <div
              className={`user-nav-item ${activeNav === 'Files' ? 'active' : ''}`}
              onClick={() => fileInputRef.current?.click()}
            >
              <FolderClosed size={17} />
              <span>Files</span>
            </div>

            <div
              className={`user-nav-item ${activeNav === 'Settings' ? 'active' : ''}`}
              onClick={() => setShowSettingsModal(true)}
            >
              <Settings size={17} />
              <span>Settings</span>
            </div>
          </nav>
        </div>

        {/* User Profile Card */}
        <div className="user-profile-bottom">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="user-avatar-circle">{(profile?.email || "U").charAt(0).toUpperCase()}</div>
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#FFFFFF' }}>{profile?.email?.split("@")[0] || "User"}</div>
              <div style={{ fontSize: '0.7rem', color: '#64748B' }}>{profile?.email || ""}</div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            title="Log out"
            style={{ color: '#64748B', background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main Area */}
      <main className="user-main-area">
        {/* Topbar */}
        <header className="user-topbar">
          <div className="user-greeting-left">
            <div
              style={{
                width: '30px',
                height: '30px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <img
                src={logoImg}
                alt="mAIra"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  filter: 'drop-shadow(0 0 8px rgba(56, 189, 248, 0.4))',
                }}
              />
            </div>
            <div>
              <h2 className="user-greeting-title">Good to see you, {profile?.email?.split("@")[0] || "there"}</h2>
              <div className="user-greeting-sub">How can mAIra help you today?</div>
            </div>
          </div>

          <div className="user-topbar-right" style={{ position: 'relative' }}>
            {/* Bell Button */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowNotifications(!showNotifications);
                  setShowUserMenu(false);
                }}
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '8px',
                  border: '1px solid #1E293B',
                  background: 'rgba(17, 24, 39, 0.6)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: showNotifications ? '#FFFFFF' : '#94A3B8',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                title="Notifications"
              >
                <Bell size={16} />
              </button>

              {/* Notifications Popover */}
              {showNotifications && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    position: 'absolute',
                    top: '44px',
                    right: 0,
                    width: '280px',
                    background: '#0F1626',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    borderRadius: '12px',
                    padding: '14px',
                    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)',
                    zIndex: 100,
                  }}
                >
                  <div style={{ fontSize: '0.86rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px' }}>
                    Notifications
                  </div>
                  <div style={{ fontSize: '0.76rem', color: '#94A3B8', padding: '8px', background: 'rgba(17, 24, 39, 0.5)', borderRadius: '6px' }}>
                    No new notifications • All systems operational.
                  </div>
                </div>
              )}
            </div>

            {/* User Avatar Button */}
            <div style={{ position: 'relative' }}>
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  setShowUserMenu(!showUserMenu);
                  setShowNotifications(false);
                }}
                style={{
                  width: '34px',
                  height: '34px',
                  borderRadius: '50%',
                  background: '#2563EB',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#FFFFFF',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                }}
                title="Profile Menu"
              >
                <User size={16} />
              </div>

              {/* User Dropdown */}
              {showUserMenu && (
                <div
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    position: 'absolute',
                    top: '44px',
                    right: 0,
                    width: '220px',
                    background: '#0F1626',
                    border: '1px solid rgba(59, 130, 246, 0.3)',
                    borderRadius: '12px',
                    padding: '12px',
                    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)',
                    zIndex: 100,
                  }}
                >
                  <div style={{ fontSize: '0.86rem', fontWeight: 600, color: '#FFFFFF' }}>{profile?.email?.split("@")[0] || "User"}</div>
                  <div style={{ fontSize: '0.72rem', color: '#64748B', marginBottom: '10px' }}>{profile?.email || ""}</div>
                  <div style={{ borderTop: '1px solid #1E293B', paddingTop: '8px' }}>
                    <button
                      onClick={handleLogout}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        background: 'none',
                        border: 'none',
                        color: '#EF4444',
                        fontSize: '0.78rem',
                        cursor: 'pointer',
                        padding: '6px 0',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                    >
                      <LogOut size={13} />
                      <span>Log Out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Clean Hero Query Section */}
        <section className="user-hero-container">
          <h1 className="user-hero-title">How can I help you today?</h1>
          <p className="user-hero-sub">
            Ask a question, upload a file, or synthesize complex research across your organization.
          </p>

          {messages.length > 0 && (
            <div style={{ width: '100%', maxWidth: '860px', margin: '0 auto 22px', display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '42vh', overflowY: 'auto' }}>
              {messages.map((message) => (
                <div key={message.message_id} style={{ alignSelf: message.sender === 'USER' ? 'flex-end' : 'flex-start', maxWidth: '85%', padding: '13px 16px', borderRadius: '12px', background: message.sender === 'USER' ? 'rgba(37,99,235,0.18)' : 'rgba(15,22,38,0.92)', border: '1px solid #1E293B', color: '#E2E8F0', whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>
                  <div style={{ fontSize: '0.68rem', color: '#60A5FA', marginBottom: '5px' }}>{message.sender === 'USER' ? 'You' : 'mAIra'}</div>
                  {message.content}
                </div>
              ))}
            </div>
          )}

          {/* Chat Box */}
          <form className="user-chat-box" onSubmit={handleSendClick}>
            <textarea
              id="user-chat-input"
              className="user-chat-textarea"
              placeholder="Ask mAIra anything..."
              rows={2}
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendClick();
                }
              }}
            />

            <div className="user-chat-controls">
              <div className="chat-controls-left">
                <button
                  type="button"
                  className="chat-control-btn"
                  onClick={() => fileInputRef.current?.click()}
                  title="Attach file from device"
                >
                  <Paperclip size={14} />
                  <span>Attach file</span>
                </button>
              </div>

              <div className="chat-controls-right">
                <button type="submit" className="chat-send-btn" title="Send Query" disabled={sending}>
                  <ArrowUp size={16} strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </form>
        </section>
      </main>

      {/* Conversation History Modal */}
      {showHistoryModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
          onClick={() => setShowHistoryModal(false)}
        >
          <div
            style={{
              width: '500px',
              background: '#0F1626',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '16px',
              padding: '28px',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <History size={20} color="#60A5FA" />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF' }}>Conversation History</h3>
              </div>
              <button
                onClick={() => setShowHistoryModal(false)}
                style={{ color: '#64748B', cursor: 'pointer', background: 'none', border: 'none' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ maxHeight: '360px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {loadingHistory && <div style={{ color: '#94A3B8', padding: '18px' }}>Loading conversation...</div>}
              {!loadingHistory && conversations.length === 0 && (
                <div style={{ textAlign: 'center', padding: '32px 16px', color: '#94A3B8' }}>
                  <div style={{ fontSize: '0.9rem', color: '#CBD5E1', marginBottom: '4px' }}>No Saved Conversations Yet</div>
                  <div style={{ fontSize: '0.76rem', color: '#64748B' }}>Start a conversation to build your workspace history.</div>
                </div>
              )}
              {conversations.map((conversation) => (
                <button key={conversation.chat_session_id} type="button" onClick={() => openConversation(conversation)} style={{ textAlign: 'left', padding: '12px', borderRadius: '8px', border: '1px solid #1E293B', background: 'rgba(17,24,39,0.65)', color: '#E2E8F0', cursor: 'pointer' }}>
                  <div style={{ fontSize: '0.84rem', fontWeight: 600 }}>{conversation.title || 'Conversation'}</div>
                  <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>{new Date(conversation.updated_at).toLocaleString()}</div>
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                className="btn-secondary-outline"
                onClick={() => setShowHistoryModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettingsModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
          }}
          onClick={() => setShowSettingsModal(false)}
        >
          <div
            style={{
              width: '460px',
              background: '#0F1626',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '16px',
              padding: '28px',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Settings size={20} color="#60A5FA" />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF' }}>Workspace Settings</h3>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                style={{ color: '#64748B', cursor: 'pointer', background: 'none', border: 'none' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.84rem' }}>
              <div>
                <label style={{ display: 'block', color: '#94A3B8', marginBottom: '6px' }}>Default Model</label>
                <select
                  style={{
                    width: '100%',
                    height: '38px',
                    background: '#111827',
                    border: '1px solid #1E293B',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    padding: '0 12px',
                  }}
                  defaultValue="mAIra Ultra 2.5"
                >
                  <option>mAIra Ultra 2.5</option>
                  <option>mAIra 2.5 Pro</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', color: '#94A3B8', marginBottom: '6px' }}>Interface Theme</label>
                <select
                  style={{
                    width: '100%',
                    height: '38px',
                    background: '#111827',
                    border: '1px solid #1E293B',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    padding: '0 12px',
                  }}
                  defaultValue="Midnight Dark (Default)"
                >
                  <option>Midnight Dark (Default)</option>
                  <option>Cyber Blue Contrast</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px' }}>
              <button
                className="btn-primary-gradient"
                onClick={() => {
                  showToast('Settings saved.');
                  setShowSettingsModal(false);
                }}
                style={{ padding: '8px 20px', borderRadius: '8px' }}
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
