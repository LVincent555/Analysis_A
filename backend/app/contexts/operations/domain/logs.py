"""Operation log domain vocabulary."""

LOG_TYPES = {
    "LOGIN": "登录日志",
    "USER": "用户操作",
    "SESSION": "会话操作",
    "SECURITY": "安全事件",
    "SYSTEM": "系统操作",
}

LOG_ACTIONS = {
    "login_success": "登录成功",
    "login_failed": "登录失败",
    "logout": "登出",
    "token_refresh": "刷新令牌",
    "session_expired": "会话过期",
    "user_create": "创建用户",
    "user_update": "更新用户",
    "user_delete": "删除用户",
    "user_enable": "启用用户",
    "user_disable": "禁用用户",
    "password_reset": "重置密码",
    "password_change": "修改密码",
    "user_unlock": "解锁用户",
    "session_revoke": "撤销会话",
    "session_revoke_all": "撤销所有会话",
    "account_locked": "账户锁定",
    "account_unlocked": "账户解锁",
    "suspicious_login": "可疑登录",
    "config_update": "更新配置",
    "role_create": "创建角色",
    "role_update": "更新角色",
    "role_delete": "删除角色",
    "role_assign": "分配角色",
    "role_remove": "移除角色",
}

SYSTEM_OPERATOR_NAME = "系统"


def log_type_label(log_type: str) -> str:
    return LOG_TYPES.get(log_type, log_type)


def action_label(action: str) -> str:
    return LOG_ACTIONS.get(action, action)


def status_label(status: str | None) -> str:
    return "成功" if status == "success" else "失败"
