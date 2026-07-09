"""Identity application use cases."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from .commands import (
    ChangePasswordCommand,
    LoginCommand,
    LogoutAllDevicesCommand,
    LogoutDeviceCommand,
    RefreshAccessTokenCommand,
    RegisterUserCommand,
)
from .ports import (
    IdentityCryptoProvider,
    IdentitySessionRepository,
    IdentityUserRepository,
    PasswordHasher,
    SessionKeyStore,
    SessionPolicyProvider,
    TokenIssuer,
)
from .queries import GetUserProfileQuery, ListUserSessionsQuery


@dataclass(frozen=True, slots=True)
class RefreshAccessTokenResult:
    token: str
    expires_at: str


@dataclass(frozen=True, slots=True)
class AuthenticatedUserResult:
    user: Any
    payload: dict
    session: Any


@dataclass(frozen=True, slots=True)
class RegisterUserResult:
    user_id: int


@dataclass(frozen=True, slots=True)
class LoginResult:
    token: str
    refresh_token: str
    session_key_encrypted: str
    expires_at: str
    user: dict


@dataclass(frozen=True, slots=True)
class UserProfileResult:
    user: dict


@dataclass(frozen=True, slots=True)
class UserSessionsResult:
    sessions: list[dict]
    total: int
    limit: int


def _unauthorized(message: str) -> AppError:
    return AppError(ErrorCode.UNAUTHORIZED, message)


def _forbidden(message: str) -> AppError:
    return AppError(ErrorCode.FORBIDDEN, message)


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _get_payload_user_id(payload: dict) -> int:
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise _unauthorized("无效的刷新令牌") from exc


def _get_access_payload_user_id(payload: dict) -> int:
    try:
        return int(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise _unauthorized("无效的Token主体") from exc


def _ensure_refresh_user_allowed(user: Any, payload: dict, now) -> None:
    if not user or getattr(user, "deleted_at", None) or not getattr(user, "is_active", False):
        raise _unauthorized("用户不存在或已禁用")

    if getattr(user, "expires_at", None) and user.expires_at < now:
        raise _unauthorized("账户已过期")

    if getattr(user, "locked_until", None) and user.locked_until > now:
        raise _forbidden("账户已锁定")

    token_version = payload.get("ver")
    if token_version is None:
        return

    try:
        payload_token_version = int(token_version)
    except (TypeError, ValueError) as exc:
        raise _unauthorized("无效的登录状态") from exc

    if payload_token_version != (getattr(user, "token_version", None) or 1):
        raise _unauthorized("登录状态已失效，请重新登录")


def _ensure_access_user_allowed(user: Any, payload: dict, now) -> None:
    if not user or getattr(user, "deleted_at", None):
        raise _unauthorized("用户不存在")

    if not getattr(user, "is_active", False):
        raise _forbidden("账户已被禁用")

    if getattr(user, "expires_at", None) and user.expires_at < now:
        raise _forbidden("账户已过期")

    if getattr(user, "locked_until", None) and user.locked_until > now:
        raise _forbidden("账户已锁定")

    token_version = payload.get("ver")
    if token_version is None:
        return

    try:
        payload_token_version = int(token_version)
    except (TypeError, ValueError) as exc:
        raise _unauthorized("无效的登录状态") from exc

    if payload_token_version != (getattr(user, "token_version", None) or 1):
        raise _unauthorized("登录状态已失效，请重新登录")


class AuthenticateAccessTokenUseCase:
    def __init__(
        self,
        *,
        token_issuer: TokenIssuer,
        users: IdentityUserRepository,
        sessions: IdentitySessionRepository,
    ) -> None:
        self.token_issuer = token_issuer
        self.users = users
        self.sessions = sessions

    def execute(self, token: str) -> AuthenticatedUserResult:
        payload = self.token_issuer.verify_token(token)
        if not payload:
            raise _unauthorized("无效的Token或Token已过期")

        if payload.get("type") != "access":
            raise _unauthorized("需要访问令牌，而非刷新令牌")

        user_id = _get_access_payload_user_id(payload)
        device_id = payload.get("device", "default")
        now = utc_now_naive()
        user = self.users.get_by_id(user_id)
        _ensure_access_user_allowed(user, payload, now)

        session = self.sessions.find_active_session(user_id, device_id, now)
        if not session:
            raise _unauthorized("会话不存在或已失效")

        return AuthenticatedUserResult(user=user, payload=payload, session=session)


class RegisterUserUseCase:
    def __init__(
        self,
        *,
        users: IdentityUserRepository,
        password_hasher: PasswordHasher,
        crypto: IdentityCryptoProvider,
    ) -> None:
        self.users = users
        self.password_hasher = password_hasher
        self.crypto = crypto

    def execute(self, command: RegisterUserCommand) -> RegisterUserResult:
        if self.users.get_by_username(command.username):
            raise _validation_error("用户名已存在")

        user_key = self.crypto.generate_key()
        user_key_encrypted = self.crypto.encrypt_user_key(user_key)
        user = self.users.add_user(
            username=command.username,
            password_hash=self.password_hasher.hash(command.password),
            user_key_encrypted=user_key_encrypted,
        )
        self.users.commit()
        self.users.refresh(user)
        return RegisterUserResult(user_id=user.id)


class LoginUseCase:
    def __init__(
        self,
        *,
        users: IdentityUserRepository,
        sessions: IdentitySessionRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        session_keys: SessionKeyStore,
        policy_provider: SessionPolicyProvider,
        crypto: IdentityCryptoProvider,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.password_hasher = password_hasher
        self.token_issuer = token_issuer
        self.session_keys = session_keys
        self.policy_provider = policy_provider
        self.crypto = crypto

    def execute(self, command: LoginCommand) -> LoginResult:
        user = self.users.get_by_username(command.username)
        if not user:
            raise _unauthorized("用户名或密码错误")

        now = utc_now_naive()
        if getattr(user, "locked_until", None) and user.locked_until > now:
            remaining = (user.locked_until - now).seconds // 60
            raise _forbidden(f"账户已锁定，请 {remaining} 分钟后重试")

        login_policy = self.policy_provider.get_login_policy()
        if not self.password_hasher.verify(command.password, user.password_hash):
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= login_policy["max_attempts"]:
                user.locked_until = now + timedelta(minutes=login_policy["lockout_minutes"])
                self.users.commit()
                raise _forbidden(f"登录失败次数过多，账户已锁定 {login_policy['lockout_minutes']} 分钟")

            self.users.commit()
            remaining_attempts = login_policy["max_attempts"] - user.failed_attempts
            raise _unauthorized(f"用户名或密码错误，还剩 {remaining_attempts} 次尝试机会")

        if user.failed_attempts or user.locked_until:
            user.failed_attempts = 0
            user.locked_until = None

        if user.deleted_at:
            raise _unauthorized("用户名或密码错误")

        if not user.is_active:
            raise _forbidden("账户已被禁用")

        if user.expires_at and user.expires_at < now:
            raise _forbidden("账户已过期")

        session_policy = self.policy_provider.get_session_policy(user)
        device_id = command.device_id or "default"
        existing_session = self.sessions.get_by_user_device(user.id, device_id)
        is_existing_active_session = (
            existing_session is not None
            and not existing_session.is_revoked
            and existing_session.expires_at > now
        )

        active_sessions = self.sessions.count_active_for_user(user.id, now)
        if not is_existing_active_session and active_sessions >= session_policy["max_devices"]:
            oldest_session = self.sessions.find_oldest_active_for_user(user.id, now)
            if oldest_session:
                self.session_keys.remove(user.id, oldest_session.device_id)
                self.sessions.delete(oldest_session)

        session_key = self.crypto.generate_key()
        session_key_encrypted = self.crypto.encrypt_session_key_with_password(command.password, session_key)
        token_version = user.token_version or 1
        token = self.token_issuer.create_access_token(
            user.id,
            device_id,
            expires_hours=session_policy["access_token_hours"],
            token_version=token_version,
        )
        refresh_token = self.token_issuer.create_refresh_token(
            user.id,
            device_id,
            expires_days=session_policy["refresh_token_days"],
            token_version=token_version,
        )
        access_expires_at = utc_now_naive() + timedelta(hours=session_policy["access_token_hours"])
        session_expires_at = utc_now_naive() + timedelta(days=session_policy["refresh_token_days"])

        self.sessions.upsert_user_device_session(
            existing_session=existing_session,
            user_id=user.id,
            device_id=device_id,
            device_name=command.device_name,
            session_key_encrypted=session_key_encrypted,
            refresh_token=refresh_token,
            expires_at=session_expires_at,
            now=utc_now_naive(),
        )
        user.last_login = utc_now_naive()
        self.sessions.commit()
        self.session_keys.set(user.id, session_key, device_id)

        return LoginResult(
            token=token,
            refresh_token=refresh_token,
            session_key_encrypted=session_key_encrypted,
            expires_at=access_expires_at.isoformat(),
            user=user.to_dict(),
        )


class RefreshAccessTokenUseCase:
    def __init__(
        self,
        *,
        token_issuer: TokenIssuer,
        users: IdentityUserRepository,
        sessions: IdentitySessionRepository,
        policy_provider: SessionPolicyProvider,
    ) -> None:
        self.token_issuer = token_issuer
        self.users = users
        self.sessions = sessions
        self.policy_provider = policy_provider

    def execute(self, command: RefreshAccessTokenCommand) -> RefreshAccessTokenResult:
        payload = self.token_issuer.verify_token(command.refresh_token)
        if not payload:
            raise _unauthorized("无效的刷新令牌")

        if payload.get("type") != "refresh":
            raise _unauthorized("需要刷新令牌")

        user_id = _get_payload_user_id(payload)
        device_id = payload.get("device", "default")
        now = utc_now_naive()
        user = self.users.get_by_id(user_id)
        _ensure_refresh_user_allowed(user, payload, now)

        session = self.sessions.find_valid_refresh_session(
            user_id=user_id,
            device_id=device_id,
            refresh_token=command.refresh_token,
            now=now,
        )
        if not session:
            raise _unauthorized("会话不存在或已失效")

        session_policy = self.policy_provider.get_session_policy(user)
        token = self.token_issuer.create_access_token(
            user_id,
            device_id,
            expires_hours=session_policy["access_token_hours"],
            token_version=getattr(user, "token_version", None) or 1,
        )
        access_expires_at = utc_now_naive() + timedelta(hours=session_policy["access_token_hours"])

        self.sessions.touch(session, utc_now_naive())
        self.sessions.commit()

        return RefreshAccessTokenResult(token=token, expires_at=access_expires_at.isoformat())


class LogoutDeviceUseCase:
    def __init__(self, *, sessions: IdentitySessionRepository, session_keys: SessionKeyStore) -> None:
        self.sessions = sessions
        self.session_keys = session_keys

    def execute(self, command: LogoutDeviceCommand) -> None:
        now = utc_now_naive()
        self.sessions.revoke_device(
            user_id=command.user_id,
            device_id=command.device_id or "default",
            revoked_by=command.user_id,
            now=now,
        )
        self.sessions.commit()
        self.session_keys.remove(command.user_id, command.device_id or "default")


class LogoutAllDevicesUseCase:
    def __init__(self, *, sessions: IdentitySessionRepository, session_keys: SessionKeyStore) -> None:
        self.sessions = sessions
        self.session_keys = session_keys

    def execute(self, command: LogoutAllDevicesCommand) -> None:
        self.sessions.delete_all_for_user(command.user_id)
        self.sessions.commit()
        self.session_keys.remove(command.user_id)


class ChangePasswordUseCase:
    def __init__(
        self,
        *,
        users: IdentityUserRepository,
        sessions: IdentitySessionRepository,
        password_hasher: PasswordHasher,
        session_keys: SessionKeyStore,
    ) -> None:
        self.users = users
        self.sessions = sessions
        self.password_hasher = password_hasher
        self.session_keys = session_keys

    def execute(self, command: ChangePasswordCommand) -> None:
        user = self.users.get_by_id(command.user_id)
        if not user:
            raise _unauthorized("用户不存在")

        if not self.password_hasher.verify(command.old_password, user.password_hash):
            raise _validation_error("旧密码错误")

        user.password_hash = self.password_hasher.hash(command.new_password)
        self.sessions.delete_all_for_user(command.user_id)
        self.sessions.commit()
        self.session_keys.remove(command.user_id)


class GetUserProfileUseCase:
    def __init__(self, *, users: IdentityUserRepository) -> None:
        self.users = users

    def execute(self, query: GetUserProfileQuery) -> UserProfileResult:
        user = self.users.get_by_id(query.user_id)
        if not user:
            raise _unauthorized("用户不存在")

        return UserProfileResult(user=user.to_dict())


class ListUserSessionsUseCase:
    def __init__(self, *, users: IdentityUserRepository, sessions: IdentitySessionRepository) -> None:
        self.users = users
        self.sessions = sessions

    def execute(self, query: ListUserSessionsQuery) -> UserSessionsResult:
        user = self.users.get_by_id(query.user_id)
        if not user:
            raise _unauthorized("用户不存在")

        active_sessions = self.sessions.list_active_for_user(query.user_id, utc_now_naive())
        rows = [
            {
                "device_id": session.device_id,
                "device_name": session.device_name,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "last_active": session.last_active.isoformat() if session.last_active else None,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            }
            for session in active_sessions
        ]

        return UserSessionsResult(
            sessions=rows,
            total=len(rows),
            limit=user.allowed_devices,
        )
