"""실시간 시세 WebSocket 엔드포인트.

국내 종목 (6자리 숫자코드): KIS H0STCNT0 WebSocket 실시간 체결가
해외 종목: Yahoo Finance v8 API 3초 폴링
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.data.kis_ws import fetch_overseas_live, stream_domestic_stock

logger = logging.getLogger(__name__)

router = APIRouter()

_OVERSEAS_POLL_SEC = 3  # 해외 폴링 간격


def _is_domestic(symbol: str) -> bool:
    return symbol.isdigit() and len(symbol) == 6


@router.websocket("/stock/{symbol}")
async def stock_realtime_ws(websocket: WebSocket, symbol: str) -> None:
    """실시간 종목 시세 스트림.

    클라이언트가 수신하는 JSON 형식:
    {
      "time":      "HH:MM"   (국내) | "" (해외),
      "price":     float,
      "open":      float,
      "high":      float,
      "low":       float,
      "volume":    int,
      "change":    float,
      "changePct": float
    }
    """
    await websocket.accept()
    symbol = symbol.upper()

    if _is_domestic(symbol):
        # ── 국내: KIS WebSocket 실시간 체결 ─────────────────────
        async def on_data(data: dict) -> None:
            try:
                await websocket.send_json(data)
            except Exception:
                raise  # 연결 종료 → stream_domestic_stock 루프 탈출

        try:
            await stream_domestic_stock(symbol, on_data)
        except (WebSocketDisconnect, Exception):
            pass
    else:
        # ── 해외: Yahoo Finance 폴링 ────────────────────────────
        try:
            while True:
                data = await fetch_overseas_live(symbol)
                if data:
                    await websocket.send_json(data)
                await asyncio.sleep(_OVERSEAS_POLL_SEC)
        except (WebSocketDisconnect, Exception):
            pass
