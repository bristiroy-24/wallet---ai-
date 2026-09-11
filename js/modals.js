/**
 * js/modals.js
 * ─────────────
 * All modal initialisation: auth, bank account, transaction detail.
 */
'use strict';

// ── Generic modal open/close ──────────────────────────────────────────────────

function openModal(id)  { const e = document.getElementById(id); if (e) { e.classList.remove('hidden'); document.body.style.overflow = 'hidden'; } }
function closeModal(id) { const e = document.getElementById(id); if (e) { e.classList.add('hidden'); document.body.style.overflow = ''; } }

// ── Auth modal ────────────────────────────────────────────────────────────────

function showAuthModal() { const m = document.getElementById('modal-auth'); if (m) m.classList.remove('hidden'); }
function hideAuthModal() { const m = document.getElementById('modal-auth'); if (m) m.classList.add('hidden'); }

function initAuthModal() {
  // Tab switching
  document.getElementById('tab-login')?.addEventListener('click', () => {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('tab-login').classList.add('active');
    document.getElementById('tab-register').classList.remove('active');
  });
  document.getElementById('tab-register')?.addEventListener('click', () => {
    document.getElementById('register-form').classList.remove('hidden');
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('tab-register').classList.add('active');
    document.getElementById('tab-login').classList.remove('active');
  });

  // Login
  document.getElementById('login-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const errEl    = document.getElementById('login-error');
    const btn      = e.target.querySelector('button[type=submit]');
    errEl.classList.add('hidden');
    btn.disabled = true; btn.textContent = '⏳ Logging in…';
    try {
      const user = await apiLogin(email, password);
      setState({ isOnline: true, currentUser: user });
      _categoryCache = null; _accountCache = null;
      hideAuthModal(); showToast(`Welcome back, ${user.full_name || user.email}! 👋`, 'success');
      await loadTransactions(); await loadAccounts();
      updateOnlineStatus(true); renderDashboard();
    } catch(err) {
      errEl.textContent = err.message === 'SESSION_EXPIRED' ? 'Invalid credentials.' : err.message;
      errEl.classList.remove('hidden');
    } finally { btn.disabled = false; btn.textContent = '🔑 Login'; }
  });

  // Register
  document.getElementById('register-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const email    = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    const name     = document.getElementById('register-name').value.trim();
    const errEl    = document.getElementById('register-error');
    const btn      = e.target.querySelector('button[type=submit]');
    errEl.classList.add('hidden');
    btn.disabled = true; btn.textContent = '⏳ Creating account…';
    try {
      const user = await apiRegister(email, password, name);
      setState({ isOnline: true, currentUser: user });
      _categoryCache = null; _accountCache = null;
      hideAuthModal(); showToast(`Account created! Welcome ${name || email} 🎉`, 'success');
      await loadTransactions(); await loadAccounts();
      updateOnlineStatus(true); renderDashboard();
    } catch(err) {
      errEl.textContent = err.message; errEl.classList.remove('hidden');
    } finally { btn.disabled = false; btn.textContent = '🚀 Create Account'; }
  });

  // Skip / offline
  document.getElementById('skip-auth-btn')?.addEventListener('click', () => {
    hideAuthModal(); showToast('Running in offline mode. Data saved locally.', 'info');
  });

  // Logout
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    auth.removeToken();
    setState({ isOnline: false, currentUser: null, transactions: [], bankAccounts: [] });
    _categoryCache = null; _accountCache = null;
    updateOnlineStatus(false); showAuthModal(); showToast('Logged out.', 'info');
  });
}

// ── Bank account modal ────────────────────────────────────────────────────────

function initBankModal() {
  const modal = document.getElementById('modal-bank');
  document.getElementById('add-bank-btn')?.addEventListener('click',     () => openModal('modal-bank'));
  document.getElementById('modal-bank-close')?.addEventListener('click',  () => closeModal('modal-bank'));
  document.getElementById('modal-bank-cancel')?.addEventListener('click', () => closeModal('modal-bank'));
  modal?.addEventListener('click', e => { if (e.target === modal) closeModal('modal-bank'); });

  document.getElementById('modal-bank-save')?.addEventListener('click', async () => {
    const name    = document.getElementById('bank-name')?.value.trim();
    const balance = document.getElementById('bank-balance')?.value;
    const color   = document.getElementById('bank-color')?.value || CONFIG.defaultBankColor;
    if (!name) { showToast('Enter a bank name.', 'error'); return; }
    await saveAccount({ name, balance, color });
    renderBankAccountsList(null);
    populatePaymentMethodDropdown();
    closeModal('modal-bank');
    showToast(`${name} added! 🏦`, 'success');
    document.getElementById('bank-name').value = '';
    document.getElementById('bank-balance').value = '';
  });
}

// ── Transaction detail modal ──────────────────────────────────────────────────

function openTransactionDetail(id) {
  const txn = state.transactions.find(t => t.id === id); if (!txn) return;
  setState({ currentTxnId: id });
  const body = document.getElementById('modal-txn-body'); if (!body) return;
  const sign     = txn.type === 'income' ? '+' : txn.type === 'transfer' ? '↔' : '−';
  const amtColor = txn.type === 'income' ? 'var(--success)' : txn.type === 'transfer' ? 'var(--info)' : 'var(--danger)';
  const rows = [
    ['Amount',      `<span style="color:${amtColor};font-size:1.1rem">${sign}${formatCurrency(txn.amount)}</span>`],
    ['Type',         capitalise(txn.type)],
    ['Category',    `${CATEGORY_EMOJI[txn.category] || ''} ${txn.category}`],
    txn.subcategory ? ['Sub-category', txn.subcategory] : null,
    ['Description',  escapeHtml(txn.description || '—')],
    ['Date',         formatDate(txn.date, txn.time)],
    ['Payment',      txn.paymentMethod],
    txn.tags?.length ? ['Tags', txn.tags.map(t => `<span class="tag-pill">${escapeHtml(t)}</span>`).join(' ')] : null,
  ].filter(Boolean);
  body.innerHTML = rows.map(([l, v]) =>
    `<div class="txn-detail-row"><span class="txn-detail-label">${l}</span><span class="txn-detail-value">${v}</span></div>`
  ).join('');
  openModal('modal-txn');
}

function initTxnDetailModal() {
  const modal = document.getElementById('modal-txn');
  document.getElementById('modal-txn-close')?.addEventListener('click', () => closeModal('modal-txn'));
  document.getElementById('modal-txn-ok')?.addEventListener('click',    () => closeModal('modal-txn'));
  modal?.addEventListener('click', e => { if (e.target === modal) closeModal('modal-txn'); });
  document.getElementById('modal-txn-delete')?.addEventListener('click', async () => {
    if (!state.currentTxnId) return;
    await removeTransaction(state.currentTxnId);
    closeModal('modal-txn'); showToast('Transaction deleted.', 'info');
    renderDashboard();
    if (state.activeView === 'transactions') renderAllTransactions();
  });
}
