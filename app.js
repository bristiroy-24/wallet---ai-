/**
 * WalletAI – app.js
 * ══════════════════════════════════════════════════════════════
 * Works in two modes automatically:
 *
 *  ONLINE  – backend running at localhost:8000
 *            → auth required, all data synced to PostgreSQL
 *
 *  OFFLINE – no backend (or not logged in)
 *            → data stored in LocalStorage, AI mocked
 *
 * Sections:
 *  1.  CONFIG & CONSTANTS
 *  2.  APP STATE
 *  3.  BACKEND / OFFLINE BRIDGE  ← key integration layer
 *  4.  AI HANDLERS
 *  5.  ROUTER
 *  6.  CHARTS
 *  7.  DASHBOARD RENDERER
 *  8.  TRANSACTION CRUD
 *  9.  FORM HANDLER
 *  10. TAG MANAGER
 *  11. BANK / ACCOUNT MANAGER
 *  12. TRANSACTION DETAIL MODAL
 *  13. AUTH MODAL
 *  14. MODAL UTILITIES
 *  15. AI INSIGHT BANNER
 *  16. TOAST
 *  17. THEME
 *  18. UTILITIES & SEED DATA
 *  19. BOOT
 * ══════════════════════════════════════════════════════════════
 */

'use strict';

/* ═══════════════════════════════════════════════════════════
   1. CONFIG & CONSTANTS
═══════════════════════════════════════════════════════════ */
const CONFIG = {
  storageKey:      'walletai_data',
  currencySymbol:  '₹',
  defaultBankColor:'#6C63FF',
  USE_REAL_AI:     false,          // flip true + add key to enable Gemini
  GEMINI_API_KEY:  'YOUR_GEMINI_API_KEY_HERE',
  GEMINI_MODEL:    'gemini-2.5-flash',
  GEMINI_ENDPOINT: 'https://generativelanguage.googleapis.com/v1beta/models',
};

const SUBCATEGORIES = {
  'Housing':       ['Groceries','Maid Salary','Electricity','Water','Gas','Internet/Wi-Fi','Maintenance'],
  'Entertainment': ['Netflix','Amazon Prime','Spotify','Disney+','YouTube Premium','Gaming','Other Subscriptions'],
  'Recharge':      ['Phone Recharge','Wi-Fi Bill','DTH / Cable','Other'],
  'Food & Drinks': ['Restaurant','Zomato' ,'Swiggy','Cafe' , 'Coffee','Tea','Cigarette','Grocery','Bear','Whiskey','Other'],
  'Transport':     ['Fuel','Ola','Uber','Metro','Bus','Auto','Flight','Train','Other'],
  'Shopping':      ['Clothing','Electronics','Amazon','Flipkart','Myntra','Meesho','Nykaa','Purpell','Ajio','Skin Care','Personal care','Other'],
};

const CATEGORY_EMOJI = {
  'Food & Drinks':'🍔','Shopping':'🛍️','Housing':'🏠','Entertainment':'🎬',
  'Recharge':'📱','Education':'📚','Transport':'🚗','Health':'💊','Other':'📦',
};

const MOCK_INSIGHTS = [
  '⚠️ Your subscription spending is up 15% this week.',
  '💡 You spend 40% of your income on Food & Drinks. Try meal prepping.',
  '📊 Total spending this month is 12% lower than last month. Keep it up!',
  '🔔 3 recurring subscriptions totalling ₹1,299/month detected.',
  '🎯 At current rate you will exceed your monthly budget by ₹2,400.',
  '✅ You saved ₹3,000 more this month vs last month!',
  '⚡ Transport costs spiked 30% this week. Review your Uber usage.',
  '💳 80% of expenses were digital payments. Cash usage is minimal.',
];

/* ═══════════════════════════════════════════════════════════
   2. APP STATE
═══════════════════════════════════════════════════════════ */
let state = {
  transactions:   [],
  bankAccounts:   [],
  activeView:     'dashboard',
  currentTxnId:   null,
  theme:          'dark',
  aiInsightIndex: 0,
  isOnline:       false,   // true when backend is reachable + user logged in
  currentUser:    null,
};

function loadLocalState() {
  try {
    const s = localStorage.getItem(CONFIG.storageKey);
    if (s) { const p = JSON.parse(s); state = { ...state, ...p, isOnline: false, currentUser: null }; }
  } catch(e) {}
}
function saveLocalState() {
  try { localStorage.setItem(CONFIG.storageKey, JSON.stringify(state)); } catch(e) {}
}
function setState(partial) { state = { ...state, ...partial }; saveLocalState(); }

/* ═══════════════════════════════════════════════════════════
   3. BACKEND / OFFLINE BRIDGE
   All data operations go through these functions.
   They call the real API when online, LocalStorage when offline.
═══════════════════════════════════════════════════════════ */

/** Load transactions — API or LocalStorage */
async function loadTransactions() {
  if (state.isOnline) {
    try {
      const raw = await apiFetchTransactions();
      // Normalise API shape → internal shape
      const txns = raw.map(normaliseApiTransaction);
      setState({ transactions: txns });
      return;
    } catch(e) { handleApiError(e); }
  }
  // offline: state.transactions already loaded from LocalStorage
}

/** Create transaction — API or LocalStorage */
async function saveTransaction(data) {
  if (state.isOnline) {
    try {
      // Map internal category name → category_id
      const categoryId = await resolveCategoryId(data.category);
      const accountId  = await resolveAccountId(data.paymentMethod);
      const payload = {
        amount:      parseFloat(data.amount),
        type:        data.type.toUpperCase(),
        note:        data.description || data.category,
        tags:        data.tags || [],
        date:        `${data.date}T${data.time || '00:00'}:00+00:00`,
        category_id: categoryId,
        account_id:  accountId,
      };
      const created = await apiCreateTransaction(payload);
      // Prepend normalised version to local state for instant UI update
      const txn = normaliseApiTransaction(created);
      setState({ transactions: [txn, ...state.transactions] });
      return txn;
    } catch(e) { handleApiError(e); }
  }
  // offline
  return addTransactionLocal(data);
}

