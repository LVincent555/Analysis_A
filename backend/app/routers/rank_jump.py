"""Compatibility entrypoint for rank jump analysis routes."""

from ..contexts.analysis.api.rank_router import rank_jump_router as router

__all__ = ["router"]
