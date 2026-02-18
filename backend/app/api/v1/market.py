from fastapi import APIRouter, HTTPException, Query

from app.services.market_service import (
    get_chart,
    get_index_sparklines,
    get_indices,
    get_movers,
    get_stock_detail,
    get_top_etfs,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/indices")
async def indices():
    return get_indices()


@router.get("/index-sparklines")
async def index_sparklines():
    return get_index_sparklines()


@router.get("/top-etfs")
async def top_etfs(limit: int = Query(10, ge=1, le=20)):
    return get_top_etfs(limit)


@router.get("/chart")
async def chart(
    symbol: str = Query("SPY"),
    period: str = Query("6mo"),
):
    return get_chart(symbol, period)


@router.get("/movers")
async def movers():
    return get_movers()


@router.get("/stock/{symbol}")
async def stock_detail(symbol: str):
    data = get_stock_detail(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail="Symbol not found.")
    return data
