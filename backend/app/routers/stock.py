"""Compatibility entrypoint for stock query routes."""

from ..contexts.market_data.api.stock_router import router

__all__ = ["router"]
