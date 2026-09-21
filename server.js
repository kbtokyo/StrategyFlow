require('dotenv').config();
const path = require('path');
const express = require('express');

const PORT = process.env.PORT || 3000;
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5';
const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';

const MAX_PROMPT_CHARS = 20000;
const MAX_TOKENS_CAP = 1600;

const app = express();
app.use(express.json({ limit: '200kb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Simple in-memory per-IP rate limit: good enough for a single-instance
// launch; swap for a shared store (e.g. Redis) if this scales to multiple
// server instances.
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const RATE_LIMIT_MAX_REQUESTS = 20;
const requestLog = new Map();

function isRateLimited(ip) {
  const now = Date.now();
  const timestamps = (requestLog.get(ip) || []).filter(t => now - t < RATE_LIMIT_WINDOW_MS);
  timestamps.push(now);
  requestLog.set(ip, timestamps);
  return timestamps.length > RATE_LIMIT_MAX_REQUESTS;
}

app.post('/api/agent', async (req, res) => {
  if (!ANTHROPIC_API_KEY) {
    return res.status(500).json({ error: 'Server is missing its ANTHROPIC_API_KEY — see README.md' });
  }

  const ip = req.ip || req.socket.remoteAddress || 'unknown';
  if (isRateLimited(ip)) {
    return res.status(429).json({ error: 'Too many requests — wait a moment and try again.' });
  }

  const { prompt, maxTokens } = req.body || {};
  if (typeof prompt !== 'string' || !prompt.trim()) {
    return res.status(400).json({ error: 'Missing prompt' });
  }
  if (prompt.length > MAX_PROMPT_CHARS) {
    return res.status(400).json({ error: 'That request was too large — try shortening the canvas text.' });
  }
  const tokens = Math.min(Math.max(Number(maxTokens) || 800, 1), MAX_TOKENS_CAP);

  try {
    const upstream = await fetch(ANTHROPIC_API_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: ANTHROPIC_MODEL,
        max_tokens: tokens,
        messages: [{ role: 'user', content: prompt }]
      })
    });

    if (!upstream.ok) {
      const status = upstream.status === 429 ? 429 : 502;
      return res.status(status).json({ error: 'A temporary error occurred — please try again.' });
    }

    const data = await upstream.json();
    const text = (data.content || []).map(block => block.text || '').join('').trim();
    if (!text) {
      return res.status(502).json({ error: "Claude didn't return a response — try again." });
    }
    res.json({ text });
  } catch (e) {
    res.status(502).json({ error: 'A temporary error occurred — please try again.' });
  }
});

app.listen(PORT, () => {
  console.log(`StrategyFlow running at http://localhost:${PORT}`);
  if (!ANTHROPIC_API_KEY) {
    console.warn('Warning: ANTHROPIC_API_KEY is not set — AI agent features will fail until it is configured.');
  }
});
