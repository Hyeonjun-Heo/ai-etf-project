# 로그인 ui

# modules/ui/auth.py

import os
import streamlit as st
from dotenv import load_dotenv

# .env 로드 (프로세스에서 한 번만 실행되면 됨)
load_dotenv()

# .env 에서 로그인용 계정 정보 읽기
APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "1234")


def _check_credentials(username: str, password: str) -> bool:
    """
    입력 아이디/비밀번호가 .env 에 설정된 값과 일치하는지 확인.
    """
    return username == APP_USERNAME and password == APP_PASSWORD


def render_login_page() -> None:
    """
    메인 영역에 로그인 화면을 렌더링한다.
    - 상단 네비의 '로그인' 버튼이 눌렸을 때 호출되는 것을 전제로 함.
    - 로그인 성공 시 session_state['authenticated'] = True 로 설정하고
      show_login 플래그를 끄고 st.rerun() 으로 새로고침한다.
    """

    # 이미 로그인 상태면 굳이 로그인 폼 안 보여줘도 됨
    if st.session_state.get("authenticated", False):
        st.success("이미 로그인된 상태입니다.")
        return

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown("### 🔐 로그인")
        st.write("AI ETF·배당주 투자 도우미에 접속하려면 ID와 비밀번호를 입력해주세요.")

        # 🔙 이전 화면으로 돌아가기 버튼
        if st.button("← 이전 화면으로 돌아가기"):
            st.session_state["show_login"] = False
            st.rerun()
            return

        # 로그인 폼
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("아이디", value=st.session_state.get("login_username", ""))
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인")

        if submitted:
            st.session_state["login_username"] = username  # 폼 값 유지용

            if _check_credentials(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.session_state["show_login"] = False  # 상단 네비에서 로그인 창 닫기
                st.success("로그인 성공! 🙌")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
