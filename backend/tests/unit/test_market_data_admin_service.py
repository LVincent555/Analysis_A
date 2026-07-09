from __future__ import annotations

from app.contexts.market_data.application.admin_commands import UploadDataFileCommand
from app.contexts.market_data.application.admin_services import MarketDataAdminService


class FakeMarketDataAdminPort:
    def __init__(self) -> None:
        self.upload_command: UploadDataFileCommand | None = None

    def upload_file(self, command: UploadDataFileCommand) -> dict:
        self.upload_command = command
        return {"success": True}


def test_market_data_admin_service_delegates_upload_command() -> None:
    port = FakeMarketDataAdminPort()
    service = MarketDataAdminService(port)
    command = UploadDataFileCommand(filename="a.xlsx", content="AA==", username="admin")

    assert service.upload_file(command) == {"success": True}
    assert port.upload_command == command