/** Delete transaction — API or LocalStorage */
async function removeTransaction(id) {
  if (state.isOnline) {
    try { await apiDeleteTransaction(id); } catch(e) { /* ignore 404 */ }
  }
  setState({ transactions: state.transactions.filter(t => t.id !== id) });
}

/** Load accounts — API or LocalStorage */
async function loadAccounts() {
  if (state.isOnline) {
    try {
      const raw = await apiFetchAccounts();
      const accounts = raw.map(a => ({
        id: a.id, name: a.name, balance: a.balance, color: a.color || CONFIG.defaultBankColor,
        type: a.type,
      }));
      setState({ bankAccounts: accounts });
      return;
    } catch(e) { handleApiError(e); }
  }
}

/** Create account — API or LocalStorage */
async function saveAccount(data) {
  if (state.isOnline) {
    try {
      const created = await apiCreateAccount({
        name: data.name, balance: parseFloat(data.balance || 0),
        type: 'BANK', color: data.color,
      });
      const acc = { id: created.id, name: created.name, balance: created.balance, color: created.color };
      setState({ bankAccounts: [...state.bankAccounts, acc] });
      return acc;
    } catch(e) { handleApiError(e); }
  }
  // offline
  const acc = { id: generateId(), name: data.name, balance: parseFloat(data.balance || 0), color: data.color };
  setState({ bankAccounts: [...state.bankAccounts, acc] });
  return acc;
}

/** Load dashboard analytics — API or computed locally */
async function loadDashboardData() {
  if (state.isOnline) {
    try {
      const dash = await apiFetchDashboard();
      return dash; // { net_balance, accounts, category_breakdown, monthly_trends }
    } catch(e) { handleApiError(e); }
  }
  return null; // null = compute locally from state.transactions
}

/** Load AI insights — API or mock */
async function loadInsights() {
  if (state.isOnline) {
    try { return await apiFetchInsights(); } catch(e) {}
  }
  return null;
}

/** Dismiss an insight */
async function dismissInsight(id) {
  if (state.isOnline) {
    try { await apiRequest(`/analytics/insights/${id}`, { method: 'DELETE' }); } catch(e) {}
  }
}

// ── Helpers ──────────────────────────────────────────────
let _categoryCache = null;
async function resolveCategoryId(categoryName) {
  if (!_categoryCache) {
    try { _categoryCache = await apiRequest('/categories/'); } catch(e) { return null; }
  }
  const flat = [];
  (_categoryCache || []).forEach(c => { flat.push(c); (c.subcategories || []).forEach(s => flat.push(s)); });
  const match = flat.find(c => c.name.toLowerCase() === categoryName.toLowerCase());
  return match ? match.id : null;
}

let _accountCache = null;
async function resolveAccountId(paymentMethodName) {
  if (!_accountCache) {
    try { _accountCache = await apiFetchAccounts(); } catch(e) { return null; }
  }
  const match = (_accountCache || []).find(a => a.name.toLowerCase() === paymentMethodName.toLowerCase());
  return match ? match.id : null;
}

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

/* ═══════════════════════════════════════════════════════════
   4. AI HANDLERS
═══════════════════════════════════════════════════════════ */
async function fetchAIInsight() {
  // If online, ask backend (which uses real Gemini if configured)
  if (state.isOnline) {
    try {
      const insights = await apiRefreshInsights();
      if (insights && insights.length > 0) return insights[0].insight_text;
    } catch(e) {}
  }
  // Fallback: local Gemini or mock
  if (CONFIG.USE_REAL_AI && CONFIG.GEMINI_API_KEY !== 'YOUR_GEMINI_API_KEY_HERE') {
    try {
      const summary = state.transactions.slice(0,15).map(t =>
        `${t.type}: ${t.description} ₹${t.amount} on ${t.date}`).join('\n');
      const url = `${CONFIG.GEMINI_ENDPOINT}/${CONFIG.GEMINI_MODEL}:generateContent?key=${CONFIG.GEMINI_API_KEY}`;
      const res = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ contents:[{parts:[{text:`Financial assistant. Give one insight (max 120 chars, start with emoji) based on:\n${summary}`}]}], generationConfig:{maxOutputTokens:150,temperature:0.7} })
      });
      const data = await res.json();
      return data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || MOCK_INSIGHTS[0];
    } catch(e) {}
  }
  await simulateDelay(500);
  const idx = state.aiInsightIndex % MOCK_INSIGHTS.length;
  setState({ aiInsightIndex: idx + 1 });
  return MOCK_INSIGHTS[idx];
}

async function parseMagicInput(text) {
  // If online, use backend AI endpoint
  if (state.isOnline) {
    try { return normaliseAIParsed(await apiMagicParse(text)); } catch(e) {}
  }
  // Fallback: local mock
  await simulateDelay(800);
  return mockParseNaturalLanguage(text);
}

async function runReceiptOCR(imageFile) {
  if (state.isOnline) {
    try { return normaliseAIParsed(await apiScanReceipt(imageFile)); } catch(e) {}
  }
  await simulateDelay(1200);
  return { amount: (Math.random()*400+50).toFixed(2), description: 'Scanned receipt', paymentMethod: 'Card', category: 'Shopping' };
}

