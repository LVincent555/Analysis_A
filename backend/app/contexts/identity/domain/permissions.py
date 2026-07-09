"""Identity permission catalog and matching rules."""

ALL_PERMISSIONS = {
    "analysis:hotspot": "最新热点分析",
    "analysis:industry": "行业趋势分析",
    "analysis:rank_jump": "排名跳变",
    "analysis:steady_rise": "稳步上升",
    "analysis:sector": "板块分析",
    "analysis:signal": "信号系统",
    "analysis:*": "所有分析功能",
    "query:stock": "股票查询",
    "query:sector": "板块查询",
    "query:*": "所有查询功能",
    "data:view": "查看数据管理",
    "data:import": "导入数据",
    "data:delete": "删除数据",
    "data:*": "所有数据功能",
    "user:view": "查看用户列表",
    "user:create": "创建用户",
    "user:update": "编辑用户",
    "user:delete": "删除用户",
    "user:reset_password": "重置密码",
    "user:*": "所有用户功能",
    "session:view": "查看会话列表",
    "session:force_logout": "强制下线",
    "session:*": "所有会话功能",
    "log:view": "查看操作日志",
    "log:export": "导出日志",
    "log:*": "所有日志功能",
    "config:view": "查看系统配置",
    "config:update": "修改系统配置",
    "config:*": "所有配置功能",
    "role:view": "查看角色列表",
    "role:create": "创建角色",
    "role:update": "编辑角色",
    "role:delete": "删除角色",
    "role:*": "所有角色功能",
    "*": "所有权限",
}


def permission_matches(granted_permissions: list[str], required_permission: str) -> bool:
    if "*" in granted_permissions:
        return True

    if required_permission in granted_permissions:
        return True

    prefix = required_permission.split(":", maxsplit=1)[0] + ":*"
    return prefix in granted_permissions
