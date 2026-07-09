"""Operation log management routes."""

import csv
import io
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ....auth.dependencies import require_admin
from ....database import get_db
from ....db_models import User
from ....shared.errors import AppError, ErrorCode
from ..application.commands import CleanupOperationLogsCommand
from ..application.log_commands import CleanupOperationLogsUseCase
from ..application.log_queries import (
    ExportOperationLogsUseCase,
    GetOperationLogDetailUseCase,
    GetOperationLogStatisticsUseCase,
    GetOperationLogTypesUseCase,
    GetUserActivityUseCase,
    ListOperationLogsUseCase,
)
from ..application.queries import (
    ExportOperationLogsQuery,
    GetOperationLogDetailQuery,
    GetOperationLogStatisticsQuery,
    GetUserActivityQuery,
    ListOperationLogsQuery,
)
from ..infrastructure.repositories import SqlAlchemyOperationLogRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/logs", tags=["操作日志"])


class LogListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[dict]


class LogStatisticsResponse(BaseModel):
    period_days: int
    total: int
    type_distribution: dict
    status_distribution: dict
    daily_trend: list[dict]
    login_failed_count: int
    security_event_count: int
    updated_at: str


class LogTypesResponse(BaseModel):
    types: dict
    actions: dict


def _operations_http_error(error: AppError) -> HTTPException:
    status_map = {
        ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.FORBIDDEN: status.HTTP_403_FORBIDDEN,
        ErrorCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.CONFLICT: status.HTTP_409_CONFLICT,
        ErrorCode.VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(
        status_code=status_map.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR),
        detail=error.message,
    )


def _log_repository(db: Session) -> SqlAlchemyOperationLogRepository:
    return SqlAlchemyOperationLogRepository(db)


@router.get("/types", response_model=LogTypesResponse)
def get_log_types(admin: User = Depends(require_admin)):
    """Get operation log types and actions."""

    return GetOperationLogTypesUseCase().execute()


@router.get("", response_model=LogListResponse)
def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    log_type: str | None = None,
    action: str | None = None,
    operator_name: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    log_status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get paginated operation logs."""

    try:
        return ListOperationLogsUseCase(logs=_log_repository(db)).execute(
            ListOperationLogsQuery(
                page=page,
                page_size=page_size,
                log_type=log_type,
                action=action,
                operator_name=operator_name,
                target_type=target_type,
                target_id=target_id,
                status=log_status,
                start_date=start_date,
                end_date=end_date,
                search=search,
            )
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to list operation logs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/statistics", response_model=LogStatisticsResponse)
def get_log_statistics(
    days: int = Query(7, ge=1, le=3650),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get operation log statistics."""

    try:
        return GetOperationLogStatisticsUseCase(logs=_log_repository(db)).execute(
            GetOperationLogStatisticsQuery(days=days)
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get operation log statistics: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/user/{user_id}", response_model=LogListResponse)
def get_user_activity(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get operation activity for a user."""

    try:
        return GetUserActivityUseCase(logs=_log_repository(db)).execute(
            GetUserActivityQuery(user_id=user_id, page=page, page_size=page_size)
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get user activity logs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{log_id}")
def get_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get operation log detail."""

    try:
        return GetOperationLogDetailUseCase(logs=_log_repository(db)).execute(
            GetOperationLogDetailQuery(log_id=log_id)
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to get operation log detail: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/export/csv")
def export_logs_csv(
    log_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Export operation logs as CSV."""

    try:
        logs = ExportOperationLogsUseCase(logs=_log_repository(db)).execute(
            ExportOperationLogsQuery(
                log_type=log_type,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        )
        if not logs:
            raise HTTPException(status_code=404, detail="没有符合条件的日志")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
        output.seek(0)

        filename = f"operation_logs_{start_date or 'all'}_{end_date or 'now'}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to export operation logs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/cleanup")
def cleanup_old_logs(
    days: int = Query(90, ge=1, le=3650),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Delete old operation logs."""

    try:
        return CleanupOperationLogsUseCase(logs=_log_repository(db)).execute(
            CleanupOperationLogsCommand(days=days)
        )
    except AppError as error:
        raise _operations_http_error(error) from error
    except Exception as exc:
        logger.error("Failed to clean old operation logs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
