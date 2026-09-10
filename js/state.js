/**
 * js/state.js
 * ────────────
 * Single source of truth. All mutations go through setState().
 * Persists to LocalStorage automatically.
 */
'use strict';

let state = {
  transactions:   [],
  bankAccounts:   [],
  activeView:     'dashboard',
  currentTxnId:   null,
  theme:          'dark',
  aiInsightIndex: 0,
  isOnline:       false,
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

function setState(partial) {
  state = { ...state, ...partial };
  saveLocalState();
}

// ── Utilities (used by multiple modules) ──────────────────────────────────────

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function simulateDelay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

function formatCurrency(n) {
  return `${CONFIG.currencySymbol}${parseFloat(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(d, t) {
  const dt = new Date(`${d}T${t || '00:00'}:00`);
  return isNaN(dt) ? d : dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function relativeTime(d) {
  const diff = (Date.now() - new Date(d)) / 1000;
  if (diff < 60)    return 'just now';
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800)return `${Math.floor(diff / 86400)}d ago`;
  return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

function capitalise(s) { return s ? s[0].toUpperCase() + s.slice(1) : ''; }

function seedDemoData() {
  if (state.transactions.length > 0) return;
  const y = new Date().getFullYear(), m = String(new Date().getMonth() + 1).padStart(2, '0');
  const demo = [
    { type:'income',  amount:65000, category:'Other',         description:'Monthly Salary',       paymentMethod:'Card', date:`${y}-${m}-01`, time:'09:00', tags:['salary'] },
    { type:'expense', amount:12000, category:'Housing',       description:'Monthly Rent',          paymentMethod:'Card', date:`${y}-${m}-02`, time:'10:30', tags:['rent'] },
    { type:'expense', amount:649,   category:'Entertainment', description:'Netflix',               paymentMethod:'Card', date:`${y}-${m}-03`, time:'11:00', tags:['subscription'] },
    { type:'expense', amount:349,   category:'Entertainment', description:'Spotify',               paymentMethod:'Card', date:`${y}-${m}-03`, time:'11:05', tags:['subscription'] },
    { type:'expense', amount:350,   category:'Food & Drinks', description:'Dinner Zomato',         paymentMethod:'Card', date:`${y}-${m}-05`, time:'20:15', tags:['food'] },
    { type:'expense', amount:180,   category:'Transport',     description:'Uber to office',        paymentMethod:'Cash', date:`${y}-${m}-06`, time:'08:45', tags:[] },
    { type:'expense', amount:1200,  category:'Shopping',      description:'Amazon order',          paymentMethod:'Card', date:`${y}-${m}-07`, time:'14:00', tags:['online'] },
    { type:'expense', amount:299,   category:'Recharge',      description:'Airtel Recharge',       paymentMethod:'Cash', date:`${y}-${m}-08`, time:'12:00', tags:[] },
    { type:'expense', amount:500,   category:'Health',        description:'Pharmacy',              paymentMethod:'Cash', date:`${y}-${m}-10`, time:'17:00', tags:[] },
  ];
  setState({
    transactions: demo.map(d => ({ ...d, id: generateId(), createdAt: new Date().toISOString() })),
    bankAccounts: [
      { id: generateId(), name: 'HDFC Savings', balance: 45000, color: '#22C55E' },
      { id: generateId(), name: 'ICICI Salary', balance: 65000, color: '#3B82F6' },
    ],
  });
}
