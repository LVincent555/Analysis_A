# -*- coding: utf-8 -*-
"""
策略引擎 (PolicyEngine)

v2.2.1 实现:
- 无状态: 不持有 _cache，直接调用 cache.get_config()
- 按 Key 限频告警: 每分钟同 Key 只报一次，防止日志刷屏
- 默认值兜底: 缓存 Miss 时返回默认值，保证系统可用性
"""

import time
import logging
from typing import Any, Dict

from ..core.caching import cache

logger = logging.getLogger(__name__)

# 按 Key 记录上次告警时间，防止日志刷屏
_last_miss_log: Dict[str, float] = {}


class PolicyEngine:
    """
    策略引擎 v2.2.1
    
    职责:
    1. 从 UnifiedCache.config() 读取配置
    2. 输出最终生效策略（全局 + 用户覆盖）
    3. 提供密码强度校验
    
    设计原则:
    - 无状态 (Stateless): 不持有缓存
    - 代理模式: 逻辑判断 → cache.get_config
    """

    @staticmethod
    def _cfg(key: str, default: Any = None) -> Any:
        """
        从缓存读取配置
        
        - 强制使用 KeyBuilder 封装 Key（由 cache.get_config 内部处理）
        - 缓存 Miss 时按 Key 限频告警（每分钟同 Key 只报一次）
        """
        val = cache.get_config(key)
        
        if val is None:
            # 按 Key 限频告警
            now = time.time()
            last_time = _last_miss_log.get(key, 0)
            
            if now - last_time > 60:  # 每分钟同 Key 只报一次
                logger.warning(
                    f"[PolicyEngine] MISS '{key}', using default='{default}'. Check preload."
                )
                _last_miss_log[key] = now
            
            return default
        return val

    # ========== 登录策略 ==========
    
    @classmethod
    def get_login_policy(cls) -> dict:
        """
        获取登录策略
        
        返回:
            max_attempts: 最大失败次数
            lockout_minutes: 锁定时长（分钟）
        """
        return {
            "max_attempts": int(cls._cfg("login_max_attempts", 5)),
            "lockout_minutes": int(cls._cfg("login_lockout_minutes", 30)),
        }

    # ========== 会话策略 ==========
    
    @classmethod
    def get_session_policy(cls, user) -> dict:
        """
        获取会话策略（支持用户覆盖全局）
        
        决议规则:
        - max_devices: User.allowed_devices > 0 时覆盖 Global
        
        返回:
            max_devices: 最大设备数
            access_token_hours: Access Token 有效期（小时）
            refresh_token_days: Refresh Token 有效期（天）
        """
        global_max = int(cls._cfg("session_max_devices", 3))
        
        # 用户覆盖逻辑
        user_max = None
        if hasattr(user, 'allowed_devices') and user.allowed_devices and user.allowed_devices > 0:
            user_max = user.allowed_devices
        
        return {
            "max_devices": user_max or global_max,
            "access_token_hours": int(cls._cfg("session_access_token_hours", 24)),
            "refresh_token_days": int(cls._cfg("session_refresh_token_days", 7)),
        }

    # ========== 密码策略 ==========
    
    @classmethod
    def get_password_policy(cls) -> dict:
        """
        获取密码策略
        
        返回:
            min_length: 最小长度
            require_digit: 是否要求数字
            require_upper: 是否要求大写
            require_lower: 是否要求小写
            require_special: 是否要求特殊字符
        """
        return {
            "min_length": int(cls._cfg("password_min_length", 6)),
            "require_digit": cls._cfg("password_require_digit", False),
            "require_upper": cls._cfg("password_require_upper", False),
            "require_lower": cls._cfg("password_require_lower", False),
            "require_special": cls._cfg("password_require_special", False),
        }

    @classmethod
    def validate_password(cls, password: str) -> None:
        """
        验证密码强度
        
        根据配置校验密码是否符合要求
        
        Raises:
            ValueError: 密码不符合策略
        """
        policy = cls.get_password_policy()
        errors = []
        
        # 最小长度
        if len(password) < policy["min_length"]:
            errors.append(f"密码长度不能少于 {policy['min_length']} 位")
        
        # 要求数字
        if policy["require_digit"] and not any(c.isdigit() for c in password):
            errors.append("密码必须包含数字")
        
        # 要求大写
        if policy["require_upper"] and not any(c.isupper() for c in password):
            errors.append("密码必须包含大写字母")
        
        # 要求小写
        if policy["require_lower"] and not any(c.islower() for c in password):
            errors.append("密码必须包含小写字母")
        
        # 要求特殊字符
        if policy["require_special"] and not any(not c.isalnum() for c in password):
            errors.append("密码必须包含特殊字符")
        
        if errors:
            raise ValueError("；".join(errors))
