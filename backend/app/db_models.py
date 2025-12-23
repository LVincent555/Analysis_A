"""
SQLAlchemy ORM 数据库模型
对应 version1.sql 的表结构
"""
from sqlalchemy import Column, String, Integer, BigInteger, Date, DECIMAL, TIMESTAMP, ForeignKey, Index, Boolean, Text, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Stock(Base):
    """
    股票主表
    存储股票基本信息
    """
    __tablename__ = "stocks"
    
    stock_code = Column(String(10), primary_key=True, comment="股票代码")
    stock_name = Column(String(50), nullable=False, comment="股票名称")
    industry = Column(String(100), comment="行业")
    last_updated = Column(TIMESTAMP, comment="最后更新时间")
    
    # 关系：一个股票有多条每日数据
    daily_data = relationship("DailyStockData", back_populates="stock", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Stock(code={self.stock_code}, name={self.stock_name})>"


class DailyStockData(Base):
    """
    每日股票数据表
    存储所有83个技术指标
    """
    __tablename__ = "daily_stock_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关键字段
    stock_code = Column(String(10), ForeignKey("stocks.stock_code", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    
    # Excel数据列（83个字段）- 统一使用 DECIMAL(30, 10)
    total_score = Column(DECIMAL(30, 10))
    open_price = Column(DECIMAL(30, 10))
    high_price = Column(DECIMAL(30, 10))
    low_price = Column(DECIMAL(30, 10))
    close_price = Column(DECIMAL(30, 10))
    jump = Column(DECIMAL(30, 10))
    price_change = Column(DECIMAL(30, 10))
    turnover_rate_percent = Column(DECIMAL(30, 10))
    volume_days = Column(DECIMAL(30, 10))
    avg_volume_ratio_50 = Column(DECIMAL(30, 10))
    volume = Column(BigInteger)
    volume_days_volume = Column(DECIMAL(30, 10))
    avg_volume_ratio_50_volume = Column(DECIMAL(30, 10))
    volatility = Column(DECIMAL(30, 10))
    volatile_consec = Column(Integer)
    beta = Column(DECIMAL(30, 10))
    beta_consec = Column(Integer)
    correlation = Column(DECIMAL(30, 10))
    market_cap_billions = Column(DECIMAL(30, 10))
    long_term = Column(DECIMAL(30, 10))
    short_term = Column(Integer)
    overbought = Column(Integer)
    oversold = Column(Integer)
    macd_signal = Column(DECIMAL(30, 10))
    slowkdj_signal = Column(DECIMAL(30, 10))
    lon_lonma = Column(DECIMAL(30, 10))
    lon_consec = Column(Integer)
    lon_0 = Column(DECIMAL(30, 10))
    loncons_consec = Column(Integer)
    lonma_0 = Column(DECIMAL(30, 10))
    lonmacons_consec = Column(Integer)
    dma = Column(DECIMAL(30, 10))
    dma_consec = Column(Integer)
    dif_dem = Column(DECIMAL(30, 10))
    macd_consec = Column(Integer)
    dif_0 = Column(DECIMAL(30, 10))
    macdcons_consec = Column(Integer)
    dem_0 = Column(DECIMAL(30, 10))
    demcons_consec = Column(Integer)
    pdi_adx = Column(DECIMAL(30, 10))
    dmiadx_consec = Column(Integer)
    pdi_ndi = Column(DECIMAL(30, 10))
    dmi_consec = Column(Integer)
    obv = Column(BigInteger)
    obv_consec = Column(Integer)
    k_kdj = Column(DECIMAL(30, 10))
    slowkdj_consec = Column(Integer)
    rsi = Column(DECIMAL(30, 10))
    rsi_consec = Column(Integer)
    cci_neg_90 = Column(DECIMAL(30, 10))
    cci_lower_consec = Column(Integer)
    cci_pos_90 = Column(DECIMAL(30, 10))
    cci_upper_consec = Column(Integer)
    bands_lower = Column(DECIMAL(30, 10))
    bands_lower_consec = Column(Integer)
    bands_middle = Column(DECIMAL(30, 10))
    bands_middle_consec = Column(Integer)
    bands_upper = Column(DECIMAL(30, 10))
    bands_upper_consec = Column(Integer)
    lon_lonma_diff = Column(DECIMAL(30, 10))
    lon = Column(DECIMAL(30, 10))
    lonma = Column(DECIMAL(30, 10))
    histgram = Column(DECIMAL(30, 10))
    dif = Column(DECIMAL(30, 10))
    dem = Column(DECIMAL(30, 10))
    adx = Column(DECIMAL(30, 10))
    plus_di = Column(DECIMAL(30, 10))
    obv_2 = Column(BigInteger)
    slowk = Column(DECIMAL(30, 10))
    rsi_2 = Column(DECIMAL(30, 10))
    cci_neg_90_2 = Column(DECIMAL(30, 10))
    cci_pos_90_2 = Column(DECIMAL(30, 10))
    lower_band = Column(DECIMAL(30, 10))
    middle_band = Column(DECIMAL(30, 10))
    upper_band = Column(DECIMAL(30, 10))
    lst_close = Column(DECIMAL(30, 10))
    code2 = Column(String(20))
    name2 = Column(String(50))
    zhangdiefu2 = Column(DECIMAL(30, 10))
    volume_consec2 = Column(DECIMAL(30, 10))
    volume_50_consec2 = Column(DECIMAL(30, 10))
    
    # 关系：每条数据属于一个股票
    stock = relationship("Stock", back_populates="daily_data")
    
    # 唯一约束索引（防止重复导入）
    __table_args__ = (
        Index('idx_daily_stock_date_unique', 'stock_code', 'date', unique=True),
        Index('idx_daily_date_rank', 'date', 'rank'),
    )
    
    def __repr__(self):
        return f"<DailyStockData(code={self.stock_code}, date={self.date}, rank={self.rank})>"


class Sector(Base):
    """
    板块主表
    存储板块基本信息
    """
    __tablename__ = "sectors"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自动递增ID")
    sector_name = Column(String(100), nullable=False, unique=True, comment="板块名称")
    
    # 关系：一个板块有多条每日数据
    daily_data = relationship("SectorDailyData", back_populates="sector", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Sector(id={self.id}, name={self.sector_name})>"


class SectorDailyData(Base):
    """
    板块每日数据表
    存储所有技术指标（与个股字段相同，但不包含jump和市值）
    """
    __tablename__ = "daily_sector_data"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 关键字段
    sector_id = Column(BigInteger, ForeignKey("sectors.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    
    # Excel数据列（与个股相同的83个字段，去掉jump和market_cap_billions）
    total_score = Column(DECIMAL(30, 10))
    open_price = Column(DECIMAL(30, 10))
    high_price = Column(DECIMAL(30, 10))
    low_price = Column(DECIMAL(30, 10))
    close_price = Column(DECIMAL(30, 10))
    price_change = Column(DECIMAL(30, 10))
    turnover_rate_percent = Column(DECIMAL(30, 10))
    volume_days = Column(DECIMAL(30, 10))
    avg_volume_ratio_50 = Column(DECIMAL(30, 10))
    volume = Column(BigInteger)
    volume_days_volume = Column(DECIMAL(30, 10))
    avg_volume_ratio_50_volume = Column(DECIMAL(30, 10))
    volatility = Column(DECIMAL(30, 10))
    volatile_consec = Column(Integer)
    beta = Column(DECIMAL(30, 10))
    beta_consec = Column(Integer)
    correlation = Column(DECIMAL(30, 10))
    long_term = Column(DECIMAL(30, 10))
    short_term = Column(Integer)
    overbought = Column(Integer)
    oversold = Column(Integer)
    macd_signal = Column(DECIMAL(30, 10))
    slowkdj_signal = Column(DECIMAL(30, 10))
    lon_lonma = Column(DECIMAL(30, 10))
    lon_consec = Column(Integer)
    lon_0 = Column(DECIMAL(30, 10))
    loncons_consec = Column(Integer)
    lonma_0 = Column(DECIMAL(30, 10))
    lonmacons_consec = Column(Integer)
    dma = Column(DECIMAL(30, 10))
    dma_consec = Column(Integer)
    dif_dem = Column(DECIMAL(30, 10))
    macd_consec = Column(Integer)
    dif_0 = Column(DECIMAL(30, 10))
    macdcons_consec = Column(Integer)
    dem_0 = Column(DECIMAL(30, 10))
    demcons_consec = Column(Integer)
    pdi_adx = Column(DECIMAL(30, 10))
    dmiadx_consec = Column(Integer)
    pdi_ndi = Column(DECIMAL(30, 10))
    dmi_consec = Column(Integer)
    obv = Column(BigInteger)
    obv_consec = Column(Integer)
    k_kdj = Column(DECIMAL(30, 10))
    slowkdj_consec = Column(Integer)
    rsi = Column(DECIMAL(30, 10))
    rsi_consec = Column(Integer)
    cci_neg_90 = Column(DECIMAL(30, 10))
    cci_lower_consec = Column(Integer)
    cci_pos_90 = Column(DECIMAL(30, 10))
    cci_upper_consec = Column(Integer)
    bands_lower = Column(DECIMAL(30, 10))
    bands_lower_consec = Column(Integer)
    bands_middle = Column(DECIMAL(30, 10))
    bands_middle_consec = Column(Integer)
    bands_upper = Column(DECIMAL(30, 10))
    bands_upper_consec = Column(Integer)
    lon_lonma_diff = Column(DECIMAL(30, 10))
    lon = Column(DECIMAL(30, 10))
    lonma = Column(DECIMAL(30, 10))
    histgram = Column(DECIMAL(30, 10))
    dif = Column(DECIMAL(30, 10))
    dem = Column(DECIMAL(30, 10))
    adx = Column(DECIMAL(30, 10))
    plus_di = Column(DECIMAL(30, 10))
    obv_2 = Column(BigInteger)
    slowk = Column(DECIMAL(30, 10))
    rsi_2 = Column(DECIMAL(30, 10))
    cci_neg_90_2 = Column(DECIMAL(30, 10))
    cci_pos_90_2 = Column(DECIMAL(30, 10))
    lower_band = Column(DECIMAL(30, 10))
    middle_band = Column(DECIMAL(30, 10))
    upper_band = Column(DECIMAL(30, 10))
    lst_close = Column(DECIMAL(30, 10))
    code2 = Column(String(20))
    name2 = Column(String(50))
    zhangdiefu2 = Column(DECIMAL(30, 10))
    volume_consec2 = Column(DECIMAL(30, 10))
    volume_50_consec2 = Column(DECIMAL(30, 10))
    
    # 关系：每条数据属于一个板块
    sector = relationship("Sector", back_populates="daily_data")
    
    # 唯一约束索引（防止重复导入）
    __table_args__ = (
        Index('idx_daily_sector_date_unique', 'sector_id', 'date', unique=True),
        Index('idx_daily_sector_date_rank', 'date', 'rank'),
    )
    
    def __repr__(self):
        return f"<SectorDailyData(sector_id={self.sector_id}, date={self.date}, rank={self.rank})>"


class User(Base):
    """
    用户表
    存储用户认证信息和配置
    v1.1.0: 新增用户信息、登录安全、审计字段
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希(bcrypt)")
    user_key_encrypted = Column(Text, nullable=False, comment="用户密钥(主密钥加密)")
    
    # 用户信息（v1.1.0 新增）
    email = Column(String(255), nullable=True, comment="邮箱")
    phone = Column(String(20), nullable=True, comment="手机号")
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    remark = Column(Text, nullable=True, comment="备注")
    
    # 角色和状态
    role = Column(String(20), default='user', comment="角色: admin/user")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 时间戳
    created_at = Column(TIMESTAMP, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_login = Column(TIMESTAMP, nullable=True, comment="最后登录时间")
    
    # 账号有效期（v1.1.0 新增）
    expires_at = Column(TIMESTAMP, nullable=True, comment="账号过期时间")
    
    # 登录安全（v1.1.0 新增）
    failed_attempts = Column(Integer, default=0, comment="登录失败次数")
    locked_until = Column(TIMESTAMP, nullable=True, comment="锁定截止时间")
    password_changed_at = Column(TIMESTAMP, nullable=True, comment="密码修改时间")
    
    # 设备和离线配置
    allowed_devices = Column(Integer, default=3, comment="允许同时登录设备数")
    offline_enabled = Column(Boolean, default=True, comment="是否允许离线使用")
    offline_days = Column(Integer, default=7, comment="离线数据保留天数")
    
    # 审计字段（v1.1.0 新增）
    created_by = Column(Integer, nullable=True, comment="创建者ID")
    deleted_at = Column(TIMESTAMP, nullable=True, comment="删除时间(软删除)")
    
    # 强制下线用（v1.1.0 新增）
    token_version = Column(Integer, default=1, comment="Token版本号")
    
    # 关系
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
    
    def get_status(self) -> str:
        """获取用户状态"""
        if self.deleted_at:
            return "deleted"
        if not self.is_active:
            return "inactive"
        if self.locked_until and self.locked_until > datetime.utcnow():
            return "locked"
        if self.expires_at and self.expires_at < datetime.utcnow():
            return "expired"
        return "active"
    
    def to_dict(self, include_sessions: bool = False):
        """转换为字典（不包含敏感信息）"""
        result = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "nickname": self.nickname,
            "avatar_url": self.avatar_url,
            "remark": self.remark,
            "role": self.role,
            "status": self.get_status(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "allowed_devices": self.allowed_devices,
            "offline_enabled": self.offline_enabled,
            "offline_days": self.offline_days,
            "failed_attempts": self.failed_attempts,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
        }
        if include_sessions:
            result["active_sessions"] = len([s for s in self.sessions if not s.is_revoked])
        return result
    
    def to_dict_simple(self):
        """简化版字典（用于列表展示）"""
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "role": self.role,
            "status": self.get_status(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class UserSession(Base):
    """
    用户会话表
    管理多设备登录和会话密钥
    v1.1.0: 新增设备详情、状态、撤销字段
    """
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(100), nullable=False, comment="设备唯一标识")
    device_name = Column(String(100), nullable=True, comment="设备名称")
    
    # 会话信息
    session_key_encrypted = Column(Text, nullable=False, comment="会话密钥(用户密钥加密)")
    refresh_token = Column(String(500), nullable=True, comment="刷新令牌")
    
    # 时间
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP, nullable=False, comment="过期时间")
    last_active = Column(TIMESTAMP, default=datetime.utcnow, comment="最后活跃时间")
    
    # 设备详情（v1.1.0 新增）
    ip_address = Column(String(45), nullable=True, comment="登录IP")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    platform = Column(String(50), nullable=True, comment="平台(win32/darwin/linux)")
    app_version = Column(String(20), nullable=True, comment="客户端版本")
    location = Column(String(100), nullable=True, comment="地理位置")
    
    # 状态（v1.1.0 新增）
    current_status = Column(String(20), default='online', comment="当前状态")
    
    # 撤销/强制下线（v1.1.0 新增）
    is_revoked = Column(Boolean, default=False, comment="是否被撤销")
    revoked_at = Column(TIMESTAMP, nullable=True, comment="撤销时间")
    revoked_by = Column(Integer, nullable=True, comment="撤销操作者ID")
    
    # 关系
    user = relationship("User", back_populates="sessions")
    
    # 唯一约束：同一用户同一设备只能有一个会话
    __table_args__ = (
        Index('idx_user_device_unique', 'user_id', 'device_id', unique=True),
    )
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, device={self.device_id})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "ip_address": self.ip_address,
            "platform": self.platform,
            "app_version": self.app_version,
            "location": self.location,
            "current_status": self.current_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "is_revoked": self.is_revoked,
        }


class OperationLog(Base):
    """
    操作日志表
    记录所有关键操作（v1.1.0 新增）
    """
    __tablename__ = "operation_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(20), nullable=False, comment="日志类型: LOGIN/USER/SESSION/SECURITY/SYSTEM")
    action = Column(String(50), nullable=False, comment="具体动作")
    
    # 操作者
    operator_id = Column(Integer, nullable=True, comment="操作者ID(null=系统)")
    operator_name = Column(String(50), nullable=True, comment="操作者用户名")
    
    # 目标
    target_type = Column(String(20), nullable=True, comment="目标类型: user/session/config")
    target_id = Column(Integer, nullable=True, comment="目标ID")
    target_name = Column(String(100), nullable=True, comment="目标名称")
    
    # 请求信息
    ip_address = Column(String(45), nullable=True, comment="操作IP")
    user_agent = Column(String(500), nullable=True, comment="User-Agent")
    
    # 详情
    detail = Column(Text, nullable=True, comment="详细信息(JSON)")
    old_value = Column(Text, nullable=True, comment="修改前的值(JSON)")
    new_value = Column(Text, nullable=True, comment="修改后的值(JSON)")
    
    # 状态
    status = Column(String(20), default='success', comment="状态: success/failed")
    error_message = Column(Text, nullable=True, comment="错误信息")
    
    # 时间
    created_at = Column(TIMESTAMP, default=datetime.utcnow, comment="创建时间")
    
    def __repr__(self):
        return f"<OperationLog(id={self.id}, type={self.log_type}, action={self.action})>"
    
    def to_dict(self):
        """转换为字典"""
        import json
        return {
            "id": self.id,
            "log_type": self.log_type,
            "action": self.action,
            "operator_id": self.operator_id,
            "operator_name": self.operator_name,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "ip_address": self.ip_address,
            "detail": json.loads(self.detail) if self.detail else None,
            "old_value": json.loads(self.old_value) if self.old_value else None,
            "new_value": json.loads(self.new_value) if self.new_value else None,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemConfig(Base):
    """
    系统配置表
    存储可配置的系统参数（v1.1.0 新增）
    """
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    config_type = Column(String(20), default='string', comment="值类型: string/int/bool/json")
    category = Column(String(50), nullable=False, comment="分类: password/login/session/system")
    description = Column(String(255), nullable=True, comment="描述")
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    updated_by = Column(Integer, nullable=True, comment="更新者ID")
    
    def __repr__(self):
        return f"<SystemConfig(key={self.config_key}, value={self.config_value})>"
    
    def get_value(self):
        """获取类型转换后的值"""
        if self.config_type == 'int':
            return int(self.config_value)
        elif self.config_type == 'bool':
            return self.config_value.lower() == 'true'
        elif self.config_type == 'json':
            import json
            return json.loads(self.config_value)
        return self.config_value


# 用户角色关联表（多对多）
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', TIMESTAMP, default=datetime.utcnow)
)


class Role(Base):
    """
    角色表
    定义系统角色和权限（v1.1.0 新增）
    """
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="角色代码")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(String(255), nullable=True, comment="描述")
    permissions = Column(Text, nullable=False, default='[]', comment="权限列表(JSON)")
    is_system = Column(Boolean, default=False, comment="是否系统预设")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    users = relationship("User", secondary=user_roles, back_populates="roles")
    
    def __repr__(self):
        return f"<Role(name={self.name}, display_name={self.display_name})>"
    
    def get_permissions(self):
        """获取权限列表"""
        import json
        try:
            return json.loads(self.permissions) if isinstance(self.permissions, str) else self.permissions
        except:
            return []
    
    def has_permission(self, permission: str) -> bool:
        """检查是否有指定权限"""
        perms = self.get_permissions()
        if "*" in perms:
            return True
        if permission in perms:
            return True
        # 检查通配符权限，如 user:* 匹配 user:create
        prefix = permission.split(":")[0] + ":*"
        return prefix in perms
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "permissions": self.get_permissions(),
            "is_system": self.is_system,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
