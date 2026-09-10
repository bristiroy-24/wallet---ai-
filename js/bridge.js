/**
 * js/bridge.js
 * ─────────────
 * Backend / Offline bridge.
 * All data operations route through these functions.
 * Online → real API calls. Offline → LocalStorage.
 */
'use strict';

// ── Category & account ID caches ─────────────────────────────────────────────
let _categoryCache = null;
let _accountCache  = null;

function normaliseApiTransaction(t) {
  return {
    id:            t.id,
    type:          (t.type || 'EXPENSE').toLowerCase(),
    amount:        parseFloat(t.amount),
    category:      t.category_name || 'Other',
    subcategory:   null,
    description:   t.note || t.category_name || 'Transaction',
    paymentMethod: t.account_name || 'Card',
    date:          (t.date || '').slice(0, 10),
    time:          (t.date || '').slice(11, 16),
    tags:          t.tags || [],
    createdAt:     t.created_at || t.date,
  };
}

function handleApiError(e) {
  if (e.message === 'SESSION_EXPIRED') {
    setState({ isOnline: false, currentUser: null });
    auth.removeToken();
    showAuthModal();
    showToast('Session expired. Please log in again.', 'error');
  }
}

async function resolveCategoryId(categoryName) {
  if (!_categoryCache) {
    try { _categoryCache = await apiRequest('/categories/'); } catch(e) { return null; }
  }
  const flat = [];
  (_categoryCache || []).forEach(c => { flat.push(c); (c.subcategories || []).forEach(s => flat.push(s)); });
  const match = flat.find(c => c.name.toLowerCase() === categoryName.toLowerCase());
  return match ? match.id : null;
}

async function resolveAccountId(paymentMethodName) {
  if (!_accountCache) {
    try { _accountCache = await apiFetchAccounts(); } catch(e) { return null; }
  }
  const match = (_accountCache || []).find(a => a.name.toLowerCase() === paymentMethodName.toLowerCase());
  return match ? match.id : null;
}

// ── Transactions ──────────────────────────────────────────────────────────────

async function loadTransactions() {
  if (state.isOnline) {
    try {
      const txns = (await apiFetchTransactions()).map(normaliseApiTransaction);
      setState({ transactions: txns });
      return;
    } catch(e) { handleApiError(e); }
  }
}

async function saveTransaction(data) {
  if (state.isOnline) {
    try {
      const payload = {
        amount:      parseFloat(data.amount),
        type:        data.type.toUpperCase(),
        note:        data.description || data.category,
        tags:        data.tags || [],
        date:        `${data.date}T${data.time || '00:00'}:00+00:00`,
        category_id: await resolveCategoryId(data.category),
        account_id:  await resolveAccountId(data.paymentMethod),
      };
      const created = normaliseApiTransaction(await apiCreateTransaction(payload));
      setState({ transactions: [created, ...state.transactions] });
      return created;
    } catch(e) { handleApiError(e); }
  }
  return addTransactionLocal(data);
}

async function removeTransaction(id) {
  if (state.isOnline) {
    try { await apiDeleteTransaction(id); } catch(e) {}
  }
  setState({ transactions: state.transactions.filter(t => t.id !== id) });
}

function addTransactionLocal(data) {
  const txn = {
    id: generateId(), type: data.type || 'expense', amount: parseFloat(data.amount),
    category: data.category || 'Other', subcategory: data.subcategory || null,
    description: data.description || data.category, paymentMethod: data.paymentMethod || 'Cash',
    date: data.date || new Date().toISOString().split('T')[0],
    time: data.time || new Date().toTimeString().slice(0, 5),
    tags: data.tags || [], createdAt: new Date().toISOString(),
  };
  setState({ transactions: [txn, ...state.transactions] });
  return txn;
}

// ── Accounts ──────────────────────────────────────────────────────────────────

async function loadAccounts() {
  if (state.isOnline) {
    try {
      const accounts = (await apiFetchAccounts()).map(a => ({
        id: a.id, name: a.name, balance: a.balance,
        color: a.color || CONFIG.defaultBankColor, type: a.type,
      }));
      setState({ bankAccounts: accounts });
    } catch(e) { handleApiError(e); }
  }
}

async function saveAccount(data) {
  if (state.isOnline) {
    try {
      const created = await apiCreateAccount({
        name: data.name, balance: parseFloat(data.balance || 0), type: 'BANK', color: data.color,
      });
      const acc = { id: created.id, name: created.name, balance: created.balance, color: created.color };
      setState({ bankAccounts: [...state.bankAccounts, acc] });
      return acc;
    } catch(e) { handleApiError(e); }
  }
  const acc = { id: generateId(), name: data.name, balance: parseFloat(data.balance || 0), color: data.color };
  setState({ bankAccounts: [...state.bankAccounts, acc] });
  return acc;
}

// ── Dashboard & insights ──────────────────────────────────────────────────────

async function loadDashboardData() {
  if (state.isOnline) {
    try { return await apiFetchDashboard(); } catch(e) { handleApiError(e); }
  }
  return null;
}

async function dismissInsight(id) {
  if (state.isOnline) {
    try { await apiRequest(`/analytics/insights/${id}`, { method: 'DELETE' }); } catch(e) {}
  }
}
