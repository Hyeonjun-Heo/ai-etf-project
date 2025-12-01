# modules/ui/top_nav.py

import streamlit as st


def render_top_nav() -> str:
    """
    화면 맨 위에 가로 메뉴바를 렌더링하고,
    선택된 메뉴 이름을 반환한다.
    (예: "홈", "피드", "주식 골라보기", "내 계좌")
    """
    _inject_top_nav_styles()

    if "top_nav_active" not in st.session_state:
        st.session_state["top_nav_active"] = "홈"

    if "show_login" not in st.session_state:
        st.session_state["show_login"] = False

    items = ["홈", "피드", "주식 골라보기", "내 계좌"]

    with st.container():
        st.markdown('<div class="top-nav-bar">', unsafe_allow_html=True)

        # 좌측 메뉴 버튼들
        cols = st.columns([0.8, 0.9, 1.4, 1.0, 4])  # 마지막은 오른쪽 여백/버튼 영역
        clicked_item = st.session_state["top_nav_active"]

        for i, label in enumerate(items):
            with cols[i]:
                if st.button(
                    label,
                    key=f"top_nav_{label}",
                    use_container_width=True,
                ):
                    clicked_item = label

        # 우측 영역 (검색 + 로그인 버튼)
        with cols[-1]:
            left, right = st.columns([3, 1])

            with left:
                st.markdown(
                    """
                    <div class="top-nav-right">
                        <div class="top-nav-search">
                            <span class="search-placeholder"> / 를 눌러 검색하세요 </span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with right:
                if not st.session_state.get("authenticated", False):
                    login_clicked = st.button("로그인", key="top_nav_login")
                    if login_clicked:
                        st.session_state["show_login"] = True
                else:
                    logout_clicked = st.button("로그아웃", key="top_nav_logout")
                    if logout_clicked:
                        for k in ("authenticated", "username"):
                            st.session_state.pop(k, None)
                        st.session_state["show_login"] = False
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.session_state["top_nav_active"] = clicked_item
    return clicked_item


@st.cache_resource
def _inject_top_nav_styles():
    """상단 네비바용 CSS 한 번만 주입"""
    st.markdown(
        """
        <style>
        .top-nav-bar {
            background-color: #020617;
            border-bottom: 1px solid #1f2937;
            padding: 6px 16px 4px 16px;
            margin: 0 -1rem 0 -1rem;
        }

        /* 버튼을 탭처럼 보이게 */
        button[data-baseweb="button"][id^="top_nav_"] {
            background: transparent;
            color: #9ca3af;
            border: 1px solid #374151;
            padding: 6px 4px;
            font-size: 13px;
            border-radius: 8px;
        }

        button[data-baseweb="button"][id^="top_nav_"]:hover {
            background: #020617;
            color: #e5e7eb;
        }

        .top-nav-right {
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
        }

        .top-nav-search {
            background-color: #020617;
            border-radius: 999px;
            border: 1px solid #374151;
            padding: 4px 10px;
            font-size: 11px;
            color: #6b7280;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
