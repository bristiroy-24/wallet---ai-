/**
 * js/forms.js
 * ────────────
 * Expense form, tag manager, magic AI input, receipt OCR scan.
 */
'use strict';

let activeTags = [];
let activeType = 'expense';

// ── Form initialisation ───────────────────────────────────────────────────────

function initForm() {
  const today = new Date();
  const di = document.getElementById('txn-date');
  const ti = document.getElementById('txn-time');
  if (di) di.value = today.toISOString().split('T')[0];
  if (ti) ti.value = today.toTimeString().slice(0, 5);

  // Type toggle
  document.querySelectorAll('.type-btn').forEach(btn => btn.addEventListener('click', () => {
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); activeType = btn.dataset.type;
  }));

  // Category → subcategory cascade
  document.getElementById('category')?.addEventListener('change', function() {
    const subs = SUBCATEGORIES[this.value];
    const grp = document.getElementById('subcategory-group');
    const sel = document.getElementById('subcategory');
    if (subs && subs.length) {
      sel.innerHTML = `<option value="">— Select sub-category —</option>` + subs.map(s => `<option value="${s}">${s}</option>`).join('');
      grp.style.display = 'flex';
    } else { grp.style.display = 'none'; sel.value = ''; }
  });

  document.getElementById('expense-form')?.addEventListener('submit', handleFormSubmit);
  document.getElementById('magic-parse-btn')?.addEventListener('click', handleMagicParse);
  document.getElementById('magic-input')?.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleMagicParse(); } });
  document.getElementById('scan-receipt-btn')?.addEventListener('click', () => document.getElementById('receipt-file-input')?.click());
  document.getElementById('receipt-file-input')?.addEventListener('change', handleReceiptScan);

  populatePaymentMethodDropdown();
}

// ── Form submit ───────────────────────────────────────────────────────────────

async function handleFormSubmit(e) {
  e.preventDefault();
  const amount   = parseFloat(document.getElementById('amount')?.value);
  const category = document.getElementById('category')?.value;
  const date     = document.getElementById('txn-date')?.value;
  const method   = document.getElementById('payment-method')?.value;

  if (!amount || amount <= 0) { showToast('Enter a valid amount.', 'error'); return; }
  if (!category)              { showToast('Please select a category.', 'error'); return; }
  if (!date)                  { showToast('Please select a date.', 'error'); return; }

  const btn = document.getElementById('submit-expense-btn');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Saving…'; }

  await saveTransaction({
    type: activeType, amount, category,
    subcategory: document.getElementById('subcategory')?.value || null,
    description: document.getElementById('description')?.value.trim(),
    date, time: document.getElementById('txn-time')?.value || '',
    paymentMethod: method, tags: [...activeTags],
  });

  showToast(state.isOnline ? 'Saved to server! 🎉' : 'Saved locally! 🎉', 'success');
  resetForm();
  navigateTo('dashboard');
  if (btn) { btn.disabled = false; btn.textContent = '💾 Save Transaction'; }
}

function resetForm() {
  document.getElementById('expense-form')?.reset();
  activeTags = []; renderTags(); activeType = 'expense';
  document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.type-btn[data-type="expense"]')?.classList.add('active');
  document.getElementById('subcategory-group').style.display = 'none';
  const today = new Date();
  const di = document.getElementById('txn-date'); if (di) di.value = today.toISOString().split('T')[0];
  const ti = document.getElementById('txn-time'); if (ti) ti.value = today.toTimeString().slice(0, 5);
  document.getElementById('magic-input').value = '';
  document.getElementById('magic-status').classList.add('hidden');
}

// ── Magic AI input ────────────────────────────────────────────────────────────

async function handleMagicParse() {
  const text = document.getElementById('magic-input')?.value.trim();
  if (!text) { showToast('Type something in Magic Input first.', 'info'); return; }
  const btn    = document.getElementById('magic-parse-btn');
  const status = document.getElementById('magic-status');
  btn.innerHTML = '⏳ Parsing…'; btn.style.opacity = '0.65';
  try {
    const parsed = await parseMagicInput(text);
    fillFormFromParsed(parsed);
    status.textContent = `✅ ${parsed.category} • ${CONFIG.currencySymbol}${parsed.amount || '?'} via ${parsed.paymentMethod}`;
    status.classList.remove('hidden');
    showToast('Form filled by AI ✨', 'success');
  } catch(err) {
    status.textContent = `❌ ${err.message}`; status.classList.remove('hidden');
    showToast('Parse failed. Fill manually.', 'error');
  } finally { btn.innerHTML = '<span>✨ Parse</span>'; btn.style.opacity = ''; }
}

