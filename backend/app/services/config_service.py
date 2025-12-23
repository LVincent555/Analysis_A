"""
系统配置服务
提供配置读取、更新、缓存等功能
v1.1.0
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..db_models import SystemConfig, OperationLog

logger = logging.getLogger(__name__)


# 配置分类
CONFIG_CATEGORIES = {
    "password": "密码策略",
    "login": "登录策略",
    "session": "会话策略",
    "system": "系统配置"
}

# 默认配置值
DEFAULT_CONFIGS = {
    # 密码策略
    "password_min_length": {"value": "6", "type": "int", "category": "password", "description": "密码最小长度"},
    "password_max_length": {"value": "100", "type": "int", "category": "password", "description": "密码最大长度"},
    "password_require_digit": {"value": "false", "type": "bool", "category": "password", "description": "要求包含数字"},
    "password_require_upper": {"value": "false", "type": "bool", "category": "password", "description": "要求包含大写字母"},
    "password_require_lower": {"value": "false", "type": "bool", "category": "password", "description": "要求包含小写字母"},
    "password_require_special": {"value": "false", "type": "bool", "category": "password", "description": "要求包含特殊字符"},
    "password_expire_days": {"value": "0", "type": "int", "category": "password", "description": "密码过期天数，0=不过期"},
    
    # 登录策略
    "login_max_attempts": {"value": "5", "type": "int", "category": "login", "description": "最大失败尝试次数"},
    "login_lockout_minutes": {"value": "30", "type": "int", "category": "login", "description": "锁定时长（分钟）"},
    "login_attempt_reset_minutes": {"value": "60", "type": "int", "category": "login", "description": "失败计数重置时间"},
    "login_captcha_enabled": {"value": "false", "type": "bool", "category": "login", "description": "启用验证码"},
    "login_captcha_threshold": {"value": "3", "type": "int", "category": "login", "description": "验证码触发次数"},
    
    # 会话策略
    "session_access_token_hours": {"value": "24", "type": "int", "category": "session", "description": "Access Token有效期（小时）"},
    "session_refresh_token_days": {"value": "7", "type": "int", "category": "session", "description": "Refresh Token有效期（天）"},
    "session_max_devices": {"value": "3", "type": "int", "category": "session", "description": "默认最大设备数"},
    "session_idle_timeout_minutes": {"value": "30", "type": "int", "category": "session", "description": "空闲超时（分钟）"},
    "session_single_device": {"value": "false", "type": "bool", "category": "session", "description": "单设备登录限制"},
}


class ConfigService:
    """系统配置服务"""
    
    # 内存缓存
    _cache: Dict[str, Any] = {}
    _cache_loaded: bool = False
    
    @classmethod
    def _load_cache(cls, db: Session) -> None:
        """加载配置到内存缓存"""
        configs = db.query(SystemConfig).all()
        for config in configs:
            cls._cache[config.config_key] = cls._parse_value(config.config_value, config.config_type)
        cls._cache_loaded = True
        logger.info(f"已加载 {len(configs)} 条系统配置到缓存")
    
    @classmethod
    def _invalidate_cache(cls) -> None:
        """清除缓存"""
        cls._cache.clear()
        cls._cache_loaded = False
    
    @staticmethod
    def _parse_value(value: str, value_type: str) -> Any:
        """解析配置值"""
        if value_type == "int":
            return int(value)
        elif value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "json":
            return json.loads(value)
        else:
            return value
    
    @staticmethod
    def _serialize_value(value: Any, value_type: str) -> str:
        """序列化配置值"""
        if value_type == "bool":
            return "true" if value else "false"
        elif value_type == "json":
            return json.dumps(value)
        else:
            return str(value)
    
    @classmethod
    def get(cls, db: Session, key: str, default: Any = None) -> Any:
        """
        获取单个配置值
        优先从缓存读取
        """
        # 尝试从缓存读取
        if cls._cache_loaded and key in cls._cache:
            return cls._cache[key]
        
        # 从数据库读取
        config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if config:
            value = cls._parse_value(config.config_value, config.config_type)
            cls._cache[key] = value
            return value
        
        # 返回默认值
        if key in DEFAULT_CONFIGS:
            default_config = DEFAULT_CONFIGS[key]
            return cls._parse_value(default_config["value"], default_config["type"])
        
        return default
    
    @classmethod
    def get_all(cls, db: Session, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有配置
        """
        query = db.query(SystemConfig)
        if category:
            query = query.filter(SystemConfig.category == category)
        
        configs = query.order_by(SystemConfig.category, SystemConfig.config_key).all()
        
        return [
            {
                "id": c.id,
                "key": c.config_key,
                "value": cls._parse_value(c.config_value, c.config_type),
                "raw_value": c.config_value,
                "type": c.config_type,
                "category": c.category,
                "category_label": CONFIG_CATEGORIES.get(c.category, c.category),
                "description": c.description,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in configs
        ]
    
    @classmethod
    def get_by_category(cls, db: Session) -> Dict[str, List[Dict[str, Any]]]:
        """
        按分类获取配置
        """
        configs = cls.get_all(db)
        result = {}
        for config in configs:
            category = config["category"]
            if category not in result:
                result[category] = []
            result[category].append(config)
        return result
    
    @classmethod
    def update(
        cls,
        db: Session,
        key: str,
        value: Any,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新配置值
        """
        config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
        if not config:
            raise ValueError(f"配置项不存在: {key}")
        
        # 记录旧值
        old_value = config.config_value
        
        # 序列化新值
        new_value = cls._serialize_value(value, config.config_type)
        
        # 更新
        config.config_value = new_value
        config.updated_at = datetime.utcnow()
        config.updated_by = operator_id
        
        # 记录操作日志
        log = OperationLog(
            log_type="SYSTEM",
            action="config_update",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="config",
            target_id=config.id,
            target_name=key,
            ip_address=ip_address,
            old_value=json.dumps({"value": old_value}),
            new_value=json.dumps({"value": new_value}),
            detail=json.dumps({"description": config.description}),
            status="success"
        )
        db.add(log)
        db.commit()
        
        # 更新 ConfigService 内部缓存
        cls._cache[key] = cls._parse_value(new_value, config.config_type)
        
        # [v2.2.1] 同步到 UnifiedCache（PolicyEngine 从这里读取）
        try:
            from ..core.caching import cache
            cache.reload_configs(db)
        except Exception as e:
            logger.warning(f"[ConfigService] UnifiedCache 同步失败: {e}")
        
        logger.info(f"配置已更新: {key} = {new_value} (by {operator_name})")
        
        return {
            "success": True,
            "message": "配置已更新",
            "key": key,
            "value": cls._cache[key]
        }
    
    @classmethod
    def batch_update(
        cls,
        db: Session,
        updates: Dict[str, Any],
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量更新配置
        """
        updated = 0
        errors = []
        
        for key, value in updates.items():
            try:
                cls.update(db, key, value, operator_id, operator_name, ip_address)
                updated += 1
            except Exception as e:
                errors.append({"key": key, "error": str(e)})
        
        return {
            "success": len(errors) == 0,
            "message": f"已更新 {updated} 项配置",
            "updated": updated,
            "errors": errors
        }
    
    @classmethod
    def reset_to_default(
        cls,
        db: Session,
        key: str,
        operator_id: int,
        operator_name: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重置配置为默认值
        """
        if key not in DEFAULT_CONFIGS:
            raise ValueError(f"没有默认值: {key}")
        
        default = DEFAULT_CONFIGS[key]
        return cls.update(db, key, default["value"], operator_id, operator_name, ip_address)
    
    # ==================== 便捷方法 ====================
    
    @classmethod
    def get_password_policy(cls, db: Session) -> Dict[str, Any]:
        """获取密码策略"""
        return {
            "min_length": cls.get(db, "password_min_length", 6),
            "max_length": cls.get(db, "password_max_length", 100),
            "require_digit": cls.get(db, "password_require_digit", False),
            "require_upper": cls.get(db, "password_require_upper", False),
            "require_lower": cls.get(db, "password_require_lower", False),
            "require_special": cls.get(db, "password_require_special", False),
            "expire_days": cls.get(db, "password_expire_days", 0),
        }
    
    @classmethod
    def get_login_policy(cls, db: Session) -> Dict[str, Any]:
        """获取登录策略"""
        return {
            "max_attempts": cls.get(db, "login_max_attempts", 5),
            "lockout_minutes": cls.get(db, "login_lockout_minutes", 30),
            "attempt_reset_minutes": cls.get(db, "login_attempt_reset_minutes", 60),
            "captcha_enabled": cls.get(db, "login_captcha_enabled", False),
            "captcha_threshold": cls.get(db, "login_captcha_threshold", 3),
        }
    
    @classmethod
    def get_session_policy(cls, db: Session) -> Dict[str, Any]:
        """获取会话策略"""
        return {
            "access_token_hours": cls.get(db, "session_access_token_hours", 24),
            "refresh_token_days": cls.get(db, "session_refresh_token_days", 7),
            "max_devices": cls.get(db, "session_max_devices", 3),
            "idle_timeout_minutes": cls.get(db, "session_idle_timeout_minutes", 30),
            "single_device": cls.get(db, "session_single_device", False),
        }
    
    @classmethod
    def validate_password(cls, db: Session, password: str) -> Dict[str, Any]:
        """
        验证密码是否符合策略
        返回: {"valid": bool, "errors": []}
        """
        policy = cls.get_password_policy(db)
        errors = []
        
        if len(password) < policy["min_length"]:
            errors.append(f"密码长度不能少于 {policy['min_length']} 位")
        
        if len(password) > policy["max_length"]:
            errors.append(f"密码长度不能超过 {policy['max_length']} 位")
        
        if policy["require_digit"] and not any(c.isdigit() for c in password):
            errors.append("密码必须包含数字")
        
        if policy["require_upper"] and not any(c.isupper() for c in password):
            errors.append("密码必须包含大写字母")
        
        if policy["require_lower"] and not any(c.islower() for c in password):
            errors.append("密码必须包含小写字母")
        
        if policy["require_special"]:
            special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            if not any(c in special_chars for c in password):
                errors.append("密码必须包含特殊字符")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
