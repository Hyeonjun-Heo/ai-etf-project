import streamlit as st

from modules.ui.main_dashboard import render_main_dashboard
from modules.ui.portfolio_page import render_portfolio_page
from modules.ui.backtest_page import render_backtest_page
from modules.ui.simulation_page import render_simulation_page
from modules.ui.settings_page import render_settings_page
from modules.ui.chat_ui import (
    init_chat_state,
    inject_chat_styles,
    render_chat_fab_and_panel,
)
from modules.ui.auth import render_login_page, render_logout_box
from modules.ui.top_nav import render_top_nav


def main():
    st.set_page_config(
        page_title="AI ETF·배당주 투자 도우미",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 로그인 체크
    logged_in = render_login_page()
    if not logged_in:
        return

    # 공통 스타일
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            min-width: 210px;
            max-width: 210px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 상단 네비바 렌더링 (홈 / 피드 / 주식 골라보기 / 내 계좌)
    active_top_tab = render_top_nav()
    # ↑ 필요하면 이 값을 이용해 페이지 내에서 서브 콘텐츠 분기 가능

    # 챗봇 상태/스타일
    init_chat_state()
    inject_chat_styles()

    # 사이드바 메뉴
    with st.sidebar:
        st.title("📂 메뉴")
        render_logout_box()

        page = st.radio(
            "이동할 페이지를 선택하세요",
            (
                "메인 대시보드",
                "포트폴리오 추천",
                "백테스트",
                "모의투자(가상 계좌)",
                "설정",
            ),
            label_visibility="collapsed",
        )

    # 본문 라우팅
    if page == "메인 대시보드":
        render_main_dashboard()
    elif page == "포트폴리오 추천":
        render_portfolio_page()
    elif page == "백테스트":
        render_backtest_page()
    elif page == "모의투자(가상 계좌)":
        render_simulation_page()
    elif page == "설정":
        render_settings_page()

    # 플로팅 챗봇
    render_chat_fab_and_panel()


if __name__ == "__main__":
    main()