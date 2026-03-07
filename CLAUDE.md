# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI ETF & Dividend Stock Investment Assistant** — React 19 (TypeScript) + FastAPI monorepo web app. AI agent-powered platform for stock/ETF investment strategy recommendation, analysis, and paper trading simulation. UI reference: [Toss Securities](https://www.tossinvest.com/) — dark theme, clean block layout, mobile-friendly card-based design.

## Development Commands

```bash
# Backend — Python venv lives at project root .venv/ (not inside backend/)
cd backend
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev          # Dev server at http://localhost:5173
npm run build        # tsc -b && vite build
npm run lint         # eslint .
```

- Vite proxy forwards `/api` → `http://127.0.0.1:8000` (configured in `frontend/vite.config.ts`)
- Swagger docs: `http://localhost:8000/docs`
- SQLite DB (`backend/app.db`) auto-created on first backend startup via `Base.metadata.create_all` in lifespan
- No test framework is set up yet (no pytest config, no vitest/jest)

## Environment Setup

`backend/.env` is required (no `.env.example` exists). Minimum required fields:

```dotenv
SECRET_KEY=change-this-in-production

# KIS 모의투자계좌 (paper trading / market data fallback)
KIS_APP_KEY=
KIS_APP_SECRET=
KIS_ACCOUNT=         # format: XXXXXXXX-XX
KIS_HTS_ID=
KIS_VIRTUAL=true     # set false for real account

# KIS 실전계좌 (real market data — better rate limits)
KIS_REAL_APP_KEY=
KIS_REAL_APP_SECRET=
KIS_REAL_ACCOUNT=

# Optional
OPENAI_API_KEY=
DATABASE_URL=sqlite:///./app.db
```

`keep_token=True` in `data/kis_client.py` caches KIS tokens to disk (avoids the 1-minute rate limit on token issuance). Token files are written to the `backend/` working directory.

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

**Health endpoint** (`api/v1/health.py`): `GET /health` — liveness check.

**Auth endpoints** (`api/v1/auth.py`): `POST /register`, `POST /login`, `POST /refresh`, `GET /me`, `GET /check-username`

**Market endpoints** (`api/v1/market.py`):
- `GET /market/indices` — 국내(KOSPI, KOSDAQ) + 해외 지수 목록
- `GET /market/index-sparklines` — 지수별 당일 스파크라인 데이터
- `GET /market/top-etfs` — 상위 ETF 목록
- `GET /market/chart?symbol=&period=&excd=` — 종목 차트 (period: 1d|1w|1mo|3mo|6mo|1y). 1w/1mo는 1y 일봉을 반환하고 프론트에서 집계
- `GET /market/movers` — 등락률 상위/하위 5종목
- `GET /market/ranking?sort=&category=&limit=` — 실시간 랭킹 (sort: amount|volume|rise|fall, category: all|domestic|overseas)
- `GET /market/search?q=` — 종목 검색 자동완성 (국내+해외, min 1자 max 50자)
- `GET /market/stock/{symbol}` — 종목 상세 정보

**Service layer** (`services/market_service.py`): Currently thin delegation to `data/market_data.py`. This is intentional — business logic (validation, transformation, caching policy) should accumulate here as features grow. Do not bypass it by calling `data/` directly from routers.

**Market data** (`data/market_data.py`): KIS OpenAPI wrapper via `python-kis`. In-memory TTL cache (5 min general, 1 min for sparklines due to KIS token rate limit).
- **국내 지수**: KOSPI(`0001`), KOSDAQ(`1001`) — KIS `FHPUP02100000` TR
- **해외 지수**: NASDAQ(`COMP`), S&P500(`SPX`), 다우존스(`DJI`) — KIS `FHKST03030200` TR; VIX — Yahoo Finance v8 API; USD/KRW — KIS `FHKST03030100` 우선, 실패 시 Yahoo Finance 폴백
- **스파크라인**: 국내 지수는 프록시 ETF 사용 (`INDEX_SPARKLINE_PROXY`: 코스피→069500 KODEX 200, 코스닥→229200 KODEX 코스닥150), 해외는 Yahoo Finance 5분봉
- **랭킹**: 거래대금/거래량 순위는 `FHPST01710000` TR, 등락률 순위는 `FHPST01700000` TR

