"""KIS OpenAPI 기반 시장 데이터 모듈."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.data.kis_client import get_kis

# ── Timezone ──────────────────────────────────────────────────
KST = ZoneInfo("Asia/Seoul")

# ── 캐시 ──────────────────────────────────────────────────────
_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300       # 5분
SPARKLINE_TTL = 60    # 1분 (KIS 토큰 레이트리밋 고려)


def _get_cached(key: str, ttl: int = CACHE_TTL) -> Any | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
        del _cache[key]
    return None


def _set_cached(key: str, data: Any) -> None:
    _cache[key] = (time.time(), data)


def _f(val) -> float:
    """Decimal/str/None → float 안전 변환."""
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


# ── 지수 시세 ─────────────────────────────────────────────────

INDEX_CONFIG = [
    {"symbol": "0001", "name": "코스피", "type": "index"},
    {"symbol": "1001", "name": "코스닥", "type": "index"},
]

# ── 해외 지수 / 환율 ────────────────────────────────────────────

# type=kis   → KIS FHKST03030200 사용 (mrkt+iscd 필요)
# type=yahoo → Yahoo Finance v8 API 사용 (추가 패키지 불필요, httpx 재사용)
OVERSEAS_CONFIG = [
    {"symbol": "KRW=X", "name": "달러환율", "type": "exchange"},
    {"symbol": "COMP",  "name": "나스닥",   "type": "kis",   "mrkt": "N", "iscd": "COMP"},
    {"symbol": "SPX",   "name": "S&P500",   "type": "kis",   "mrkt": "N", "iscd": "SPX"},
    {"symbol": "DJI",   "name": "다우존스", "type": "kis",   "mrkt": "N", "iscd": ".DJI"},
    {"symbol": "VIX",   "name": "VIX",      "type": "yahoo", "iscd": "^VIX"},
]

# 해외 심볼 → Yahoo Finance 심볼 매핑 (sparkline용)
OVERSEAS_YAHOO_SYMBOL = {
    "KRW=X": "USDKRW=X",
    "COMP":  "^IXIC",
    "SPX":   "^GSPC",
    "DJI":   "^DJI",
    "VIX":   "^VIX",
}


def _fetch_domestic_index(code: str, name: str) -> dict:
    """raw API로 국내 지수 시세 조회."""
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/domestic-stock/v1/quotations/inquire-index-price",
            method="GET",
            params={"FID_COND_MRKT_DIV_CODE": "U", "FID_INPUT_ISCD": code},
            headers={"tr_id": "FHPUP02100000"},
            domain="real",
        )
        o = r.output
        return {
            "symbol": code,
            "name": name,
            "price": round(_f(o.bstp_nmix_prpr), 2),
            "change": round(_f(o.bstp_nmix_prdy_vrss), 2),
            "changePct": round(_f(o.bstp_nmix_prdy_ctrt), 2),
        }
    except Exception:
        return {"symbol": code, "name": name, "price": 0, "change": 0, "changePct": 0}


def _fetch_yahoo_finance(symbol: str, name: str, yahoo_symbol: str) -> dict:
    """Yahoo Finance v8 API로 지수/환율 현재가 조회 (KIS 미지원 심볼용)."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        resp = httpx.get(
            url,
            params={"interval": "1d", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        meta = resp.json()["chart"]["result"][0]["meta"]
        price = float(meta.get("regularMarketPrice") or 0)
        prev = float(meta.get("previousClose") or meta.get("chartPreviousClose") or price)
        change = round(price - prev, 2)
        changePct = round((change / prev * 100) if prev else 0, 2)
        return {"symbol": symbol, "name": name, "price": round(price, 2), "change": change, "changePct": changePct}
    except Exception:
        return {"symbol": symbol, "name": name, "price": 0, "change": 0, "changePct": 0}


def _fetch_exchange_rate(symbol: str, name: str) -> dict:
    """USD/KRW 환율 조회. KIS FHKST03030100 우선, 실패 시 Yahoo Finance 폴백."""
    # 1) KIS 시도
    try:
        today = datetime.now(KST).strftime("%Y%m%d")
        kis = get_kis()
        r = kis.fetch(
            "/uapi/overseas-price/v1/quotations/inquire-daily-chartprice",
            method="GET",
            params={
                "FID_COND_MRKT_DIV_CODE": "X",
                "FID_INPUT_ISCD": "USD",
                "FID_INPUT_DATE_1": today,
                "FID_INPUT_DATE_2": today,
                "FID_PERIOD_DIV_CODE": "D",
            },
            headers={"tr_id": "FHKST03030100"},
            domain="real",
        )
        try:
            o = r.output1
        except AttributeError:
            o = r.output
        price = _f(getattr(o, "ovrs_nmix_prpr", 0))
        if price > 0:
            return {
                "symbol": symbol,
                "name": name,
                "price": round(price, 2),
                "change": round(_f(getattr(o, "ovrs_nmix_prdy_vrss", 0)), 2),
                "changePct": round(_f(getattr(o, "prdy_ctrt", 0)), 2),
            }
    except Exception:
        pass

    # 2) Yahoo Finance 폴백 (USDKRW=X: 1 USD = X KRW, 한국 표준 방향)
    return _fetch_yahoo_finance(symbol, name, "USDKRW=X")


def _get_usd_krw() -> float:
    """캐시된 indices에서 USD/KRW 환율 반환. 없으면 직접 조회, 최종 폴백 1300."""
    cached = _get_cached("indices")
    if cached:
        for item in cached:
            if item.get("symbol") == "KRW=X" and item.get("price"):
                return float(item["price"])
    try:
        result = _fetch_exchange_rate("KRW=X", "달러환율")
        return result.get("price") or 1300.0
    except Exception:
        return 1300.0


def _fetch_overseas_index(symbol: str, name: str, mrkt: str, iscd: str) -> dict:
    """FHKST03030200로 해외 지수 및 환율 현재가 조회."""
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice",
            method="GET",
            params={
                "FID_COND_MRKT_DIV_CODE": mrkt,
                "FID_INPUT_ISCD": iscd,
                "FID_HOUR_CLS_CODE": "0",
                "FID_PW_DATA_INCU_YN": "N",
            },
            headers={"tr_id": "FHKST03030200"},
            domain="real",
        )
        try:
            o = r.output1
        except AttributeError:
            o = r.output
        return {
            "symbol": symbol,
            "name": name,
            "price": round(_f(o.ovrs_nmix_prpr), 2),
            "change": round(_f(o.ovrs_nmix_prdy_vrss), 2),
            "changePct": round(_f(o.prdy_ctrt), 2),
        }
    except Exception:
        return {"symbol": symbol, "name": name, "price": 0, "change": 0, "changePct": 0}


