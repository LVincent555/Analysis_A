"""Compatibility entrypoint for legacy /admin routes."""

from fastapi import APIRouter

from ..contexts.identity.api.login_history_router import router as login_history_router
from ..contexts.market_data.api.admin_router import router as market_data_admin_router

router = APIRouter()
router.include_router(market_data_admin_router)
router.include_router(login_history_router)

__all__ = ["router"]
