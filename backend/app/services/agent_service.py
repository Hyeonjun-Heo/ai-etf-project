"""AI Agent service — Claude Tool Use + SSE streaming."""

import json
from collections.abc import AsyncGenerator

import anthropic

from app.core.config import settings
from app.data.agent_tools import TOOLS, TOOL_LABELS, execute_tool

SYSTEM_PROMPT = """당신은 AI ETF & 주식 투자 도우미입니다.
투자 초보자도 쉽게 이해할 수 있도록 실시간 시장 데이터를 바탕으로 ETF와 주식을 설명하고 인사이트를 제공합니다.

규칙:
- 항상 한국어로 답변하세요.
- 투자 초보자 기준으로 쉽게 설명하세요. 어려운 용어는 반드시 풀어서 설명하세요.
- 데이터가 필요한 질문에는 반드시 도구를 사용하여 최신 정보를 가져오세요.
- 답변은 간결하고 핵심만 담아주세요. 불필요한 면책 조항은 최소화하세요.
- 투자 손실 책임은 본인에게 있음을 전제하되, 정보 제공에 집중하세요.
- 마크다운을 적극 활용해 가독성을 높이세요 (볼드, 불릿, 표 등).
"""


async def stream_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    """
    Claude Tool Use 루프를 실행하고 SSE 이벤트를 yield합니다.

    SSE 이벤트 형식:
    - {"type": "tool_start", "label": "시장 지수 조회 중..."}
    - {"type": "text_delta", "text": "..."}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    if not settings.ANTHROPIC_API_KEY:
        yield _sse({"type": "error", "message": "ANTHROPIC_API_KEY가 설정되지 않았습니다."})
        return

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    current_messages = list(messages)

    try:
        # Tool Use 루프 (non-streaming): tool_use stop_reason이 없을 때까지 반복
        while True:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=current_messages,
            )

            if response.stop_reason != "tool_use":
                # 최종 텍스트 응답 — 스트리밍 전송
                for block in response.content:
                    if hasattr(block, "text"):
                        # 단어 단위로 잘라서 스트리밍 효과 부여
                        text = block.text
                        chunk_size = 4
                        for i in range(0, len(text), chunk_size):
                            yield _sse({"type": "text_delta", "text": text[i : i + chunk_size]})
                yield _sse({"type": "done"})
                return

            # Tool 호출 처리
            tool_results = []
            assistant_content = [_block_to_dict(b) for b in response.content]

            for block in response.content:
                if block.type == "tool_use":
                    label = TOOL_LABELS.get(block.name, "데이터 조회 중...")
                    yield _sse({"type": "tool_start", "label": label})

                    result = await execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )

            current_messages.append({"role": "assistant", "content": assistant_content})
            current_messages.append({"role": "user", "content": tool_results})

    except anthropic.APIError as e:
        yield _sse({"type": "error", "message": f"API 오류: {str(e)}"})
    except Exception as e:
        yield _sse({"type": "error", "message": f"서버 오류가 발생했습니다."})


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _block_to_dict(block) -> dict:
    """ContentBlock Pydantic 모델을 dict로 변환합니다."""
    if block.type == "text":
        return {"type": "text", "text": block.text}
    elif block.type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    return block.model_dump()
