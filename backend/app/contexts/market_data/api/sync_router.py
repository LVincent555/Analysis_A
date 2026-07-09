"""Offline market data sync routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ....auth.dependencies import get_current_user
from ..application.errors import InvalidOfflineSyncRequestError, OfflineSyncDisabledError
from ..application.offline_sync_queries import OfflineSyncQueryService
from ..application.queries import (
    GetDailySyncQuery,
    GetIncrementalSyncQuery,
    GetOfflineDatesQuery,
    GetOfflineStocksQuery,
    GetOfflineSyncStatusQuery,
    OfflineSyncUserSettings,
)
from ..infrastructure.offline_sync import LegacyOfflineSyncAdapter

router = APIRouter(prefix="/api/sync", tags=["数据同步"])


def _sync_service() -> OfflineSyncQueryService:
    return OfflineSyncQueryService(LegacyOfflineSyncAdapter())


def _user_settings(user) -> OfflineSyncUserSettings:
    return OfflineSyncUserSettings(
        offline_days=user.offline_days,
        offline_enabled=user.offline_enabled,
    )


def _map_sync_error(exc: Exception) -> HTTPException:
    if isinstance(exc, OfflineSyncDisabledError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, InvalidOfflineSyncRequestError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
def get_sync_status(user=Depends(get_current_user)):
    return _sync_service().get_sync_status(GetOfflineSyncStatusQuery(user_settings=_user_settings(user)))


@router.get("/incremental")
def incremental_sync(
    since: str = Query(..., description="Last sync timestamp in ISO format"),
    user=Depends(get_current_user),
):
    try:
        return _sync_service().get_incremental_sync(
            GetIncrementalSyncQuery(since=since, user_settings=_user_settings(user))
        )
    except (OfflineSyncDisabledError, InvalidOfflineSyncRequestError) as exc:
        raise _map_sync_error(exc) from exc


@router.get("/daily/{date}")
def sync_daily(
    date: str,
    limit: int = Query(default=1000, le=5000),
    offset: int = Query(default=0, ge=0),
    user=Depends(get_current_user),
):
    try:
        return _sync_service().get_daily_sync(
            GetDailySyncQuery(date=date, limit=limit, offset=offset, user_settings=_user_settings(user))
        )
    except (OfflineSyncDisabledError, InvalidOfflineSyncRequestError) as exc:
        raise _map_sync_error(exc) from exc


@router.get("/stocks")
def sync_stocks(user=Depends(get_current_user)):
    try:
        return _sync_service().get_stocks(GetOfflineStocksQuery(user_settings=_user_settings(user)))
    except OfflineSyncDisabledError as exc:
        raise _map_sync_error(exc) from exc


@router.get("/dates")
def sync_dates(user=Depends(get_current_user)):
    return _sync_service().get_dates(GetOfflineDatesQuery(user_settings=_user_settings(user)))
