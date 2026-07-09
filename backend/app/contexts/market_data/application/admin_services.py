"""Market data admin use cases."""

from __future__ import annotations

from typing import Any

from .admin_commands import (
    DeleteDataBatchCommand,
    DeleteDataByDateCommand,
    DeleteDataFileCommand,
    PreviewDeleteDataQuery,
    TriggerDataImportCommand,
    UploadDataFileCommand,
)
from .admin_ports import MarketDataAdminPort


class MarketDataAdminService:
    def __init__(self, admin_port: MarketDataAdminPort) -> None:
        self.admin_port = admin_port

    def upload_file(self, command: UploadDataFileCommand) -> Any:
        return self.admin_port.upload_file(command)

    def trigger_import(self, command: TriggerDataImportCommand) -> Any:
        return self.admin_port.trigger_import(command)

    def get_import_status(self) -> Any:
        return self.admin_port.get_import_status()

    def list_data_files(self) -> Any:
        return self.admin_port.list_data_files()

    def delete_data_file(self, command: DeleteDataFileCommand) -> Any:
        return self.admin_port.delete_data_file(command)

    def get_imported_dates(self) -> Any:
        return self.admin_port.get_imported_dates()

    def preview_delete_data(self, query: PreviewDeleteDataQuery) -> Any:
        return self.admin_port.preview_delete_data(query)

    def delete_data_by_date(self, command: DeleteDataByDateCommand) -> Any:
        return self.admin_port.delete_data_by_date(command)

    def delete_data_batch(self, command: DeleteDataBatchCommand) -> Any:
        return self.admin_port.delete_data_batch(command)
