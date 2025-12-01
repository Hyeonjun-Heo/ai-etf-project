# AI ETF · 배당주 투자 보조 웹앱 (Streamlit)

개인용 **ETF·배당주 투자 보조 서비스**입니다.  
Streamlit 기반으로 동작하며, 향후 자동매매(모의투자 → 실제 계좌 연동)까지 확장을 목표로 합니다.

---

## 🎯 주요 기능 (계획)

- 메인 대시보드
  - 오늘 시장 한눈에 (지수 / 환율 / 금리 요약)
  - ETF·배당주 랭킹
  - 요약 차트 (Plotly)
- 포트폴리오 추천
  - 투자 성향 / 기간 / 선호 타입을 기반으로 ETF 비중 추천
- 백테스트
  - 포트폴리오 과거 성과 시뮬레이션 (CAGR, MDD 등)
- 모의투자(가상 계좌)
  - 가상 잔고 관리, 매수/매도, 평가손익 확인
- 설정
  - 손절/익절 비율, 리스크 수준, 기본 선호 옵션 등
- 챗봇 (AI 코치)
  - 화면 우측 하단 플로팅 아이콘 + 패널
  - 투자 개념 설명, 포트폴리오/백테스트 결과 해설 예정

UI 스타일은 **토스증권 느낌의 다크 테마 + 깔끔한 블록 구조**를 지향합니다.

---

## 📁 폴더 구조

```text
project_root/
│
├─ app.py                     # Streamlit 진입점 (메인 라우팅)
│
├─ ui/                        # 화면(페이지) 렌더링 모음
│   ├─ __init__.py
│   ├─ main_dashboard.py      # 메인 대시보드 화면
│   ├─ portfolio_page.py      # 포트폴리오 추천 화면
│   ├─ backtest_page.py       # 백테스트 화면
│   ├─ simulation_page.py     # 모의투자(가상 계좌) 화면
│   ├─ settings_page.py       # 설정 화면
│   └─ chat_ui.py             # 우측 하단 플로팅 챗봇 UI (HTML/CSS/JS)
│
└─ modules/                   # 데이터/엔진/비즈니스 로직
    ├─ __init__.py
    ├─ mock_data.py           # 초기 개발용 더미 데이터
    ├─ data_providers/        # (예정) yfinance 등 가격 데이터 로더
    ├─ portfolio_engine/      # (예정) 포트폴리오 추천 로직
    ├─ backtest_engine/       # (예정) 백테스트 엔진
    ├─ simulation_engine/     # (예정) 모의투자(가상 계좌) 엔진
    └─ ai_engine.py           # (예정) OpenAI 기반 투자 코치 엔진