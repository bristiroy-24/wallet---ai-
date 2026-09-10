/**
 * js/ui.js
 * ─────────
 * All UI rendering: router, charts, dashboard, transactions, toast, theme.
 */
'use strict';

// ── Router ────────────────────────────────────────────────────────────────────

function navigateTo(viewName) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`view-${viewName}`)?.classList.add('active');
  document.querySelector(`.nav-btn[data-view="${viewName}"]`)?.classList.add('active');
  setState({ activeView: viewName });
  if (viewName === 'dashboard')    renderDashboard();
  if (viewName === 'transactions') renderAllTransactions();
}

function initRouter() {
  document.querySelectorAll('.nav-btn[data-view]').forEach(btn =>
    btn.addEventListener('click', () => navigateTo(btn.dataset.view)));
  document.getElementById('view-all-btn')?.addEventListener('click', () => navigateTo('transactions'));
}

// ── Charts ────────────────────────────────────────────────────────────────────

let pieChartInst = null, barChartInst = null;

function setChartDefaults() {
  const dark = state.theme !== 'light';
  Chart.defaults.color       = dark ? '#94A3B8' : '#4B5563';
  Chart.defaults.borderColor = dark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
  Chart.defaults.font.family = "'Inter',system-ui,sans-serif";
  Chart.defaults.font.size   = 11;
}

function renderPieChart(categoryBreakdown) {
  const canvas = document.getElementById('pieChart');
  if (!canvas) return;
  let labels, amounts;
  if (categoryBreakdown && categoryBreakdown.length > 0) {
    labels  = categoryBreakdown.map(c => c.category_name);
    amounts = categoryBreakdown.map(c => c.total);
  } else {
    const now = new Date();
    const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    const totals = {};
    state.transactions.filter(t => t.type === 'expense' && t.date.startsWith(key))
      .forEach(t => { totals[t.category] = (totals[t.category] || 0) + Number(t.amount); });
    labels = Object.keys(totals); amounts = Object.values(totals);
  }
  const COLORS = ['#6C63FF','#22C55E','#EF4444','#F59E0B','#3B82F6','#EC4899','#14B8A6','#A855F7','#F97316'];
  if (pieChartInst) pieChartInst.destroy();
  if (!labels.length) {
    canvas.parentElement.innerHTML = `<p style="text-align:center;color:var(--text-muted);font-size:0.8rem;padding:40px 0">No expenses this month yet.</p>`;
    return;
  }
  pieChartInst = new Chart(canvas, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: amounts, backgroundColor: COLORS.slice(0, labels.length), borderWidth: 2, borderColor: '#1E2130', hoverOffset: 8 }] },
    options: { responsive: true, maintainAspectRatio: true, cutout: '62%',
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } },
        tooltip: { callbacks: { label: ctx => ` ${CONFIG.currencySymbol}${ctx.parsed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` } } } },
  });
}

