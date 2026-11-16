const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

const ACCESS_KEY = 'maira_access_token';
const REFRESH_KEY = 'maira_refresh_token';
const USER_KEY = 'maira_user';

export const authStore = {
  getAccessToken: () => sessionStorage.getItem(ACCESS_KEY),
  getRefreshToken: () => sessionStorage.getItem(REFRESH_KEY),
  getUser: () => {
    try { return JSON.parse(sessionStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  },
  saveSession: (data) => {
    sessionStorage.setItem(ACCESS_KEY, data.access_token);
    sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
    if (data.user) sessionStorage.setItem(USER_KEY, JSON.stringify(data.user));
  },
  clear: () => {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    sessionStorage.removeItem(USER_KEY);
  },
};

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(', ')
      : (typeof detail === 'string' ? detail : payload?.message);
    throw new Error(message || `Request failed (${response.status})`);
  }
  return payload;
}

async function refreshSession() {
  const refreshToken = authStore.getRefreshToken();
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    authStore.clear();
    return false;
  }
  const data = await response.json();
  authStore.saveSession({ ...data, user: authStore.getUser() });
  return true;
}

export async function apiRequest(path, options = {}) {
  const { auth = false, retry = true, ...requestOptions } = options;
  const headers = {
    'Content-Type': 'application/json',
    ...(requestOptions.headers || {}),
  };
  if (auth) {
    const token = authStore.getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestOptions,
    headers,
  });

  if (response.status === 401 && auth && retry && await refreshSession()) {
    const token = authStore.getAccessToken();
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      headers: { ...headers, Authorization: `Bearer ${token}` },
    });
  }
  return parseResponse(response);
}

export const api = {
  identify: (email) => apiRequest('/api/v1/auth/identify', {
    method: 'POST', body: JSON.stringify({ email }),
  }),
  initiateRegistration: (email) => apiRequest('/api/v1/auth/register/initiate', {
    method: 'POST', body: JSON.stringify({ email }),
  }),
  verifyRegistrationOtp: (email, otp) => apiRequest('/api/v1/auth/register/verify-otp', {
    method: 'POST', body: JSON.stringify({ email, otp }),
  }),
  setRegistrationPassword: (registrationTicket, password, confirmPassword) => apiRequest('/api/v1/auth/register/set-password', {
    method: 'POST',
    body: JSON.stringify({
      registration_ticket: registrationTicket,
      password,
      confirm_password: confirmPassword,
    }),
  }),
  login: (email, password) => apiRequest('/api/v1/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }),
  verifyMfa: (mfaToken, code) => apiRequest('/api/v1/auth/mfa/verify', {
    method: 'POST', body: JSON.stringify({ mfa_token: mfaToken, code }),
  }),
  profile: () => apiRequest('/api/v1/users/me', { auth: true }),
  logout: () => apiRequest('/api/v1/auth/logout', {
    method: 'POST', auth: true, body: JSON.stringify({ all_sessions: false }),
  }),
  listChats: () => apiRequest('/api/v1/chat/sessions', { auth: true }),
  createChat: (title = 'New Conversation') => apiRequest('/api/v1/chat/sessions', {
    method: 'POST', auth: true, body: JSON.stringify({ title }),
  }),
  getChat: (sessionId) => apiRequest(`/api/v1/chat/sessions/${sessionId}`, { auth: true }),
  deleteChat: (sessionId) => apiRequest(`/api/v1/chat/sessions/${sessionId}`, {
    method: 'DELETE', auth: true,
  }),
  sendMessage: (sessionId, content) => apiRequest(`/api/v1/chat/sessions/${sessionId}/messages`, {
    method: 'POST', auth: true, body: JSON.stringify({ content }),
  }),
  adminAnalytics: () => apiRequest('/api/v1/admin/users/analytics', { auth: true }),
  adminStudents: () => apiRequest('/api/v1/admin/users/students', { auth: true }),
  createStudent: (email, name, userType) => apiRequest('/api/v1/admin/users/students', {
    method: 'POST', auth: true, body: JSON.stringify({ email, name: name || null, user_type: userType }),
  }),
};
