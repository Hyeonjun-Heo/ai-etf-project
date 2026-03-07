"""Agent tool definitions and execution for Claude Tool Use."""

import json
from app.services.market_service import (
    get_indices,
    get_stock_detail,
    get_search,
    get_ranking,
    get_top_etfs,
)

# Tool definitions (JSON Schema)
TOOLS = [
    {
        "name": "get_market_indices",
        "description": "현재 국내(KOSPI, KOSDAQ) 및 해외(NASDAQ, S&P500, 다우존스, VIX) 시장 지수와 USD/KRW 환율을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_stock_info",
        "description": "특정 종목의 현재가, 시가총액, P/E, 52주 범위, 거래량 등 상세 정보를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "종목 코드 (예: 005930 삼성전자, AAPL 애플, SPY)",
                }
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "search_stocks",
        "description": "종목명 또는 코드로 국내/해외 종목을 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색어 (종목명 또는 코드)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_market_ranking",
        "description": "거래대금, 거래량, 급상승, 급하락 기준으로 시장 랭킹 TOP 10을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sort": {
                    "type": "string",
                    "enum": ["amount", "volume", "rise", "fall"],
                    "description": "정렬 기준: amount(거래대금), volume(거래량), rise(급상승), fall(급하락)",
                },
                "category": {
                    "type": "string",
                    "enum": ["all", "domestic", "overseas"],
                    "description": "시장 구분: all(전체), domestic(국내), overseas(해외). 기본값 domestic",
                },
                "limit": {
                    "type": "integer",
                    "description": "조회 개수 (기본 10, 최대 20)",
                },
            },
            "required": ["sort"],
        },
    },
    {
        "name": "get_top_etfs",
        "description": "국내 상위 ETF 목록과 현재 등락률을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "조회 개수 (기본 10)",
                }
            },
            "required": [],
        },
    },
]

# UI 표시 레이블 (한국어)
TOOL_LABELS: dict[str, str] = {
    "get_market_indices": "시장 지수 조회 중...",
    "get_stock_info": "종목 정보 조회 중...",
    "search_stocks": "종목 검색 중...",
    "get_market_ranking": "시장 랭킹 조회 중...",
    "get_top_etfs": "ETF 목록 조회 중...",
}


async def execute_tool(name: str, tool_input: dict) -> dict:
    """Tool 이름과 입력을 받아 실행하고 결과를 반환합니다."""
    try:
        if name == "get_market_indices":
            return {"indices": get_indices()}

        elif name == "get_stock_info":
            symbol = tool_input.get("symbol", "")
            result = get_stock_detail(symbol)
            return result or {"error": f"종목을 찾을 수 없습니다: {symbol}"}

        elif name == "search_stocks":
            query = tool_input.get("query", "")
            return {"results": get_search(query)}

        elif name == "get_market_ranking":
            return {
                "ranking": get_ranking(
                    sort=tool_input.get("sort", "amount"),
                    category=tool_input.get("category", "domestic"),
                    limit=min(tool_input.get("limit", 10), 20),
                )
            }

        elif name == "get_top_etfs":
            return {"etfs": get_top_etfs(tool_input.get("limit", 10))}

        else:
            return {"error": f"알 수 없는 도구: {name}"}

    except Exception as e:
        return {"error": f"도구 실행 오류: {str(e)}"}
