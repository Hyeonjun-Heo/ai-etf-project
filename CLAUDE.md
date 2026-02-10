# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI ETF·배당주 투자 도우미** - React(TypeScript) + FastAPI 하이브리드 웹 애플리케이션. 시장 분석, 포트폴리오 추천, 백테스트, 모의투자, AI 투자 코치 챗봇 기능 제공.

UI 디자인: 토스 증권 스타일 다크 테마 + 블록 구조

## Development Commands

```bash
# 백엔드 실행
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# 프론트엔드 실행
cd frontend && npm install && npm run dev

# Swagger API 문서: http://localhost:8000/docs
```

- 프론트엔드: `http://localhost:5173` (Vite dev server)
- 백엔드: `http://localhost:8000` (FastAPI + Uvicorn)
- Vite 프록시가 `/api` 요청을 백엔드로 전달

## Git Workflow

- **main**: 프로덕션 브랜치 (에러 없는 코드만)
- **develop**: 기능 통합 브랜치
- 항상 feature 브랜치에서 작업 → develop 머지 → main 머지

## Architecture

### 모노레포 구조

```
ai-etf-project/
├── frontend/                    # React + TypeScript (Vite)
│   └── src/
│       ├── api/client.ts        # Axios 인스턴스 (JWT 인터셉터)
│       ├── components/          # 재사용 컴포넌트 (common/, charts/, chat/)
│       ├── pages/               # 라우트별 페이지 컴포넌트
│       ├── hooks/               # 커스텀 훅
│       ├── stores/              # Zustand 스토어
│       ├── styles/global.css    # 디자인 토큰 + 글로벌 스타일
│       ├── types/               # TypeScript 인터페이스
│       └── utils/               # 포맷터, 헬퍼
├── backend/
│   └── app/
│       ├── main.py              # FastAPI 엔트리포인트
│       ├── core/                # config, security(JWT), deps
│       ├── api/v1/              # 라우터 (auth, market, portfolio, backtest, simulation, chat)
│       ├── models/              # SQLAlchemy + Pydantic 모델
│       ├── services/            # 비즈니스 로직 계층
│       ├── data/                # yfinance 클라이언트, 캐시
│       └── db/                  # DB 연결, 마이그레이션
├── modules/                     # (기존 Streamlit 코드 — 참고용 보존)
└── app.py                       # (기존 Streamlit — 참고용 보존)
```

### 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React + TypeScript, Vite, React Router v6, Zustand, TanStack Query, Axios, Recharts |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic, python-jose (JWT) |
| DB | SQLite (개발) → PostgreSQL (프로덕션) |
| AI | OpenAI API + SSE 스트리밍 |
| CSS | CSS Modules + CSS 변수 (글로벌 토큰) |

### Key Patterns

1. **프론트-백 통신**: Vite 프록시(`/api` → `localhost:8000`). `api/client.ts`의 Axios 인스턴스가 JWT 자동 첨부/401 처리.

2. **상태관리**: Zustand로 클라이언트 상태 (auth, chat 등), TanStack Query로 서버 상태 (API 데이터 캐싱/리페치).

3. **인증**: JWT (access + refresh token). 백엔드 `core/security.py`에서 토큰 생성/검증, 프론트에서 localStorage에 저장.

4. **백엔드 레이어**: API 라우터 → 서비스(비즈니스 로직) → 데이터(yfinance/DB). 관심사 분리.

5. **스타일링**: `styles/global.css`의 CSS 변수로 다크 테마 토큰 정의. 컴포넌트별 CSS Modules 사용.

### CSS 디자인 토큰 (주요 값)

```css
--bg-primary: #020617;      /* 메인 배경 */
--bg-secondary: #111827;    /* 카드/패널 배경 */
--accent-blue: #2563eb;     /* CTA 버튼 */
--text-primary: #e5e7eb;    /* 본문 텍스트 */
--border-default: #374151;  /* 기본 보더 */
--radius-lg: 16px;          /* 카드 라운딩 */
```

## Configuration

- `backend/.env`: `APP_USERNAME`, `APP_PASSWORD`, `SECRET_KEY`, `OPENAI_API_KEY`
- `backend/app/core/config.py`: pydantic-settings 기반 설정 관리
- `frontend/vite.config.ts`: 프록시 설정

## 코딩 규칙

- 프론트엔드: 함수형 컴포넌트, TypeScript strict mode, CSS Modules
- 백엔드: FastAPI 라우터 → 서비스 → 데이터 레이어 패턴, Pydantic으로 요청/응답 검증
- API 엔드포인트: `/api/v1/` 프리픽스

## Claude 활용 가이드

- 코드 생성, 코드 리뷰, 질문 시 모든 답변은 한국어로 작성해 주세요.
- 코드 설명, 오류 지적, TODO 리스트 등도 반드시 한국어로 출력하게 해주세요.
