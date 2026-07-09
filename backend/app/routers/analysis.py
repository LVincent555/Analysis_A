"""Compatibility entrypoint for analysis routes."""

from fastapi import APIRouter

from ..contexts.analysis.api.basic_router import router as basic_analysis_router
from ..contexts.analysis.api.hot_spots_router import router as hot_spots_router

router = APIRouter()
router.include_router(basic_analysis_router)
router.include_router(hot_spots_router)
