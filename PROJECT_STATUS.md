# AI ETF & Dividend Stock Investment Assistant - Project Status

> AI 에이전트 기반 주식/ETF 투자 전략 추천, 분석, 모의투자 플랫폼
> UI 참고: [토스증권](https://www.tossinvest.com/) — 다크 테마, 카드 기반 모바일 친화 디자인

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | React 19, TypeScript 5.9, Vite 6, React Router v7, Zustand 5, TanStack Query 5, Axios, Recharts 3, lightweight-charts 4 |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic 2, python-jose (JWT), bcrypt, python-kis (KIS OpenAPI), httpx |
| DB | SQLite (dev) → PostgreSQL (prod) |
| AI | Claude (Anthropic) + OpenAI GPT-4o — Tool Use 기반 Agent |

---

## Architecture Overview

```
[Browser]
   │
   ├─ React SPA (Vite dev server :5173)
   │     ├─ Pages (Dashboard, Login, Register, StockDetail, ...)
   │     ├─ Components (TopNav, MarketChart, CandleChart, RealTimeRanking, ...)
   │     ├─ Stores (Zustand - authStore)
   │     └─ API Client (Axios, JWT auto-attach, 401 refresh)
   │
   └─ /api proxy ──▶ FastAPI (:8000)
                       ├─ api/v1/auth/*      → Auth Service → DB (SQLAlchemy)
                       ├─ api/v1/market/*    → Market Service → KIS OpenAPI (인메모리 캐시)
                       ├─ api/v1/ws/*        → WebSocket (KIS 실시간 시세, 개발 중)
                       ├─ api/v1/chat/*      → Agent Service → Claude/OpenAI (Tool Use)
                       └─ api/v1/health
```

**Backend 패턴**: Router → Service → Data Layer (`data/market_data.py` ← KIS OpenAPI via python-kis)
**Frontend 패턴**: Page → API Client → TanStack Query → Component

---

## Phase별 구현 현황

### Phase 0: Foundation (Auth & Infra) — COMPLETED ✅

| 항목 | 상태 | 설명 |
|------|------|------|
| 프로젝트 구조 | ✅ 완료 | 모노레포 (backend/ + frontend/) |
| FastAPI 앱 설정 | ✅ 완료 | create_app 팩토리, CORS, lifespan DB 초기화 |
| DB 설정 | ✅ 완료 | SQLAlchemy 2.0 + SQLite, 세션 관리 |
| User 모델 | ✅ 완료 | id, username, password_hash, created_at |
| JWT 인증 | ✅ 완료 | access token (30min) + refresh token (7days), HS256 |
| 회원가입 API | ✅ 완료 | `POST /auth/register` |
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

### Phase 1: Market Data & Dashboard — COMPLETED ✅

#### 1-1. 시장 데이터 백엔드 (KIS OpenAPI)

| 항목 | 상태 | 설명 |
|------|------|------|
| KIS 클라이언트 | ✅ 완료 | `data/kis_client.py` — PyKis 싱글톤, real/virtual 도메인 |
| 인메모리 TTL 캐시 | ✅ 완료 | 5분 (일반) / 1분 (스파크라인) |
| 국내 지수 API | ✅ 완료 | KOSPI(`0001`), KOSDAQ(`1001`) — KIS `FHPUP02100000` |
| 해외 지수 API | ✅ 완료 | NASDAQ/S&P500/DJI — KIS `FHKST03030200`, VIX — Yahoo Finance |
| USD/KRW 환율 | ✅ 완료 | KIS `FHKST03030100` 우선, Yahoo Finance 폴백 |
| 지수 스파크라인 | ✅ 완료 | 국내: 프록시 ETF(KODEX 200 등) 1분봉, 해외: Yahoo Finance 5분봉 |
| Top ETF API | ✅ 완료 | `GET /market/top-etfs` — KR_ETF_POOL 기반 10개 등락률 정렬 |
| 차트 데이터 API | ✅ 완료 | `GET /market/chart?symbol=&period=&excd=` — 기간별 (1d~5y) |
| 시장 무버 API | ✅ 완료 | `GET /market/movers` — KOSPI+KOSDAQ 등락률 상위/하위 5 |
| 실시간 랭킹 API | ✅ 완료 | `GET /market/ranking?sort=&category=&limit=` |
| 종목 검색 API | ✅ 완료 | `GET /market/search?q=` — 국내+해외 자동완성 |
| 종목 상세 API | ✅ 완료 | `GET /market/stock/{symbol}` |
| 분봉 히스토리 (해외) | ✅ 완료 | Yahoo Finance v8 5분봉 30일치 (`_fetch_overseas_intraday_yahoo`) |
| 분봉 히스토리 (국내 KOSPI) | ✅ 완료 | Yahoo Finance `.KS` 30일치 (`_fetch_domestic_intraday_yahoo`) |
| 분봉 히스토리 (국내 KOSDAQ) | ✅ 완료 | Naver Finance JSON API ~6거래일 (`_fetch_domestic_intraday_naver`) |
| 분봉 데이터 소스 폴백 체계 | ✅ 완료 | Yahoo → Naver → KIS(당일) 순 폴백 |

**랭킹 API 상세:**
- `category=domestic` — KOSPI+KOSDAQ 합산 (주식+ETF 포함), KIS `FHPST01710000`/`FHPST01700000`
- `category=overseas` — NAS+NYS 합산 (주식+ETF 포함), KIS `HHDFS76320010`/`HHDFS76260000`
- `category=all` — 국내(KRW) + 해외(USD→KRW 환산) 합산 정렬 TOP 100
- `sort` — `amount`(거래대금) / `volume`(거래량) / `rise`(급상승) / `fall`(급하락)

#### 1-2. Dashboard 페이지

| 항목 | 상태 | 설명 |
|------|------|------|
| 시장 지수 카드 | ✅ 완료 | KOSPI, KOSDAQ, NASDAQ, S&P500, DJI, VIX, USD/KRW |
| 지수 스파크라인 | ✅ 완료 | 당일 인트라데이 미니 차트 |
| SPY 차트 | ✅ 완료 | CandleChart (lightweight-charts) + 기간 선택 + 분봉 간격 드롭다운 |
| Top ETF 랭킹 테이블 | ✅ 완료 | 심볼, 가격, 변동률 |
| Market Movers | ✅ 완료 | 상승/하락 탭 전환 |
| 실시간 랭킹 컴포넌트 | ✅ 완료 | `RealTimeRanking.tsx` |
| 스켈레톤 로딩 | ✅ 완료 | 모든 섹션 로딩 상태 |
| 홈 전체 한글화 | ✅ 완료 | 모든 UI 레이블 한국어 |

**실시간 랭킹 컴포넌트 상세:**
- 마켓 탭: `전체` / `국내` / `해외`
- 정렬 칩: `거래대금` / `거래량` / `급상승` / `급하락`
- 가격 포맷: 국내 → `원`, 해외 → `$` (item.market 필드 기반)
- 거래대금 단위: 조/억/만 자동 변환
- 해외 종목 거래소 뱃지: NASDAQ / NYSE

#### 1-3. Stock Detail 페이지

| 항목 | 상태 | 설명 |
|------|------|------|
| 종목 헤더 | ✅ 완료 | 심볼 뱃지, 회사명, 현재가, 변동 |
| 차트 (기간 선택) | ✅ 완료 | 1d / 일봉 / 주봉 / 월봉 — CandleChart (lightweight-charts) |
| 분봉 차트 | ✅ 완료 | 1/3/5/10/15/30/60/120/240분 인터벌 선택 |
| 통화 토글 | ✅ 완료 | 원/달러 전환 (해외 종목) |
| 차트 가격 포맷 | ✅ 완료 | 우측 축 천단위 콤마 |
| Key Stats 그리드 | ✅ 완료 | 시총, P/E, 52주 범위, 거래량 등 |

**차트 기간 시스템:**
- `1d` → 분봉 (candleInterval='minute'), 30일치 히스토리 (Yahoo/Naver/KIS 폴백)
- `daily` → 일봉 (5y 데이터 요청)
- `weekly` → 주봉 (5y 일봉 데이터를 클라이언트에서 집계)
- `monthly` → 월봉 (5y 일봉 데이터를 클라이언트에서 집계)

#### 1-4. TopNav 검색

| 항목 | 상태 | 설명 |
|------|------|------|
| 종목 검색 자동완성 | ✅ 완료 | 검색바 + 300ms 디바운스 + 드롭다운 (국내+해외) |
| 검색 API 연결 | ✅ 완료 | `/market/search?q=` (min 1자, max 50자) |

#### 1-5. 차트 컴포넌트

| 항목 | 상태 | 설명 |
|------|------|------|
| CandleChart | ✅ 완료 | `lightweight-charts` 기반 캔들차트 + 거래량 바 |
| MarketChart | ✅ 완료 | CandleChart 래퍼, 분봉 인터벌 드롭다운 포함 |
| MiniLineChart | ✅ 완료 | 스파크라인용 미니 차트 |

#### 1-6. Phase 1 잔여 항목

| 항목 | 상태 | 설명 |
|------|------|------|
| 관심 종목 (Watchlist) | ❌ 미구현 | DB 모델 + 즐겨찾기 API + UI |
| Top ETF → KRX 동적 조회 | ❌ 미구현 | 현재 KR_ETF_POOL 하드코딩 → KRX API 동적 조회 교체 예정 |

---

---

## 서비스 비전 (2026-03-07 기획 확정)

> **"ETF·주식을 잘 모르는 투자 초보자에게, AI Agent가 실시간 데이터 기반으로 쉽게 설명하고 인사이트를 제공하는 서비스"**

### AI 모델 역할 분담

| 역할 | 모델 | 이유 |
|------|------|------|
| 대화 / 설명 / 요약 | **Claude Sonnet 4.6** | 한국어 품질 우수, Tool Use 강점 |
| 데이터 분석 / 수치 처리 | **GPT-4o** | Function Calling, 수치 해석 강점 |
| 일일 브리핑 생성 | **Claude** | 자연스러운 한국어 문체 |

### Agent Tools (전체)

| Tool | 설명 |
|------|------|
| `get_market_indices` | 현재 국내/해외 지수 조회 |
| `get_stock_info` | 종목/ETF 상세 정보 |
| `search_stocks` | 종목 검색 |
| `get_chart_data` | 가격 히스토리 |
| `get_market_ranking` | 거래량/상승률 랭킹 |
| `get_top_etfs` | 상위 ETF 목록 |
| `get_news` | 종목/시장 뉴스 (Phase B) |
| `get_macro_indicators` | 매크로 경제 지표 (Phase C) |
| `get_etf_holdings` | ETF 구성 종목 조회 (Phase D) |

---

### Phase 2: AI Agent 코어 — NOT STARTED ⭐ 다음 작업

> 모든 AI 기능의 기반. 이것이 완성되면 이후 Phase는 Tool 추가만으로 확장 가능.

#### 2-1. 백엔드

| 항목 | 상태 | 설명 |
|------|------|------|
| `anthropic` 패키지 추가 | ❌ 미구현 | requirements.txt + config.py ANTHROPIC_API_KEY |
| `data/agent_tools.py` | ❌ 미구현 | Tool 정의 (JSON Schema) + 실행 함수 (market_service 위임) |
| `services/agent_service.py` | ❌ 미구현 | Claude AsyncAnthropic, Tool Use 루프, SSE 스트리밍 |
| `api/v1/chat.py` | ❌ 미구현 | `POST /api/v1/chat` — StreamingResponse (SSE) |
| router.py 등록 | ❌ 미구현 | chat 라우터 api_router에 연결 |

**Agent 동작 흐름:**
```
사용자 메시지
    ↓
Claude (Tool Use 판단)
    ↓ (tool_use)
Tool 실행 (market_service 조회)  →  UI에 "📊 데이터 조회 중..." 표시
    ↓
Claude (결과 해석 + 최종 답변 생성)  →  SSE 스트리밍
    ↓
사용자 화면에 실시간 출력
```

#### 2-2. 프론트엔드

| 항목 | 상태 | 설명 |
|------|------|------|
| `hooks/useChat.ts` | ❌ 미구현 | SSE fetch 스트리밍, 메시지 상태 관리 |
| `components/chat/ChatWidget.tsx` | ❌ 미구현 | 우하단 플로팅 버튼 + 사이드 패널 |
| `components/chat/ChatWidget.module.css` | ❌ 미구현 | 다크 테마 채팅 UI |
| App.tsx 통합 | ❌ 미구현 | ChatWidget 전역 마운트 |

**Tool Call 표시 (한국어):**

| Tool | UI 표시 |
|------|---------|
| `get_market_indices` | 📊 시장 지수 조회 중... |
| `get_stock_info` | 🔍 종목 정보 조회 중... |
| `search_stocks` | 🔎 종목 검색 중... |
| `get_market_ranking` | 📈 시장 랭킹 조회 중... |
| `get_top_etfs` | 📋 ETF 목록 조회 중... |

---

### Phase 3: 데일리 브리핑 — NOT STARTED

> "매일 앱을 열게 만드는 기능" — 첫 접속 시 AI가 3개 카드로 오늘의 핵심 정보 요약

| 항목 | 상태 | 설명 |
|------|------|------|
| 뉴스 수집 API 연동 | ❌ 미구현 | 금융 뉴스 API (네이버/Yahoo Finance) |
| `GET /market/news` | ❌ 미구현 | 시장/종목별 뉴스 조회 엔드포인트 |
| `POST /chat/daily-brief` | ❌ 미구현 | Claude가 3개 카드 생성 (캐시: 1일) |
| 브리핑 DB 캐시 | ❌ 미구현 | 사용자별 당일 브리핑 1회 생성 후 캐시 |
| DailyBrief 컴포넌트 | ❌ 미구현 | 대시보드 상단 3개 카드 UI |

**3개 카드 구성:**
1. 📊 **오늘의 시장** — 국내/해외 주요 지수 흐름 한줄 요약
2. 📦 **내 종목 소식** — 보유 종목 관련 뉴스/전망 (로그인 시)
3. 💡 **오늘의 인사이트** — 주목할 섹터/종목/이벤트

---

### Phase 4: 시장 인사이트 확장 — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 시장 브리핑 Tool | ❌ 미구현 | Agent가 오늘 시장 상황 자연어 해설 |
| 경제 지표 해설 Tool | ❌ 미구현 | CPI/금리/환율 → 초보자 언어 번역 |
| 종목 인사이트 Tool | ❌ 미구현 | 특정 종목 흐름 + 섹터 동향 분석 |
| 시장 역사 비교 Tool | ❌ 미구현 | 현재 패턴 vs 과거 유사 구간 매칭 |
| `get_macro_indicators` | ❌ 미구현 | 매크로 경제 지표 조회 Tool |

---

### Phase 5: 포트폴리오 기능 — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 보유 종목 등록 DB | ❌ 미구현 | `portfolios` 테이블 (symbol, quantity, avg_price) |
| 보유 종목 CRUD API | ❌ 미구현 | `POST/GET/DELETE /portfolio/holdings` |
| **ETF 중복 보유 분석** | ❌ 미구현 | 구성 종목 파싱 → 겹침 시각화 ("삼성전자 42% 노출") |
| `get_etf_holdings` Tool | ❌ 미구현 | ETF 구성 종목 조회 Tool |
| 투자 성향 설문 | ❌ 미구현 | 위험 성향, 투자 기간, 목표 수익률 설문 폼 |
| 포트폴리오 설계 Agent | ❌ 미구현 | 설문 결과 기반 ETF 조합 추천 |
| Portfolio 페이지 | 📋 스캐폴드 | 플레이스홀더만 존재 |

---

### Phase 6: 투자 저널 — NOT STARTED

> 독창적 차별점 — 기존 증권 앱에 없는 기능

| 항목 | 상태 | 설명 |
|------|------|------|
| 저널 DB 모델 | ❌ 미구현 | `trade_journals` (symbol, action, reason, date) |
| 저널 작성 API | ❌ 미구현 | `POST /journal` — 매매 이유 기록 |
| AI 회고 분석 | ❌ 미구현 | Claude가 3개월 후 "당신의 판단은 맞았습니까?" 분석 |
| 감정 투자 패턴 감지 | ❌ 미구현 | FOMO 매수/공포 매도 패턴 AI 감지 |
| 저널 UI | ❌ 미구현 | 타임라인 + AI 코멘트 |

---

### Phase 7: 백테스팅 — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 백테스트 엔진 | ❌ 미구현 | 히스토리컬 데이터 기반 시뮬레이션 |
| CAGR / MDD / Sharpe 계산 | ❌ 미구현 | 핵심 투자 지표 산출 |
| **나만의 지수 만들기** | ❌ 미구현 | 사용자 선택 종목 → 가상 지수 → 백테스팅 |
| 벤치마크 비교 | ❌ 미구현 | KOSPI / S&P500 대비 성과 비교 |
| AI 결과 해설 | ❌ 미구현 | Claude가 백테스트 결과를 쉬운 말로 설명 |
| 백테스트 차트 UI | ❌ 미구현 | 수익률 곡선, 지표 대시보드 |
| Backtest 페이지 | 📋 스캐폴드 | 플레이스홀더만 존재 |

---

### Phase 8: 모의투자 & 고도화 — NOT STARTED

| 항목 | 상태 | 설명 |
|------|------|------|
| 가상 계좌 시스템 | ❌ 미구현 | 초기 자본 설정, 잔고 관리 |
| 매수/매도 주문 API | ❌ 미구현 | KIS 모의투자 도메인 활용 |
| P&L 추적 | ❌ 미구현 | 실현/미실현 손익 계산 |
| WebSocket 실시간 시세 | 🔧 개발 중 | `api/v1/ws.py`, `data/kis_ws.py` 스캐폴드 생성됨 |
| 시장 역사 비교 Engine | ❌ 미구현 | 현재 VIX/금리/섹터 → 과거 구간 패턴 매칭 |
| Simulation 페이지 | 📋 스캐폴드 | 플레이스홀더만 존재 |

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
| GET | `/api/v1/market/indices` | Public | 국내(KOSPI/KOSDAQ) + 해외 지수 + 환율 |
| GET | `/api/v1/market/index-sparklines` | Public | 지수별 당일 스파크라인 데이터 |
| GET | `/api/v1/market/top-etfs?limit=` | Public | Top KR ETF 목록 (등락률 정렬) |
| GET | `/api/v1/market/chart?symbol=&period=&excd=` | Public | 종목 차트 (1d\|1w\|1mo\|3mo\|6mo\|1y\|5y) |
| GET | `/api/v1/market/movers` | Public | 등락률 상위/하위 5종목 |
| GET | `/api/v1/market/ranking?sort=&category=&limit=` | Public | 실시간 랭킹 TOP 100 |
| GET | `/api/v1/market/search?q=` | Public | 종목 검색 자동완성 (국내+해외) |
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

### DB 설계 원칙
- **채팅 히스토리**: DB 저장 안 함 — 프론트엔드 상태(React state)로 관리, 매 요청 시 전체 대화 기록 전송
- **데일리 브리핑**: DB 저장 안 함 — 인메모리 캐시(TTL 24시간)로 처리
- **백테스트 결과**: DB 저장 안 함 — 매번 계산, "저장" 기능 필요 시 Phase 7에서 추가
- **자동화**: APScheduler를 FastAPI lifespan에 등록 (데일리 브리핑 08:00, 저널 회고 00:00)

### 테이블 전체 목록 (Phase별)

#### 현재 존재
| 테이블 | 설명 |
|--------|------|
| `users` | id, username, password_hash, created_at |

#### Phase 5 추가 예정
| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `investment_profiles` | user_id(FK, unique), risk_level(1~5), investment_period, target_return, investment_amount | 투자 성향 설문 결과 |
| `portfolio_holdings` | user_id(FK), symbol, name, market, quantity, avg_price, added_at | 보유 종목 |
| `watchlists` | user_id(FK), symbol, name, market, added_at | 관심 종목 |

#### Phase 6 추가 예정
| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `trade_journals` | user_id(FK), symbol, action(buy/sell/watch), price_at_time, reason, emotion, created_at | 매매 이유 기록 |
| `journal_ai_reviews` | journal_id(FK), price_now, verdict(correct/incorrect/neutral), ai_comment, pattern_detected, reviewed_at | AI 회고 분석 결과 |

#### Phase 8 추가 예정
| 테이블 | 주요 컬럼 | 설명 |
|--------|----------|------|
| `virtual_accounts` | user_id(FK, unique), cash_balance, created_at | 모의투자 가상 계좌 |
| `virtual_orders` | account_id(FK), symbol, action(buy/sell), quantity, price, total_amount, created_at | 모의투자 주문 내역 |

### Alembic 마이그레이션 계획
```
현재:      users (이미 존재, 마이그레이션 파일 없음)
Phase 5:   investment_profiles, portfolio_holdings, watchlists
Phase 6:   trade_journals, journal_ai_reviews
Phase 8:   virtual_accounts, virtual_orders
```
> Phase 2~4는 DB 신규 테이블 없이 진행

---

## 실행 방법

### Backend
```bash
cd backend
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```
- Swagger 문서: http://localhost:8000/docs
- SQLite DB 첫 실행시 자동 생성
- KIS API 키: `backend/.env` 설정 필요 (`KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT`, `KIS_HTS_ID`)

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
| Phase 1 | Market Data & Dashboard | █████████░ 95% |
| Phase 2 | AI Agent 코어 + 챗봇 UI | ░░░░░░░░░░ 0% ⭐ Next |
| Phase 3 | 데일리 브리핑 | ░░░░░░░░░░ 0% |
| Phase 4 | 시장 인사이트 확장 | ░░░░░░░░░░ 0% |
| Phase 5 | 포트폴리오 기능 + ETF 중복 분석 | ░░░░░░░░░░ 0% |
| Phase 6 | 투자 저널 | ░░░░░░░░░░ 0% |
| Phase 7 | 백테스팅 | ░░░░░░░░░░ 0% |
| Phase 8 | 모의투자 & 고도화 | ░░░░░░░░░░ 0% |

**전체 진행률: ~25%** (Phase 0 완료 + Phase 1 거의 완료)

---

## Phase 1 잔여 → Phase 2 진입 전 권장 작업

1. **관심 종목 (Watchlist)** — DB 모델 추가 + 즐겨찾기 API + UI (Phase 5 때 같이 진행 가능)
2. **Top ETF 동적 조회** — `KR_ETF_POOL` 하드코딩 → KRX Open API 동적 조회 교체

---

*Last updated: 2026-03-07 (기획 회의 반영 — Phase 2~8 전면 재설계)*
