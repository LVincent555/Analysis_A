"""Operation log command-side use cases."""

from datetime import timedelta

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from .commands import CleanupOperationLogsCommand
from .ports import OperationLogCommandRepository


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _validate_cleanup_days(days: int) -> None:
    if days < 1 or days > 3650:
        raise _validation_error("清理天数必须在 1 到 3650 之间")


class CleanupOperationLogsUseCase:
    def __init__(self, *, logs: OperationLogCommandRepository) -> None:
        self.logs = logs

    def execute(self, command: CleanupOperationLogsCommand) -> dict:
        _validate_cleanup_days(command.days)
        cutoff = utc_now_naive() - timedelta(days=command.days)
        deleted = self.logs.delete_before(cutoff)
        self.logs.commit()
        return {
            "success": True,
            "message": f"已清理 {deleted} 条旧日志",
            "deleted": deleted,
        }
