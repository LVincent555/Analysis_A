"""Market data admin command DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadDataFileCommand:
    filename: str
    content: str
    username: str


@dataclass(frozen=True, slots=True)
class TriggerDataImportCommand:
    username: str
    date: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteDataFileCommand:
    filename: str
    username: str


@dataclass(frozen=True, slots=True)
class PreviewDeleteDataQuery:
    date: str
    data_type: str = "all"


@dataclass(frozen=True, slots=True)
class DeleteDataByDateCommand:
    date: str
    data_type: str = "all"
    username: str = "unknown"


@dataclass(frozen=True, slots=True)
class DeleteDataBatchCommand:
    dates: list[str]
    data_type: str = "all"
    username: str = "unknown"
