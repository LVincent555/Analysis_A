"""
认证中间件
根据配置决定是否要求所有API都需要认证
强制所有API只能通过加密网关访问
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import API_REQUIRE_AUTH
from ..auth.jwt_handler import verify_token

logger = logging.getLogger(__name__)

# 白名单路径（无论配置如何都不需要认证，且允许直接访问）
# 注意：/docs、/redoc、/openapi.json 由 ENABLE_DOCS 配置控制
PUBLIC_PATHS = [
    "/",                    # 根路径
    "/docs",                # Swagger文档（如启用）
    "/redoc",               # ReDoc文档（如启用）
    "/openapi.json",        # OpenAPI规范（如启用）
    "/api/auth/login",      # 登录
    "/api/auth/register",   # 注册
    "/api/auth/refresh",    # 刷新Token
    "/api/auth/logout",     # 登出
    "/api/secure",          # 加密网关（端点自己处理认证）
    "/api/secure/routes",   # 加密路由列表
]

# 白名单前缀
PUBLIC_PREFIXES = [
    "/static",              # 静态文件
    # "/updates" 需要认证，通过 Bearer Token 访问
]

# 是否强制只允许通过加密网关访问API
# 可通过环境变量 FORCE_SECURE_API=false 关闭（用于测试）
import os
FORCE_SECURE_API = os.getenv("FORCE_SECURE_API", "true").lower() == "true"


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件
    
    当 API_REQUIRE_AUTH=true 时：
    - 所有非白名单API都需要Bearer Token认证
    - 未认证请求返回401
    
    当 API_REQUIRE_AUTH=false 时：
    - 所有API都可以匿名访问（兼容模式）
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        # OPTIONS预检请求直接放行（CORS需要）
        if method == "OPTIONS":
            return await call_next(request)
        
        # 白名单路径直接放行
        if self._is_public_path(path):
            return await call_next(request)
        
        # 强制只允许通过加密网关访问API
        if FORCE_SECURE_API and path.startswith("/api/"):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "禁止直接访问API，请通过加密网关 /api/secure 访问",
                    "code": "DIRECT_API_FORBIDDEN",
                    "hint": "所有API调用必须通过加密通道"
                }
            )
        
        # 如果不要求认证，直接放行
        if not API_REQUIRE_AUTH:
            return await call_next(request)
        
        # 检查Authorization头
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "需要登录认证",
                    "code": "AUTH_REQUIRED",
                    "hint": "请在请求头中添加 Authorization: Bearer <token>"
                }
            )
        
        # 验证Token格式
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "无效的认证格式",
                    "code": "INVALID_AUTH_FORMAT",
                    "hint": "格式应为: Bearer <token>"
                }
            )
        
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        
        # 验证Token
        payload = verify_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Token无效或已过期",
                    "code": "INVALID_TOKEN",
                    "hint": "请重新登录获取新Token"
                }
            )
        
        # Token有效，继续处理请求
        # 将用户信息存入request.state供后续使用
        request.state.user_id = payload.get("sub")
        request.state.device_id = payload.get("device")
        
        return await call_next(request)
    
    def _is_public_path(self, path: str) -> bool:
        """检查是否为公开路径"""
        # 精确匹配
        if path in PUBLIC_PATHS:
            return True
        
        # 前缀匹配
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True
        
        return False
