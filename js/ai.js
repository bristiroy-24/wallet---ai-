/**
 * js/ai.js
 * ─────────
 * AI handlers: insight banner, magic input parser, receipt OCR.
 * Uses backend API when online; falls back to local mock/Gemini direct call.
 */
'use strict';

// ── Insight banner ────────────────────────────────────────────────────────────

async function fetchAIInsight() {
  if (state.isOnline) {
    try {
      const insights = await apiRefreshInsights();
      if (insights && insights.length > 0) return insights[0].insight_text;
    } catch(e) {}
  }
  if (CONFIG.USE_REAL_AI && CONFIG.GEMINI_API_KEY !== 'YOUR_GEMINI_API_KEY_HERE') {
    try {
      const summary = state.transactions.slice(0, 15)
        .map(t => `${t.type}: ${t.description} ₹${t.amount} on ${t.date}`).join('\n');
      const url = `${CONFIG.GEMINI_ENDPOINT}/${CONFIG.GEMINI_MODEL}:generateContent?key=${CONFIG.GEMINI_API_KEY}`;
      const res = await fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: `Financial assistant. One insight (max 120 chars, start with emoji):\n${summary}` }] }],
          generationConfig: { maxOutputTokens: 150, temperature: 0.7 },
        }),
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

// ── Magic input (NLP parser) ──────────────────────────────────────────────────

async function parseMagicInput(text) {
  if (state.isOnline) {
    try { return normaliseAIParsed(await apiMagicParse(text)); } catch(e) {}
  }
  await simulateDelay(800);
  return mockParseNaturalLanguage(text);
}

// ── Receipt OCR ───────────────────────────────────────────────────────────────

async function runReceiptOCR(imageFile) {
  if (state.isOnline) {
    try { return normaliseAIParsed(await apiScanReceipt(imageFile)); } catch(e) {}
  }
  await simulateDelay(1200);
  return { amount: (Math.random() * 400 + 50).toFixed(2), description: 'Scanned receipt', paymentMethod: 'Card', category: 'Shopping' };
}

// ── Normalise backend AI response → internal shape ────────────────────────────

function normaliseAIParsed(p) {
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

// ── Offline mock NLP parser ───────────────────────────────────────────────────

function mockParseNaturalLanguage(text) {
  const lower = text.toLowerCase();
  const r = { amount: null, type: 'expense', category: 'Other', subcategory: null, description: text, paymentMethod: 'Cash', tags: [] };

  const m = text.match(/(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)/i);
  if (m) r.amount = parseFloat(m[1].replace(/,/g, ''));

  if (/salary|income|received|got paid/i.test(lower))   r.type = 'income';
  if (/transfer|sent to/i.test(lower))                  r.type = 'transfer';
  if (/upi|gpay|card|credit|debit|phonepe|paytm/i.test(lower)) r.paymentMethod = 'Card';

  // Subcategory names must match DEFAULT_CATEGORIES in backend/app/db/seed.py exactly
  if (/zomato|swiggy|lunch|dinner|restaurant|food|pizza|cafe|coffee/i.test(lower)) {
    r.category = 'Food & Drinks';
    r.subcategory = /zomato|swiggy/i.test(lower) ? 'Zomato / Swiggy' : /cafe|coffee/i.test(lower) ? 'Cafe / Coffee' : 'Restaurant';
  } else if (/netflix|spotify|amazon prime|subscription/i.test(lower)) {
    r.category = 'Entertainment';
    r.subcategory = /netflix/i.test(lower) ? 'Netflix' : /spotify/i.test(lower) ? 'Spotify' : /amazon/i.test(lower) ? 'Amazon Prime' : null;
  } else if (/uber|ola|metro|bus|fuel|petrol/i.test(lower)) {
    r.category = 'Transport';
    r.subcategory = /uber|ola/i.test(lower) ? 'Ola / Uber' : /fuel|petrol/i.test(lower) ? 'Fuel' : 'Metro / Bus';
  } else if (/rent|maid|electricity|wifi|wi-fi|broadband/i.test(lower)) {
    r.category = 'Housing';
    r.subcategory = /maid/i.test(lower) ? 'Maid Salary' : /electricity/i.test(lower) ? 'Electricity' : /wifi|wi-fi|broadband/i.test(lower) ? 'Internet / Wi-Fi' : null;
  } else if (/grocery|groceries|dmart|bigbasket/i.test(lower)) {
    r.category = 'Housing';
    r.subcategory = 'Groceries';
  } else if (/recharge|airtel|jio|wifi recharge/i.test(lower)) {
    r.category = 'Recharge';
    r.subcategory = /wifi/i.test(lower) ? 'Wi-Fi Bill' : 'Phone Recharge';
  } else if (/medicine|doctor|pharmacy|hospital/i.test(lower)) {
    r.category = 'Health';
    r.subcategory = /medicine|pharmacy|chemist/i.test(lower) ? 'Pharmacy' : 'Doctor';
  } else if (/amazon|flipkart|myntra|shopping|clothes/i.test(lower)) {
    r.category = 'Shopping';
    r.subcategory = /amazon|flipkart|myntra/i.test(lower) ? 'Amazon / Flipkart' : null;
  } else if (/book|course|school|tuition|udemy/i.test(lower)) {
    r.category = 'Education';
    r.subcategory = /book/i.test(lower) ? 'Books' : /course|udemy/i.test(lower) ? 'Courses' : 'Tuition';
  } else if (/mutual fund|sip|zerodha|groww|stocks|investment|fd/i.test(lower)) {
    r.category = 'Investments';
    r.subcategory = /mutual fund|sip/i.test(lower) ? 'Mutual Funds' : /stocks/i.test(lower) ? 'Stocks' : null;
  } else if (/gym|salon|haircut|dining|spa|yoga/i.test(lower)) {
    r.category = 'Lifestyle';
    r.subcategory = /gym|yoga|fitness/i.test(lower) ? 'Gym' : /salon|haircut|spa/i.test(lower) ? 'Salon' : 'Dining Out';
  }
    r.category = 'Shopping';
  } else if (/book|course|school|tuition/i.test(lower)) {
    r.category = 'Education';
  }

  r.description = text.replace(/(?:₹|Rs\.?|INR)?\s*[\d,]+(?:\.\d{1,2})?\s*/gi, '').trim() || text;
  r.tags = [r.category.toLowerCase().split(' ')[0]];
  return r;
}