def fetch_indices() -> list[dict]:
    cache_key = "indices"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    with ThreadPoolExecutor(max_workers=7) as pool:
        overseas_futures = [
            pool.submit(_fetch_exchange_rate, cfg["symbol"], cfg["name"])
            if cfg["type"] == "exchange"
            else pool.submit(_fetch_yahoo_finance, cfg["symbol"], cfg["name"], cfg["iscd"])
            if cfg["type"] == "yahoo"
            else pool.submit(_fetch_overseas_index, cfg["symbol"], cfg["name"], cfg["mrkt"], cfg["iscd"])
            for cfg in OVERSEAS_CONFIG
        ]
        domestic_futures = [
            pool.submit(_fetch_domestic_index, "0001", "코스피"),
            pool.submit(_fetch_domestic_index, "1001", "코스닥"),
        ]
        # 순서: 달러환율, 나스닥, S&P500, 다우존스, VIX, 코스피, 코스닥
        results = [f.result() for f in overseas_futures] + [f.result() for f in domestic_futures]

    _set_cached(cache_key, results)
    return results


# ── 지수 스파크라인 (당일 1분봉) ──────────────────────────────

# 지수별 프록시 ETF (인트라데이 차트용)
INDEX_SPARKLINE_PROXY = {
    "0001": "069500",   # 코스피  → KODEX 200
    "1001": "229200",   # 코스닥  → KODEX 코스닥150
}


def _fetch_one_sparkline(symbol: str) -> dict:
    proxy = INDEX_SPARKLINE_PROXY.get(symbol, symbol)
    try:
        kis = get_kis()
        chart = kis.stock(proxy).chart("1d")
        bars = list(chart.bars)[-180:]
        prev_close = _f(bars[0].prev_price) if bars and hasattr(bars[0], "prev_price") else None
        points = [
            {"date": b.time_kst.strftime("%H:%M"), "close": round(_f(b.close), 2)}
            for b in bars
        ]
        return {"points": points, "previousClose": prev_close}
    except Exception:
        return {"points": [], "previousClose": None}