**KIS client** (`data/kis_client.py`): PyKis singleton (`get_kis()`). Supports three modes: real-only, virtual-only, or real+virtual simultaneously (real domain for market data, virtual domain for paper trading). Initialized lazily on first call. Uses `keep_token=True` to cache tokens to disk and avoid the 1-minute rate limit on token issuance.

**Config**: `core/config.py` uses pydantic-settings, reads from `backend/.env`. Key vars: `SECRET_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`. KIS vars: `KIS_APP_KEY`/`KIS_APP_SECRET`/`KIS_ACCOUNT`/`KIS_HTS_ID`/`KIS_VIRTUAL` (모의투자), `KIS_REAL_APP_KEY`/`KIS_REAL_APP_SECRET`/`KIS_REAL_ACCOUNT` (실전).

**Database & Migrations**: Only one table currently (`users`). Alembic is installed but no migration files have been created yet. When adding new ORM models:
```bash
cd backend
../.venv/Scripts/alembic revision --autogenerate -m "description"
../.venv/Scripts/alembic upgrade head
```

**Models naming note**: `models/user.py` = SQLAlchemy ORM model; `models/auth.py` = Pydantic request/response schemas. The folder mixes both kinds — do not assume everything in `models/` is an ORM model.

### Frontend (React + Vite)

**Routing** (`App.tsx`): Public routes (`/`, `/login`, `/register`, `/stock/:symbol`) + protected routes wrapped in `<ProtectedRoute>` (`/portfolio`, `/backtest`, `/simulation`, `/settings`). TopNav hidden on auth pages.

**Implemented pages**: `Dashboard`, `Login`, `Register`, `StockDetail`.
**Scaffold-only placeholders**: `Portfolio`, `Backtest`, `Simulation`, `Settings` — these exist as route targets but contain no real functionality yet.

**API client** (`api/client.ts`): Axios instance with `baseURL: '/api/v1'`. Auto-attaches JWT from localStorage. Response interceptor handles 401 → silent token refresh → retry failed requests (with queue for concurrent failures).

**State**: Zustand stores (`stores/`) for client state (currently `authStore`). TanStack Query for server state.

**Component structure**: `components/common/` (TopNav with search autocomplete, ProtectedRoute, IndexTickerBar, RealTimeRanking), `components/charts/` (MarketChart — Recharts AreaChart; CandleChart — `lightweight-charts` candlestick+volume with daily/weekly/monthly aggregation; MiniLineChart). `components/chat/` and `components/hooks/` are empty placeholder directories for future features.

**Styling**: CSS Modules per component + global design tokens in `styles/global.css`. Key tokens:
- Backgrounds: `--bg-primary: #020617`, `--bg-secondary: #111827`
- Text: `--text-primary: #e5e7eb`, `--text-secondary: #9ca3af`
- Accent: `--accent-blue: #2563eb`
- Border: `--border-default: #374151`
- Border radius: `--radius-lg: 16px` (cards)

**Types**: Shared TypeScript interfaces in `types/` (`auth.ts`, `market.ts`). `ChartPoint` includes optional OHLCV fields (`open`, `high`, `low`, `volume`) used by `CandleChart`. `StockDetail` includes fields (`sector`, `industry`, `longBusinessSummary`, `avgVolume`, `dividendYield`) that the backend may return as `null` for domestic symbols. `SearchResult` shape: `{ symbol, name, type: 'equity'|'etf', market: 'domestic'|'overseas', exchange }`.

### Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript 5.9, Vite 6, React Router v7, Zustand 5, TanStack Query 5, Axios, Recharts 3, lightweight-charts 4 |
| Backend | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2, python-jose (JWT), bcrypt, python-kis (KIS OpenAPI) |
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
- Market data API (KIS OpenAPI): 국내 지수(KOSPI/KOSDAQ) + 해외 지수(NASDAQ/S&P500/DJI/VIX/USD환율), top Korean ETFs, intraday sparklines, chart history, market movers (gainers/losers), real-time ranking
- Dashboard page: market overview cards, index chart with period selector, ETF ranking table, movers with tab switching, skeleton loading
- Login & Register pages with form validation
- Stock detail page (`/stock/:symbol`) + backend `GET /market/stock/{symbol}` endpoint

### Next Up
- Phase 1 (remaining): watchlist (DB model + API + UI), dynamic Top ETF lookup (replace `KR_ETF_POOL` hardcode with KRX API)
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
- data/ → external APIs (KIS OpenAPI via python-kis)

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
