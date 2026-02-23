# AI ETF & 배당주 투자 보조 플랫폼

> **KIS OpenAPI 기반 실시간 시장 데이터 + AI 에이전트 투자 전략 추천 · 백테스트 · 모의투자**
> UI 스타일: 토스증권 다크 테마, 카드 기반 모바일 친화 레이아웃

---

## 스크린샷

| Dashboard | 실시간 랭킹 |
|-----------|------------|
| 지수 카드 · 스파크라인 · 차트 · ETF 랭킹 | 전체/국내/해외 탭, 거래대금/거래량/급상승/급하락 |

---

## 주요 기능 현황

### 구현 완료
- **인증 시스템** — 회원가입 / 로그인 / JWT 자동 갱신 (access 30분 + refresh 7일)
- **시장 지수** — KOSPI · KOSDAQ · NASDAQ · S&P500 · DJI · VIX · USD/KRW 실시간 시세
- **당일 스파크라인** — 지수별 인트라데이 미니 차트 (국내: KIS 1분봉 / 해외: Yahoo Finance 5분봉)
- **종목 차트** — 기간 선택(1d · 1w · 1mo · 3mo · 6mo · 1y) Recharts 차트
- **Market Movers** — KOSPI+KOSDAQ 합산 등락률 상위/하위 5종목
- **실시간 랭킹** — 국내(주식+ETF) · 해외(NAS+NYS 주식+ETF) · 전체(USD→KRW 환산 합산) TOP 100
- **종목 상세** — 현재가 · P/E · PBR · 52주 범위 · 시총 등 Key Stats

### 구현 예정
| Phase | 기능 | 상태 |
|-------|------|------|
| 1 (잔여) | 종목 검색 자동완성, 관심종목(Watchlist) | 🔜 |
| 2 | AI 포트폴리오 추천 (OpenAI 에이전트) | 📋 |
| 3 | 백테스팅 엔진 (CAGR · MDD · Sharpe) | 📋 |
| 4 | 모의투자 (KIS 가상 계좌) | 📋 |
| 5 | AI 투자 코치 챗봇 (SSE 스트리밍) | 📋 |
| 6 | WebSocket 실시간 시세 · 종목 DB | 📋 |

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| **Frontend** | React 19, TypeScript 5.9, Vite 6, React Router v7, Zustand 5, TanStack Query 5, Axios, Recharts 3 |
| **Backend** | FastAPI, SQLAlchemy 2.0, Pydantic 2, python-jose, bcrypt, python-kis (KIS OpenAPI), httpx |
| **DB** | SQLite (개발) → PostgreSQL (운영) |
| **AI** | OpenAI API (예정) |

---

## 아키텍처

```
[브라우저]
    │
    ├─ React SPA (:5173)
    │     ├─ pages/          Dashboard · Login · Register · StockDetail
    │     ├─ components/     TopNav · RealTimeRanking · MarketChart · IndexTickerBar
    │     ├─ stores/         authStore (Zustand)
    │     └─ api/client.ts   Axios · JWT 자동 첨부 · 401 자동 갱신
    │
    └─ /api 프록시 ──▶ FastAPI (:8000)
                          ├─ /auth/*     인증 (회원가입 · 로그인 · 갱신)
                          ├─ /market/*   시장 데이터 (KIS OpenAPI + Yahoo Finance)
                          └─ /health     헬스 체크
```

**백엔드 흐름**: `Router → Service → data/market_data.py → KIS OpenAPI`
**캐시**: 인메모리 TTL 캐시 (일반 5분 / 스파크라인 1분)

---

## 로컬 실행

### 사전 준비
- Python 3.11+, Node.js 18+
- KIS OpenAPI 앱 키 발급 (한국투자증권 개발자 포털)

### 환경 변수 설정
```bash
# backend/.env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./app.db
OPENAI_API_KEY=sk-...          # Phase 2+ 필요

# KIS 실전 API
KIS_APP_KEY=PSxxxxxxxx
KIS_APP_SECRET=xxxxxxxxxx
KIS_ACCOUNT=12345678-01
KIS_HTS_ID=your_hts_id

# KIS 모의투자 API (Paper Trading용, 선택)
KIS_VIRTUAL=true
KIS_REAL_APP_KEY=PSxxxxxxxx
KIS_REAL_APP_SECRET=xxxxxxxxxx
KIS_REAL_ACCOUNT=12345678-01
```

### 백엔드 실행
```bash
# 프로젝트 루트에서
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt

cd backend
../.venv/Scripts/uvicorn app.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173
```

---

## API 엔드포인트 요약

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/auth/register` | 회원가입 |
| POST | `/api/v1/auth/login` | 로그인 |
| POST | `/api/v1/auth/refresh` | 토큰 갱신 |
| GET | `/api/v1/auth/me` | 내 정보 |
| GET | `/api/v1/market/indices` | 국내+해외 지수 · 환율 |
| GET | `/api/v1/market/index-sparklines` | 지수별 당일 스파크라인 |
| GET | `/api/v1/market/top-etfs` | Top KR ETF 목록 |
| GET | `/api/v1/market/chart?symbol=&period=` | 종목 차트 |
| GET | `/api/v1/market/movers` | 등락률 상위/하위 5 |
| GET | `/api/v1/market/ranking?sort=&category=&limit=` | 실시간 랭킹 TOP 100 |
| GET | `/api/v1/market/stock/{symbol}` | 종목 상세 |

**랭킹 파라미터**:
- `category`: `all` · `domestic` · `overseas`
- `sort`: `amount`(거래대금) · `volume`(거래량) · `rise`(급상승) · `fall`(급하락)
- `limit`: 1~100 (기본 100)

---

## 폴더 구조

```
ai-etf-project/
├─ backend/
│   ├─ app/
│   │   ├─ api/v1/        auth.py · market.py · health.py
│   │   ├─ core/          config.py · deps.py · security.py
│   │   ├─ data/          market_data.py · kis_client.py
│   │   ├─ models/        user.py (ORM) · auth.py (Pydantic)
│   │   ├─ services/      auth_service.py · market_service.py
│   │   └─ main.py
│   ├─ requirements.txt
│   └─ .env               (gitignore)
│
└─ frontend/
    ├─ src/
    │   ├─ api/            client.ts
    │   ├─ components/     TopNav · RealTimeRanking · MarketChart · ...
    │   ├─ pages/          Dashboard · Login · Register · StockDetail
    │   ├─ stores/         authStore.ts
    │   ├─ types/          auth.ts · market.ts
    │   └─ styles/         global.css
    └─ package.json
```

---

## Git 브랜치 전략

| 브랜치 | 용도 |
|--------|------|
| `main` | 프로덕션 (오류 없는 코드만) |
| `develop` | 기능 통합 브랜치 |
| `feature/*` | 개별 기능 개발 |

---

*Last updated: 2026-02-23*
