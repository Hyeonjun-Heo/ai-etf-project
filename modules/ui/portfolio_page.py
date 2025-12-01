# modules/ui/portfolio_page.py

import streamlit as st


def render_portfolio_page():
    """포트폴리오 추천 페이지 렌더링 함수"""
    st.header("🧩 포트폴리오 추천")
    st.caption("투자 성향에 따라 ETF 비중을 추천해주는 페이지입니다.")

    st.subheader("1. 투자 성향 입력")
    risk = st.slider("리스크 성향 (1=안정형, 5=공격형)", 1, 5, 3)
    horizon = st.selectbox(
        "투자 기간",
        ["단기 (1년)", "중기 (3~5년)", "장기 (10년 이상)"],
    )

    st.subheader("2. 선호 자산")
    prefs = st.multiselect(
        "선호 ETF 타입",
        ["미국 S&P", "나스닥 성장주", "배당주", "섹터 ETF", "글로벌 분산"],
        default=["미국 S&P", "배당주"],
    )

    st.divider()
    st.subheader("3. 추천 포트폴리오 (더미 데이터)")
    st.write("여기에 나중에 추천 결과 테이블/파이차트가 들어갈 예정입니다.")

    # 나중에 modules.engines.portfolio_engine 와 연결할 자리
    debug_info = {
        "risk": risk,
        "horizon": horizon,
        "prefs": prefs,
    }
    st.caption(f"[DEBUG] 현재 입력값: {debug_info}")