"""Compatibility facade for Operations operation-log use cases."""

import json
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..contexts.operations.application.commands import CleanupOperationLogsCommand
from ..contexts.operations.application.log_commands import CleanupOperationLogsUseCase
from ..contexts.operations.application.log_queries import (
    ExportOperationLogsUseCase,
    GetOperationLogDetailUseCase,
    GetOperationLogStatisticsUseCase,
    GetUserActivityUseCase,
    ListOperationLogsUseCase,
)
from ..contexts.operations.application.queries import (
    ExportOperationLogsQuery,
    GetOperationLogDetailQuery,
    GetOperationLogStatisticsQuery,
    GetUserActivityQuery,
    ListOperationLogsQuery,
)
from ..contexts.operations.domain.logs import LOG_ACTIONS, LOG_TYPES
from ..contexts.operations.infrastructure.repositories import SqlAlchemyOperationLogRepository
from ..db_models import OperationLog
from ..shared.errors import AppError, ErrorCode


class LogService:
    """Legacy service API backed by the Operations context."""

    @staticmethod
    def _repository(db: Session) -> SqlAlchemyOperationLogRepository:
        return SqlAlchemyOperationLogRepository(db)

    @staticmethod
    def get_logs(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        log_type: Optional[str] = None,
        action: Optional[str] = None,
        operator_id: Optional[int] = None,
        operator_name: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict[str, Any]:
        return ListOperationLogsUseCase(logs=LogService._repository(db)).execute(
            ListOperationLogsQuery(
                page=page,
                page_size=page_size,
                log_type=log_type,
                action=action,
                operator_id=operator_id,
                operator_name=operator_name,
                target_type=target_type,
                target_id=target_id,
                status=status,
                start_date=start_date,
                end_date=end_date,
                search=search,
            )
        )

    @staticmethod
    def get_log_detail(db: Session, log_id: int) -> dict[str, Any] | None:
        try:
            return GetOperationLogDetailUseCase(logs=LogService._repository(db)).execute(
                GetOperationLogDetailQuery(log_id=log_id)
            )
        except AppError as error:
            if error.code == ErrorCode.NOT_FOUND:
                return None
            raise

    @staticmethod
    def get_log_statistics(db: Session, days: int = 7) -> dict[str, Any]:
        return GetOperationLogStatisticsUseCase(logs=LogService._repository(db)).execute(
            GetOperationLogStatisticsQuery(days=days)
        )

    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        return GetUserActivityUseCase(logs=LogService._repository(db)).execute(
            GetUserActivityQuery(user_id=user_id, page=page, page_size=page_size)
        )

    @staticmethod
    def export_logs(
        db: Session,
        log_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        return ExportOperationLogsUseCase(logs=LogService._repository(db)).execute(
            ExportOperationLogsQuery(
                log_type=log_type,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        )

    @staticmethod
    def cleanup_old_logs(db: Session, days: int = 90) -> int:
        result = CleanupOperationLogsUseCase(logs=LogService._repository(db)).execute(
            CleanupOperationLogsCommand(days=days)
        )
        return result["deleted"]

    @staticmethod
    def log_operation(
        db: Session,
        log_type: str,
        action: str,
        operator_id: Optional[int] = None,
        operator_name: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        target_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        detail: Optional[dict] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> OperationLog:
        log = OperationLog(
            log_type=log_type,
            action=action,
            operator_id=operator_id,
            operator_name=operator_name,
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
            new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
            status=status,
            error_message=error_message,
        )
        db.add(log)
        db.commit()
        return log
