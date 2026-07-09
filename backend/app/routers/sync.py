"""Compatibility entrypoint for offline market data sync routes."""

from ..contexts.market_data.api.sync_router import router

__all__ = ["router"]
