"""Small result type for application services."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from .errors import AppError


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Result(Generic[T]):
    value: T | None = None
    error: AppError | None = None

    @property
    def is_ok(self) -> bool:
        return self.error is None

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        return cls(value=value)

    @classmethod
    def fail(cls, error: AppError) -> "Result[T]":
        return cls(error=error)

    def unwrap(self) -> T:
        if self.error is not None:
            raise self.error
        return self.value  # type: ignore[return-value]
