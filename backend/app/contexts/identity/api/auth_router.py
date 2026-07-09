"""
认证路由模块
提供用户注册、登录、Token刷新等API
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....database import get_db
from ....db_models import User
from ....auth.dependencies import get_current_user
from ....core.security_settings import require_secure_login
from .schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    SecureLoginRequest,
    SecureLoginResponse,
)
from ..application.commands import (
    ChangePasswordCommand,
    LoginCommand,
    LogoutAllDevicesCommand,
    LogoutDeviceCommand,
    RefreshAccessTokenCommand,
    RegisterUserCommand,
)
from ..application.use_cases import (
    ChangePasswordUseCase,
    GetUserProfileUseCase,
    ListUserSessionsUseCase,
    LoginUseCase,
    LogoutAllDevicesUseCase,
    LogoutDeviceUseCase,
    RefreshAccessTokenUseCase,
    RegisterUserUseCase,
)
from ..application.queries import GetUserProfileQuery, ListUserSessionsQuery
from ..infrastructure.crypto_provider import identity_crypto_provider
from ..infrastructure.jwt_tokens import jwt_token_issuer
from ..infrastructure.login_envelope import (
    LoginEnvelopeError,
    LoginEnvelopeReplayError,
    LoginEnvelopeService,
)
from ..infrastructure.password_hasher import password_hasher
from ..infrastructure.policy_provider import session_policy_provider
from ..infrastructure.repositories import (
    SqlAlchemyIdentitySessionRepository,
    SqlAlchemyIdentityUserRepository,
)
from ..infrastructure.session_key_store import session_key_store
from ....shared.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])


def _identity_http_error(error: AppError) -> HTTPException:
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


def _identity_repositories(db: Session):
    return (
        SqlAlchemyIdentityUserRepository(db),
        SqlAlchemyIdentitySessionRepository(db),
    )


def _execute_login(req: LoginRequest, db: Session) -> LoginResponse:
    users, sessions = _identity_repositories(db)
    use_case = LoginUseCase(
        users=users,
        sessions=sessions,
        password_hasher=password_hasher,
        token_issuer=jwt_token_issuer,
        session_keys=session_key_store,
        policy_provider=session_policy_provider,
        crypto=identity_crypto_provider,
    )
    try:
        result = use_case.execute(
            LoginCommand(
                username=req.username,
                password=req.password,
                device_id=req.device_id,
                device_name=req.device_name,
            )
        )
    except AppError as error:
        raise _identity_http_error(error) from error

    return LoginResponse(
        token=result.token,
        refresh_token=result.refresh_token,
        session_key=result.session_key_encrypted,
        expires_at=result.expires_at,
        user=result.user,
    )


# ==================== API端点 ====================

@router.post("/register", response_model=RegisterResponse)
async def register(
    req: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册

    - 用户名唯一性检查
    - 密码bcrypt哈希存储
    - 生成用户专属加密密钥
    """
    users, _ = _identity_repositories(db)
    use_case = RegisterUserUseCase(
        users=users,
        password_hasher=password_hasher,
        crypto=identity_crypto_provider,
    )
    try:
        result = use_case.execute(RegisterUserCommand(username=req.username, password=req.password))
    except AppError as error:
        raise _identity_http_error(error) from error

    return RegisterResponse(
        success=True,
        message="注册成功",
        user_id=result.user_id
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录 (v2.2.1)

    安全逻辑顺序:
    1. 查找用户
    2. [先检查锁定] 防止锁定期间恶意刷写数据库
    3. 验证密码（失败时更新 failed_attempts，可能触发锁定）
    4. 检查账户状态
    5. 检查设备数量限制（使用策略提供器决议）
    6. 生成 Token（动态 TTL）
    """
    if require_secure_login():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前环境要求使用 secure-login")

    return _execute_login(req, db)


@router.post("/secure-login", response_model=SecureLoginResponse)
async def secure_login(
    req: SecureLoginRequest,
    db: Session = Depends(get_db),
):
    """Secure login over an application-level encrypted envelope."""
    envelope = LoginEnvelopeService()
    try:
        payload, context = envelope.decrypt_request(req)
    except LoginEnvelopeReplayError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except LoginEnvelopeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    try:
        login_req = LoginRequest(
            username=payload["username"],
            password=payload["password"],
            device_id=payload.get("device_id") or "default",
            device_name=payload.get("device_name"),
        )
    except KeyError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="登录载荷缺少用户名或密码") from error

    response = _execute_login(login_req, db)
    encrypted = envelope.encrypt_response(response.model_dump(), context)
    return SecureLoginResponse(**encrypted)


@router.post("/secure-refresh", response_model=SecureLoginResponse)
async def secure_refresh_token(
    req: SecureLoginRequest,
    db: Session = Depends(get_db),
):
    """Refresh an access token inside the same secure envelope format."""
    envelope = LoginEnvelopeService()
    try:
        payload, context = envelope.decrypt_request(req)
    except LoginEnvelopeReplayError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except LoginEnvelopeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    refresh_token_value = payload.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少刷新令牌")

    users, sessions = _identity_repositories(db)
    use_case = RefreshAccessTokenUseCase(
        token_issuer=jwt_token_issuer,
        users=users,
        sessions=sessions,
        policy_provider=session_policy_provider,
    )
    try:
        result = use_case.execute(RefreshAccessTokenCommand(refresh_token=refresh_token_value))
    except AppError as error:
        if error.message == "会话不存在或已失效":
            logger.warning("刷新Token失败: %s", error.message)
        raise _identity_http_error(error) from error

    encrypted = envelope.encrypt_response(
        {
            "token": result.token,
            "expires_at": result.expires_at,
        },
        context,
    )
    return SecureLoginResponse(**encrypted)


@router.post("/refresh")
async def refresh_token(
    req: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌

    使用Refresh Token获取新的Access Token
    """
    users, sessions = _identity_repositories(db)
    use_case = RefreshAccessTokenUseCase(
        token_issuer=jwt_token_issuer,
        users=users,
        sessions=sessions,
        policy_provider=session_policy_provider,
    )
    try:
        result = use_case.execute(RefreshAccessTokenCommand(refresh_token=req.refresh_token))
    except AppError as error:
        if error.message == "会话不存在或已失效":
            logger.warning("刷新Token失败: %s", error.message)
        raise _identity_http_error(error) from error

    return {
        "token": result.token,
        "expires_at": result.expires_at,
    }


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    用户登出

    清除当前设备的会话
    """
    payload = getattr(user, "_auth_payload", {}) or {}
    device_id = payload.get("device", "default")

    _, sessions = _identity_repositories(db)
    LogoutDeviceUseCase(
        sessions=sessions,
        session_keys=session_key_store,
    ).execute(LogoutDeviceCommand(user_id=user.id, device_id=device_id))

    return {"success": True, "message": "已登出"}


@router.post("/logout-all")
async def logout_all_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    登出所有设备

    清除用户的所有会话
    """
    _, sessions = _identity_repositories(db)
    LogoutAllDevicesUseCase(
        sessions=sessions,
        session_keys=session_key_store,
    ).execute(LogoutAllDevicesCommand(user_id=user.id))

    return {"success": True, "message": "已登出所有设备"}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改密码
    """
    users, sessions = _identity_repositories(db)
    use_case = ChangePasswordUseCase(
        users=users,
        sessions=sessions,
        password_hasher=password_hasher,
        session_keys=session_key_store,
    )
    try:
        use_case.execute(
            ChangePasswordCommand(
                user_id=user.id,
                old_password=req.old_password,
                new_password=req.new_password,
            )
        )
    except AppError as error:
        raise _identity_http_error(error) from error

    return {"success": True, "message": "密码已修改，请重新登录"}


@router.get("/me")
async def get_current_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户信息
    """
    users, _ = _identity_repositories(db)
    try:
        result = GetUserProfileUseCase(users=users).execute(GetUserProfileQuery(user_id=user.id))
    except AppError as error:
        raise _identity_http_error(error) from error
    return result.user


@router.get("/sessions")
async def get_user_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户的所有活跃会话
    """
    users, sessions = _identity_repositories(db)
    try:
        result = ListUserSessionsUseCase(
            users=users,
            sessions=sessions,
        ).execute(ListUserSessionsQuery(user_id=user.id))
    except AppError as error:
        raise _identity_http_error(error) from error

    return {
        "sessions": result.sessions,
        "total": result.total,
        "limit": result.limit,
    }
