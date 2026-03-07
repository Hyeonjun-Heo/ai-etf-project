"""KIS WebSocket 실시간 시세 클라이언트.

국내 종목: KIS H0STCNT0 (실시간 체결가)
해외 종목: Yahoo Finance v8 API 폴링 (3초 간격)
"""

import json
import logging
from collections.abc import Awaitable, Callable

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── 도메인 설정 (실전 키가 있으면 실전 도메인 사용) ──────────────
_USE_REAL = bool(settings.KIS_REAL_APP_KEY and settings.KIS_REAL_APP_SECRET)

_KIS_APPROVAL_URL = (
    "https://openapi.koreainvestment.com/oauth2/approvalkey"
    if _USE_REAL
    else "https://openapivts.koreainvestment.com/oauth2/approvalkey"
)
_KIS_WS_URL = (
    "ws://ops.koreainvestment.com:21000"
    if _USE_REAL
    else "ws://ops.koreainvestment.com:31000"
)
_APP_KEY    = settings.KIS_REAL_APP_KEY    if _USE_REAL else settings.KIS_APP_KEY
_APP_SECRET = settings.KIS_REAL_APP_SECRET if _USE_REAL else settings.KIS_APP_SECRET


async def _get_approval_key() -> str:
    """KIS WebSocket 접속 승인키 발급."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            _KIS_APPROVAL_URL,
            json={
                "grant_type": "client_credentials",
                "appkey":     _APP_KEY,
                "secretkey":  _APP_SECRET,
            },
            headers={"content-type": "application/json"},
        )
        return resp.json()["approval_key"]


# ── H0STCNT0 필드 인덱스 ('^' 구분자) ───────────────────────────
_F_TIME  = 1   # 체결시간 HHMMSS
_F_PRICE = 2   # 현재가
_F_SIGN  = 3   # 전일대비부호 (1:상한, 2:상승, 3:보합, 4:하락, 5:하한)
_F_CHNG  = 4   # 전일대비
_F_RATE  = 5   # 전일대비율
_F_OPEN  = 7   # 시가
_F_HIGH  = 8   # 고가
_F_LOW   = 9   # 저가
_F_VOL   = 13  # 누적거래량


def _parse_h0stcnt0(data: str) -> dict | None:
    """H0STCNT0 실시간 체결 데이터('^' 구분) 파싱."""
    fields = data.split("^")
    if len(fields) < 15:
        return None
    try:
        sign = fields[_F_SIGN]
        neg  = sign in ("4", "5")
        t    = fields[_F_TIME]
        return {
            "time":      f"{t[:2]}:{t[2:4]}",
            "price":     float(fields[_F_PRICE]),
            "open":      float(fields[_F_OPEN]),
            "high":      float(fields[_F_HIGH]),
            "low":       float(fields[_F_LOW]),
            "volume":    int(fields[_F_VOL]),
            "change":    float(fields[_F_CHNG]) * (-1 if neg else 1),
            "changePct": float(fields[_F_RATE]) * (-1 if neg else 1),
        }
    except (ValueError, IndexError):
        return None


async def stream_domestic_stock(
    symbol: str,
    callback: Callable[[dict], Awaitable[None]],
) -> None:
    """KIS H0STCNT0 실시간 체결가를 구독하고 파싱된 데이터를 callback으로 전달.

    FastAPI WebSocket 핸들러에서 await으로 호출. 연결이 끊기면 반환됩니다.
    websockets 패키지는 uvicorn[standard]에 포함됩니다.
    """
    import websockets  # noqa: PLC0415 — uvicorn[standard] 의존성

    if not _APP_KEY or not _APP_SECRET:
        logger.warning("KIS API 키가 설정되지 않아 실시간 스트림을 시작할 수 없습니다.")
        return

    try:
        approval_key = await _get_approval_key()
    except Exception as exc:
        logger.warning("KIS 승인키 발급 실패: %s", exc)
        return

    subscribe_msg = json.dumps({
        "header": {
            "approval_key": approval_key,
            "custtype":     "P",
            "tr_type":      "1",
            "content-type": "utf-8",
        },
        "body": {"input": {"tr_id": "H0STCNT0", "tr_key": symbol}},
    })

    try:
        async with websockets.connect(_KIS_WS_URL, ping_interval=None) as ws:
            await ws.send(subscribe_msg)
            async for raw in ws:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")

                # PINGPONG: 서버가 보낸 메시지를 그대로 에코
                if "PINGPONG" in raw:
                    try:
                        await ws.send(raw)
                    except Exception:
                        pass
                    continue

                # 파이프 구분 실시간 데이터
                parts = raw.split("|")
                if len(parts) < 4 or parts[1] != "H0STCNT0":
                    continue

                parsed = _parse_h0stcnt0(parts[3])
                if parsed:
                    await callback(parsed)
    except Exception as exc:
        logger.debug("KIS WebSocket 스트림 종료 (%s): %s", symbol, exc)


async def fetch_overseas_live(symbol: str) -> dict | None:
    """Yahoo Finance v8 API로 해외 종목 현재가를 실시간 조회 (캐시 없음).

    미국 장중에는 ~15분 지연 시세, 장 마감 후에는 after-hours 가격을 반환합니다.
    """
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            resp = await client.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params={"interval": "1d", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            result = resp.json()["chart"]["result"][0]
            meta   = result["meta"]

            price = float(meta.get("regularMarketPrice") or 0)
            prev  = float(meta.get("previousClose") or price)

            # intraday OHLV
            quotes = result.get("indicators", {}).get("quote", [{}])[0]
            open_  = float((quotes.get("open")  or [price])[-1] or price)
            high_  = float((quotes.get("high")  or [price])[-1] or price)
            low_   = float((quotes.get("low")   or [price])[-1] or price)
            vol_   = int((quotes.get("volume") or [0])[-1] or 0)

            return {
                "time":      "",
                "price":     round(price, 4),
                "open":      round(open_,  4),
                "high":      round(high_,  4),
                "low":       round(low_,   4),
                "volume":    vol_,
                "change":    round(price - prev, 4),
                "changePct": round((price - prev) / prev * 100 if prev else 0, 2),
            }
    except Exception as exc:
        logger.debug("Yahoo Finance 조회 실패 (%s): %s", symbol, exc)
        return None
