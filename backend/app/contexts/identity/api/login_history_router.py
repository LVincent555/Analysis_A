"""Admin login history route."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ....auth.dependencies import require_admin
from ....database import get_db
from ..application.login_history_queries import GetLoginHistoryUseCase
from ..application.queries import GetLoginHistoryQuery
from ..infrastructure.login_history import SqlLoginHistoryAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/login-history")
async def get_login_history(db: Session = Depends(get_db), current_user=Depends(require_admin)):
    try:
        return GetLoginHistoryUseCase(SqlLoginHistoryAdapter(db)).execute(GetLoginHistoryQuery())
    except Exception as exc:
        logger.error("获取登录历史失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"获取登录历史失败: {exc}") from exc
