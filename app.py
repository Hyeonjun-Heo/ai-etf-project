import streamlit as st
from modules.main_dashboard import render_main_dashboard
from modules.chat_ui import init_chat_state, inject_chat_styles, render_chat_fab_and_panel

# 페이지 기본 설정
st.set_page_config(
    page_title="AI ETF·배당주 투자 도우미",
    layout="wide"
)

# 공통 스타일 (사이드바)
st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        min-width: 210px;
        max-width: 210px;
    }
    </style>
""", unsafe_allow_html=True)

# 챗봇 상태/스타일 초기화
init_chat_state()
inject_chat_styles()

# 사이드바 메뉴
st.sidebar.title("📂 메뉴")
page = st.sidebar.radio(
    "이동할 페이지를 선택하세요",
    ("메인 대시보드", "포트폴리오 추천", "백테스트", "모의투자(가상 계좌)", "설정")
)

# 본문
if page == "메인 대시보드":
    render_main_dashboard()
elif page == "포트폴리오 추천":
    st.header("🧩 포트폴리오 추천")
    st.write("여기에 포트폴리오 추천 UI가 들어갈 예정입니다.")
elif page == "백테스트":
    st.header("⏱ 백테스트")
    st.write("여기에 백테스트 UI가 들어갈 예정입니다.")
elif page == "모의투자(가상 계좌)":
    st.header("💸 모의투자 (가상 계좌)")
    st.write("여기에 모의투자 UI가 들어갈 예정입니다.")
elif page == "설정":
    st.header("⚙️ 설정")
    st.write("여기에 설정 UI가 들어갈 예정입니다.")

# 화면 가장 마지막에 챗봇 FAB + 패널 렌더
render_chat_fab_and_panel()