function normaliseAIParsed(p) {
  // Backend returns snake_case, normalize to our internal shape
  return {
    amount:        p.amount,
    type:          (p.type || 'expense').toLowerCase(),
    category:      p.category || 'Other',
    subcategory:   p.subcategory || null,
    description:   p.note || p.description || '',
    paymentMethod: p.payment_method || p.paymentMethod || 'Cash',
    tags:          p.tags || [],
    date:          p.date || null,
  };
}

function mockParseNaturalLanguage(text) {
  const lower = text.toLowerCase();
  const r = { amount:null, type:'expense', category:'Other', subcategory:null, description:text, paymentMethod:'Cash', tags:[] };
  const m = text.match(/(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)/i);
  if (m) r.amount = parseFloat(m[1].replace(/,/g,''));
  if (/salary|income|received|got paid/i.test(lower)) r.type = 'income';
  if (/transfer|sent to/i.test(lower)) r.type = 'transfer';
  if (/upi|gpay|card|credit|debit|phonepe|paytm/i.test(lower)) r.paymentMethod = 'Card';
  if (/zomato|swiggy|lunch|dinner|restaurant|food|pizza|cafe|coffee/i.test(lower)) { r.category='Food & Drinks'; r.subcategory=/zomato|swiggy/i.test(lower)?'Zomato / Swiggy':/cafe|coffee/i.test(lower)?'Cafe / Coffee':'Restaurant'; }
  else if (/netflix|spotify|amazon prime|subscription/i.test(lower)) { r.category='Entertainment'; r.subcategory=/netflix/i.test(lower)?'Netflix':/spotify/i.test(lower)?'Spotify':/amazon/i.test(lower)?'Amazon Prime':null; }
  else if (/uber|ola|metro|bus|fuel|petrol/i.test(lower)) { r.category='Transport'; r.subcategory=/uber|ola/i.test(lower)?'Ola / Uber':/fuel|petrol/i.test(lower)?'Fuel':null; }
  else if (/rent|grocery|maid|electricity/i.test(lower)) { r.category='Housing'; r.subcategory=/grocery/i.test(lower)?'Groceries':/maid/i.test(lower)?'Maid Salary':null; }
  else if (/recharge|airtel|jio|wifi/i.test(lower)) { r.category='Recharge'; r.subcategory=/wifi/i.test(lower)?'Wi-Fi Bill':'Phone Recharge'; }
  else if (/medicine|doctor|pharmacy|hospital/i.test(lower)) r.category='Health';
  else if (/amazon|flipkart|shopping|clothes/i.test(lower)) r.category='Shopping';
  else if (/book|course|school|tuition/i.test(lower)) r.category='Education';
  r.description = text.replace(/(?:₹|Rs\.?|INR)?\s*[\d,]+(?:\.\d{1,2})?\s*/gi,'').trim() || text;
  r.tags = [r.category.toLowerCase().split(' ')[0]];
  return r;
}

/* ═══════════════════════════════════════════════════════════
   5. ROUTER
═══════════════════════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════════════════════
   6. CHARTS
═══════════════════════════════════════════════════════════ */
let pieChartInst = null, barChartInst = null;

function setChartDefaults() {
  const d = state.theme !== 'light';
  Chart.defaults.color       = d ? '#94A3B8' : '#4B5563';
  Chart.defaults.borderColor = d ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
  Chart.defaults.font.family = "'Inter',system-ui,sans-serif";
  Chart.defaults.font.size   = 11;
}