def _fetch_overseas_sparkline(yahoo_symbol: str) -> dict:
    """Yahoo Finance 5분봉으로 오늘 마지막 3시간(36봉) sparkline 조회."""
    try:
        resp = httpx.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
            params={"interval": "5m", "range": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        data = resp.json()["chart"]["result"][0]
        meta = data["meta"]
        prev_close = float(meta.get("previousClose") or meta.get("chartPreviousClose") or 0) or None
        timestamps = data.get("timestamp", [])
        closes = data["indicators"]["quote"][0].get("close", [])

        # ✅ 유효한 bar만 추출 + timestamp를 KST HH:MM 라벨로 변환
        bars: list[dict] = []
        for ts, c in zip(timestamps, closes):
            if c is None:
                continue
            dt = datetime.fromtimestamp(int(ts), tz=KST)
            bars.append({"date": dt.strftime("%H:%M"), "close": round(float(c), 4)})

        # 마지막 36개(3시간 = 36 × 5분)
        points = bars[-36:]

        return {"points": points, "previousClose": prev_close}
    except Exception:
        return {"points": [], "previousClose": None}


def fetch_index_sparklines() -> dict[str, dict]:
    cache_key = "index_sparklines"
    cached = _get_cached(cache_key, ttl=SPARKLINE_TTL)
    if cached is not None:
        return cached

    domestic_symbols = [cfg["symbol"] for cfg in INDEX_CONFIG]
    overseas_symbols = [(s, y) for s, y in OVERSEAS_YAHOO_SYMBOL.items()]

    with ThreadPoolExecutor(max_workers=9) as pool:
        domestic_futures = [pool.submit(_fetch_one_sparkline, sym) for sym in domestic_symbols]
        overseas_futures = [pool.submit(_fetch_overseas_sparkline, yahoo) for _, yahoo in overseas_symbols]

    result = dict(zip(domestic_symbols, [f.result() for f in domestic_futures]))
    result.update(dict(zip([s for s, _ in overseas_symbols], [f.result() for f in overseas_futures])))

    _set_cached(cache_key, result)
    return result


# ── 한국 ETF 랭킹 ──────────────────────────────────────────────

def _parse_num(s: str | None) -> float:
    """Naver Finance 숫자 문자열 → float 변환."""
    if not s:
        return 0.0
    try:
        return float(str(s).replace(",", "").replace("-", "0") or 0)
    except ValueError:
        return 0.0


def _fetch_etf_list_naver(page_size: int = 100) -> list[dict]:
    """Naver Finance 모바일 API — 국내 ETF 전체 목록 (동적, 신규/상장폐지 자동 반영)."""
    try:
        resp = httpx.get(
            "https://m.stock.naver.com/api/stocks/etf",
            params={"pageSize": str(page_size)},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        stocks = json.loads(resp.content).get("stocks", [])
        results = []
        for s in stocks:
            code = s.get("itemCode", "")
            name = s.get("stockName", "")
            if not code or not name:
                continue
            results.append({
                "symbol":    code,
                "name":      name,
                "price":     _parse_num(s.get("closePrice")),
                "change":    _parse_num(s.get("compareToPreviousClosePrice")),
                "changePct": _parse_num(s.get("fluctuationsRatio")),
                "volume":    int(_parse_num(s.get("accumulatedTradingVolume"))),
                "amount":    int(_parse_num(s.get("accumulatedTradingValue"))),
            })
        return results
    except Exception:
        return []


def fetch_top_etfs(limit: int = 10) -> list[dict]:
    cache_key = f"top_etfs_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    etfs = _fetch_etf_list_naver(page_size=100)
    etfs.sort(key=lambda x: x["changePct"], reverse=True)
    results = etfs[:limit]
    _set_cached(cache_key, results)
    return results


def fetch_domestic_etf_ranking(sort: str = "amount", limit: int = 20) -> list[dict]:
    """Naver Finance ETF 전체 목록에서 sort 기준으로 반환 (동적)."""
    cache_key = f"domestic_etf_{sort}_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    etfs = _fetch_etf_list_naver(page_size=100)

    if sort == "volume":
        etfs.sort(key=lambda x: x.get("volume") or 0, reverse=True)
    elif sort == "rise":
        etfs.sort(key=lambda x: x.get("changePct") or 0, reverse=True)
    elif sort == "fall":
        etfs.sort(key=lambda x: x.get("changePct") or 0)
    else:  # amount
        etfs.sort(key=lambda x: x.get("amount") or 0, reverse=True)

    results = etfs[:limit]
    _set_cached(cache_key, results)
    return results


# ── 차트 데이터 ────────────────────────────────────────────────

VALID_PERIODS = {"1d", "1w", "1mo", "3mo", "6mo", "1y", "2y", "3y", "5y"}

PERIOD_MAP = {
    "1d":  "1d",
    "1w":  "7d",
    "1mo": "30d",
    "3mo": "90d",
    "6mo": "180d",
    "1y":  "1y",
}

# 1y 초과 국내 장기 기간 → daily_chart(start=timedelta) 사용
DOMESTIC_LONG_PERIOD_DELTA: dict[str, timedelta] = {
    "2y": timedelta(days=365 * 2),
    "3y": timedelta(days=365 * 3),
    "5y": timedelta(days=365 * 5),
}


def _is_domestic_symbol(symbol: str) -> bool:
    """6자리 숫자면 국내 종목 코드로 판단."""
    return symbol.isdigit() and len(symbol) == 6


# KIS excd 코드 → python-kis market 이름 매핑
EXCD_TO_MARKET: dict[str, str] = {
    "NAS": "NASDAQ",
    "NYS": "NYSE",
    "AMS": "AMEX",
}

# period → daily_chart() start 인자 (timedelta)
OVERSEAS_PERIOD_DELTA: dict[str, timedelta] = {
    "1w":  timedelta(weeks=1),
    "1mo": timedelta(days=31),
    "3mo": timedelta(days=93),
    "6mo": timedelta(days=186),
    "1y":  timedelta(days=365),
    "2y":  timedelta(days=365 * 2),
    "3y":  timedelta(days=365 * 3),
    "5y":  timedelta(days=365 * 5),
}


# ── Yahoo Finance interval 매핑 ────────────────────────────────
# 사용자 interval(분) → (Yahoo interval 문자열, Yahoo interval 분 단위, 최대 조회 가능 일수)
_YF_INTRADAY: dict[int, tuple[str, int, int]] = {
    1:   ("1m",  1,  7),
    3:   ("5m",  5, 60),
    5:   ("5m",  5, 60),
    10:  ("5m",  5, 60),
    15:  ("15m", 15, 730),
    30:  ("30m", 30, 730),
    60:  ("60m", 60, 730),
    120: ("60m", 60, 730),
    240: ("60m", 60, 730),
}


def _aggregate_intraday(bars: list[dict], source_min: int, target_min: int) -> list[dict]:
    """source_min 단위 봉을 target_min 단위 봉으로 집계 (target이 source의 배수일 때만)."""
    if target_min <= source_min or target_min % source_min != 0:
        return bars
    ratio = target_min // source_min
    result = []
    for i in range(0, len(bars), ratio):
        chunk = [b for b in bars[i:i + ratio] if b.get("close") is not None]
        if not chunk:
            continue
        first = chunk[0]
        result.append({
            "date":   first["date"],
            "ts":     first["ts"],
            "open":   first["open"],
            "high":   max(b["high"] for b in chunk),
            "low":    min(b["low"] for b in chunk),
            "close":  chunk[-1]["close"],
            "volume": sum(b["volume"] for b in chunk),
        })
    return result


def _fetch_overseas_intraday_yahoo(symbol: str, interval_minutes: int, days: int = 30) -> list[dict]:
    """Yahoo Finance v8 API로 해외 종목 분봉 히스토리 조회."""
    yf_interval, source_min, max_days = _YF_INTRADAY.get(interval_minutes, ("5m", 5, 60))
    actual_days = min(days, max_days)
    try:
        resp = httpx.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": yf_interval, "range": f"{actual_days}d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        result_list = resp.json().get("chart", {}).get("result")
        if not result_list:
            return []
        raw = result_list[0]
        timestamps = raw.get("timestamp", [])
        q = raw["indicators"]["quote"][0]
        bars: list[dict] = []
        for ts, o, h, l, c, v in zip(
            timestamps,
            q.get("open", []),
            q.get("high", []),
            q.get("low", []),
            q.get("close", []),
            q.get("volume", []),
        ):
            if ts is None or c is None:
                continue
            kst_dt = datetime.fromtimestamp(int(ts), tz=KST)
            bars.append({
                "date":   kst_dt.strftime("%H:%M"),
                "ts":     int(ts),
                "open":   round(float(o or c), 4),
                "high":   round(float(h or c), 4),
                "low":    round(float(l or c), 4),
                "close":  round(float(c), 4),
                "volume": int(v or 0),
            })
        bars.sort(key=lambda x: x["ts"])
        return _aggregate_intraday(bars, source_min, interval_minutes)
    except Exception:
        return []


def _fetch_domestic_intraday_yahoo(symbol: str, interval_minutes: int, days: int = 30) -> list[dict]:
    """Yahoo Finance v8 API로 국내 종목(KOSPI) 분봉 히스토리 조회.
    KOSPI 종목은 {symbol}.KS 심볼로 5m/30d 데이터를 제공한다.
    KOSDAQ 종목은 Yahoo Finance가 일봉만 반환하므로 빈 리스트를 반환한다.
    """
    yf_interval, source_min, max_days = _YF_INTRADAY.get(interval_minutes, ("5m", 5, 60))
    actual_days = min(days, max_days)

    # .KS(KOSPI) 먼저, .KQ(KOSDAQ)는 Yahoo에서 일봉만 반환하므로 시도하지 않음
    for suffix in (".KS",):
        yahoo_symbol = f"{symbol}{suffix}"
        try:
            resp = httpx.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
                params={"interval": yf_interval, "range": f"{actual_days}d"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            resp.raise_for_status()
            result_list = resp.json().get("chart", {}).get("result")
            if not result_list:
                continue
            raw = result_list[0]
            # dataGranularity가 일봉이면 KOSDAQ 일봉 응답 — 사용 안 함
            if raw.get("meta", {}).get("dataGranularity", "") not in (yf_interval, "5m", "1m", "15m", "30m", "60m"):
                continue
            timestamps = raw.get("timestamp", [])
            if not timestamps or len(timestamps) < 30:
                continue
            q = raw["indicators"]["quote"][0]
            bars: list[dict] = []
            for ts, o, h, l, c, v in zip(
                timestamps,
                q.get("open", []),
                q.get("high", []),
                q.get("low", []),
                q.get("close", []),
                q.get("volume", []),
            ):
                if ts is None or c is None:
                    continue
                kst_dt = datetime.fromtimestamp(int(ts), tz=KST)
                bars.append({
                    "date":   kst_dt.strftime("%H:%M"),
                    "ts":     int(ts),
                    "open":   round(float(o or c), 2),
                    "high":   round(float(h or c), 2),
                    "low":    round(float(l or c), 2),
                    "close":  round(float(c), 2),
                    "volume": int(v or 0),
                })
            bars.sort(key=lambda x: x["ts"])
            return _aggregate_intraday(bars, source_min, interval_minutes)
        except Exception:
            continue
    return []


def _fetch_domestic_intraday_naver(symbol: str, interval_minutes: int, days: int = 30) -> list[dict]:
    """Naver Finance JSON API로 국내 종목 1분봉 히스토리 조회 → interval_minutes 단위로 집계.
    KOSPI/KOSDAQ 모두 지원. 약 6거래일치 데이터 제공.
    volume은 당일 누적 거래량이므로 봉간 차이로 변환.
    """
    now = datetime.now(KST)
    start = (now - timedelta(days=days + 7)).strftime("%Y%m%d090000")
    end = now.strftime("%Y%m%d%H%M%S")
    try:
        resp = httpx.get(
            f"https://api.stock.naver.com/chart/domestic/item/{symbol}/minute",
            params={"startDateTime": start, "endDateTime": end},
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"},
            timeout=15,
        )
        resp.raise_for_status()
        raw_bars = resp.json()
        if not raw_bars or len(raw_bars) < 10:
            return []

        bars: list[dict] = []
        prev_date = ""
        prev_acml_vol = 0

        for item in raw_bars:
            dt_str = item.get("localDateTime", "")
            if len(dt_str) < 12:
                continue
            c = item.get("currentPrice")
            if c is None:
                continue
            dt = datetime.strptime(dt_str[:12], "%Y%m%d%H%M").replace(tzinfo=KST)
            cur_date = dt_str[:8]
            acml_vol = int(item.get("accumulatedTradingVolume") or 0)

            # 봉별 거래량 = 누적 거래량 차이 (날짜 바뀌면 리셋)
            if cur_date != prev_date:
                bar_vol = acml_vol
                prev_date = cur_date
            else:
                bar_vol = max(0, acml_vol - prev_acml_vol)
            prev_acml_vol = acml_vol

            o = float(item.get("openPrice") or c)
            h = float(item.get("highPrice") or c)
            l = float(item.get("lowPrice") or c)
            bars.append({
                "date":   dt.strftime("%H:%M"),
                "ts":     int(dt.timestamp()),
                "open":   round(o, 2),
                "high":   round(h, 2),
                "low":    round(l, 2),
                "close":  round(float(c), 2),
                "volume": bar_vol,
            })

        bars.sort(key=lambda x: x["ts"])
        return _aggregate_intraday(bars, 1, interval_minutes)
    except Exception:
        return []


def _fetch_domestic_long_chart(symbol: str, period: str) -> list[dict]:
    """국내 종목 장기 차트 — Yahoo Finance .KS/.KQ 심볼로 조회.
    KIS API가 일봉 데이터를 최대 1년치만 반환하는 한계를 우회한다.
    """
    # Yahoo Finance range: 2y 또는 5y (3y는 5y로 처리)
    yahoo_range = "2y" if period == "2y" else "5y"
    for suffix in (".KS", ".KQ"):
        yahoo_symbol = f"{symbol}{suffix}"
        try:
            resp = httpx.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
                params={"interval": "1d", "range": yahoo_range},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            result = resp.json()["chart"]["result"]
            if not result:
                continue
            raw = result[0]
            timestamps = raw.get("timestamp", [])
            if not timestamps:
                continue
            q = raw["indicators"]["quote"][0]
            rows: list[dict] = []
            for ts, o, h, l, c, v in zip(
                timestamps,
                q.get("open", []),
                q.get("high", []),
                q.get("low", []),
                q.get("close", []),
                q.get("volume", []),
            ):
                if c is None:
                    continue
                dt = datetime.fromtimestamp(int(ts), tz=KST)
                rows.append({
                    "date":   dt.strftime("%Y-%m-%d"),
                    "open":   round(float(o or c), 2),
                    "high":   round(float(h or c), 2),
                    "low":    round(float(l or c), 2),
                    "close":  round(float(c), 2),
                    "volume": int(v or 0),
                })
            if rows:
                return sorted(rows, key=lambda x: x["date"])
        except Exception:
            continue
    return []


def fetch_chart(symbol: str = "005930", period: str = "1y", excd: str = "", interval: int = 10) -> list[dict]:
    if period not in VALID_PERIODS:
        period = "1y"

    cache_key = f"chart_{symbol}_{period}_{excd}_{interval if period == '1d' else ''}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # 해외 심볼
    if not _is_domestic_symbol(symbol):
        markets = [EXCD_TO_MARKET[excd]] if excd in EXCD_TO_MARKET else ["NASDAQ", "NYSE", "AMEX"]
        data: list[dict] = []

        if period == "1d":
            # 해외 인트라데이 — Yahoo Finance로 30일치 분봉 히스토리 조회
            data = _fetch_overseas_intraday_yahoo(symbol, interval, days=30)
            if not data:
                # Yahoo 실패 시 KIS 폴백 (당일 세션만)
                for market in markets:
                    try:
                        kis = get_kis()
                        chart = kis.stock(symbol, market=market).chart("1d", period=interval)
                        rows: list[dict] = []
                        for b in chart.bars:
                            c = round(_f(b.close), 4)
                            o = round(_f(b.open),  4)
                            h = round(_f(b.high),  4)
                            l = round(_f(b.low),   4)
                            v = int(_f(b.volume))
                            ts = int(b.time_kst.timestamp())
                            rows.append({
                                "date":   b.time_kst.strftime("%H:%M"),
                                "ts":     ts,
                                "open":   o or c,
                                "high":   h or c,
                                "low":    l or c,
                                "close":  c,
                                "volume": v,
                            })
                        if rows:
                            data = sorted(rows, key=lambda x: x["ts"])
                            break
                    except Exception:
                        continue
        else:
            # 해외 일봉 이상 — daily_chart(start=timedelta)
            expr = OVERSEAS_PERIOD_DELTA.get(period, timedelta(days=365))
            for market in markets:
                try:
                    kis = get_kis()
                    chart = kis.stock(symbol, market=market).daily_chart(start=expr)
                    rows = []
                    for b in chart.bars:
                        c = round(_f(b.close), 4)
                        o = round(_f(b.open),  4)
                        h = round(_f(b.high),  4)
                        l = round(_f(b.low),   4)
                        v = int(_f(b.volume))
                        rows.append({
                            "date":   b.time_kst.strftime("%Y-%m-%d"),
                            "open":   o or c,
                            "high":   h or c,
                            "low":    l or c,
                            "close":  c,
                            "volume": v,
                        })
                    if rows:
                        data = sorted(rows, key=lambda x: x["date"])
                        break
                except Exception:
                    continue

        _set_cached(cache_key, data)
        return data

    # 국내 종목 → 장기(2y/3y/5y)는 Yahoo Finance .KS/.KQ 폴백 사용
    intraday = period == "1d"

    if period in DOMESTIC_LONG_PERIOD_DELTA:
        data = _fetch_domestic_long_chart(symbol, period)
        if data:
            _set_cached(cache_key, data)
            return data
        # Yahoo Finance 실패 시 KIS 1y 폴백
        period = "1y"

    if intraday:
        # 국내 인트라데이: Yahoo(.KS, KOSPI 30일) → Naver(국내 ~6거래일) → KIS(당일)
        data = _fetch_domestic_intraday_yahoo(symbol, interval, days=30)
        if not data:
            data = _fetch_domestic_intraday_naver(symbol, interval, days=30)

    if not intraday or not data:
        try:
            kis = get_kis()
            kis_period = PERIOD_MAP.get(period, "1y")
            chart = (
                kis.stock(symbol).chart("1d", period=interval)
                if intraday
                else kis.stock(symbol).chart(kis_period)
            )
            data = []
            for b in chart.bars:
                c = round(_f(b.close), 2)
                o = round(_f(b.open),  2) if hasattr(b, "open")   else c
                h = round(_f(b.high),  2) if hasattr(b, "high")   else c
                l = round(_f(b.low),   2) if hasattr(b, "low")    else c
                v = int(_f(b.volume))     if hasattr(b, "volume") else 0
                entry: dict = {
                    "date":   b.time_kst.strftime("%H:%M" if intraday else "%Y-%m-%d"),
                    "open":   o,
                    "high":   h,
                    "low":    l,
                    "close":  c,
                    "volume": v,
                }
                if intraday:
                    entry["ts"] = int(b.time_kst.timestamp())
                data.append(entry)
        except Exception:
            if not data:
                data = []

    _set_cached(cache_key, data)
    return data


# ── 종목 상세 정보 ────────────────────────────────────────────

def fetch_stock_detail(symbol: str) -> dict | None:
    cache_key = f"stock_detail_{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        kis = get_kis()
        q = kis.stock(symbol).quote()
        ind = q.indicator if hasattr(q, "indicator") else None

        data = {
            "symbol": symbol,
            "name": q.info.name if (hasattr(q, "info") and q.info and hasattr(q.info, "name")) else symbol,
            "price": round(_f(q.price), 2),
            "change": round(_f(q.change), 2),
            "changePct": round(_f(q.rate), 2),
            "volume": int(_f(q.volume)) if hasattr(q, "volume") else None,
            "open": round(_f(q.open), 2) if hasattr(q, "open") else None,
            "high": round(_f(q.high), 2) if hasattr(q, "high") else None,
            "low": round(_f(q.low), 2) if hasattr(q, "low") else None,
            "previousClose": round(_f(q.prev_price), 2) if hasattr(q, "prev_price") else None,
            "marketCap": int(_f(q.market_cap)) if (hasattr(q, "market_cap") and q.market_cap) else None,
            "peRatio": round(_f(ind.per), 2) if (ind and hasattr(ind, "per") and ind.per) else None,
            "pbr": round(_f(ind.pbr), 2) if (ind and hasattr(ind, "pbr") and ind.pbr) else None,
            "eps": round(_f(ind.eps), 2) if (ind and hasattr(ind, "eps") and ind.eps) else None,
            "fiftyTwoWeekHigh": round(_f(ind.week52_high), 2) if (ind and hasattr(ind, "week52_high")) else None,
            "fiftyTwoWeekLow": round(_f(ind.week52_low), 2) if (ind and hasattr(ind, "week52_low")) else None,
        }
        _set_cached(cache_key, data)
        return data
    except Exception:
        return None


# ── 시장 무버 (등락률 상위/하위) ──────────────────────────────

def _fetch_fluctuation_rank_single(sort_code: str, iscd: str, mrkt: str = "J") -> list[dict]:
    """KIS FHPST01700000 — 등락률 상위/하위 단일 ISCD 조회."""
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/domestic-stock/v1/ranking/fluctuation",
            method="GET",
            params={
                "FID_COND_MRKT_DIV_CODE": mrkt,
                "FID_COND_SCR_DIV_CODE": "20170",
                "FID_INPUT_ISCD": iscd,
                "FID_RANK_SORT_CLS_CODE": sort_code,  # "1"=상승률, "0"=하락률
                "FID_INPUT_CNT_1": "0",
                "FID_PRC_CLS_CODE": "0",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_TRGT_CLS_CODE": "0",
                "FID_TRGT_EXLS_CLS_CODE": "0",
                "FID_DIV_CLS_CODE": "0",
                "FID_RSFL_RATE1": "",
                "FID_RSFL_RATE2": "",
            },
            headers={"tr_id": "FHPST01700000"},
            domain="real",
        )
        output = r.output
        if not isinstance(output, list):
            output = [output] if output else []
        return [
            {
                "symbol":    str(getattr(o, "mksc_shrn_iscd", "")),
                "name":      str(getattr(o, "hts_kor_isnm", "")),
                "price":     round(_f(getattr(o, "stck_prpr", 0)), 0),
                "change":    round(_f(getattr(o, "prdy_vrss", 0)), 0),
                "changePct": round(_f(getattr(o, "prdy_ctrt", 0)), 2),
            }
            for o in output
        ]
    except Exception:
        return []


def _fetch_fluctuation_rank(sort_code: str, limit: int, mrkt: str = "J") -> list[dict]:
    """KIS FHPST01700000 — 등락률 상위/하위.
    KOSPI(0001) + KOSDAQ(1001) 병렬 조회 후 등락률 재정렬 → 최대 60건.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_kospi  = pool.submit(_fetch_fluctuation_rank_single, sort_code, "0001", mrkt)
        f_kosdaq = pool.submit(_fetch_fluctuation_rank_single, sort_code, "1001", mrkt)
        kospi  = f_kospi.result()
        kosdaq = f_kosdaq.result()

    # 심볼 기준 중복 제거 (코스피·코스닥은 코드 체계가 달라 실제 중복 없음)
    seen: set[str] = set()
    merged: list[dict] = []
    for item in kospi + kosdaq:
        if item["symbol"] not in seen:
            seen.add(item["symbol"])
            merged.append(item)

    # 상승률(1) → changePct 내림차순 / 하락률(0) → changePct 오름차순
    reverse = (sort_code == "1")
    merged.sort(key=lambda x: x.get("changePct") or 0, reverse=reverse)
    return merged[:limit]


def fetch_movers() -> dict[str, list[dict]]:
    cache_key = "movers"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_gainers = pool.submit(_fetch_fluctuation_rank, "1", 5)   # 1=상승률
        f_losers  = pool.submit(_fetch_fluctuation_rank, "0", 5)   # 0=하락률
        gainers = f_gainers.result()
        losers  = f_losers.result()

    data = {"gainers": gainers, "losers": losers}
    _set_cached(cache_key, data)
    return data


# ── 실시간 랭킹 ────────────────────────────────────────────────

def _fetch_volume_rank_single(blng_cls_code: str, iscd: str, mrkt: str = "J") -> list[dict]:
    """KIS FHPST01710000 — 거래량(0)/거래대금(3) 순위 단일 ISCD 조회."""
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/domestic-stock/v1/quotations/volume-rank",
            method="GET",
            params={
                "FID_COND_MRKT_DIV_CODE": mrkt,
                "FID_COND_SCR_DIV_CODE": "20171",
                "FID_INPUT_ISCD": iscd,
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": blng_cls_code,
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000",
                "FID_INPUT_PRICE_1": "",
                "FID_INPUT_PRICE_2": "",
                "FID_VOL_CNT": "",
                "FID_INPUT_DATE_1": "",
            },
            headers={"tr_id": "FHPST01710000"},
            domain="real",
        )
        output = r.output
        if not isinstance(output, list):
            output = [output] if output else []
        return [
            {
                "symbol":    str(getattr(o, "mksc_shrn_iscd", "")),
                "name":      str(getattr(o, "hts_kor_isnm", "")),
                "price":     round(_f(getattr(o, "stck_prpr", 0)), 0),
                "change":    round(_f(getattr(o, "prdy_vrss", 0)), 0),
                "changePct": round(_f(getattr(o, "prdy_ctrt", 0)), 2),
                "volume":    int(_f(getattr(o, "acml_vol", 0))),
                "amount":    int(_f(getattr(o, "acml_tr_pbmn", 0))),
            }
            for o in output
        ]
    except Exception:
        return []


def _fetch_volume_rank(blng_cls_code: str, limit: int, mrkt: str = "J") -> list[dict]:
    """KIS FHPST01710000 — 거래량(0) / 거래대금(3) 순위.
    KOSPI(0001) + KOSDAQ(1001) 병렬 조회 후 기준값 재정렬 → 최대 60건.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_kospi  = pool.submit(_fetch_volume_rank_single, blng_cls_code, "0001", mrkt)
        f_kosdaq = pool.submit(_fetch_volume_rank_single, blng_cls_code, "1001", mrkt)
        kospi  = f_kospi.result()
        kosdaq = f_kosdaq.result()

    # 심볼 기준 중복 제거
    seen: set[str] = set()
    merged: list[dict] = []
    for item in kospi + kosdaq:
        if item["symbol"] not in seen:
            seen.add(item["symbol"])
            merged.append(item)

    # blng_cls_code 기준 재정렬
    sort_key = "volume" if blng_cls_code == "0" else "amount"
    merged.sort(key=lambda x: x.get(sort_key) or 0, reverse=True)
    return merged[:limit]


def _fetch_overseas_trade_rank(excd: str, limit: int) -> list[dict]:
    """KIS HHDFS76320010 — 해외주식 거래대금 순위 (당일, 전체 거래량 조건).
    excd: NAS=나스닥, NYS=뉴욕
    """
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/overseas-stock/v1/ranking/trade-pbmn",
            method="GET",
            params={
                "EXCD": excd,
                "NDAY": "0",
                "VOL_RANG": "0",
                "AUTH": "",
                "KEYB": "",
                "PRC1": "",
                "PRC2": "",
            },
            headers={"tr_id": "HHDFS76320010"},
            domain="real",
        )
        output = getattr(r, "output2", None) or getattr(r, "output", None)
        if not isinstance(output, list):
            output = [output] if output else []
        items = []
        for o in output[:limit]:
            items.append({
                "symbol":    str(getattr(o, "symb", "")),
                "name":      str(getattr(o, "name", "")),
                "price":     round(_f(getattr(o, "last", 0)), 2),
                "change":    round(_f(getattr(o, "diff", 0)), 2),
                "changePct": round(_f(getattr(o, "rate", 0)), 2),
                "volume":    int(_f(getattr(o, "tvol", 0))),
                "amount":    int(_f(getattr(o, "tamt", 0))),
                "exchange":  str(getattr(o, "excd", excd)),
            })
        return items
    except Exception:
        return []


def _fetch_overseas_fluct_rank(excd: str, gubn: str, limit: int) -> list[dict]:
    """KIS HHDFS76260000 — 해외주식 가격급등락 (60분전 기준).
    gubn: 1=급등(상승률), 0=급락(하락률)
    """
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/overseas-stock/v1/ranking/price-fluct",
            method="GET",
            params={
                "EXCD": excd,
                "GUBN": gubn,
                "MIXN": "8",   # 60분전
                "VOL_RANG": "0",
                "KEYB": "",
                "AUTH": "",
            },
            headers={"tr_id": "HHDFS76260000"},
            domain="real",
        )
        output = getattr(r, "output2", None) or getattr(r, "output", None)
        if not isinstance(output, list):
            output = [output] if output else []
        items = []
        for o in output[:limit]:
            items.append({
                "symbol":    str(getattr(o, "symb", "")),
                "name":      str(getattr(o, "knam", "") or getattr(o, "name", "")),
                "price":     round(_f(getattr(o, "last", 0)), 2),
                "change":    round(_f(getattr(o, "diff", 0)), 2),
                "changePct": round(_f(getattr(o, "rate", 0)), 2),
                "volume":    int(_f(getattr(o, "tvol", 0))),
                "amount":    None,
                "exchange":  excd,
            })
        return items
    except Exception:
        return []


