"""Pagination value objects used by query-side services."""

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    page_size: int = 50

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page must be greater than or equal to 1")
        if self.page_size < 1:
            raise ValueError("page_size must be greater than or equal to 1")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: Sequence[T]
    total: int
    request: PageRequest

    @property
    def page(self) -> int:
        return self.request.page

    @property
    def page_size(self) -> int:
        return self.request.page_size
