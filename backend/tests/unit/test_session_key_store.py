from app.auth.dependencies import (
    get_session_key_by_user_id,
    remove_session_key,
    set_session_key,
)


def test_session_keys_are_scoped_by_device():
    set_session_key(7, b"desktop-key", "desktop")
    set_session_key(7, b"laptop-key", "laptop")

    assert get_session_key_by_user_id(7, "desktop") == b"desktop-key"
    assert get_session_key_by_user_id(7, "laptop") == b"laptop-key"


def test_remove_session_key_can_target_one_device():
    set_session_key(7, b"desktop-key", "desktop")
    set_session_key(7, b"laptop-key", "laptop")

    remove_session_key(7, "desktop")

    assert get_session_key_by_user_id(7, "desktop") is None
    assert get_session_key_by_user_id(7, "laptop") == b"laptop-key"


def test_remove_session_key_without_device_removes_all_user_devices():
    set_session_key(7, b"desktop-key", "desktop")
    set_session_key(7, b"laptop-key", "laptop")
    set_session_key(8, b"other-user-key", "desktop")

    remove_session_key(7)

    assert get_session_key_by_user_id(7, "desktop") is None
    assert get_session_key_by_user_id(7, "laptop") is None
    assert get_session_key_by_user_id(8, "desktop") == b"other-user-key"
