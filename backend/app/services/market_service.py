"""Market data business logic layer."""

from app.data.market_data import (
    fetch_chart,
    fetch_indices,
    fetch_movers,
    fetch_stock_detail,
    fetch_top_etfs,
)


def get_indices() -> list[dict]:
    return fetch_indices()


def get_top_etfs(limit: int = 10) -> list[dict]:
    return fetch_top_etfs(limit)


def get_chart(symbol: str = "SPY", period: str = "6mo") -> list[dict]:
    return fetch_chart(symbol, period)


def get_movers() -> dict[str, list[dict]]:
    return fetch_movers()


def get_stock_detail(symbol: str) -> dict | None:
    return fetch_stock_detail(symbol.upper())
