from collections.abc import Generator
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("ALLOW_INSECURE_DEV_KEYS", "true")

from app.auth import dependencies as auth_dependencies
from app.contexts.operations.infrastructure.policy_engine import CachedPolicyProvider
from app.db_models import Base
from app.services.policy_engine import PolicyEngine


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(autouse=True)
def clear_session_key_fallback() -> Generator[None, None, None]:
    auth_dependencies._fallback_session_keys.clear()
    yield
    auth_dependencies._fallback_session_keys.clear()


@pytest.fixture()
def session_policy(monkeypatch: pytest.MonkeyPatch) -> dict:
    policy = {
        "max_devices": 2,
        "access_token_hours": 1,
        "refresh_token_days": 9,
    }

    def fake_get_session_policy(cls, user):
        return policy

    monkeypatch.setattr(
        CachedPolicyProvider,
        "get_session_policy",
        classmethod(fake_get_session_policy),
    )
    monkeypatch.setattr(
        PolicyEngine,
        "get_session_policy",
        classmethod(fake_get_session_policy),
    )
    return policy
