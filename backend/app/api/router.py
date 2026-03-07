from fastapi import APIRouter

from app.api.v1 import auth, chat, health, market, watchlist, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(market.router)
api_router.include_router(watchlist.router)
api_router.include_router(chat.router)
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"])