def _fetch_overseas_combined(sort: str, limit: int) -> list[dict]:
    """NAS + NYS 합산 해외 랭킹."""
    if sort in ("rise", "fall"):
        sort_code = "1" if sort == "rise" else "0"
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_nas = pool.submit(_fetch_overseas_fluct_rank, "NAS", sort_code, limit * 2)
            f_nys = pool.submit(_fetch_overseas_fluct_rank, "NYS", sort_code, limit * 2)
            combined = f_nas.result() + f_nys.result()
        # 장 마감 등으로 빈 결과면 거래대금 순위로 폴백 후 등락률 정렬
        if not combined:
            with ThreadPoolExecutor(max_workers=2) as pool:
                f_nas = pool.submit(_fetch_overseas_trade_rank, "NAS", limit * 2)
                f_nys = pool.submit(_fetch_overseas_trade_rank, "NYS", limit * 2)
                combined = f_nas.result() + f_nys.result()
            combined.sort(key=lambda x: x.get("changePct") or 0, reverse=(sort == "rise"))
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_nas = pool.submit(_fetch_overseas_trade_rank, "NAS", limit * 2)
            f_nys = pool.submit(_fetch_overseas_trade_rank, "NYS", limit * 2)
            combined = f_nas.result() + f_nys.result()
        if sort == "volume":
            combined.sort(key=lambda x: x.get("volume") or 0, reverse=True)
        else:
            combined.sort(key=lambda x: x.get("amount") or 0, reverse=True)

    # symbol 기준 중복 제거
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in combined:
        if item["symbol"] not in seen:
            seen.add(item["symbol"])
            item["market"] = "overseas"
            deduped.append(item)

    return deduped[:limit]


