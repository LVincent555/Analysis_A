"""Compatibility facade for Operations system-configuration use cases."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from ..contexts.operations.application.commands import (
    BatchUpdateSystemConfigsCommand,
    ResetSystemConfigCommand,
    UpdateSystemConfigCommand,
)
from ..contexts.operations.application.config_commands import (
    BatchUpdateSystemConfigsUseCase,
    ResetSystemConfigUseCase,
    UpdateSystemConfigUseCase,
)
from ..contexts.operations.application.config_queries import (
    GetLoginPolicyUseCase,
    GetPasswordPolicyUseCase,
    GetSessionPolicyUseCase,
    GroupSystemConfigsByCategoryUseCase,
    ListSystemConfigsUseCase,
    ValidatePasswordPolicyUseCase,
)
from ..contexts.operations.application.queries import ListSystemConfigsQuery, ValidatePasswordPolicyQuery
from ..contexts.operations.domain.config import (
    CONFIG_CATEGORIES,
    DEFAULT_CONFIGS,
    default_config_value,
    parse_config_value,
    serialize_config_value,
)
from ..contexts.operations.infrastructure.config_cache import UnifiedConfigCacheReloader
from ..contexts.operations.infrastructure.repositories import (
    SqlAlchemyOperationLogRepository,
    SqlAlchemySystemConfigRepository,
)
from ..shared.errors import AppError, ErrorCode


class ConfigService:
    """Legacy service API backed by the Operations context."""

    _cache: dict[str, Any] = {}
    _cache_loaded: bool = False

    @staticmethod
    def _repository(db: Session) -> SqlAlchemySystemConfigRepository:
        return SqlAlchemySystemConfigRepository(db)

    @staticmethod
    def _audit_repository(db: Session) -> SqlAlchemyOperationLogRepository:
        return SqlAlchemyOperationLogRepository(db)

    @classmethod
    def _load_cache(cls, db: Session) -> None:
        cls._cache.clear()
        for config in cls._repository(db).list_configs():
            cls._cache[config.config_key] = parse_config_value(config.config_value, config.config_type)
        cls._cache_loaded = True

    @classmethod
    def _invalidate_cache(cls) -> None:
        cls._cache.clear()
        cls._cache_loaded = False

    @staticmethod
    def _parse_value(value: str, value_type: str) -> Any:
        return parse_config_value(value, value_type)

    @staticmethod
    def _serialize_value(value: Any, value_type: str) -> str:
        return serialize_config_value(value, value_type)

    @staticmethod
    def _legacy_value_error(error: AppError) -> Exception:
        if error.code in (ErrorCode.NOT_FOUND, ErrorCode.VALIDATION_ERROR):
            return ValueError(error.message)
        return error

    @classmethod
    def get(cls, db: Session, key: str, default: Any = None) -> Any:
        if cls._cache_loaded and key in cls._cache:
            return cls._cache[key]

        config = cls._repository(db).get_by_key(key)
        if config:
            value = parse_config_value(config.config_value, config.config_type)
            cls._cache[key] = value
            return value

        if key in DEFAULT_CONFIGS:
            return default_config_value(key)

        return default

    @classmethod
    def get_all(cls, db: Session, category: Optional[str] = None) -> list[dict[str, Any]]:
        return ListSystemConfigsUseCase(configs=cls._repository(db)).execute(
            ListSystemConfigsQuery(category=category)
        )

    @classmethod
    def get_by_category(cls, db: Session) -> dict[str, list[dict[str, Any]]]:
        return GroupSystemConfigsByCategoryUseCase(configs=cls._repository(db)).execute()

    @classmethod
    def update(
        cls,
        db: Session,
        key: str,
        value: Any,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            result = UpdateSystemConfigUseCase(
                configs=cls._repository(db),
                audit_logs=cls._audit_repository(db),
                config_cache=UnifiedConfigCacheReloader(db),
            ).execute(
                UpdateSystemConfigCommand(
                    key=key,
                    value=value,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    ip_address=ip_address,
                )
            )
        except AppError as error:
            raise cls._legacy_value_error(error) from error

        cls._cache[key] = result["value"]
        return result

    @classmethod
    def batch_update(
        cls,
        db: Session,
        updates: dict[str, Any],
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None,
    ) -> dict[str, Any]:
        result = BatchUpdateSystemConfigsUseCase(
            configs=cls._repository(db),
            audit_logs=cls._audit_repository(db),
            config_cache=UnifiedConfigCacheReloader(db),
        ).execute(
            BatchUpdateSystemConfigsCommand(
                updates=updates,
                operator_id=operator_id,
                operator_name=operator_name,
                ip_address=ip_address,
            )
        )
        cls._invalidate_cache()
        return result

    @classmethod
    def reset_to_default(
        cls,
        db: Session,
        key: str,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            result = ResetSystemConfigUseCase(
                configs=cls._repository(db),
                audit_logs=cls._audit_repository(db),
                config_cache=UnifiedConfigCacheReloader(db),
            ).execute(
                ResetSystemConfigCommand(
                    key=key,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    ip_address=ip_address,
                )
            )
        except AppError as error:
            raise cls._legacy_value_error(error) from error

        cls._cache[key] = result["value"]
        return result

    @classmethod
    def get_password_policy(cls, db: Session) -> dict[str, Any]:
        return GetPasswordPolicyUseCase(configs=cls._repository(db)).execute()

    @classmethod
    def get_login_policy(cls, db: Session) -> dict[str, Any]:
        return GetLoginPolicyUseCase(configs=cls._repository(db)).execute()

    @classmethod
    def get_session_policy(cls, db: Session) -> dict[str, Any]:
        return GetSessionPolicyUseCase(configs=cls._repository(db)).execute()

    @classmethod
    def validate_password(cls, db: Session, password: str) -> dict[str, Any]:
        return ValidatePasswordPolicyUseCase(configs=cls._repository(db)).execute(
            ValidatePasswordPolicyQuery(password=password)
        )
