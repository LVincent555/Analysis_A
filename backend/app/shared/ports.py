"""Shared protocol abstractions for adapters."""

from collections.abc import Iterable
from typing import Any, Protocol, TypeVar


T = TypeVar("T")


class CachePort(Protocol):
    def get(self, key: str) -> Any:
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def keys(self) -> Iterable[str]:
        ...


class Repository(Protocol[T]):
    def get(self, identity: Any) -> T | None:
        ...

    def add(self, entity: T) -> None:
        ...
