-- ============================================================
-- 系统管理模块 - 升级脚本（从现有表结构升级）
-- 版本: v1.1.0
-- 日期: 2025-12-05
-- 说明: 保留现有数据，仅添加新字段和新表
-- 
-- ⚠️ 重要：执行前请先备份数据库！
-- pg_dump -U postgres -d your_database > backup_before_upgrade.sql
--
-- 适用场景: 从 v0.4.0 或更早版本升级到 v1.1.0
-- ============================================================

-- ============================================================
-- 1. 扩展 Users 表（添加新字段）
-- ============================================================

-- 用户信息扩展
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
ALTER TABLE users ADD COLUMN IF NOT EXISTS remark TEXT;

-- 账号有效期
ALTER TABLE users ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP;

-- 登录安全
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;

-- 审计字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by INT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

-- 强制下线用
ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INT DEFAULT 1;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users(deleted_at);

-- ============================================================
-- 2. 扩展 UserSessions 表（添加新字段）
-- ============================================================

-- 设备详情
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45);
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS user_agent VARCHAR(500);
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS platform VARCHAR(50);
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS app_version VARCHAR(20);
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS location VARCHAR(100);
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS device_info JSONB;

-- 状态
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS current_status VARCHAR(20) DEFAULT 'online';

-- 撤销/强制下线
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT FALSE;
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP;
ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS revoked_by INT;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_sessions_is_revoked ON user_sessions(is_revoked);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON user_sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_current_status ON user_sessions(current_status);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);

-- ============================================================
-- 3. 创建 OperationLogs 表（新表）
-- ============================================================
CREATE TABLE IF NOT EXISTS operation_logs (
    id SERIAL PRIMARY KEY,
    log_type VARCHAR(20) NOT NULL,           -- LOGIN/USER/SESSION/SECURITY/SYSTEM
    action VARCHAR(50) NOT NULL,             -- login_success/user_create/...
    
    operator_id INT,                         -- 操作者ID（null=系统）
    operator_name VARCHAR(50),               -- 操作者用户名
    
    target_type VARCHAR(20),                 -- user/session/config
    target_id INT,
    target_name VARCHAR(100),
    
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    
    detail JSONB,                            -- 详细信息
    old_value JSONB,                         -- 修改前的值（变更审计）
    new_value JSONB,                         -- 修改后的值（变更审计）
    status VARCHAR(20) DEFAULT 'success',    -- success/failed
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- OperationLogs 表索引
CREATE INDEX IF NOT EXISTS idx_logs_log_type ON operation_logs(log_type);
CREATE INDEX IF NOT EXISTS idx_logs_action ON operation_logs(action);
CREATE INDEX IF NOT EXISTS idx_logs_operator_id ON operation_logs(operator_id);
CREATE INDEX IF NOT EXISTS idx_logs_target ON operation_logs(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON operation_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_status ON operation_logs(status);

-- ============================================================
-- 4. 创建 SystemConfigs 表（新表）
-- ============================================================
CREATE TABLE IF NOT EXISTS system_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string',  -- string/int/bool/json
    category VARCHAR(50) NOT NULL,             -- password/login/session/system
    description VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INT
);

-- 初始化默认配置（仅在不存在时插入）
INSERT INTO system_configs (config_key, config_value, config_type, category, description) VALUES
-- 密码策略
('password_min_length', '6', 'int', 'password', '密码最小长度'),
('password_max_length', '100', 'int', 'password', '密码最大长度'),
('password_require_digit', 'false', 'bool', 'password', '要求包含数字'),
('password_require_upper', 'false', 'bool', 'password', '要求包含大写字母'),
('password_require_lower', 'false', 'bool', 'password', '要求包含小写字母'),
('password_require_special', 'false', 'bool', 'password', '要求包含特殊字符'),
('password_expire_days', '0', 'int', 'password', '密码过期天数，0=不过期'),

-- 登录策略
('login_max_attempts', '5', 'int', 'login', '最大失败尝试次数'),
('login_lockout_minutes', '30', 'int', 'login', '锁定时长（分钟）'),
('login_attempt_reset_minutes', '60', 'int', 'login', '失败计数重置时间'),
('login_captcha_enabled', 'false', 'bool', 'login', '启用验证码'),
('login_captcha_threshold', '3', 'int', 'login', '验证码触发次数'),

-- 会话策略
('session_access_token_hours', '24', 'int', 'session', 'Access Token有效期（小时）'),
('session_refresh_token_days', '7', 'int', 'session', 'Refresh Token有效期（天）'),
('session_max_devices', '3', 'int', 'session', '默认最大设备数'),
('session_idle_timeout_minutes', '30', 'int', 'session', '空闲超时（分钟）'),
('session_single_device', 'false', 'bool', 'session', '单设备登录限制')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================
-- 5. 创建 Roles 表（角色）
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,           -- 角色代码 (admin/user/readonly)
    display_name VARCHAR(100) NOT NULL,         -- 显示名称
    description VARCHAR(255),                   -- 描述
    permissions JSONB NOT NULL DEFAULT '[]',    -- 权限列表
    is_system BOOLEAN DEFAULT FALSE,            -- 是否系统预设（不可删除）
    is_active BOOLEAN DEFAULT TRUE,             -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roles 表索引
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_is_active ON roles(is_active);

-- ============================================================
-- 6. 创建 UserRoles 表（用户角色关联，多对多）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- UserRoles 表索引
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);

