"""PyKis 싱글톤 클라이언트."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.config import settings
from datetime import datetime
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from pykis import PyKis

logger = logging.getLogger(__name__)

_kis: "PyKis | None" = None


def get_kis() -> "PyKis":
    """PyKis 싱글톤을 반환합니다. 최초 호출 시 초기화합니다."""
    global _kis
    if _kis is None:
        _kis = _init_kis()
    return _kis


def _init_kis() -> "PyKis":
    from pykis import PyKis

    if not settings.KIS_APP_KEY or not settings.KIS_APP_SECRET:
        raise RuntimeError("KIS_APP_KEY / KIS_APP_SECRET가 .env에 설정되지 않았습니다.")

    logger.info(
        "KIS 클라이언트 초기화 (모의투자=%s, 계좌=%s)",
        settings.KIS_VIRTUAL,
        settings.KIS_ACCOUNT,
    )

    has_real = bool(settings.KIS_REAL_APP_KEY and settings.KIS_REAL_APP_SECRET)
    has_virtual = bool(settings.KIS_APP_KEY and settings.KIS_APP_SECRET and settings.KIS_VIRTUAL)

    if has_real and has_virtual:
        # 실전 + 모의투자 동시 사용: 시세는 실전 도메인, 매매는 모의 도메인
        kis = PyKis(
            id=settings.KIS_HTS_ID,
            appkey=settings.KIS_REAL_APP_KEY,
            secretkey=settings.KIS_REAL_APP_SECRET,
            account=settings.KIS_ACCOUNT,       # 모의 계좌를 primary로
            virtual_id=settings.KIS_HTS_ID,
            virtual_appkey=settings.KIS_APP_KEY,
            virtual_secretkey=settings.KIS_APP_SECRET,
            use_websocket=False,
            keep_token=True,                    # 토큰 디스크 캐시 (1분 레이트리밋 방지)
        )
    elif has_real:
        # 실전 전용
        kis = PyKis(
            id=settings.KIS_HTS_ID,
            appkey=settings.KIS_REAL_APP_KEY,
            secretkey=settings.KIS_REAL_APP_SECRET,
            account=settings.KIS_REAL_ACCOUNT,
            use_websocket=False,
            keep_token=True,
        )
    else:
        # 모의투자 전용 (실전 키 없음 — 시세 조회 제한될 수 있음)
        kis = PyKis(
            id=settings.KIS_HTS_ID,
            appkey=settings.KIS_APP_KEY,
            secretkey=settings.KIS_APP_SECRET,
            account=settings.KIS_ACCOUNT,
            virtual_id=settings.KIS_HTS_ID,
            virtual_appkey=settings.KIS_APP_KEY,
            virtual_secretkey=settings.KIS_APP_SECRET,
            use_websocket=False,
            keep_token=True,
        )

    return kis
