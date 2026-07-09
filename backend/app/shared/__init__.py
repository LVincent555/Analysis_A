"""Shared primitives for backend contexts."""

from .errors import AppError, ErrorCode
from .pagination import Page, PageRequest
from .result import Result
from .time import utc_now, utc_now_naive

__all__ = [
    "AppError",
    "ErrorCode",
    "Page",
    "PageRequest",
    "Result",
    "utc_now",
    "utc_now_naive",
]