def _fetch_all_ranking(sort: str, limit: int) -> list[dict]:
    """전체 랭킹: 국내(KRW) + 해외 NAS+NYS(USD→KRW 환산) 합산 정렬."""
    usd_krw = _get_usd_krw()

    with ThreadPoolExecutor(max_workers=3) as pool:
        if sort in ("rise", "fall"):
            sort_code = "1" if sort == "rise" else "0"
            f_dom = pool.submit(_fetch_fluctuation_rank, sort_code, limit * 2)
            f_nas = pool.submit(_fetch_overseas_fluct_rank, "NAS", sort_code, limit * 2)
            f_nys = pool.submit(_fetch_overseas_fluct_rank, "NYS", sort_code, limit * 2)
            domestic = [{**r, "volume": None, "amount": None, "market": "domestic"} for r in f_dom.result()]
            overseas = [{**r, "market": "overseas"} for r in f_nas.result() + f_nys.result()]
        else:
            blng = "0" if sort == "volume" else "3"
            f_dom = pool.submit(_fetch_volume_rank, blng, limit * 2)
            f_nas = pool.submit(_fetch_overseas_trade_rank, "NAS", limit * 2)
            f_nys = pool.submit(_fetch_overseas_trade_rank, "NYS", limit * 2)
            domestic = [{**r, "market": "domestic"} for r in f_dom.result()]
            overseas_raw = f_nas.result() + f_nys.result()
            # 해외 거래대금 USD → KRW 환산 (국내와 동일 단위로 정렬)
            for item in overseas_raw:
                item["amount"] = int((item.get("amount") or 0) * usd_krw)
                item["market"] = "overseas"
            overseas = overseas_raw

    # symbol 기준 중복 제거 후 합산
    seen: set[str] = set()
    all_items: list[dict] = []
    for item in domestic + overseas:
        if item["symbol"] not in seen:
            seen.add(item["symbol"])
            all_items.append(item)

    if sort in ("rise", "fall"):
        all_items.sort(key=lambda x: x.get("changePct") or 0, reverse=(sort == "rise"))
    elif sort == "volume":
        all_items.sort(key=lambda x: x.get("volume") or 0, reverse=True)
    else:  # amount — 국내 KRW · 해외 USD→KRW 이미 환산됨
        all_items.sort(key=lambda x: x.get("amount") or 0, reverse=True)

    return all_items[:limit]


