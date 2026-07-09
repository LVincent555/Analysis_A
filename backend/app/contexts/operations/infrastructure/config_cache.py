"""Config cache adapters."""

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UnifiedConfigCacheReloader:
    def __init__(self, db: Session) -> None:
        self.db = db

    def reload(self) -> None:
        try:
            from ....core.caching import cache

            cache.reload_configs(self.db)
        except Exception as exc:
            logger.warning("[OperationsConfig] UnifiedCache reload failed: %s", exc)
