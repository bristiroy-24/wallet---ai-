/**
 * app.js – Boot / Entry point
 * ════════════════════════════
 * All logic has been split into focused modules under js/:
 *
 *   js/config.js  – CONFIG, SUBCATEGORIES, CATEGORY_EMOJI, MOCK_INSIGHTS
 *   js/state.js   – state, setState, loadLocalState, utilities, seedDemoData
 *   js/bridge.js  – backend/offline data bridge (transactions, accounts, dashboard)
 *   js/ai.js      – AI insight fetch, magic NLP parser, receipt OCR
 *   js/ui.js      – router, charts, dashboard, transaction lists, toast, theme
 *   js/forms.js   – expense form, tag manager, magic input, receipt scan
 *   js/modals.js  – auth modal, bank modal, transaction detail modal
 *   api.js        – HTTP client, auth token management
 *
 * Load order in index.html:
 *   api.js → js/config.js → js/state.js → js/bridge.js →
 *   js/ai.js → js/ui.js → js/forms.js → js/modals.js → app.js
 */
'use strict';

async function init() {
  loadLocalState();

  if (auth.isAuthenticated()) {
    // Token exists — try to restore session directly (skip health check so
    // Render cold-start delay doesn't wrongly show the login modal)
    try {
      const [txns, accs] = await Promise.all([apiFetchTransactions(), apiFetchAccounts()]);
      setState({
        isOnline:     true,
        transactions: txns.map(normaliseApiTransaction),
        bankAccounts: accs.map(a => ({ id: a.id, name: a.name, balance: a.balance, color: a.color || CONFIG.defaultBankColor })),
      });
      showToast('Session restored ●', 'success', 2000);
    } catch(e) {
      if (e.message === 'SESSION_EXPIRED') {
        // Token is genuinely invalid/expired — clear and force login
        auth.removeToken();
        setState({ isOnline: false });
        showAuthModal();
      } else {
        // Network error (Render cold start, timeout, etc.) — keep the token,
        // load cached local state and let the user continue
        setState({ isOnline: false });
        showToast('Backend waking up… data may be stale. Refresh in a moment. ⏳', 'info', 6000);
      }
    }
  } else {
    // No token — check if backend is up to decide online vs offline mode
    const backendUp = await checkBackendAvailable();
    if (backendUp) {
      showAuthModal();
    } else {
      seedDemoData();
      showToast('Backend offline – running in local mode 📴', 'info', 4000);
    }
  }

  initTheme();
  initRouter();
  initForm();
  initTagInput();
  initBankModal();
  initTxnDetailModal();
  initAuthModal();
  initAIBanner();
  bindTransactionClicks();
  populatePaymentMethodDropdown();
  updateOnlineStatus(state.isOnline);

  document.getElementById('filter-category')?.addEventListener('change', renderAllTransactions);
  document.getElementById('filter-method')?.addEventListener('change',   renderAllTransactions);

  navigateTo(state.activeView || 'dashboard');
  console.info(`[WalletAI] Ready. Mode: ${state.isOnline ? 'ONLINE' : 'OFFLINE'}`);
}

/* ── Splash → App transition ─────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    const splash = document.getElementById('splash-screen');
    const app    = document.getElementById('app');
    splash.style.animation = 'fadeOut 0.4s ease forwards';
    setTimeout(() => { splash.style.display = 'none'; app.classList.remove('hidden'); init(); }, 380);
  }, 1400);
});

const _s = document.createElement('style');
_s.textContent = `@keyframes fadeOut { to { opacity:0; transform:scale(0.97); } }`;
document.head.appendChild(_s);