def fetch_ranking(sort: str = "amount", category: str = "domestic", limit: int = 20) -> list[dict]:
    """실시간 랭킹.
    category: all | domestic | overseas
    sort:     amount | volume | rise | fall
    """
    cache_key = f"ranking_{sort}_{category}_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    if category == "all":
        result = _fetch_all_ranking(sort, limit)
    elif category == "overseas":
        result = _fetch_overseas_combined(sort, limit)
    else:  # domestic — 주식 + ETF 모두 포함
        if sort == "rise":
            result = [{**r, "volume": None, "amount": None} for r in _fetch_fluctuation_rank("1", limit)]
        elif sort == "fall":
            result = [{**r, "volume": None, "amount": None} for r in _fetch_fluctuation_rank("0", limit)]
        elif sort == "volume":
            result = _fetch_volume_rank("0", limit)
        else:  # amount
            result = _fetch_volume_rank("3", limit)

    _set_cached(cache_key, result)
    return result


# ── 종목 검색 (자동완성) ───────────────────────────────────────

# KRX 전종목 인덱스 (24시간 캐시)
_krx_index: list[dict] = []
_krx_index_ts: float = 0.0
_KRX_TTL = 86400  # 24시간


def _load_krx_listings() -> list[dict]:
    """KRX 공공 데이터에서 KOSPI + KOSDAQ 전종목 및 ETF 목록을 로드한다."""
    results: list[dict] = []
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://data.krx.co.kr/",
    }
    today = datetime.today().strftime("%Y%m%d")

    # 주식: KOSPI(STK) + KOSDAQ(KSQ)
    for mkt_id in ("STK", "KSQ"):
        try:
            resp = httpx.post(
                "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
                data={
                    "bld": "dbms/MDC/STAT/standard/MDCSTAT01901",
                    "mktId": mkt_id,
                    "share": "1",
                    "money": "1",
                    "csvxls_isNo": "false",
                },
                headers=headers,
                timeout=15,
            )
            for item in resp.json().get("OutBlock_1", []):
                code = item.get("ISU_SRT_CD", "").strip()
                name = item.get("ISU_NM", "").strip()
                eng  = item.get("ISU_ENG_NM", "").strip()
                if code and name:
                    results.append({
                        "symbol":   code,
                        "name":     name,
                        "eng_name": eng,
                        "type":     "equity",
                        "market":   "domestic",
                        "exchange": "KRX",
                    })
        except Exception:
            pass

    # ETF
    try:
        resp = httpx.post(
            "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
            data={
                "bld": "dbms/MDC/STAT/standard/MDCSTAT04301",
                "trdDd": today,
                "share": "1",
                "money": "1",
                "csvxls_isNo": "false",
            },
            headers=headers,
            timeout=15,
        )
        for item in resp.json().get("OutBlock_1", []):
            code = item.get("ISU_SRT_CD", "").strip()
            name = item.get("ISU_NM", "").strip()
            if code and name:
                results.append({
                    "symbol":   code,
                    "name":     name,
                    "eng_name": "",
                    "type":     "etf",
                    "market":   "domestic",
                    "exchange": "KRX",
                })
    except Exception:
        pass

    return results


