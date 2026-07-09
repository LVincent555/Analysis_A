"""Hot spots analysis routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..application.hot_spots_queries import GetHotSpotsFullUseCase
from ..application.queries import GetHotSpotsFullQuery
from ..infrastructure.hot_spots_queries import LegacyHotSpotsAnalysisAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


def _hot_spots_adapter() -> LegacyHotSpotsAnalysisAdapter:
    return LegacyHotSpotsAnalysisAdapter()


@router.get("/hot-spots/full")
def get_hot_spots_full(date: str | None = None):
    try:
        result = GetHotSpotsFullUseCase(_hot_spots_adapter()).execute(GetHotSpotsFullQuery(date=date))
        if result is None:
            raise HTTPException(status_code=404, detail="无可用日期")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get hot spots data: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
