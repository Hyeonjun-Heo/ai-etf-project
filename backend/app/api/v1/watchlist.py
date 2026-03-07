from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.deps import require_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import watchlist_service

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    symbol: str
    name: str
    market: str  # domestic | overseas

    @field_validator("symbol")
    @classmethod
    def symbol_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("market")
    @classmethod
    def market_valid(cls, v: str) -> str:
        if v not in ("domestic", "overseas"):
            raise ValueError("market must be 'domestic' or 'overseas'")
        return v


class WatchlistItemResponse(BaseModel):
    symbol: str
    name: str
    market: str
    added_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[WatchlistItemResponse])
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    items = watchlist_service.get_watchlist(db, current_user.id)
    return [
        WatchlistItemResponse(
            symbol=i.symbol,
            name=i.name,
            market=i.market,
            added_at=i.added_at.isoformat(),
        )
        for i in items
    ]


@router.get("/{symbol}")
def check_watchlist(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    return {"symbol": symbol.upper(), "in_watchlist": watchlist_service.is_in_watchlist(db, current_user.id, symbol)}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=WatchlistItemResponse)
def add_to_watchlist(
    body: WatchlistAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    item = watchlist_service.add_to_watchlist(db, current_user.id, body.symbol, body.name, body.market)
    if item is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in watchlist.")
    return WatchlistItemResponse(
        symbol=item.symbol,
        name=item.name,
        market=item.market,
        added_at=item.added_at.isoformat(),
    )


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
):
    deleted = watchlist_service.remove_from_watchlist(db, current_user.id, symbol)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in watchlist.")
