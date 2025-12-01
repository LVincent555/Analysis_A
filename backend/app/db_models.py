"""
SQLAlchemy ORM 数据库模型
对应 version1.sql 的表结构
"""
from sqlalchemy import Column, String, Integer, BigInteger, Date, DECIMAL, TIMESTAMP, ForeignKey, Index, Boolean, Text
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
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="密码哈希(bcrypt)")
    user_key_encrypted = Column(Text, nullable=False, comment="用户密钥(主密钥加密)")
    
    # 用户信息
    role = Column(String(20), default='user', comment="角色: admin/user")
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 时间戳
    created_at = Column(TIMESTAMP, default=datetime.utcnow, comment="创建时间")
    last_login = Column(TIMESTAMP, nullable=True, comment="最后登录时间")
    
    # 设备和离线配置
    allowed_devices = Column(Integer, default=3, comment="允许同时登录设备数")
    offline_enabled = Column(Boolean, default=True, comment="是否允许离线使用")
    offline_days = Column(Integer, default=7, comment="离线数据保留天数")
    
    # 关系
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
    
    def to_dict(self):
        """转换为字典（不包含敏感信息）"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "offline_enabled": self.offline_enabled,
            "offline_days": self.offline_days
        }


class UserSession(Base):
    """
    用户会话表
    管理多设备登录和会话密钥
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
    
    # 关系
    user = relationship("User", back_populates="sessions")
    
    # 唯一约束：同一用户同一设备只能有一个会话
    __table_args__ = (
        Index('idx_user_device_unique', 'user_id', 'device_id', unique=True),
    )
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, device={self.device_id})>"