function fillFormFromParsed(p) {
  if (p.amount)       { const a = document.getElementById('amount');          if (a) a.value = p.amount; }
  if (p.type)         { activeType = p.type; document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('active')); document.querySelector(`.type-btn[data-type="${p.type}"]`)?.classList.add('active'); }
  if (p.category)     { const c = document.getElementById('category');        if (c) { c.value = p.category; c.dispatchEvent(new Event('change')); } }
  if (p.subcategory)  { const s = document.getElementById('subcategory');     if (s) s.value = p.subcategory; }
  if (p.description)  { const d = document.getElementById('description');     if (d) d.value = p.description; }
  if (p.paymentMethod){ const m = document.getElementById('payment-method');  if (m) m.value = p.paymentMethod; }
  if (p.date)         { const d = document.getElementById('txn-date');        if (d) d.value = typeof p.date === 'string' ? p.date.slice(0, 10) : p.date; }
  if (p.tags && p.tags.length) { activeTags = [...p.tags]; renderTags(); }
}

// ── Receipt OCR ───────────────────────────────────────────────────────────────

async function handleReceiptScan(e) {
  const file = e.target.files?.[0]; if (!file) return;
  const scanBtn    = document.getElementById('scan-receipt-btn');
  const scanStatus = document.getElementById('scan-status');
  scanBtn.innerHTML = '⏳ Scanning…'; scanBtn.disabled = true;
  try {
    const result = await runReceiptOCR(file);
    fillFormFromParsed({ ...result, paymentMethod: result.paymentMethod || 'Card' });
    scanStatus.textContent = `✅ Receipt scanned! Amount: ${CONFIG.currencySymbol}${result.amount || 'N/A'}`;
    scanStatus.classList.remove('hidden');
    showToast('Receipt scanned! 📷', 'success');
  } catch(err) {
    scanStatus.textContent = `❌ Scan failed: ${err.message}`; scanStatus.classList.remove('hidden');
    showToast('Scan failed. Fill manually.', 'error');
  } finally {
    scanBtn.innerHTML = '<span class="scan-icon">📷</span><span>Scan Receipt (OCR)</span><span class="scan-badge">Beta</span>';
    scanBtn.disabled = false; e.target.value = '';
  }
}

// ── Payment method dropdown ───────────────────────────────────────────────────

function populatePaymentMethodDropdown() {
  const sel = document.getElementById('payment-method'); if (!sel) return;
  Array.from(sel.options).forEach(o => { if (!['Cash', 'Card'].includes(o.value)) o.remove(); });
  state.bankAccounts.forEach(a => {
    const o = document.createElement('option'); o.value = a.name; o.textContent = `🏦 ${a.name}`; sel.appendChild(o);
  });
}

// ── Tag manager ───────────────────────────────────────────────────────────────

function initTagInput() {
  const input = document.getElementById('tags-input');
  const wrap  = document.getElementById('tags-wrap');
  if (!input || !wrap) return;
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const v = input.value.trim().replace(/,$/, '');
      if (v) { activeTags.push(v); renderTags(); }
      input.value = '';
    } else if (e.key === 'Backspace' && input.value === '' && activeTags.length) {
      activeTags.pop(); renderTags();
    }
  });
  wrap.addEventListener('click', () => input.focus());
}

function removeTag(tag) { activeTags = activeTags.filter(t => t !== tag); renderTags(); }

function renderTags() {
  const d = document.getElementById('tags-display'); if (!d) return;
  d.innerHTML = activeTags.map(t =>
    `<span class="tag-pill">${escapeHtml(t)}<span class="tag-remove" onclick="removeTag('${escapeHtml(t)}')" role="button" tabindex="0">✕</span></span>`
  ).join('');
}
