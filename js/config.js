/**
 * js/config.js
 * ─────────────
 * App-wide constants. All other modules read from these globals.
 */
'use strict';

const CONFIG = {
  storageKey:      'walletai_data',
  currencySymbol:  '₹',
  defaultBankColor:'#6C63FF',
  USE_REAL_AI:     false,
  GEMINI_API_KEY:  'YOUR_GEMINI_API_KEY_HERE',
  GEMINI_MODEL:    'gemini-2.5-flash',
  GEMINI_ENDPOINT: 'https://generativelanguage.googleapis.com/v1beta/models',
};

const SUBCATEGORIES = {
  // Must match DEFAULT_CATEGORIES in backend/app/db/seed.py exactly
  'Food & Drinks': ['Restaurant','Zomato / Swiggy','Cafe / Coffee','Grocery','Other'],
  'Shopping':      ['Clothing','Electronics','Amazon / Flipkart','Myntra','Personal Care','Other'],
  'Housing':       ['Groceries','Maid Salary','Electricity','Water','Gas','Internet / Wi-Fi','Maintenance'],
  'Entertainment': ['Netflix','Amazon Prime','Spotify','Disney+','YouTube Premium','Gaming','Other'],
  'Recharge':      ['Phone Recharge','Wi-Fi Bill','DTH / Cable','Other'],
  'Education':     ['Books','Courses','Tuition','Other'],
  'Transport':     ['Fuel','Ola / Uber','Metro / Bus','Auto','Flight / Train','Other'],
  'Health':        ['Doctor','Pharmacy','Hospital','Insurance','Other'],
  'Investments':   ['Stocks','Mutual Funds','Fixed Deposit','Crypto','Other'],
  'Lifestyle':     ['Gym','Salon','Dining Out','Travel','Hobbies','Other'],
  'Other':         [],
};

const CATEGORY_EMOJI = {
  // Must match DEFAULT_CATEGORIES in backend/app/db/seed.py exactly
  'Food & Drinks': '🍔',
  'Shopping':      '🛍️',
  'Housing':       '🏠',
  'Entertainment': '🎬',
  'Recharge':      '📱',
  'Education':     '📚',
  'Transport':     '🚗',
  'Health':        '💊',
  'Investments':   '💰',
  'Lifestyle':     '🙎',
  'Other':         '📦',
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
