"""Watchlist business logic."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.watchlist import Watchlist


def get_watchlist(db: Session, user_id: int) -> list[Watchlist]:
    return db.query(Watchlist).filter(Watchlist.user_id == user_id).order_by(Watchlist.added_at.desc()).all()


def is_in_watchlist(db: Session, user_id: int, symbol: str) -> bool:
    return db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.symbol == symbol.upper(),
    ).first() is not None


def add_to_watchlist(db: Session, user_id: int, symbol: str, name: str, market: str) -> Watchlist | None:
    """Returns the created item, or None if already exists."""
    item = Watchlist(user_id=user_id, symbol=symbol.upper(), name=name, market=market)
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
        return item
    except IntegrityError:
        db.rollback()
        return None


def remove_from_watchlist(db: Session, user_id: int, symbol: str) -> bool:
    """Returns True if deleted, False if not found."""
    item = db.query(Watchlist).filter(
        Watchlist.user_id == user_id,
        Watchlist.symbol == symbol.upper(),
    ).first()
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True
