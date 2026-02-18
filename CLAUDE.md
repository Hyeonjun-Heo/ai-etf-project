# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI ETF & Dividend Stock Investment Assistant** — React 19 (TypeScript) + FastAPI monorepo web app. AI agent-powered platform for stock/ETF investment strategy recommendation, analysis, and paper trading simulation. UI reference: [Toss Securities](https://www.tossinvest.com/) — dark theme, clean block layout, mobile-friendly card-based design.

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

## Current Status

### Completed
- Auth system: register, login, JWT refresh, `/me` endpoint
- Market data API: indices (S&P 500, NASDAQ, Dow, VIX), top ETFs, chart history, market movers
- Dashboard page: market overview cards, SPY chart with period selector, ETF ranking table, movers with tab switching, skeleton loading
- Login & Register pages with form validation
- Stock detail page scaffold (`/stock/:symbol`)

### Next Up
- Phase 1: Stock/ETF detail page (chart, stats, company overview), search with autocomplete, watchlist
- Phase 2: AI portfolio recommendation (investment profile survey → OpenAI agent → allocation)
- Phase 3: Backtesting engine (CAGR, MDD, Sharpe ratio, benchmark comparison)
- Phase 4: Paper trading simulation (virtual account, trade execution, P&L tracking)
- Phase 5: AI investment coach chatbot (SSE streaming, context-aware conversations)
- Phase 6: Dashboard enhancement (trending categories, investor trends, settings page)

## Claude Usage Guide
- Use TypeScript strict mode
- All API endpoints must have tests
- CLAUDE.md content must be written in English.
- 코드 생성, 코드 리뷰, 설명, 오류 보고 등 모든 대화 응답은 한국어로 작성해 주세요.

# AI ETF Project — Claude Rules

## 1. Think First
- List assumptions.
- Confirm affected layer (backend or frontend).
- If unclear → ask before coding.

## 2. Minimal Changes Only
- Touch only required files.
- No refactors unless requested.
- No formatting-only edits.
- No new dependencies.

## 3. Architecture Boundaries (Strict)

Backend:
- api/ → routers only
- services/ → business logic
- models/ → SQLAlchemy models
- db/ → session & Base
- data/ → external APIs (yfinance)

Frontend:
- api/ → Axios client only
- pages/ → page components
- components/ → reusable UI
- stores/ → Zustand state
- No hardcoded backend URLs (use Vite proxy /api)

## 4. Execution Protocol

For non-trivial tasks, respond with:

- Assumptions:
- Plan:
- Changes:
- Verification:
- Files touched:

## 5. Definition of Done

Task is complete only if:
- It runs without breaking:
  - Backend (8000)
  - Frontend (5173)
- It respects folder boundaries
- It includes verification steps
