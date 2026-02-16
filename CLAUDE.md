# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI ETF & Dividend Stock Investment Assistant** — React 19 (TypeScript) + FastAPI monorepo web app. An AI agent-powered platform for stock/ETF investment strategy recommendation, analysis, and paper trading simulation. UI reference: [Toss Securities](https://www.tossinvest.com/) — dark theme, clean block layout, mobile-friendly card-based design.

## Development Commands

```bash
# Backend — Python venv lives at project root .venv/ (not inside backend/)
cd backend
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev          # Dev server at http://localhost:5173
npm run build        # tsc -b && vite build
npm run lint         # eslint .
```

- Vite proxy forwards `/api` → `http://127.0.0.1:8000` (configured in `frontend/vite.config.ts`)
- Swagger docs: `http://localhost:8000/docs`
- SQLite DB auto-created on first backend startup via `Base.metadata.create_all` in lifespan
- No test framework is set up yet (no pytest config, no vitest/jest)
- Node.js 18.17.1 in use — upgrade to Node 20+ recommended

## Git Workflow

- **main**: Production branch (error-free code only)
- **develop**: Feature integration branch
- Work on feature branches → merge to develop → merge to main

## Architecture

### Backend (FastAPI)

Entry point: `backend/app/main.py` → `create_app()` factory pattern.

**Request flow**: API router (`api/router.py`) → v1 routers (`api/v1/`) → services (`services/`) → data layer (`data/`)

**Auth dependency injection** (in `core/deps.py`):
- `get_current_user` — returns `User | None` (optional auth, for public endpoints that behave differently when logged in)
- `require_current_user` — wraps `get_current_user`, raises 401 if None (use for protected endpoints)

**Auth endpoints** (`api/v1/auth.py`): `POST /register`, `POST /login`, `POST /refresh`, `GET /me`, `GET /check-username`

**Market data** (`data/market_data.py`): yfinance wrapper with in-memory TTL cache (5 min). Provides indices, top ETFs, chart history, and market movers.

**Config**: `core/config.py` uses pydantic-settings, reads from `backend/.env`. Key vars: `SECRET_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`.

### Frontend (React + Vite)

**Routing** (`App.tsx`): Public routes (`/`, `/login`, `/register`) + protected routes wrapped in `<ProtectedRoute>` (`/portfolio`, `/backtest`, `/simulation`, `/settings`). TopNav hidden on auth pages.

**API client** (`api/client.ts`): Axios instance with `baseURL: '/api/v1'`. Auto-attaches JWT from localStorage. Response interceptor handles 401 → silent token refresh → retry failed requests (with queue for concurrent failures).

**State**: Zustand stores (`stores/`) for client state (currently `authStore`). TanStack Query for server state.

**Styling**: CSS Modules per component + global design tokens in `styles/global.css`. Key tokens:
- Backgrounds: `--bg-primary: #020617`, `--bg-secondary: #111827`
- Text: `--text-primary: #e5e7eb`, `--text-secondary: #9ca3af`
- Accent: `--accent-blue: #2563eb`
- Border: `--border-default: #374151`
- Border radius: `--radius-lg: 16px` (cards)

**Types**: Shared TypeScript interfaces in `types/` (`auth.ts`, `market.ts`).

### Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript 5.9, Vite 6, React Router v7, Zustand 5, TanStack Query 5, Axios, Recharts 3 |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2, python-jose (JWT), bcrypt, yfinance |
| DB | SQLite (dev) → PostgreSQL (prod) |
| AI | OpenAI API (for AI agent coach — planned) |

## Coding Conventions

- Frontend: Functional components, TypeScript strict mode, CSS Modules (`.module.css`)
- Backend: Router → Service → Data layer pattern, Pydantic models for request/response
- All API endpoints: `/api/v1/` prefix
- New backend routers must be registered in `api/router.py`

## Current Status & Roadmap

### Completed
- Auth system: register, login, JWT refresh, `/me` endpoint
- Market data API: indices (S&P 500, NASDAQ, Dow, VIX), top ETFs, chart history, market movers (gainers/losers)
- Dashboard page: market overview cards, SPY chart with period selector, ETF ranking table, movers with tab switching, skeleton loading states
- Login & Register pages with form validation

### Phase 1 — Stock/ETF Detail & Search
- **Stock/ETF detail page** (`/stock/:symbol`): price chart (1D/1W/1M/3M/1Y), key stats (market cap, P/E, dividend yield, 52w range), company overview, related ETFs
- **Search**: global search bar in TopNav, search by ticker/name, recent searches, autocomplete suggestions
- **Watchlist**: add/remove favorites, persist per user in DB, watchlist section on Dashboard

### Phase 2 — Portfolio Recommendation (AI-powered)
- **Investment profile survey**: risk tolerance, investment horizon, preferred sectors, monthly budget
- **AI portfolio builder**: OpenAI agent analyzes profile → recommends ETF/stock allocation with rationale
- **Portfolio detail view**: allocation pie chart, expected return/risk metrics, individual holding cards
- **Rebalancing suggestions**: AI agent compares current vs target allocation, suggests trades

### Phase 3 — Backtesting Engine
- **Backtest configuration**: select tickers, set weights, define date range, initial capital
- **Backend engine**: historical data via yfinance → calculate CAGR, MDD, Sharpe ratio, annual returns
- **Results visualization**: cumulative return chart, drawdown chart, yearly performance table, benchmark comparison (vs SPY)
- **AI analysis**: agent interprets backtest results, explains risk/return characteristics in plain language

### Phase 4 — Paper Trading Simulation
- **Virtual account**: starting balance (default $100,000), track cash + holdings
- **Trade execution**: market buy/sell at real-time prices (yfinance), order history log
- **Portfolio tracker**: current holdings, unrealized P&L, total return, allocation breakdown
- **AI trade advisor**: agent evaluates proposed trades, warns about concentration risk, suggests position sizing

### Phase 5 — AI Investment Coach (Chatbot)
- **Floating chat widget**: bottom-right panel (like Toss Securities CS chat)
- **Context-aware conversations**: agent can reference user's portfolio, backtest results, watchlist
- **Capabilities**: explain investment concepts, analyze specific stocks/ETFs, compare strategies, interpret market news
- **SSE streaming**: real-time token-by-token response via Server-Sent Events
- **Conversation history**: persist per user, resumable across sessions

### Phase 6 — Dashboard Enhancement & Polish
- **Trending categories**: sector performance heatmap (like Toss's "지금 뜨는 카테고리")
- **Investor trends**: popular stocks among platform users, most-watched ETFs
- **Recently viewed**: track and display user's recently viewed stocks/ETFs
- **Settings page**: notification preferences, display currency (USD/KRW), risk level defaults, account management

## Claude Usage Guide

- Use TypeScript strict mode
- All API endpoints must have tests
- Follow the existing error handling patterns in `src/utils/errors.ts`
- CLAUDE.md content must be written in English.
- 코드 생성, 코드 리뷰, 설명, 오류 보고 등 모든 대화 응답은 한국어로 작성해 주세요.
