"""Identity API schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    device_id: str = Field(default="default", description="设备标识")
    device_name: Optional[str] = Field(default=None, description="设备名称")


class SecureLoginRequest(BaseModel):
    """Secure login hybrid envelope."""

    key_id: str = Field(..., description="登录公钥ID")
    encrypted_key: str = Field(..., description="Base64 RSA-OAEP encrypted AES key")
    iv: str = Field(..., description="Base64 AES-GCM IV")
    nonce: str = Field(..., description="登录请求nonce")
    timestamp: int = Field(..., description="Unix毫秒时间戳")
    data: str = Field(..., description="Base64 AES-GCM ciphertext + tag")


class SecureLoginResponse(BaseModel):
    """Secure login encrypted response envelope."""

    iv: str
    data: str


class RefreshRequest(BaseModel):
    """刷新Token请求"""

    refresh_token: str = Field(..., description="刷新令牌")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class LoginResponse(BaseModel):
    """登录响应"""

    token: str
    refresh_token: str
    session_key: str
    expires_at: str
    user: dict


class RegisterResponse(BaseModel):
    """注册响应"""

    success: bool
    message: str
    user_id: Optional[int] = None


class SessionListResponse(BaseModel):
    """Admin session list response."""

    total: int
    page: int
    page_size: int
    items: list[dict]


class SessionDetailResponse(BaseModel):
    """Admin session detail response."""

    id: int
    user_id: int
    username: Optional[str]
    nickname: Optional[str]
    user_role: Optional[str]
    device_id: str
    device_name: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    platform: Optional[str]
    app_version: Optional[str]
    location: Optional[str]
    status: str
    status_color: str
    status_label: str
    current_status: Optional[str]
    created_at: Optional[str]
    last_active: Optional[str]
    expires_at: Optional[str]
    is_revoked: bool
    revoked_at: Optional[str]
    revoked_by: Optional[int]


class RevokeUserSessionsRequest(BaseModel):
    """Request for revoking sessions owned by a user."""

    exclude_current: bool = Field(default=False, description="是否排除当前会话")


class SessionStatisticsResponse(BaseModel):
    """Admin session statistics response."""

    total_sessions: int
    online_users: int
    status_distribution: dict
    platform_distribution: dict
    updated_at: str


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool
    message: str


class PermissionsResponse(BaseModel):
    """Permission catalog response."""

    permissions: dict