function renderBarChart(monthlyTrends) {
  const canvas = document.getElementById('barChart');
  if (!canvas) return;
  let months, totals;
  if (monthlyTrends && monthlyTrends.length > 0) {
    months = monthlyTrends.map(m => m.month);
    totals = monthlyTrends.map(m => m.total_expense);
  } else {
    months = []; totals = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
      months.push(d.toLocaleString('en-IN', { month: 'short' }));
      totals.push(state.transactions.filter(t => t.type === 'expense' && t.date.startsWith(key)).reduce((s, t) => s + Number(t.amount), 0));
    }
  }
  if (barChartInst) barChartInst.destroy();
  barChartInst = new Chart(canvas, {
    type: 'bar',
    data: { labels: months, datasets: [{ label: 'Expenses', data: totals,
      backgroundColor: months.map((_, i) => i === months.length - 1 ? 'rgba(108,99,255,0.85)' : 'rgba(108,99,255,0.35)'),
      borderRadius: 6, borderSkipped: false }] },
    options: { responsive: true, maintainAspectRatio: true,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${CONFIG.currencySymbol}${ctx.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` } } },
      scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { callback: v => `${CONFIG.currencySymbol}${(v / 1000).toFixed(0)}k` } } } },
  });
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

async function renderDashboard() {
  const dash = await loadDashboardData();
  const txns = state.transactions;
  const totalIncome  = dash ? dash.total_income  : txns.filter(t => t.type === 'income').reduce((s, t) => s + Number(t.amount), 0);
  const totalExpense = dash ? dash.total_expense : txns.filter(t => t.type === 'expense').reduce((s, t) => s + Number(t.amount), 0);
  const netBalance   = dash ? dash.net_balance   : totalIncome - totalExpense;
  const cashTotal    = txns.filter(t => t.paymentMethod === 'Cash' && t.type === 'expense').reduce((s, t) => s + Number(t.amount), 0);
  const cardTotal    = txns.filter(t => t.paymentMethod === 'Card' && t.type === 'expense').reduce((s, t) => s + Number(t.amount), 0);

  document.getElementById('balance-total').textContent = formatCurrency(netBalance);
  document.getElementById('balance-meta').textContent  = `${txns.length} transaction${txns.length !== 1 ? 's' : ''}`;
  document.getElementById('balance-cash').textContent  = formatCurrency(cashTotal);
  document.getElementById('balance-card').textContent  = formatCurrency(cardTotal);

  const lbl = document.getElementById('current-month-label');
  if (lbl) lbl.textContent = new Date().toLocaleString('en-IN', { month: 'long', year: 'numeric' });

  renderBankAccountsList(dash ? dash.accounts : null);
  setChartDefaults();
  renderPieChart(dash?.category_breakdown);
  renderBarChart(dash?.monthly_trends);
  renderRecentTransactions();
  refreshAIInsightBanner();
}

function renderBankAccountsList(apiAccounts) {
  const container = document.getElementById('bank-accounts-list');
  if (!container) return;
  const accounts = apiAccounts || state.bankAccounts;
  if (!accounts || accounts.length === 0) {
    container.innerHTML = `<p class="bank-empty">No accounts added yet</p>`;
    return;
  }
  container.innerHTML = accounts.map(a => `
    <div class="bank-account-item">
      <div class="bank-account-dot" style="background:${a.color || CONFIG.defaultBankColor}"></div>
      <span class="bank-account-name">${escapeHtml(a.name)}</span>
      <span class="bank-account-bal">${formatCurrency(a.balance || 0)}</span>
    </div>`).join('');
}

// ── Transaction lists ─────────────────────────────────────────────────────────

function renderRecentTransactions() {
  const container = document.getElementById('transactions-list');
  if (container) container.innerHTML = buildTransactionListHTML(state.transactions.slice(0, 5));
}

function renderAllTransactions() {
  const container = document.getElementById('all-transactions-list');
  if (!container) return;
  const cat = document.getElementById('filter-category')?.value || '';
  const mth = document.getElementById('filter-method')?.value   || '';
  let list = state.transactions;
  if (cat) list = list.filter(t => t.category === cat);
  if (mth) list = list.filter(t => t.paymentMethod === mth);
  container.innerHTML = buildTransactionListHTML(list);
  populateFilterDropdowns();
}

function buildTransactionListHTML(txns) {
  if (!txns.length) return `<div class="txn-empty"><span class="empty-icon">🧾</span>No transactions found. Add one with the + button!</div>`;
  const BG = { 'Food & Drinks':'rgba(239,68,68,0.12)','Shopping':'rgba(236,72,153,0.12)','Housing':'rgba(245,158,11,0.12)',
    'Entertainment':'rgba(168,85,247,0.12)','Recharge':'rgba(59,130,246,0.12)','Transport':'rgba(20,184,166,0.12)',
    'Education':'rgba(34,197,94,0.12)','Health':'rgba(249,115,22,0.12)' };
  return txns.map(t => {
    const sign = t.type === 'income' ? '+' : t.type === 'transfer' ? '↔' : '−';
    return `<div class="txn-item" data-id="${t.id}" role="button" tabindex="0">
      <div class="txn-icon" style="background:${BG[t.category] || 'rgba(100,116,139,0.12)'}">${CATEGORY_EMOJI[t.category] || '📦'}</div>
      <div class="txn-info">
        <div class="txn-desc">${escapeHtml(t.description || t.category)}</div>
        <div class="txn-meta">${t.category} • ${relativeTime(t.date)}</div>
      </div>
      <div class="txn-amount ${t.type}">${sign}${formatCurrency(t.amount)}</div>
    </div>`;
  }).join('');
}

function populateFilterDropdowns() {
  const sel = document.getElementById('filter-category');
  if (!sel) return;
  const current = sel.value;
  const cats = [...new Set(state.transactions.map(t => t.category))].sort();
  sel.innerHTML = `<option value="">All Categories</option>` + cats.map(c => `<option value="${c}" ${c === current ? 'selected' : ''}>${c}</option>`).join('');
}

function bindTransactionClicks() {
  document.addEventListener('click', e => { const i = e.target.closest('.txn-item[data-id]'); if (i) openTransactionDetail(i.dataset.id); });
  document.addEventListener('keydown', e => { if (e.key === 'Enter') { const i = e.target.closest('.txn-item[data-id]'); if (i) openTransactionDetail(i.dataset.id); } });
}

// ── AI Insight banner ─────────────────────────────────────────────────────────

async function refreshAIInsightBanner() {
  const textEl = document.getElementById('ai-insight-text');
  const btn    = document.getElementById('ai-refresh-btn');
  if (!textEl) return;
  textEl.textContent = 'Analysing your spending…';
  if (btn) btn.style.pointerEvents = 'none';
  try { textEl.textContent = await fetchAIInsight(); }
  catch { textEl.textContent = '💡 Tip: Track every expense to understand your spending habits.'; }
  finally { if (btn) btn.style.pointerEvents = ''; }
}

function initAIBanner() {
  document.getElementById('ai-refresh-btn')?.addEventListener('click', refreshAIInsightBanner);
}

// ── Toast ─────────────────────────────────────────────────────────────────────

let _toastTimer = null;
function showToast(msg, type = 'info', duration = 2800) {
  const t = document.getElementById('toast'); if (!t) return;
  if (_toastTimer) clearTimeout(_toastTimer);
  t.textContent = msg; t.className = `toast ${type}`; t.classList.remove('hidden');
  _toastTimer = setTimeout(() => t.classList.add('hidden'), duration);
}

// ── Theme ─────────────────────────────────────────────────────────────────────

function initTheme() {
  applyTheme(state.theme || 'dark');
  document.getElementById('theme-toggle')?.addEventListener('click', () => {
    const next = state.theme === 'dark' ? 'light' : 'dark';
    setState({ theme: next }); applyTheme(next);
    setChartDefaults();
    if (pieChartInst) { pieChartInst.destroy(); pieChartInst = null; } renderPieChart();
    if (barChartInst) { barChartInst.destroy(); barChartInst = null; }  renderBarChart();
  });
}

function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  const btn = document.getElementById('theme-toggle'); if (btn) btn.textContent = t === 'dark' ? '🌙' : '☀️';
}

// ── Online status indicator ───────────────────────────────────────────────────

function updateOnlineStatus(online) {
  const logoutBtn = document.getElementById('logout-btn');
  const avatar    = document.getElementById('user-avatar');
  if (logoutBtn) logoutBtn.classList.toggle('hidden', !online);
  if (avatar && state.currentUser) {
    avatar.textContent = (state.currentUser.full_name || state.currentUser.email || 'U')[0].toUpperCase();
    avatar.title = state.currentUser.email || '';
  }
  const title = document.querySelector('.topbar-title');
  if (title) { title.textContent = online ? 'WalletAI ●' : 'WalletAI'; title.title = online ? 'Connected to server' : 'Offline mode'; }
}