-- 初始化预设角色
INSERT INTO roles (name, display_name, description, permissions, is_system) VALUES
(
    'super_admin',
    '超级管理员',
    '拥有所有权限，不可删除',
    '["*"]',
    true
),
(
    'admin',
    '管理员',
    '用户管理、系统管理、数据分析',
    '["user:*", "session:*", "log:*", "config:*", "analysis:*", "query:*", "data:view", "data:import"]',
    true
),
(
    'user',
    '普通用户',
    '数据分析功能',
    '["analysis:*", "query:*"]',
    true
),
(
    'readonly',
    '只读用户',
    '仅查看权限',
    '["analysis:hotspot", "analysis:industry", "query:stock"]',
    true
)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    permissions = EXCLUDED.permissions;

-- ============================================================
-- 7. 数据迁移（为现有用户设置默认值）
-- ============================================================

-- 设置现有用户的 updated_at（如果为空）
UPDATE users SET updated_at = created_at WHERE updated_at IS NULL;

-- 设置现有用户的 token_version（如果为空）
UPDATE users SET token_version = 1 WHERE token_version IS NULL;

-- 设置现有用户的 failed_attempts（如果为空）
UPDATE users SET failed_attempts = 0 WHERE failed_attempts IS NULL;

-- 设置现有会话的 current_status（如果为空）
UPDATE user_sessions SET current_status = 'offline' WHERE current_status IS NULL;

-- 设置现有会话的 is_revoked（如果为空）
UPDATE user_sessions SET is_revoked = FALSE WHERE is_revoked IS NULL;

-- ============================================================
-- 8. 为现有用户分配角色（基于 users.role 字段）
-- ============================================================

-- 管理员用户
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.role = 'admin' AND r.name = 'admin'
ON CONFLICT DO NOTHING;

-- 普通用户
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.role = 'user' AND r.name = 'user'
ON CONFLICT DO NOTHING;

-- ============================================================
-- 9. 验证升级结果
-- ============================================================

-- 验证 Users 表新字段
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' 
-- ORDER BY ordinal_position;

-- 验证 UserSessions 表新字段
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'user_sessions' 
-- ORDER BY ordinal_position;

-- 验证新表
-- SELECT COUNT(*) as operation_logs_count FROM operation_logs;
-- SELECT COUNT(*) as system_configs_count FROM system_configs;
-- SELECT COUNT(*) as roles_count FROM roles;
-- SELECT COUNT(*) as user_roles_count FROM user_roles;

-- 验证现有数据完整性
-- SELECT id, username, role, is_active, token_version, failed_attempts FROM users;

-- ============================================================
-- 完成
-- ============================================================
-- 升级完成后，请验证：
-- 1. 现有用户数据是否完整
-- 2. 现有会话是否正常
-- 3. 新表是否创建成功
-- 4. 系统配置是否初始化
-- 5. 角色是否正确分配
SELECT 'Upgrade to v1.1.0 completed successfully' AS status;
