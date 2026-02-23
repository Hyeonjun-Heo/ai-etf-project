"""KIS OpenAPI 기반 시장 데이터 모듈."""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
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

KR_ETF_POOL = [
    ("069500", "KODEX 200"),
    ("102110", "TIGER 200"),
    ("122630", "KODEX 레버리지"),
    ("114800", "KODEX 인버스"),
    ("133690", "TIGER 나스닥100"),
    ("229200", "KODEX 코스닥150"),
    ("360750", "TIGER 미국S&P500"),
    ("091160", "KODEX 반도체"),
    ("292150", "TIGER TOP10"),
    ("278530", "KODEX 200TR"),
    ("148020", "KODEX 코스닥150 레버리지"),
    ("251340", "KODEX 코스닥150 인버스"),
    ("294400", "KODEX 코스피"),
    ("395160", "TIGER 미국나스닥100"),
    ("381170", "TIGER 미국S&P500레버리지"),
    ("364980", "TIGER 차이나CSI300"),
    ("305080", "TIGER 2차전지테마"),
    ("139230", "TIGER 200 IT"),
    ("276990", "KODEX 200 모멘텀"),
    ("379800", "KODEX 미국S&P500TR"),
    ("143850", "TIGER 200 헬스케어"),
    ("091180", "KODEX 자동차"),
    ("266360", "KODEX 200 선물인버스2X"),
    ("252670", "KODEX 200선물인버스2X"),
    ("233740", "KODEX 코스닥150선물인버스"),
]


def _fetch_etf_quote_full(code: str, name: str) -> dict | None:
    """ETF 현재가 + 거래량/거래대금 조회."""
    try:
        kis = get_kis()
        r = kis.fetch(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            method="GET",
            params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
            headers={"tr_id": "FHKST01010100"},
            domain="real",
        )
        o = r.output
        return {
            "symbol": code,
            "name": name,
            "price": round(_f(getattr(o, "stck_prpr", 0)), 0),
            "change": round(_f(getattr(o, "prdy_vrss", 0)), 0),
            "changePct": round(_f(getattr(o, "prdy_ctrt", 0)), 2),
            "volume": int(_f(getattr(o, "acml_vol", 0))),
            "amount": int(_f(getattr(o, "acml_tr_pbmn", 0))),
        }
    except Exception:
        return None


def _fetch_etf_quote(code: str, name: str) -> dict | None:
    try:
        kis = get_kis()
        q = kis.stock(code).quote()
        return {
            "symbol": code,
            "name": name,
            "price": round(_f(q.price), 0),
            "change": round(_f(q.change), 0),
            "changePct": round(_f(q.rate), 2),
        }
    except Exception:
        return None


def fetch_top_etfs(limit: int = 10) -> list[dict]:
    cache_key = f"top_etfs_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(_fetch_etf_quote, code, name) for code, name in KR_ETF_POOL[:10]]
        results = [f.result() for f in futures]

    results = [r for r in results if r is not None]
    results.sort(key=lambda x: x["changePct"], reverse=True)
    results = results[:limit]
    _set_cached(cache_key, results)
    return results


def fetch_domestic_etf_ranking(sort: str = "amount", limit: int = 20) -> list[dict]:
    """KR_ETF_POOL 전체를 개별 조회 후 sort 기준으로 반환."""
    cache_key = f"domestic_etf_{sort}_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    with ThreadPoolExecutor(max_workers=len(KR_ETF_POOL)) as pool:
        futures = [pool.submit(_fetch_etf_quote_full, code, name) for code, name in KR_ETF_POOL]
        results = [f.result() for f in futures]

    results = [r for r in results if r is not None]

    if sort == "volume":
        results.sort(key=lambda x: x.get("volume") or 0, reverse=True)
    elif sort == "rise":
        results.sort(key=lambda x: x.get("changePct") or 0, reverse=True)
    elif sort == "fall":
        results.sort(key=lambda x: x.get("changePct") or 0)
    else:  # amount
        results.sort(key=lambda x: x.get("amount") or 0, reverse=True)

    results = results[:limit]
    _set_cached(cache_key, results)
    return results


# ── 차트 데이터 ────────────────────────────────────────────────

VALID_PERIODS = {"1d", "1w", "1mo", "3mo", "6mo", "1y"}

PERIOD_MAP = {
    "1d":  "1d",
    "1w":  "7d",
    "1mo": "30d",
    "3mo": "90d",
    "6mo": "180d",
    "1y":  "1y",
}


def fetch_chart(symbol: str = "005930", period: str = "1y") -> list[dict]:
    if period not in VALID_PERIODS:
        period = "1y"

    cache_key = f"chart_{symbol}_{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    kis_period = PERIOD_MAP.get(period, "1y")
    intraday = period == "1d"
    date_fmt = "%H:%M" if intraday else "%Y-%m-%d"

    try:
        kis = get_kis()
        chart = kis.stock(symbol).chart(kis_period)
        data = [
            {"date": b.time_kst.strftime(date_fmt), "close": round(_f(b.close), 2)}
            for b in chart.bars
        ]
    except Exception:
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