function renderPieChart(categoryBreakdown) {
  const canvas = document.getElementById('pieChart');
  if (!canvas) return;

  let labels, amounts;
  if (categoryBreakdown && categoryBreakdown.length > 0) {
    // From API dashboard data
    labels  = categoryBreakdown.map(c => c.category_name);
    amounts = categoryBreakdown.map(c => c.total);
  } else {
    // Compute locally
    const now = new Date();
    const m = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`;
    const totals = {};
    state.transactions.filter(t => t.type==='expense' && t.date.startsWith(m))
      .forEach(t => { totals[t.category] = (totals[t.category]||0) + Number(t.amount); });
    labels  = Object.keys(totals);
    amounts = Object.values(totals);
  }

  const COLORS = ['#6C63FF','#22C55E','#EF4444','#F59E0B','#3B82F6','#EC4899','#14B8A6','#A855F7','#F97316'];
  if (pieChartInst) pieChartInst.destroy();
  if (!labels.length) {
    canvas.parentElement.innerHTML = `<p style="text-align:center;color:var(--text-muted);font-size:0.8rem;padding:40px 0">No expenses this month yet.</p>`;
    return;
  }
  pieChartInst = new Chart(canvas, {
    type:'doughnut',
    data:{ labels, datasets:[{ data:amounts, backgroundColor:COLORS.slice(0,labels.length), borderWidth:2, borderColor:'#1E2130', hoverOffset:8 }] },
    options:{ responsive:true, maintainAspectRatio:true, cutout:'62%',
      plugins:{ legend:{position:'bottom',labels:{boxWidth:10,padding:12}},
        tooltip:{callbacks:{label:ctx=>` ${CONFIG.currencySymbol}${ctx.parsed.toLocaleString('en-IN',{minimumFractionDigits:2})}`}} } },
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
    for (let i=5;i>=0;i--) {
      const d = new Date(now.getFullYear(), now.getMonth()-i, 1);
      const key = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
      months.push(d.toLocaleString('en-IN',{month:'short'}));
      totals.push(state.transactions.filter(t=>t.type==='expense'&&t.date.startsWith(key)).reduce((s,t)=>s+Number(t.amount),0));
    }
  }

  if (barChartInst) barChartInst.destroy();
  barChartInst = new Chart(canvas, {
    type:'bar',
    data:{ labels:months, datasets:[{ label:'Expenses', data:totals,
      backgroundColor:months.map((_,i)=>i===months.length-1?'rgba(108,99,255,0.85)':'rgba(108,99,255,0.35)'),
      borderRadius:6, borderSkipped:false }] },
    options:{ responsive:true, maintainAspectRatio:true,
      plugins:{ legend:{display:false}, tooltip:{callbacks:{label:ctx=>` ${CONFIG.currencySymbol}${ctx.parsed.y.toLocaleString('en-IN',{minimumFractionDigits:2})}`}} },
      scales:{ x:{grid:{display:false}}, y:{beginAtZero:true, ticks:{callback:v=>`${CONFIG.currencySymbol}${(v/1000).toFixed(0)}k`}} } },
  });
}

/* ═══════════════════════════════════════════════════════════
   7. DASHBOARD RENDERER
═══════════════════════════════════════════════════════════ */
async function renderDashboard() {
  // Try to get rich dashboard data from API
  const dash = await loadDashboardData();

  // Balance cards
  const txns = state.transactions;
  const totalIncome  = dash ? dash.total_income  : txns.filter(t=>t.type==='income').reduce((s,t)=>s+Number(t.amount),0);
  const totalExpense = dash ? dash.total_expense : txns.filter(t=>t.type==='expense').reduce((s,t)=>s+Number(t.amount),0);
  const netBalance   = dash ? dash.net_balance   : totalIncome - totalExpense;
  const cashTotal    = txns.filter(t=>t.paymentMethod==='Cash'&&t.type==='expense').reduce((s,t)=>s+Number(t.amount),0);
  const cardTotal    = txns.filter(t=>t.paymentMethod==='Card'&&t.type==='expense').reduce((s,t)=>s+Number(t.amount),0);

  document.getElementById('balance-total').textContent = formatCurrency(netBalance);
  document.getElementById('balance-meta').textContent  = `${txns.length} transaction${txns.length!==1?'s':''}`;
  document.getElementById('balance-cash').textContent  = formatCurrency(cashTotal);
  document.getElementById('balance-card').textContent  = formatCurrency(cardTotal);

  const lbl = document.getElementById('current-month-label');
  if (lbl) lbl.textContent = new Date().toLocaleString('en-IN',{month:'long',year:'numeric'});

  // Bank accounts
  renderBankAccountsList(dash ? dash.accounts : null);

  // Charts
  setChartDefaults();
  renderPieChart(dash?.category_breakdown);
  renderBarChart(dash?.monthly_trends);

  // Recent transactions (always from local state for speed)
  renderRecentTransactions();

  // AI insight
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
      <div class="bank-account-dot" style="background:${a.color||CONFIG.defaultBankColor}"></div>
      <span class="bank-account-name">${escapeHtml(a.name)}</span>
      <span class="bank-account-bal">${formatCurrency(a.balance||0)}</span>
    </div>`).join('');
}

