# modules/main_dashboard.py
import streamlit as st
from .mock_data import get_mock_market_cards


def render_main_dashboard() -> None:
    st.header("📊 메인 대시보드")

    # 상단: 오늘 시장 한눈에
    st.subheader("📌 오늘 시장 한눈에")
    st.caption("주요 지수·환율·금리를 간단히 요약해서 보여줄 영역입니다.")

    cards = get_mock_market_cards()
    cols = st.columns(len(cards))

    for col, card in zip(cols, cards):
        with col:
            st.metric(
                label=card["label"],
                value=card["value"],
                delta=card["delta"],
            )

    st.markdown("---")

    # 중단: 카테고리 탭 + ETF/배당주 리스트
    st.subheader("📈 ETF·배당주 리스트 (랭킹)")
    st.caption("관심 ETF / 인기 ETF / 배당주 랭킹 등을 보여줄 영역입니다.")

    tab1, tab2, tab3 = st.tabs(["관심 ETF", "인기 ETF", "배당주 랭킹"])

    with tab1:
        st.write("관심 ETF 테이블 자리")
    with tab2:
        st.write("인기 ETF 테이블 자리")
    with tab3:
        st.write("배당주 랭킹 테이블 자리")

    st.markdown("---")

    # 하단: 요약 차트 영역
    st.subheader("📉 요약 차트")
    st.caption("상위 ETF 수익률 비교 차트 등이 들어갈 예정입니다.")
    st.write("여기에 Plotly 차트 자리")