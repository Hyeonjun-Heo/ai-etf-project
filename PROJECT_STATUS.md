# AI ETF & Dividend Stock Investment Assistant - Project Status

> AI 에이전트 기반 주식/ETF 투자 전략 추천, 분석, 모의투자 플랫폼
> UI 참고: [토스증권](https://www.tossinvest.com/) — 다크 테마, 카드 기반 모바일 친화 디자인

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript 5.9, Vite 6, React Router v7, Zustand 5, TanStack Query 5, Axios, Recharts 3 |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2, python-jose (JWT), bcrypt, yfinance |
| DB | SQLite (dev) → PostgreSQL (prod) |
| AI | OpenAI API (planned) |

---

## Architecture Overview

```
[Browser]
   │
   ├─ React SPA (Vite dev server :5173)
   │     ├─ Pages (Dashboard, Login, Register, StockDetail, ...)
   │     ├─ Components (TopNav, MarketChart, ProtectedRoute, ...)
   │     ├─ Stores (Zustand - authStore)
   │     └─ API Client (Axios, JWT auto-attach, 401 refresh)
   │
   └─ /api proxy ──▶ FastAPI (:8000)
                       ├─ api/v1/auth/*      → Auth Service → DB (SQLAlchemy)
                       ├─ api/v1/market/*    → Market Service → yfinance (5min cache)
                       └─ api/v1/health
```

**Backend 패턴**: Router → Service → Data Layer
**Frontend 패턴**: Page → API Client → Zustand/TanStack Query → Component

---

## Phase별 구현 현황

### Phase 0: Foundation (Auth & Infra) — COMPLETED

| 항목 | 상태 | 설명 |
|------|------|------|
| 프로젝트 구조 | ✅ 완료 | 모노레포 (backend/ + frontend/) |
| FastAPI 앱 설정 | ✅ 완료 | create_app 팩토리, CORS, lifespan DB 초기화 |
| DB 설정 | ✅ 완료 | SQLAlchemy 2.0 + SQLite, 세션 관리 |
| User 모델 | ✅ 완료 | id, username, password_hash, created_at |
| JWT 인증 | ✅ 완료 | access token (30min) + refresh token (7days), HS256 |
| 회원가입 API | ✅ 완료 | `POST /auth/register` (유효성 검증, 중복 체크) |
| 로그인 API | ✅ 완료 | `POST /auth/login` → TokenResponse |
| 토큰 갱신 API | ✅ 완료 | `POST /auth/refresh` |
| 사용자 조회 API | ✅ 완료 | `GET /auth/me` (protected) |
| 유저명 중복 확인 API | ✅ 완료 | `GET /auth/check-username` |
| 프론트엔드 Auth Store | ✅ 완료 | Zustand (login, logout, checkAuth) |
| 로그인 페이지 | ✅ 완료 | 폼, 에러 처리, 리다이렉트 |
| 회원가입 페이지 | ✅ 완료 | 실시간 유저명 확인, 비밀번호 확인 |
| ProtectedRoute | ✅ 완료 | 미인증시 /login 리다이렉트 |
| API Client | ✅ 완료 | Axios, JWT 자동 첨부, 401 자동 갱신 + 요청 큐 |
| TopNav | ✅ 완료 | 로고, 네비게이션 5개, 로그인/로그아웃 |
| 글로벌 디자인 토큰 | ✅ 완료 | CSS Variables (다크 테마, Pretendard 폰트) |

---

### Phase 1: Market Data & Stock Detail — IN PROGRESS

#### 1-1. 시장 데이터 API (Backend)

| 항목 | 상태 | 설명 |
|------|------|------|
| 시장 지수 API | ✅ 완료 | `GET /market/indices` — S&P 500, NASDAQ, Dow, VIX |
| Top ETF API | ✅ 완료 | `GET /market/top-etfs` — 10개 ETF 등락률 정렬 |
| 차트 데이터 API | ✅ 완료 | `GET /market/chart` — 기간별 (1d~1y) OHLC |
| 시장 등락 API | ✅ 완료 | `GET /market/movers` — 상승 5 / 하락 5 |
| 종목 상세 API | ✅ 완료 | `GET /market/stock/{symbol}` — 가격, P/E, 시총, 배당 등 |
| yfinance 캐시 | ✅ 완료 | 인메모리 TTL 캐시 (5분) |

#### 1-2. Dashboard 페이지 (Frontend)

| 항목 | 상태 | 설명 |
|------|------|------|
| 시장 지수 카드 (4종) | ✅ 완료 | S&P 500, NASDAQ, Dow, VIX 실시간 가격/변동 |
| SPY 차트 | ✅ 완료 | Recharts AreaChart + 기간 선택 (1mo~1y) |
| Top ETF 랭킹 테이블 | ✅ 완료 | 심볼, 가격, 변동률 |
| Market Movers | ✅ 완료 | 상승/하락 탭 전환, 스크롤 리스트 |
| 스켈레톤 로딩 | ✅ 완료 | 모든 섹션 로딩 상태 |

#### 1-3. Stock Detail 페이지 (Frontend)

| 항목 | 상태 | 설명 |
|------|------|------|
| 종목 헤더 | ✅ 완료 | 심볼 뱃지, 회사명, 섹터, 현재가, 변동 |
| 차트 (기간 선택) | ✅ 완료 | 1d~1y 기간 선택, Recharts AreaChart |
| Key Stats 그리드 | ✅ 완료 | 시총, P/E, 배당률, 52주 범위, 거래량 등 8항목 |
| About 섹션 | ✅ 완료 | 기업 개요 (longBusinessSummary) |
| 에러 핸들링 | ✅ 완료 | 종목 미발견시 에러 메시지 |

#### 1-4. 미구현 항목

| 항목 | 상태 | 설명 |
|------|------|------|
| 종목 검색 (자동완성) | ❌ 미구현 | 검색바 + 실시간 자동완성 드롭다운 |
| 관심 종목 (Watchlist) | ❌ 미구현 | 종목 즐겨찾기, 리스트 관리 |
| Dashboard → StockDetail 연결 | ❌ 미구현 | ETF/Mover 클릭시 상세 페이지 이동 |

---

### Phase 2: AI Portfolio Recommendation — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 투자 성향 설문 UI | ❌ 미구현 | 위험 성향, 투자 기간, 목표 수익률 등 설문 폼 |
| 설문 결과 저장 API | ❌ 미구현 | 사용자 투자 프로필 DB 저장 |
| OpenAI 에이전트 연동 | ❌ 미구현 | 설문 기반 포트폴리오 추천 로직 |
| 추천 포트폴리오 UI | ❌ 미구현 | 자산 배분 차트, ETF 추천 리스트 |
| Portfolio 페이지 | 📋 스캐폴드 | 플레이스홀더만 존재 |

---

### Phase 3: Backtesting Engine — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 백테스트 엔진 (Backend) | ❌ 미구현 | 히스토리컬 데이터 기반 시뮬레이션 |
| CAGR / MDD / Sharpe 계산 | ❌ 미구현 | 핵심 투자 지표 산출 |
| 벤치마크 비교 | ❌ 미구현 | S&P 500 대비 성과 비교 |
| 백테스트 설정 UI | ❌ 미구현 | 기간, 종목, 비중 입력 폼 |
| 백테스트 결과 차트 | ❌ 미구현 | 수익률 곡선, 지표 대시보드 |
| Backtest 페이지 | 📋 스캐폴드 | 플레이스홀더만 존재 |

---

### Phase 4: Paper Trading Simulation — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 가상 계좌 시스템 | ❌ 미구현 | 초기 자본 설정, 잔고 관리 |
| 매수/매도 주문 API | ❌ 미구현 | 시장가/지정가 주문 처리 |
| 포지션 관리 | ❌ 미구현 | 보유 종목, 평균 단가, 수익률 |
| 거래 내역 | ❌ 미구현 | 주문 히스토리, 체결 로그 |
| P&L 추적 | ❌ 미구현 | 실현/미실현 손익 계산 |
| Simulation 페이지 | 📋 스캐폴드 | 플레이스홀더만 존재 |

---

### Phase 5: AI Investment Coach — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 채팅 UI | ❌ 미구현 | 실시간 메시지 인터페이스 |
| SSE 스트리밍 | ❌ 미구현 | 서버→클라이언트 실시간 응답 스트리밍 |
| OpenAI 컨텍스트 관리 | ❌ 미구현 | 대화 기록, 포트폴리오 컨텍스트 주입 |
| 투자 조언 에이전트 | ❌ 미구현 | 종목 분석, 시장 동향 질의 응답 |

---

### Phase 6: Dashboard Enhancement & Settings — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 트렌딩 카테고리 | ❌ 미구현 | 섹터별/테마별 인기 종목 |
| 투자자 트렌드 | ❌ 미구현 | 기관/개인 매매 동향 |
| 설정 페이지 | 📋 스캐폴드 | 투자 프로필 수정, 알림 설정 등 |
| 다크/라이트 테마 전환 | ❌ 미구현 | 테마 토글 기능 |

---

## 현재 구현된 API 엔드포인트 전체 목록

| Method | Endpoint | 인증 | 설명 |
|--------|----------|------|------|
| GET | `/api/v1/health` | - | 헬스 체크 |
| GET | `/api/v1/auth/check-username` | Public | 유저명 중복 확인 |
| POST | `/api/v1/auth/register` | Public | 회원가입 |
| POST | `/api/v1/auth/login` | Public | 로그인 → 토큰 발급 |
| POST | `/api/v1/auth/refresh` | Public | 토큰 갱신 |
| GET | `/api/v1/auth/me` | Protected | 현재 사용자 정보 |
| GET | `/api/v1/market/indices` | Public | 시장 지수 (4종) |
| GET | `/api/v1/market/top-etfs` | Public | Top ETF 목록 |
| GET | `/api/v1/market/chart` | Public | 차트 데이터 (기간별) |
| GET | `/api/v1/market/movers` | Public | 시장 등락 (상승/하락 5) |
| GET | `/api/v1/market/stock/{symbol}` | Public | 종목 상세 정보 |

---

## 현재 프론트엔드 라우트

| Path | 페이지 | 인증 | 상태 |
|------|--------|------|------|
| `/` | Dashboard | Public | ✅ 구현 완료 |
| `/login` | Login | Public | ✅ 구현 완료 |
| `/register` | Register | Public | ✅ 구현 완료 |
| `/stock/:symbol` | StockDetail | Public | ✅ 구현 완료 |
| `/portfolio` | Portfolio | Protected | 📋 스캐폴드 |
| `/backtest` | Backtest | Protected | 📋 스캐폴드 |
| `/simulation` | Simulation | Protected | 📋 스캐폴드 |
| `/settings` | Settings | Protected | 📋 스캐폴드 |

---

## DB 모델

### users
| Column | Type | 제약 |
|--------|------|------|
| id | Integer | PK, Auto Increment |
| username | String(50) | Unique, Indexed, Not Null |
| password_hash | String(255) | Not Null |
| created_at | DateTime | Default: UTC now |

> Phase 2+ 에서 추가 예정: investment_profiles, portfolios, watchlists, orders, trades, chat_messages 등

---

## 실행 방법

### Backend
```bash
cd backend
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/uvicorn app.main:app --reload --port 8000
```
- Swagger 문서: http://localhost:8000/docs
- SQLite DB 첫 실행시 자동 생성

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # 프로덕션 빌드
npm run lint       # ESLint 실행
```
- Vite 프록시: `/api` → `http://127.0.0.1:8000`

---

## 진행률 요약

| Phase | 설명 | 진행률 |
|-------|------|--------|
| Phase 0 | Foundation (Auth & Infra) | ██████████ 100% |
| Phase 1 | Market Data & Stock Detail | ████████░░ 80% |
| Phase 2 | AI Portfolio Recommendation | ░░░░░░░░░░ 0% |
| Phase 3 | Backtesting Engine | ░░░░░░░░░░ 0% |
| Phase 4 | Paper Trading Simulation | ░░░░░░░░░░ 0% |
| Phase 5 | AI Investment Coach | ░░░░░░░░░░ 0% |
| Phase 6 | Dashboard Enhancement | ░░░░░░░░░░ 0% |

**전체 진행률: ~25%** (Phase 0 완료 + Phase 1 거의 완료)

---

*Last updated: 2026-02-17*
