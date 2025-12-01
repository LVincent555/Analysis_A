"""
加密网关路由模块 - 通用代理版
所有加密请求的统一入口，自动转发到内部路由
"""
import time
import logging
import json
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field
from starlette.requests import Request as StarletteRequest
from starlette.datastructures import Headers, QueryParams

from ..auth.dependencies import get_current_user, get_session_key
from ..crypto.aes_handler import AESCrypto
from ..db_models import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["加密网关"])


# ==================== 请求/响应模型 ====================

class SecureRequest(BaseModel):
    """加密请求"""
    data: str = Field(..., description="Base64编码的AES加密数据")


class SecureResponse(BaseModel):
    """加密响应"""
    data: str = Field(..., description="Base64编码的AES加密响应")


# ==================== 加密网关端点 ====================

@router.post("/api/secure", response_model=SecureResponse)
async def secure_gateway(
    request: Request,
    secure_request: SecureRequest,
    user: User = Depends(get_current_user),
    session_key: bytes = Depends(get_session_key)
):
    """
    加密网关 - 通用代理
    
    自动将加密请求解密后转发到对应的内部路由，无需为每个API单独注册。
    
    流程:
    1. 解密请求，获取真实path/method/params/body
    2. 构造内部请求，调用FastAPI路由
    3. 加密响应返回
    """
    crypto = AESCrypto(session_key)
    
    try:
        # 1. 解密请求
        decrypted = crypto.decrypt(secure_request.data)
        
        if not isinstance(decrypted, dict):
            raise HTTPException(400, "无效的请求格式")
        
        # 2. 提取请求信息
        path = decrypted.get("path", "")
        method = decrypted.get("method", "GET").upper()
        params = decrypted.get("params", {})
        body = decrypted.get("body")
        timestamp = decrypted.get("timestamp", 0)
        
        if not path:
            raise HTTPException(400, "缺少请求路径")
        
        # 3. 验证时间戳（防重放攻击，5分钟内有效）
        current_time = time.time() * 1000
        if abs(current_time - timestamp) > 300000:
            raise HTTPException(400, "请求已过期")
        
        # 4. 内部路由调用
        app = request.app
        
        # 构建查询字符串
        query_string = "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
        
        # 构建内部请求的scope
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string.encode(),
            "headers": [
                (b"content-type", b"application/json"),
                (b"x-forwarded-user", str(user.id).encode()),
            ],
            "app": app,
            "state": {"user": user, "user_id": user.id},
        }
        
        # 构建请求体
        if body:
            body_bytes = json.dumps(body).encode() if isinstance(body, dict) else str(body).encode()
        else:
            body_bytes = b""
        
        # 创建内部请求
        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        
        internal_request = Request(scope, receive)
        internal_request.state.user = user
        internal_request.state.user_id = user.id
        
        # 5. 查找并执行路由
        result = await _call_internal_route(app, path, method, params, body, user)
        
        # 6. 加密响应
        encrypted_response = crypto.encrypt(result)
        
        return SecureResponse(data=encrypted_response)
        
    except HTTPException as he:
        logger.warning(f"加密网关HTTP错误: {he.status_code} - {he.detail}")
        raise
    except ValueError as e:
        logger.error(f"加密网关解密失败: {str(e)}")
        raise HTTPException(400, f"解密失败: {str(e)}")
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"加密网关错误: {e}\n{error_detail}")
        raise HTTPException(500, f"处理失败: {str(e)}")


