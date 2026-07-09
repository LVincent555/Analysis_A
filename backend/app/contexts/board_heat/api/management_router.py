"""External board management routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ....auth.dependencies import require_admin
from ....database import get_db
from ..application.commands import (
    CalculateBoardHeatCommand,
    ListExternalBoardsQuery,
    ListSyncHistoryQuery,
    SyncExternalBoardsCommand,
)
from ..application.management_services import BoardHeatManagementService
from ..infrastructure.management import (
    BoardHeatManagementAdapter,
    BoardHeatTaskConflictError,
    BoardHeatTaskNotRunningError,
)

router = APIRouter(prefix="/api/admin/ext-boards", tags=["外部板块管理"])


class SyncRequest(BaseModel):
    provider: str = "all"
    force: bool = False
    use_proxy: bool = True
    date: str | None = None
    board_type: str = "all"
    delay: float = 1.0
    concurrent: bool = False
    workers: int = 10
    max_ips: int = 200
    ip_ttl: float = 50.0
    req_delay_min: float = 1.0
    req_delay_max: float = 3.0
    limit: int | None = None
    skip_cons: bool = False
    skip_map: bool = False


class HeatCalcRequest(BaseModel):
    date: str | None = None
    calc_all: bool = False
    force: bool = False
    allow_fallback: bool = True


class SyncStatusResponse(BaseModel):
    is_syncing: bool
    task_id: str | None
    provider: str | None
    start_time: str | None
    logs: list[str]
    progress: dict[str, Any] | None


class StatsResponse(BaseModel):
    total_boards: int
    total_cons_records: int
    providers: list[dict[str, Any]]
    last_sync: dict[str, Any] | None
    mapping_count: int


def _management_service(db: Session | None = None) -> BoardHeatManagementService:
    return BoardHeatManagementService(BoardHeatManagementAdapter(db))


@router.post("/sync", summary="触发今日同步")
async def trigger_sync(request: SyncRequest, current_user=Depends(require_admin)):
    try:
        return await _management_service().start_sync(SyncExternalBoardsCommand(**request.model_dump()))
    except BoardHeatTaskConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/sync-status", response_model=SyncStatusResponse, summary="获取同步状态")
async def get_sync_status(current_user=Depends(require_admin)):
    return _management_service().get_sync_status()


@router.post("/sync/cancel", summary="取消同步任务")
async def cancel_sync(current_user=Depends(require_admin)):
    try:
        return _management_service().cancel_sync()
    except BoardHeatTaskNotRunningError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/heat/calc", summary="触发板块热度计算")
async def trigger_heat_calc(request: HeatCalcRequest, current_user=Depends(require_admin)):
    try:
        return await _management_service().start_heat_calculation(
            CalculateBoardHeatCommand(**request.model_dump())
        )
    except BoardHeatTaskConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/heat/status", summary="获取热度计算状态")
async def get_heat_status(current_user=Depends(require_admin)):
    return _management_service().get_heat_status()


@router.post("/heat/cancel", summary="取消热度计算任务")
async def cancel_heat_calc(current_user=Depends(require_admin)):
    try:
        return _management_service().cancel_heat_calculation()
    except BoardHeatTaskNotRunningError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/mapping/auto", summary="编制数据库关系（自动映射）")
async def auto_mapping(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    try:
        return _management_service(db).auto_mapping()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"自动映射失败: {exc}") from exc


@router.get("/sync-history", summary="获取同步历史")
async def get_sync_history(limit: int = 30, current_user=Depends(require_admin)):
    return _management_service().get_sync_history(ListSyncHistoryQuery(limit=limit))


@router.get("/stats", response_model=StatsResponse, summary="获取运维统计")
async def get_stats(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return _management_service(db).get_stats()


@router.get("/boards", summary="查询板块列表")
async def get_boards(
    provider: str | None = None,
    board_type: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    return _management_service(db).get_boards(
        ListExternalBoardsQuery(
            provider=provider,
            board_type=board_type,
            search=search,
            page=page,
            page_size=page_size,
        )
    )
