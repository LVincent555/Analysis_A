"""SQLAlchemy adapters for the Operations context."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from ....db_models import OperationLog, SystemConfig


class SqlAlchemySystemConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_key(self, key: str) -> SystemConfig | None:
        return self.db.query(SystemConfig).filter(SystemConfig.config_key == key).first()

    def list_configs(self, category: str | None = None) -> list[SystemConfig]:
        query = self.db.query(SystemConfig)
        if category:
            query = query.filter(SystemConfig.category == category)
        return query.order_by(SystemConfig.category, SystemConfig.config_key).all()

    def set_value(
        self,
        config: SystemConfig,
        serialized_value: str,
        operator_id: int,
        updated_at: datetime,
    ) -> None:
        config.config_value = serialized_value
        config.updated_by = operator_id
        config.updated_at = updated_at

    def commit(self) -> None:
        self.db.commit()


class SqlAlchemyOperationLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _query_logs(
        self,
        *,
        log_type: str | None = None,
        action: str | None = None,
        operator_id: int | None = None,
        operator_name: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
        status: str | None = None,
        start_at: datetime | None = None,
        end_before: datetime | None = None,
        search: str | None = None,
    ):
        query = self.db.query(OperationLog)

        if log_type:
            query = query.filter(OperationLog.log_type == log_type)
        if action:
            query = query.filter(OperationLog.action == action)
        if operator_id is not None:
            query = query.filter(OperationLog.operator_id == operator_id)
        if operator_name:
            query = query.filter(OperationLog.operator_name.ilike(f"%{operator_name}%"))
        if target_type:
            query = query.filter(OperationLog.target_type == target_type)
        if target_id is not None:
            query = query.filter(OperationLog.target_id == target_id)
        if status:
            query = query.filter(OperationLog.status == status)
        if start_at:
            query = query.filter(OperationLog.created_at >= start_at)
        if end_before:
            query = query.filter(OperationLog.created_at < end_before)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    OperationLog.operator_name.ilike(search_pattern),
                    OperationLog.target_name.ilike(search_pattern),
                    OperationLog.ip_address.ilike(search_pattern),
                    OperationLog.detail.ilike(search_pattern),
                )
            )

        return query

    def list_logs(
        self,
        *,
        page: int,
        page_size: int,
        log_type: str | None,
        action: str | None,
        operator_id: int | None,
        operator_name: str | None,
        target_type: str | None,
        target_id: int | None,
        status: str | None,
        start_at: datetime | None,
        end_before: datetime | None,
        search: str | None,
    ) -> tuple[int, list[OperationLog]]:
        query = self._query_logs(
            log_type=log_type,
            action=action,
            operator_id=operator_id,
            operator_name=operator_name,
            target_type=target_type,
            target_id=target_id,
            status=status,
            start_at=start_at,
            end_before=end_before,
            search=search,
        )
        total = query.count()
        rows = (
            query.order_by(desc(OperationLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, rows

    def get_log_by_id(self, log_id: int) -> OperationLog | None:
        return self.db.query(OperationLog).filter(OperationLog.id == log_id).first()

    def type_distribution_since(self, start_at: datetime) -> dict[str, int]:
        rows = (
            self.db.query(OperationLog.log_type, func.count(OperationLog.id))
            .filter(OperationLog.created_at >= start_at)
            .group_by(OperationLog.log_type)
            .all()
        )
        return {log_type: count for log_type, count in rows}

    def status_distribution_since(self, start_at: datetime) -> dict[str | None, int]:
        rows = (
            self.db.query(OperationLog.status, func.count(OperationLog.id))
            .filter(OperationLog.created_at >= start_at)
            .group_by(OperationLog.status)
            .all()
        )
        return {status: count for status, count in rows}

    def daily_counts_since(self, start_at: datetime) -> list[tuple[Any, int]]:
        day = func.date(OperationLog.created_at)
        return (
            self.db.query(day, func.count(OperationLog.id))
            .filter(OperationLog.created_at >= start_at)
            .group_by(day)
            .order_by(day)
            .all()
        )

    def count_action_since(self, action: str, start_at: datetime) -> int:
        count = (
            self.db.query(func.count(OperationLog.id))
            .filter(OperationLog.action == action, OperationLog.created_at >= start_at)
            .scalar()
        )
        return count or 0

    def count_type_since(self, log_type: str, start_at: datetime) -> int:
        count = (
            self.db.query(func.count(OperationLog.id))
            .filter(OperationLog.log_type == log_type, OperationLog.created_at >= start_at)
            .scalar()
        )
        return count or 0

    def count_since(self, start_at: datetime) -> int:
        count = (
            self.db.query(func.count(OperationLog.id))
            .filter(OperationLog.created_at >= start_at)
            .scalar()
        )
        return count or 0

    def list_user_activity(self, *, user_id: int, page: int, page_size: int) -> tuple[int, list[OperationLog]]:
        query = self.db.query(OperationLog).filter(
            or_(
                OperationLog.operator_id == user_id,
                (OperationLog.target_type == "user") & (OperationLog.target_id == user_id),
            )
        )
        total = query.count()
        rows = (
            query.order_by(desc(OperationLog.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return total, rows

    def export_logs(
        self,
        *,
        log_type: str | None,
        start_at: datetime | None,
        end_before: datetime | None,
        limit: int,
    ) -> list[OperationLog]:
        query = self._query_logs(
            log_type=log_type,
            start_at=start_at,
            end_before=end_before,
        )
        return query.order_by(desc(OperationLog.created_at)).limit(limit).all()

    def delete_before(self, cutoff: datetime) -> int:
        return (
            self.db.query(OperationLog)
            .filter(OperationLog.created_at < cutoff)
            .delete(synchronize_session=False)
        )

    def record(
        self,
        *,
        log_type: str,
        action: str,
        operator_id: int | None,
        operator_name: str | None,
        target_type: str | None = None,
        target_id: int | None = None,
        target_name: str | None = None,
        ip_address: str | None = None,
        detail: dict | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        status: str = "success",
    ) -> None:
        self.db.add(
            OperationLog(
                log_type=log_type,
                action=action,
                operator_id=operator_id,
                operator_name=operator_name,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                ip_address=ip_address,
                detail=json.dumps(detail, ensure_ascii=False) if detail else None,
                old_value=json.dumps(old_value, ensure_ascii=False) if old_value else None,
                new_value=json.dumps(new_value, ensure_ascii=False) if new_value else None,
                status=status,
            )
        )

    def commit(self) -> None:
        self.db.commit()
