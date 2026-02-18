"""yfinance wrapper with in-memory TTL cache."""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import yfinance as yf
import pandas as pd

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300  # 5 minutes
SPARKLINE_TTL = 30  # ✅ 스파크라인 전용 TTL (30초)
SPARKLINE_WINDOW_MINUTES = 180  # ✅ 3시간 = 180분(1분봉 180개)


def _get_cached(key: str, ttl: int = CACHE_TTL) -> Any | None:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
        del _cache[key]
    return None


def _set_cached(key: str, data: Any) -> None:
    _cache[key] = (time.time(), data)


# ── Index quotes ──────────────────────────────────────────────

INDEX_SYMBOLS = {
    "KRW=X": "달러/원",
    "^IXIC": "나스닥",
    "NQ=F": "나스닥100 선물",
    "^GSPC": "S&P 500",
    "^DJI": "다우존스",
    "^VIX": "VIX",
    "^KS11": "코스피",
    "^KQ11": "코스닥",
}


def fetch_indices() -> list[dict]:
    cache_key = "indices"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    results = []
    tickers = yf.Tickers(" ".join(INDEX_SYMBOLS.keys()))
    for symbol, name in INDEX_SYMBOLS.items():
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev = info.previous_close
            change = price - prev
            change_pct = (change / prev) * 100 if prev else 0
            results.append({
                "symbol": symbol,
                "name": name,
                "price": round(price, 2),
                "change": round(change, 2),
                "changePct": round(change_pct, 2),
            })
        except Exception:
            results.append({
                "symbol": symbol,
                "name": name,
                "price": 0,
                "change": 0,
                "changePct": 0,
            })

    _set_cached(cache_key, results)
    return results


# ── Index sparklines (today 1-min intraday + previous close) ──

def _fetch_one_sparkline(symbol: str) -> dict:
    """Fetch recent 3h 1m chart + previous close for a single symbol."""
    try:
        ticker = yf.Ticker(symbol)
        prev_close = ticker.fast_info.previous_close
        prev_close = round(prev_close, 2) if prev_close is not None else None

        hist: pd.DataFrame = ticker.history(period="1d", interval="1m")
        if hist is None or hist.empty:
            return {"points": [], "previousClose": prev_close}

        # ✅ 최근 3시간(=180개)만 사용
        hist = hist.tail(SPARKLINE_WINDOW_MINUTES)

        points = [
            {"date": idx.strftime("%H:%M"), "close": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
        ]
        return {"points": points, "previousClose": prev_close}
    except Exception:
        return {"points": [], "previousClose": None}


def fetch_index_sparklines() -> dict[str, dict]:
    cache_key = "index_sparklines"
    cached = _get_cached(cache_key, ttl=SPARKLINE_TTL)  # ✅ 30초 TTL
    if cached is not None:
        return cached

    symbols = list(INDEX_SYMBOLS.keys())
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_fetch_one_sparkline, symbols))

    result = dict(zip(symbols, results))
    _set_cached(cache_key, result)
    return result


# ── Top ETFs ──────────────────────────────────────────────────

ETF_POOL = ["SPY", "QQQ", "IWM", "VTI", "ARKK", "XLF", "XLE", "XLK", "SCHD", "VYM"]


def fetch_top_etfs(limit: int = 10) -> list[dict]:
    cache_key = f"top_etfs_{limit}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    results = []
    tickers = yf.Tickers(" ".join(ETF_POOL))
    for symbol in ETF_POOL:
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev = info.previous_close
            change = price - prev
            change_pct = (change / prev) * 100 if prev else 0
            results.append({
                "symbol": symbol,
                "name": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "changePct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["changePct"], reverse=True)
    results = results[:limit]
    _set_cached(cache_key, results)
    return results


# ── Chart data ────────────────────────────────────────────────

VALID_PERIODS = {"1d", "1w", "1mo", "3mo", "6mo", "1y"}

PERIOD_INTERVAL = {"1d": "5m", "1w": "30m"}
PERIOD_DATE_FMT = {"1d": "%H:%M", "1w": "%m/%d %H:%M"}


def fetch_chart(symbol: str = "SPY", period: str = "6mo") -> list[dict]:
    if period not in VALID_PERIODS:
        period = "6mo"

    cache_key = f"chart_{symbol}_{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    interval = PERIOD_INTERVAL.get(period, "1d")
    hist: pd.DataFrame = ticker.history(period=period, interval=interval)
    date_fmt = PERIOD_DATE_FMT.get(period, "%Y-%m-%d")

    data = [
        {"date": idx.strftime(date_fmt), "close": round(row["Close"], 2)}
        for idx, row in hist.iterrows()
    ]

    _set_cached(cache_key, data)
    return data


# ── Stock detail ─────────────────────────────────────────────

def fetch_stock_detail(symbol: str) -> dict | None:
    cache_key = f"stock_detail_{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(symbol)
    try:
        info = ticker.info
        if not info or info.get("trailingPegRatio") is None and info.get("shortName") is None:
            return None
    except Exception:
        return None

    fast = ticker.fast_info
    price = fast.last_price
    prev = fast.previous_close
    change = price - prev
    change_pct = (change / prev) * 100 if prev else 0

    data = {
        "symbol": symbol,
        "name": info.get("shortName", symbol),
        "price": round(price, 2),
        "change": round(change, 2),
        "changePct": round(change_pct, 2),
        "marketCap": info.get("marketCap"),
        "peRatio": info.get("trailingPE"),
        "dividendYield": info.get("dividendYield"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
        "volume": info.get("volume"),
        "avgVolume": info.get("averageVolume"),
        "open": info.get("open"),
        "previousClose": info.get("previousClose"),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "longBusinessSummary": info.get("longBusinessSummary", ""),
    }

    _set_cached(cache_key, data)
    return data


# ── Market movers ─────────────────────────────────────────────

MOVER_POOL = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM",
    "V", "JNJ", "WMT", "PG", "XOM", "UNH", "HD", "MA", "BAC", "PFE",
    "KO", "PEP", "COST", "ABBV", "MRK", "AVGO", "TMO", "CSCO", "ACN",
    "CRM", "MCD", "NKE",
]


def fetch_movers() -> dict[str, list[dict]]:
    cache_key = "movers"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    results = []
    tickers = yf.Tickers(" ".join(MOVER_POOL))
    for symbol in MOVER_POOL:
        try:
            info = tickers.tickers[symbol].fast_info
            price = info.last_price
            prev = info.previous_close
            change = price - prev
            change_pct = (change / prev) * 100 if prev else 0
            results.append({
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "changePct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["changePct"], reverse=True)
    data = {
        "gainers": results[:5],
        "losers": list(reversed(results[-5:])),
    }

    _set_cached(cache_key, data)
    return data
