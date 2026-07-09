from __future__ import annotations

from app.contexts.identity.application.login_history_queries import GetLoginHistoryUseCase
from app.contexts.identity.application.queries import GetLoginHistoryQuery


class FakeLoginHistoryPort:
    def __init__(self) -> None:
        self.called = False

    def get_login_history(self) -> dict:
        self.called = True
        return {"success": True}


def test_login_history_use_case_delegates_to_port() -> None:
    port = FakeLoginHistoryPort()

    assert GetLoginHistoryUseCase(port).execute(GetLoginHistoryQuery()) == {"success": True}
    assert port.called is True