function renderRecentTransactions() {
  const container = document.getElementById('transactions-list');
  if (container) container.innerHTML = buildTransactionListHTML(state.transactions.slice(0,5));
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
  const BG = {'Food & Drinks':'rgba(239,68,68,0.12)','Shopping':'rgba(236,72,153,0.12)','Housing':'rgba(245,158,11,0.12)','Entertainment':'rgba(168,85,247,0.12)','Recharge':'rgba(59,130,246,0.12)','Transport':'rgba(20,184,166,0.12)','Education':'rgba(34,197,94,0.12)','Health':'rgba(249,115,22,0.12)'};
  return txns.map(t => {
    const sign = t.type==='income'?'+':t.type==='transfer'?'↔':'−';
    return `<div class="txn-item" data-id="${t.id}" role="button" tabindex="0">
      <div class="txn-icon" style="background:${BG[t.category]||'rgba(100,116,139,0.12)'}">${CATEGORY_EMOJI[t.category]||'📦'}</div>
      <div class="txn-info">
        <div class="txn-desc">${escapeHtml(t.description||t.category)}</div>
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
  const cats = [...new Set(state.transactions.map(t=>t.category))].sort();
  sel.innerHTML = `<option value="">All Categories</option>` + cats.map(c=>`<option value="${c}" ${c===current?'selected':''}>${c}</option>`).join('');
}

function bindTransactionClicks() {
  document.addEventListener('click', e => { const i = e.target.closest('.txn-item[data-id]'); if(i) openTransactionDetail(i.dataset.id); });
  document.addEventListener('keydown', e => { if(e.key==='Enter'){const i=e.target.closest('.txn-item[data-id]');if(i)openTransactionDetail(i.dataset.id);} });
}

/* ═══════════════════════════════════════════════════════════
   8. TRANSACTION CRUD (offline / local)
═══════════════════════════════════════════════════════════ */
function addTransactionLocal(data) {
  const txn = {
    id: generateId(), type: data.type||'expense', amount: parseFloat(data.amount),
    category: data.category||'Other', subcategory: data.subcategory||null,
    description: data.description||data.category, paymentMethod: data.paymentMethod||'Cash',
    date: data.date||new Date().toISOString().split('T')[0],
    time: data.time||new Date().toTimeString().slice(0,5),
    tags: data.tags||[], createdAt: new Date().toISOString(),
  };
  setState({ transactions: [txn, ...state.transactions] });
  return txn;
}

/* ═══════════════════════════════════════════════════════════
   9. FORM HANDLER
═══════════════════════════════════════════════════════════ */
let activeTags = [];
let activeType = 'expense';

function initForm() {
  const today = new Date();
  const di = document.getElementById('txn-date');
  const ti = document.getElementById('txn-time');
  if (di) di.value = today.toISOString().split('T')[0];
  if (ti) ti.value = today.toTimeString().slice(0,5);

  // Type toggle
  document.querySelectorAll('.type-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.type-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active'); activeType = btn.dataset.type;
  }));

  // Category → subcategory cascade
  document.getElementById('category')?.addEventListener('change', function() {
    const subs = SUBCATEGORIES[this.value];
    const grp = document.getElementById('subcategory-group');
    const sel = document.getElementById('subcategory');
    if (subs && subs.length) {
      sel.innerHTML = `<option value="">— Select sub-category —</option>` + subs.map(s=>`<option value="${s}">${s}</option>`).join('');
      grp.style.display = 'flex';
    } else { grp.style.display = 'none'; sel.value = ''; }
  });

  document.getElementById('expense-form')?.addEventListener('submit', handleFormSubmit);
  document.getElementById('magic-parse-btn')?.addEventListener('click', handleMagicParse);
  document.getElementById('magic-input')?.addEventListener('keydown', e => { if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();handleMagicParse();} });
  document.getElementById('scan-receipt-btn')?.addEventListener('click', () => document.getElementById('receipt-file-input')?.click());
  document.getElementById('receipt-file-input')?.addEventListener('change', handleReceiptScan);

  populatePaymentMethodDropdown();
}

async function handleFormSubmit(e) {
  e.preventDefault();
  const amount   = parseFloat(document.getElementById('amount')?.value);
  const category = document.getElementById('category')?.value;
  const date     = document.getElementById('txn-date')?.value;
  const method   = document.getElementById('payment-method')?.value;
  if (!amount || amount <= 0) { showToast('Enter a valid amount.','error'); return; }
  if (!category)              { showToast('Please select a category.','error'); return; }
  if (!date)                  { showToast('Please select a date.','error'); return; }

  const btn = document.getElementById('submit-expense-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Saving…'; }

  const data = {
    type: activeType, amount, category,
    subcategory: document.getElementById('subcategory')?.value || null,
    description: document.getElementById('description')?.value.trim(),
    date, time: document.getElementById('txn-time')?.value || '',
    paymentMethod: method, tags: [...activeTags],
  };

  await saveTransaction(data);
  showToast(state.isOnline ? 'Saved to server! 🎉' : 'Saved locally! 🎉', 'success');
  resetForm();
  navigateTo('dashboard');

  if (btn) { btn.disabled = false; btn.textContent = '💾 Save Transaction'; }
}

function resetForm() {
  document.getElementById('expense-form')?.reset();
  activeTags = []; renderTags(); activeType = 'expense';
  document.querySelectorAll('.type-btn').forEach(b=>b.classList.remove('active'));
  document.querySelector('.type-btn[data-type="expense"]')?.classList.add('active');
  document.getElementById('subcategory-group').style.display = 'none';
  const today = new Date();
  const di = document.getElementById('txn-date'); if(di) di.value = today.toISOString().split('T')[0];
  const ti = document.getElementById('txn-time'); if(ti) ti.value = today.toTimeString().slice(0,5);
  document.getElementById('magic-input').value = '';
  document.getElementById('magic-status').classList.add('hidden');
}

async function handleMagicParse() {
  const text = document.getElementById('magic-input')?.value.trim();
  if (!text) { showToast('Type something in Magic Input first.','info'); return; }
  const btn    = document.getElementById('magic-parse-btn');
  const status = document.getElementById('magic-status');
  btn.innerHTML = '⏳ Parsing…'; btn.style.opacity = '0.65';
  try {
    const parsed = await parseMagicInput(text);
    fillFormFromParsed(parsed);
    status.textContent = `✅ ${parsed.category} • ${CONFIG.currencySymbol}${parsed.amount||'?'} via ${parsed.paymentMethod}`;
    status.classList.remove('hidden');
    showToast('Form filled by AI ✨','success');
  } catch(err) {
    status.textContent = `❌ ${err.message}`; status.classList.remove('hidden');
    showToast('Parse failed. Fill manually.','error');
  } finally { btn.innerHTML = '<span>✨ Parse</span>'; btn.style.opacity = ''; }
}

function fillFormFromParsed(p) {
  if (p.amount) { const a = document.getElementById('amount'); if(a) a.value = p.amount; }
  if (p.type)   { activeType=p.type; document.querySelectorAll('.type-btn').forEach(b=>b.classList.remove('active')); document.querySelector(`.type-btn[data-type="${p.type}"]`)?.classList.add('active'); }
  if (p.category) { const c=document.getElementById('category'); if(c){c.value=p.category; c.dispatchEvent(new Event('change'));} }
  if (p.subcategory) { const s=document.getElementById('subcategory'); if(s) s.value=p.subcategory; }
  if (p.description) { const d=document.getElementById('description'); if(d) d.value=p.description; }
  if (p.paymentMethod) { const m=document.getElementById('payment-method'); if(m) m.value=p.paymentMethod; }
  if (p.date) { const d=document.getElementById('txn-date'); if(d) d.value=typeof p.date==='string'?p.date.slice(0,10):p.date; }
  if (p.tags && p.tags.length) { activeTags=[...p.tags]; renderTags(); }
}

async function handleReceiptScan(e) {
  const file = e.target.files?.[0]; if (!file) return;
  const scanBtn = document.getElementById('scan-receipt-btn');
  const scanStatus = document.getElementById('scan-status');
  scanBtn.innerHTML = '⏳ Scanning…'; scanBtn.disabled = true;
  try {
    const result = await runReceiptOCR(file);
    fillFormFromParsed({ ...result, paymentMethod: result.paymentMethod||'Card' });
    scanStatus.textContent = `✅ Receipt scanned! Amount: ${CONFIG.currencySymbol}${result.amount||'N/A'}`;
    scanStatus.classList.remove('hidden');
    showToast('Receipt scanned! 📷','success');
  } catch(err) {
    scanStatus.textContent = `❌ Scan failed: ${err.message}`; scanStatus.classList.remove('hidden');
    showToast('Scan failed. Fill manually.','error');
  } finally {
    scanBtn.innerHTML = '<span class="scan-icon">📷</span><span>Scan Receipt (OCR)</span><span class="scan-badge">Beta</span>';
    scanBtn.disabled = false; e.target.value = '';
  }
}

function populatePaymentMethodDropdown() {
  const sel = document.getElementById('payment-method'); if (!sel) return;
  Array.from(sel.options).forEach(o => { if (!['Cash','Card'].includes(o.value)) o.remove(); });
  state.bankAccounts.forEach(a => {
    const o = document.createElement('option'); o.value = a.name; o.textContent = `🏦 ${a.name}`; sel.appendChild(o);
  });
}

/* ═══════════════════════════════════════════════════════════
   10. TAG MANAGER
═══════════════════════════════════════════════════════════ */
function initTagInput() {
  const input = document.getElementById('tags-input');
  const wrap  = document.getElementById('tags-wrap');
  if (!input || !wrap) return;
  input.addEventListener('keydown', e => {
    if (e.key==='Enter'||e.key===',') { e.preventDefault(); const v=input.value.trim().replace(/,$/,''); if(v){activeTags.push(v);renderTags();} input.value=''; }
    else if (e.key==='Backspace'&&input.value===''&&activeTags.length) { activeTags.pop(); renderTags(); }
  });
  wrap.addEventListener('click', ()=>input.focus());
}
function removeTag(tag) { activeTags=activeTags.filter(t=>t!==tag); renderTags(); }
function renderTags() {
  const d = document.getElementById('tags-display'); if(!d) return;
  d.innerHTML = activeTags.map(t=>`<span class="tag-pill">${escapeHtml(t)}<span class="tag-remove" onclick="removeTag('${escapeHtml(t)}')" role="button" tabindex="0">✕</span></span>`).join('');
}

/* ═══════════════════════════════════════════════════════════
   11. BANK / ACCOUNT MANAGER
═══════════════════════════════════════════════════════════ */
function initBankModal() {
  const modal = document.getElementById('modal-bank');
  document.getElementById('add-bank-btn')?.addEventListener('click',    ()=>openModal('modal-bank'));
  document.getElementById('modal-bank-close')?.addEventListener('click', ()=>closeModal('modal-bank'));
  document.getElementById('modal-bank-cancel')?.addEventListener('click',()=>closeModal('modal-bank'));
  modal?.addEventListener('click', e=>{ if(e.target===modal) closeModal('modal-bank'); });
  document.getElementById('modal-bank-save')?.addEventListener('click', async ()=>{
    const name    = document.getElementById('bank-name')?.value.trim();
    const balance = document.getElementById('bank-balance')?.value;
    const color   = document.getElementById('bank-color')?.value || CONFIG.defaultBankColor;
    if (!name) { showToast('Enter a bank name.','error'); return; }
    await saveAccount({ name, balance, color });
    renderBankAccountsList(null);
    populatePaymentMethodDropdown();
    closeModal('modal-bank');
    showToast(`${name} added! 🏦`,'success');
    document.getElementById('bank-name').value=''; document.getElementById('bank-balance').value='';
  });
}

/* ═══════════════════════════════════════════════════════════
   12. TRANSACTION DETAIL MODAL
═══════════════════════════════════════════════════════════ */
function openTransactionDetail(id) {
  const txn = state.transactions.find(t=>t.id===id); if (!txn) return;
  setState({ currentTxnId: id });
  const body = document.getElementById('modal-txn-body'); if (!body) return;
  const sign = txn.type==='income'?'+':txn.type==='transfer'?'↔':'−';
  const amtColor = txn.type==='income'?'var(--success)':txn.type==='transfer'?'var(--info)':'var(--danger)';
  const rows = [
    ['Amount',`<span style="color:${amtColor};font-size:1.1rem">${sign}${formatCurrency(txn.amount)}</span>`],
    ['Type', capitalise(txn.type)],
    ['Category',`${CATEGORY_EMOJI[txn.category]||''} ${txn.category}`],
    txn.subcategory?['Sub-category',txn.subcategory]:null,
    ['Description',escapeHtml(txn.description||'—')],
    ['Date',formatDate(txn.date,txn.time)],
    ['Payment',txn.paymentMethod],
    txn.tags?.length?['Tags',txn.tags.map(t=>`<span class="tag-pill">${escapeHtml(t)}</span>`).join(' ')]:null,
  ].filter(Boolean);
  body.innerHTML = rows.map(([l,v])=>`<div class="txn-detail-row"><span class="txn-detail-label">${l}</span><span class="txn-detail-value">${v}</span></div>`).join('');
  openModal('modal-txn');
}

function initTxnDetailModal() {
  const modal = document.getElementById('modal-txn');
  document.getElementById('modal-txn-close')?.addEventListener('click', ()=>closeModal('modal-txn'));
  document.getElementById('modal-txn-ok')?.addEventListener('click',    ()=>closeModal('modal-txn'));
  modal?.addEventListener('click', e=>{ if(e.target===modal) closeModal('modal-txn'); });
  document.getElementById('modal-txn-delete')?.addEventListener('click', async ()=>{
    if (!state.currentTxnId) return;
    await removeTransaction(state.currentTxnId);
    closeModal('modal-txn'); showToast('Transaction deleted.','info');
    renderDashboard();
    if (state.activeView==='transactions') renderAllTransactions();
  });
}

/* ═══════════════════════════════════════════════════════════
   13. AUTH MODAL
═══════════════════════════════════════════════════════════ */
function showAuthModal()   { const m=document.getElementById('modal-auth'); if(m) m.classList.remove('hidden'); }
function hideAuthModal()   { const m=document.getElementById('modal-auth'); if(m) m.classList.add('hidden'); }

function initAuthModal() {
  // Tab switching
  document.getElementById('tab-login')?.addEventListener('click', ()=>{
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('tab-login').classList.add('active');
    document.getElementById('tab-register').classList.remove('active');
  });
  document.getElementById('tab-register')?.addEventListener('click', ()=>{
    document.getElementById('register-form').classList.remove('hidden');
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('tab-register').classList.add('active');
    document.getElementById('tab-login').classList.remove('active');
  });

  // Login submit
  document.getElementById('login-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const email    = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const errEl    = document.getElementById('login-error');
    const btn      = e.target.querySelector('button[type=submit]');
    errEl.classList.add('hidden');
    btn.disabled = true; btn.textContent = '⏳ Logging in…';
    try {
      const up = await checkBackendAvailable();
      if (!up) throw new Error('Server not reachable. Double-click start-backend.bat to start it, then try again.');
      const user = await apiLogin(email, password);
      setState({ isOnline: true, currentUser: user });
      _categoryCache = null; _accountCache = null;
      hideAuthModal(); showToast(`Welcome back, ${user.full_name||user.email}! 👋`,'success');
      await loadTransactions(); await loadAccounts();
      updateOnlineStatus(true);
      renderDashboard();
    } catch(err) {
      errEl.textContent = err.message === 'SESSION_EXPIRED' ? 'Invalid credentials.' : err.message;
      errEl.classList.remove('hidden');
    } finally { btn.disabled = false; btn.textContent = '🔑 Login'; }
  });

  // Register submit
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
      const up = await checkBackendAvailable();
      if (!up) throw new Error('Server not reachable. Double-click start-backend.bat to start it, then try again.');
      const user = await apiRegister(email, password, name);
      setState({ isOnline: true, currentUser: user });
      _categoryCache = null; _accountCache = null;
      hideAuthModal(); showToast(`Account created! Welcome ${name||email} 🎉`,'success');
      await loadTransactions(); await loadAccounts();
      updateOnlineStatus(true);
      renderDashboard();
    } catch(err) {
      errEl.textContent = err.message; errEl.classList.remove('hidden');
    } finally { btn.disabled = false; btn.textContent = '🚀 Create Account'; }
  });

  // Skip / offline mode
  document.getElementById('skip-auth-btn')?.addEventListener('click', ()=>{
    hideAuthModal(); showToast('Running in offline mode. Data saved locally.','info');
  });

  // Logout
  document.getElementById('logout-btn')?.addEventListener('click', ()=>{
    auth.removeToken(); setState({ isOnline:false, currentUser:null, transactions:[], bankAccounts:[] });
    _categoryCache=null; _accountCache=null;
    updateOnlineStatus(false);
    showAuthModal(); showToast('Logged out.','info');
  });
}

function updateOnlineStatus(online) {
  const logoutBtn = document.getElementById('logout-btn');
  const avatar    = document.getElementById('user-avatar');
  if (logoutBtn) logoutBtn.classList.toggle('hidden', !online);
  if (avatar && state.currentUser) {
    const initials = (state.currentUser.full_name||state.currentUser.email||'U')[0].toUpperCase();
    avatar.textContent = initials; avatar.title = state.currentUser.email||'';
  }
  // Show online/offline badge in topbar
  const title = document.querySelector('.topbar-title');
  if (title) title.textContent = online ? 'WalletAI ●' : 'WalletAI';
  if (title) title.title = online ? 'Connected to server' : 'Offline mode';
}

/* ═══════════════════════════════════════════════════════════
   14. MODAL UTILITIES
═══════════════════════════════════════════════════════════ */
function openModal(id)  { const e=document.getElementById(id); if(e){e.classList.remove('hidden');document.body.style.overflow='hidden';} }
function closeModal(id) { const e=document.getElementById(id); if(e){e.classList.add('hidden');document.body.style.overflow='';} }

/* ═══════════════════════════════════════════════════════════
   15. AI INSIGHT BANNER
═══════════════════════════════════════════════════════════ */
async function refreshAIInsightBanner() {
  const textEl = document.getElementById('ai-insight-text');
  const btn    = document.getElementById('ai-refresh-btn');
  if (!textEl) return;
  textEl.textContent = 'Analysing your spending…';
  if (btn) btn.style.pointerEvents = 'none';
  try { textEl.textContent = await fetchAIInsight(); }
  catch { textEl.textContent = '💡 Tip: Track every expense to understand your spending habits.'; }
  finally { if(btn) btn.style.pointerEvents=''; }
}
function initAIBanner() {
  document.getElementById('ai-refresh-btn')?.addEventListener('click', refreshAIInsightBanner);
}

/* ═══════════════════════════════════════════════════════════
   16. TOAST
═══════════════════════════════════════════════════════════ */
let _toastTimer = null;
function showToast(msg, type='info', duration=2800) {
  const t = document.getElementById('toast'); if (!t) return;
  if (_toastTimer) clearTimeout(_toastTimer);
  t.textContent = msg; t.className = `toast ${type}`; t.classList.remove('hidden');
  _toastTimer = setTimeout(()=>t.classList.add('hidden'), duration);
}

/* ═══════════════════════════════════════════════════════════
   17. THEME
═══════════════════════════════════════════════════════════ */
function initTheme() {
  applyTheme(state.theme||'dark');
  document.getElementById('theme-toggle')?.addEventListener('click', ()=>{
    const next = state.theme==='dark'?'light':'dark';
    setState({ theme:next }); applyTheme(next);
    setChartDefaults();
    if(pieChartInst){pieChartInst.destroy();pieChartInst=null;} renderPieChart();
    if(barChartInst){barChartInst.destroy();barChartInst=null;}  renderBarChart();
  });
}
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme',t);
  const btn = document.getElementById('theme-toggle'); if(btn) btn.textContent = t==='dark'?'🌙':'☀️';
}

/* ═══════════════════════════════════════════════════════════
   18. UTILITIES & SEED DATA
═══════════════════════════════════════════════════════════ */
function escapeHtml(str) {
  if (typeof str!=='string') return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}
function capitalise(s) { return s?s[0].toUpperCase()+s.slice(1):''; }
function generateId()  { return Date.now().toString(36)+Math.random().toString(36).slice(2,7); }
function simulateDelay(ms) { return new Promise(r=>setTimeout(r,ms)); }
function formatCurrency(n) { return `${CONFIG.currencySymbol}${parseFloat(n).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:2})}`; }
function formatDate(d,t) { const dt=new Date(`${d}T${t||'00:00'}:00`); return isNaN(dt)?d:dt.toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}); }
function relativeTime(d) { const diff=(Date.now()-new Date(d))/1000; if(diff<60)return'just now';if(diff<3600)return`${Math.floor(diff/60)}m ago`;if(diff<86400)return`${Math.floor(diff/3600)}h ago`;if(diff<604800)return`${Math.floor(diff/86400)}d ago`;return new Date(d).toLocaleDateString('en-IN',{day:'numeric',month:'short'}); }

function seedDemoData() {
  if (state.transactions.length > 0) return;
  const y=new Date().getFullYear(), m=String(new Date().getMonth()+1).padStart(2,'0');
  const demo = [
    {type:'income', amount:65000,category:'Other',       description:'Monthly Salary',       paymentMethod:'Card',date:`${y}-${m}-01`,time:'09:00',tags:['salary']},
    {type:'expense',amount:12000,category:'Housing',     description:'Monthly Rent',          paymentMethod:'Card',date:`${y}-${m}-02`,time:'10:30',tags:['rent']},
    {type:'expense',amount:649,  category:'Entertainment',subcategory:'Netflix',description:'Netflix',paymentMethod:'Card',date:`${y}-${m}-03`,time:'11:00',tags:['subscription']},
    {type:'expense',amount:349,  category:'Entertainment',subcategory:'Spotify', description:'Spotify',paymentMethod:'Card',date:`${y}-${m}-03`,time:'11:05',tags:['subscription']},
    {type:'expense',amount:350,  category:'Food & Drinks',subcategory:'Zomato / Swiggy',description:'Dinner Zomato',paymentMethod:'Card',date:`${y}-${m}-05`,time:'20:15',tags:['food']},
    {type:'expense',amount:180,  category:'Transport',   subcategory:'Ola / Uber',description:'Uber to office',paymentMethod:'Cash',date:`${y}-${m}-06`,time:'08:45',tags:[]},
    {type:'expense',amount:1200, category:'Shopping',    description:'Amazon order',          paymentMethod:'Card',date:`${y}-${m}-07`,time:'14:00',tags:['online']},
    {type:'expense',amount:299,  category:'Recharge',    subcategory:'Phone Recharge',description:'Airtel Recharge',paymentMethod:'Cash',date:`${y}-${m}-08`,time:'12:00',tags:[]},
    {type:'expense',amount:500,  category:'Health',      description:'Pharmacy',              paymentMethod:'Cash',date:`${y}-${m}-10`,time:'17:00',tags:[]},
  ];
  const withIds = demo.map(d=>({...d,id:generateId(),createdAt:new Date().toISOString()}));
  setState({ transactions: withIds, bankAccounts: [
    {id:generateId(),name:'HDFC Savings',balance:45000,color:'#22C55E'},
    {id:generateId(),name:'ICICI Salary',balance:65000,color:'#3B82F6'},
  ]});
}

/* ═══════════════════════════════════════════════════════════
   19. BOOT
═══════════════════════════════════════════════════════════ */
async function init() {
  loadLocalState();

  // Check if backend is reachable
  const backendUp = await checkBackendAvailable();

  if (backendUp && auth.isAuthenticated()) {
    // Token exists and backend is up — silently restore the session
    try {
      const txns = await apiFetchTransactions();
      const accs = await apiFetchAccounts();
      const txnNorm = txns.map(normaliseApiTransaction);
      const accNorm = accs.map(a=>({id:a.id,name:a.name,balance:a.balance,color:a.color||CONFIG.defaultBankColor}));
      setState({ isOnline:true, transactions:txnNorm, bankAccounts:accNorm });
      showToast('Session restored ●','success',2000);
      // Don't show auth modal — go straight to dashboard
    } catch(e) {
      // Token invalid or expired — clear and ask to log in
      auth.removeToken();
      setState({ isOnline:false });
      showAuthModal();
    }
  } else if (backendUp && !auth.isAuthenticated()) {
    // Backend up but no token
    showAuthModal();
  } else {
    // Backend down — offline mode with local/seed data
    seedDemoData();
    showToast('Backend offline – running in local mode 📴','info',4000);
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

  // Filter wiring
  document.getElementById('filter-category')?.addEventListener('change', renderAllTransactions);
  document.getElementById('filter-method')?.addEventListener('change',   renderAllTransactions);

  navigateTo(state.activeView || 'dashboard');
  console.info(`[WalletAI] Ready. Mode: ${state.isOnline ? 'ONLINE (backend connected)' : 'OFFLINE (local)'}`);
}

/* ── Splash → App transition ──────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  setTimeout(()=>{
    const splash = document.getElementById('splash-screen');
    const app    = document.getElementById('app');
    splash.style.animation = 'fadeOut 0.4s ease forwards';
    setTimeout(()=>{ splash.style.display='none'; app.classList.remove('hidden'); init(); }, 380);
  }, 1400);
});

// Inject fadeOut keyframe
const _s = document.createElement('style');
_s.textContent = `@keyframes fadeOut { to { opacity:0; transform:scale(0.97); } }`;
document.head.appendChild(_s);