async def _call_internal_route(app, path: str, method: str, params: dict, body: Any, user: User):
    """
    调用内部路由
    
    遍历FastAPI的路由表，找到匹配的路由并执行
    """
    from fastapi import FastAPI
    from fastapi.routing import APIRoute
    from urllib.parse import unquote
    import re
    import inspect
    
    # 过滤掉前端可能传的无效参数
    filtered_params = {k: v for k, v in params.items() if not k.startswith('_')}
    
    # 遍历所有路由
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        
        # 检查方法是否匹配
        if method not in route.methods:
            continue
        
        # 检查路径是否匹配
        path_params = _match_route_path(route.path, path)
        if path_params is None:
            continue
        
        # 找到匹配的路由，执行处理函数
        endpoint = route.endpoint
        sig = inspect.signature(endpoint)
        
        # 构建参数，并根据类型注解转换类型
        kwargs = {}
        
        # 注入 current_user（如果路由需要）
        if 'current_user' in sig.parameters:
            kwargs['current_user'] = user
        
        # 处理路径参数（需要URL解码）
        for key, value in path_params.items():
            decoded_value = unquote(str(value))
            kwargs[key] = _convert_param_type(key, decoded_value, sig)
        
        # 处理查询参数
        for key, value in filtered_params.items():
            if key in sig.parameters:
                # URL解码查询参数值
                decoded_value = unquote(str(value)) if isinstance(value, str) else value
                kwargs[key] = _convert_param_type(key, decoded_value, sig)
        
        # 为未传入的参数填充默认值
        for param_name, param in sig.parameters.items():
            if param_name in kwargs or param_name in ['request', 'db', 'current_user']:
                continue
            default = param.default
            if default != inspect.Parameter.empty:
                # 检查是否是FastAPI的FieldInfo（Query, Path等）
                if hasattr(default, 'default'):
                    # 从Query/Path等对象提取默认值
                    actual_default = default.default
                    # 如果默认值是PydanticUndefinedType或Ellipsis，跳过
                    if actual_default is not ... and not (hasattr(actual_default, '__class__') and 'PydanticUndefined' in str(type(actual_default))):
                        kwargs[param_name] = actual_default
                else:
                    # 普通默认值
                    kwargs[param_name] = default
        
        # 如果有body且endpoint需要body参数
        if body is not None:
            for param_name, param in sig.parameters.items():
                if param_name not in kwargs and param_name not in ['request', 'db', 'current_user']:
                    if param.annotation != inspect.Parameter.empty:
                        try:
                            if isinstance(body, dict):
                                kwargs[param_name] = param.annotation(**body)
                            else:
                                kwargs[param_name] = body
                        except:
                            kwargs[param_name] = body
                    break
        
        # 执行路由处理函数
        import asyncio
        logger.debug(f"执行路由: {method} {path}, kwargs: {list(kwargs.keys())}")
        try:
            if asyncio.iscoroutinefunction(endpoint):
                result = await endpoint(**kwargs)
            else:
                result = endpoint(**kwargs)
        except Exception as route_error:
            logger.error(f"路由执行失败 {method} {path}: {route_error}")
            raise
        
        # 处理返回值
        if hasattr(result, 'dict'):
            return result.dict()
        elif hasattr(result, 'model_dump'):
            return result.model_dump()
        else:
            return result
    
    logger.warning(f"路由未找到: {method} {path}")
    raise HTTPException(404, f"路由不存在: {method} {path}")


def _convert_param_type(param_name: str, value: Any, sig) -> Any:
    """
    根据函数签名中的类型注解转换参数类型
    支持处理FastAPI的Query/Path等参数默认值
    """
    import inspect
    from typing import get_origin, get_args, Union
    
    if param_name not in sig.parameters:
        return value
    
    param = sig.parameters[param_name]
    annotation = param.annotation
    
    # 如果没有类型注解，尝试从默认值推断
    if annotation == inspect.Parameter.empty:
        default = param.default
        # 检查默认值是否是FastAPI的FieldInfo（Query, Path等）
        if hasattr(default, 'annotation'):
            annotation = default.annotation
        elif default != inspect.Parameter.empty and default is not None:
            annotation = type(default)
        else:
            return value
    
    # 处理Union类型（如 Optional[str] = Union[str, None]）
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        # 取第一个非None类型
        for arg in args:
            if arg is not type(None):
                annotation = arg
                break
    
    # 如果值已经是正确类型，直接返回
    try:
        if isinstance(value, annotation) if isinstance(annotation, type) else False:
            return value
    except TypeError:
        pass
    
    try:
        # 处理常见类型
        if annotation == int or annotation is int:
            return int(float(value))  # 先转float再转int，处理"3.0"这种情况
        elif annotation == float or annotation is float:
            return float(value)
        elif annotation == bool or annotation is bool:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
        elif annotation == str or annotation is str:
            return str(value)
        else:
            # 对于其他类型，返回原值
            return value
    except (ValueError, TypeError):
        return value


def _match_route_path(route_path: str, request_path: str) -> dict | None:
    """
    匹配路由路径，提取路径参数
    
    Args:
        route_path: 路由定义的路径，如 "/api/stock/{code}"
        request_path: 实际请求路径，如 "/api/stock/000001"
    
    Returns:
        匹配成功返回路径参数字典，失败返回None
    """
    import re
    
    # 将路由路径转换为正则表达式
    # {param} -> (?P<param>[^/]+)
    pattern = route_path
    param_names = []
    
    # 找出所有路径参数
    for match in re.finditer(r'\{(\w+)\}', route_path):
        param_names.append(match.group(1))
    
    # 替换为正则
    pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
    pattern = f"^{pattern}$"
    
    # 匹配
    match = re.match(pattern, request_path)
    if match:
        return match.groupdict()
    return None


@router.get("/api/secure/routes")
async def list_secure_routes(
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    列出所有可用的API路由（调试用）
    """
    from fastapi.routing import APIRoute
    
    routes = []
    for route in request.app.routes:
        if isinstance(route, APIRoute):
            # 排除secure相关路由和认证路由
            if not route.path.startswith("/api/secure") and not route.path.startswith("/api/auth"):
                routes.append({
                    "path": route.path,
                    "methods": list(route.methods - {"HEAD", "OPTIONS"}),
                    "name": route.name
                })
    
    return {"routes": routes, "total": len(routes)}
