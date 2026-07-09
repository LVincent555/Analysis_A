"""Compatibility entrypoint for board heat query routes."""

from ..contexts.board_heat.api.query_router import router

__all__ = ["router"]
