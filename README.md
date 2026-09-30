# StrategyFlow

A standalone Strategic Intelligence Canvas — a Value Proposition Canvas workspace with
Product-Market-Fit scoring, a facilitated workshop mode, and six AI strategy agents
(Socrates, Strategist, Devil's Advocate, Market Intel, VC Diligence, Synthesis).

The frontend (`public/index.html`) is a self-contained single-page app. A small
Express server (`server.js`) serves it and proxies AI requests to the Anthropic
API, so the API key never reaches the browser.

## How it works

- **Frontend**: plain HTML/CSS/JS, no build step. All canvas data lives in memory
  and autosaves to the browser's `localStorage`, plus manual JSON export/import
  ("Save" / "Load" in the header) and a full HTML export ("Export").
- **Backend**: `POST /api/agent` accepts `{ prompt, maxTokens }`, calls the
  Anthropic Messages API with a server-held key, and returns `{ text }`. It
  includes a basic per-IP rate limit (20 requests/minute) to protect the API
  key from abuse on a public deployment.
- **No accounts / no database**: this is a local-first tool. Each user's data
  stays in their own browser.

## Local setup

```bash
npm install
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY to a real key
npm start
```

Then open http://localhost:3000.

## Deploying

Any Node hosting platform works (Render, Railway, Fly.io, a VPS, etc.):

1. Push this repo to the platform.
2. Set the `ANTHROPIC_API_KEY` environment variable in the platform's dashboard
   (and optionally `ANTHROPIC_MODEL`, `PORT`).
3. Build command: `npm install`. Start command: `npm start`.

There is no database or persistent volume required.

## Notes / next steps

- The per-IP rate limit is in-memory and per-instance — fine for a single
  server, but won't coordinate across multiple instances behind a load
  balancer. Swap in a shared store (e.g. Redis) if you scale horizontally.
- If you later want cross-device sync, real user accounts, or usage-based
  billing, that needs an actual auth + database layer — this build
  intentionally ships without one to keep the app simple to run.