def _get_krx_index() -> list[dict]:
    """KRX 인덱스를 반환한다. 만료 시 재로드, 실패 시 이전 캐시 유지 (하드코딩 폴백 없음)."""
    global _krx_index, _krx_index_ts
    if not _krx_index or time.time() - _krx_index_ts > _KRX_TTL:
        loaded = _load_krx_listings()
        if loaded:
            _krx_index = loaded
            _krx_index_ts = time.time()
        # KRX API 실패 시: 기존 캐시가 있으면 유지, 없으면 빈 목록 반환
        # (하드코딩 폴백 제거 — 상장폐지/신규상장 반영을 위해)
    return _krx_index


def _has_korean(s: str) -> bool:
    return any("\uAC00" <= c <= "\uD7A3" for c in s)


def _search_krx(query: str) -> list[dict]:
    """KRX 전종목 인덱스에서 한글 이름, 영문명, 코드로 검색."""
    q = query.strip().lower().replace(" ", "")
    index = _get_krx_index()
    exact: list[dict] = []
    partial: list[dict] = []
    for item in index:
        code   = item["symbol"]
        name_q = item["name"].lower().replace(" ", "")
        eng_q  = item["eng_name"].lower().replace(" ", "")
        if q == code:
            exact.append(item)
        elif q in name_q or q in code or (eng_q and q in eng_q):
            partial.append(item)
    return (exact + partial)[:8]


