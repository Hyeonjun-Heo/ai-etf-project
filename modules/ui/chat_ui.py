# modules/chat_ui.py
import streamlit as st


def init_chat_state():
    """지금은 별도 상태가 필요 없어서 빈 함수로 둠 (호환용)."""
    return


def inject_chat_styles():
    """스타일은 아래 render 함수에서 같이 주입하므로 여기선 아무것도 안 함."""
    return


def render_chat_fab_and_panel():
    """
    화면 오른쪽 하단에 고정된 플로팅 버튼(FAB)과
    버튼 클릭 시 열리고 닫히는 챗봇 패널을 렌더링한다.

    - JS 없이 CSS checkbox hack으로 토글
    - position: fixed로 스크롤해도 항상 오른쪽 하단 유지
    """
    st.markdown(
        """
        <style>
        /* 토글용 체크박스는 화면에 보이지 않게 숨김 */
        #ai-chat-toggle {
            display: none;
        }

        /* 플로팅 버튼 (라벨을 버튼처럼 사용) */
        #ai-chat-fab {
            position: fixed;
            right: 24px;
            bottom: 24px;
            width: 48px;
            height: 48px;
            border-radius: 999px;
            background: #2563eb;
            box-shadow: 0 10px 24px rgba(0,0,0,0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 999;
        }
        #ai-chat-fab span {
            font-size: 22px;
            color: #ffffff;
        }

        /* 챗봇 패널 기본 상태: 숨김 */
        #ai-chat-panel {
            position: fixed;
            right: 24px;
            bottom: 84px;
            width: 360px;
            max-height: 70vh;
            background: #111827;
            border-radius: 16px;
            padding: 16px 18px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.5);
            z-index: 998;
            border: 1px solid #1f2933;
            color: #e5e7eb;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
                         sans-serif;
            opacity: 0;
            pointer-events: none;
            transform: translateY(12px);
            transition: opacity 0.18s ease-out, transform 0.18s ease-out;
        }

        #ai-chat-panel-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        #ai-chat-panel-caption {
            font-size: 13px;
            color: #9ca3af;
            margin-bottom: 12px;
        }

        /* 체크박스가 체크되면 패널을 보이게 */
        #ai-chat-toggle:checked ~ #ai-chat-panel {
            opacity: 1;
            pointer-events: auto;
            transform: translateY(0);
        }
        </style>

        <!-- 체크박스 + 라벨(플로팅 버튼) + 패널 -->
        <input type="checkbox" id="ai-chat-toggle" />

        <label id="ai-chat-fab" for="ai-chat-toggle">
            <span>💬</span>
        </label>

        <div id="ai-chat-panel">
            <div id="ai-chat-panel-title">🤖 AI 투자 코치 (준비중)</div>
            <div id="ai-chat-panel-caption">
                나중에 이 패널에는 OpenAI API를 붙여서<br/>
                • 투자 개념 설명<br/>
                • 포트폴리오·백테스트 결과 해설<br/>
                • 질문/답변 챗봇<br/>
                기능을 제공할 예정입니다.
            </div>
            <div style="font-size:13px; color:#d1d5db;">
                지금은 레이아웃과 인터랙션만 먼저 구현한 단계입니다 🙂
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )