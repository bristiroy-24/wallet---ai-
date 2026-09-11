/**
 * api.js – WalletAI Backend Client
 * ─────────────────────────────────
 * Plain script (no ES modules) – loaded before app.js.
 * Handles all HTTP communication with the FastAPI backend.
 * Falls back gracefully if the backend is unreachable.
 */

'use strict';

const API_BASE_URL = "https://wallet-ai-04ej.onrender.com";

/* ── Token management ─────────────────────────────────── */
const auth = {
  getToken:        () => localStorage.getItem('walletai_token'),
  setToken:        (t) => localStorage.setItem('walletai_token', t),
  removeToken:     () => localStorage.removeItem('walletai_token'),
  isAuthenticated: () => !!localStorage.getItem('walletai_token'),
};

/* ── Central fetch wrapper ────────────────────────────── */
async function apiRequest(endpoint, options = {}) {
  const token = auth.getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

  if (response.status === 401) {
    auth.removeToken();
    throw new Error('SESSION_EXPIRED');
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

/* ── Auth endpoints ───────────────────────────────────── */
async function apiLogin(email, password) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  auth.setToken(data.access_token);
  return data.user;
}

async function apiRegister(email, password, full_name) {
  await apiRequest('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, full_name }),
  });
  return apiLogin(email, password);
}

/* ── Transactions ─────────────────────────────────────── */
async function apiFetchTransactions() {
  return apiRequest('/transactions/?limit=200');
}

async function apiCreateTransaction(payload) {
  return apiRequest('/transactions/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

async function apiDeleteTransaction(id) {
  return apiRequest(`/transactions/${id}`, { method: 'DELETE' });
}

/* ── Accounts ─────────────────────────────────────────── */
async function apiFetchAccounts() {
  return apiRequest('/accounts/');
}

async function apiCreateAccount(payload) {
  return apiRequest('/accounts/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/* ── Analytics ────────────────────────────────────────── */
async function apiFetchDashboard() {
  return apiRequest('/analytics/dashboard');
}

async function apiFetchInsights() {
  return apiRequest('/analytics/insights');
}

async function apiRefreshInsights() {
  return apiRequest('/analytics/insights/refresh', { method: 'POST' });
}

/* ── AI magic input ───────────────────────────────────── */
async function apiMagicParse(prompt) {
  return apiRequest('/transactions/magic-input', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });
}

/* ── Receipt OCR ──────────────────────────────────────── */
async function apiScanReceipt(file) {
  const token = auth.getToken();
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE_URL}/transactions/scan-receipt`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}

/* ── Backend health check ─────────────────────────────── */
async function checkBackendAvailable() {
  try {
    // Use Promise.race for timeout — works in all browsers including file://
    const timeout = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('timeout')), 3000)
    );
    const fetchPromise = fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      cache: 'no-cache',
    });
    const res = await Promise.race([fetchPromise, timeout]);
    return res.ok;
  } catch {
    return false;
  }
}
