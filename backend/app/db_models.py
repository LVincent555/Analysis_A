"""
SQLAlchemy ORM 数据库模型
对应 version1.sql 的表结构
"""
from sqlalchemy import Column, String, Integer, BigInteger, Date, DECIMAL, TIMESTAMP, ForeignKey, Index
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
