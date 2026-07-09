"""Compatibility entrypoint for steady rise analysis routes."""

from ..contexts.analysis.api.rank_router import steady_rise_router as router

__all__ = ["router"]
