import pytest

from app.contexts.identity.domain.policies import account_status
from app.contexts.identity.domain.value_objects import DeviceId, SessionPolicy
from app.shared.pagination import PageRequest


def test_page_request_calculates_offset_and_limit() -> None:
    request = PageRequest(page=3, page_size=25)

    assert request.offset == 50
    assert request.limit == 25


def test_device_id_normalizes_blank_value() -> None:
    assert str(DeviceId("")) == "default"


def test_session_policy_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        SessionPolicy(max_devices=0, access_token_hours=1, refresh_token_days=1)


def test_account_status_prioritizes_terminal_states() -> None:
    from datetime import timedelta

    from app.shared.time import utc_now_naive

    now = utc_now_naive()

    assert account_status(is_active=True, deleted_at=now, now=now) == "deleted"
    assert account_status(is_active=False, now=now) == "inactive"
    assert account_status(is_active=True, locked_until=now + timedelta(minutes=1), now=now) == "locked"
    assert account_status(is_active=True, expires_at=now - timedelta(minutes=1), now=now) == "expired"
    assert account_status(is_active=True, now=now) == "active"