def _search_naver(query: str) -> list[dict]:
    """Naver Finance 자동완성 API — 한글/영문 모두 지원, 국내+해외 종목."""
    try:
        resp = httpx.get(
            "https://ac.stock.naver.com/ac",
            params={"q": query, "q_enc": "UTF-8", "target": "stock", "st": "0", "r_lt": "10"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        items = json.loads(resp.content).get("items", [])
        results: list[dict] = []
        for item in items:
            code = item.get("code", "")
            name = item.get("name", "")
            nation = item.get("nationCode", "")
            type_code = item.get("typeCode", "")
            if not code or not name:
                continue
            # 국내 종목: 표준 6자리 숫자 코드만 허용 (신규 상장 비정형 코드 제외)
            if nation == "KOR" and not code.isdigit():
                continue
            results.append({
                "symbol":   code,
                "name":     name,
                "eng_name": "",
                "type":     "equity",
                "market":   "domestic" if nation == "KOR" else "overseas",
                "exchange": type_code,
            })
        return results
    except Exception:
        return []


def _search_yahoo(query: str) -> list[dict]:
    """Yahoo Finance 검색 API — 해외 종목 영문 이름/코드 검색."""
    try:
        resp = httpx.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={
                "q": query,
                "quotesCount": 8,
                "newsCount": 0,
                "enableFuzzyQuery": "true",
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        quotes = resp.json().get("quotes", [])
        results: list[dict] = []
        for item in quotes:
            quote_type = item.get("quoteType", "")
            if quote_type not in ("EQUITY", "ETF"):
                continue
            raw_symbol = item.get("symbol", "")
            # 국내 종목(.KS/.KQ)은 KRX 인덱스에서 처리하므로 제외
            if raw_symbol.endswith(".KS") or raw_symbol.endswith(".KQ"):
                continue
            results.append({
                "symbol":   raw_symbol,
                "name":     item.get("shortname") or item.get("longname") or raw_symbol,
                "eng_name": "",
                "type":     quote_type.lower(),
                "market":   "overseas",
                "exchange": item.get("exchange", ""),
            })
        return results
    except Exception:
        return []


def fetch_search(query: str) -> list[dict]:
    """종목 검색: Naver Finance 우선, 영문 쿼리는 Yahoo + KRX 보완."""
    cache_key = f"search_{query.lower()}"
    cached = _get_cached(cache_key, ttl=120)
    if cached is not None:
        return cached

    naver = _search_naver(query)

    if _has_korean(query):
        # 한글 쿼리: Naver 결과 사용 (국내+해외 한글명 모두 커버)
        results = naver[:8]
    else:
        # 영문/코드 쿼리: Naver + Yahoo Finance + KRX 병합
        yahoo  = _search_yahoo(query)
        krx    = _search_krx(query)
        seen   = {r["symbol"] for r in naver}
        merged = naver[:]
        for item in yahoo:
            if item["symbol"] not in seen:
                seen.add(item["symbol"])
                merged.append(item)
        for item in krx:
            if item["symbol"] not in seen:
                seen.add(item["symbol"])
                merged.append(item)
        results = merged[:8]

    _set_cached(cache_key, results)
    return results