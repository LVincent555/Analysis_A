"""Compatibility entrypoint for external board management routes."""

from ..contexts.board_heat.api.management_router import router

__all__ = ["router"]
