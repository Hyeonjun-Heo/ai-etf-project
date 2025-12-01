# modules/ui/backtest_page.py

import streamlit as st


def render_backtest_page():
    """백테스트 페이지 렌더링 함수"""
    st.header("⏱ 백테스트")
    st.caption("ETF 포트폴리오의 과거 성과를 시뮬레이션하는 페이지입니다.")

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("시작일")
    with col2:
        end = st.date_input("종료일")

    tickers = st.text_input("ETF 티커 (쉼표로 구분)", "VOO, QQQ")

    st.button("백테스트 실행")

    st.divider()
    st.subheader("결과 요약")
    st.write("여기에 수익곡선 차트와 주요 지표(CAGR, MDD 등)가 들어갈 예정입니다.")