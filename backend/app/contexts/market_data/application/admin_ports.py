"""Market data admin ports."""

from __future__ import annotations

from typing import Any, Protocol

from .admin_commands import (
    DeleteDataBatchCommand,
    DeleteDataByDateCommand,
    DeleteDataFileCommand,
    PreviewDeleteDataQuery,
    TriggerDataImportCommand,
    UploadDataFileCommand,
)


class MarketDataAdminPort(Protocol):
    def upload_file(self, command: UploadDataFileCommand) -> Any:
        ...

    def trigger_import(self, command: TriggerDataImportCommand) -> Any:
        ...

    def get_import_status(self) -> Any:
        ...

    def list_data_files(self) -> Any:
        ...

    def delete_data_file(self, command: DeleteDataFileCommand) -> Any:
        ...

    def get_imported_dates(self) -> Any:
        ...

    def preview_delete_data(self, query: PreviewDeleteDataQuery) -> Any:
        ...

    def delete_data_by_date(self, command: DeleteDataByDateCommand) -> Any:
        ...

    def delete_data_batch(self, command: DeleteDataBatchCommand) -> Any:
        ...
