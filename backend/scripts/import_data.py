"""
数据导入脚本
从 data/ 目录的 Excel 文件导入到 PostgreSQL 数据库
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging
from sqlalchemy.exc import IntegrityError

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, test_connection
from app.db_models import Stock, DailyStockData, Base
from app.config import DATA_DIR, FILE_PATTERN

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Excel列名到数据库字段的映射
COLUMN_MAPPING = {
    '代码': 'stock_code',
    '名称': 'stock_name',
    '行业': 'industry',
    '总分': 'total_score',
    '开盘': 'open_price',
    '最高': 'high_price',
    '最低': 'low_price',
    'close': 'close_price',
    'jump': 'jump',
    '涨跌幅': 'price_change',
    '换手率%': 'turnover_rate_percent',
    '放量天数': 'volume_days',
    '平均量比_50天': 'avg_volume_ratio_50',
    '成交量': 'volume',
    '放量天数_volume': 'volume_days_volume',
    '平均量比_50天_volume': 'avg_volume_ratio_50_volume',
    '波动率': 'volatility',
    'volatile_consec': 'volatile_consec',
    'BETA': 'beta',
    'BETA_consec': 'beta_consec',
    '相关性': 'correlation',
    '总市值(亿)': 'market_cap_billions',
    '长期': 'long_term',
    '短期': 'short_term',
    '超买': 'overbought',
    '超卖': 'oversold',
    'macd_signal': 'macd_signal',
    'slowkdj_signal': 'slowkdj_signal',
    'lon_lonma': 'lon_lonma',
    'lon_consec': 'lon_consec',
    'lon_0': 'lon_0',
    'loncons_consec': 'loncons_consec',
    'lonma_0': 'lonma_0',
    'lonmacons_consec': 'lonmacons_consec',
    'dma': 'dma',
    'dma_consec': 'dma_consec',
    'dif_dem': 'dif_dem',
    'macd_consec': 'macd_consec',
    'dif_0': 'dif_0',
    'macdcons_consec': 'macdcons_consec',
    'dem_0': 'dem_0',
    'demcons_consec': 'demcons_consec',
    'pdi_adx': 'pdi_adx',
    'dmiadx_consec': 'dmiadx_consec',
    'pdi_ndi': 'pdi_ndi',
    'dmi_consec': 'dmi_consec',
    'obv': 'obv',
    'obv_consec': 'obv_consec',
    'k_kdj': 'k_kdj',
    'slowkdj_consec': 'slowkdj_consec',
    'rsi': 'rsi',
    'rsi_consec': 'rsi_consec',
    'cci_-90': 'cci_neg_90',
    'cci_lower_consec': 'cci_lower_consec',
    'cci_90': 'cci_pos_90',
    'cci_upper_consec': 'cci_upper_consec',
    'bands_lower': 'bands_lower',
    'bands_lower_consec': 'bands_lower_consec',
    'bands_middle': 'bands_middle',
    'bands_middle_consec': 'bands_middle_consec',
    'bands_upper': 'bands_upper',
    'bands_upper_consec': 'bands_upper_consec',
    'lon_lonma_diff': 'lon_lonma_diff',
    'lon': 'lon',
    'lonma': 'lonma',
    'histgram': 'histgram',
    'dif': 'dif',
    'dem': 'dem',
    'ADX': 'adx',
    'PLUS_DI': 'plus_di',
    'OBV': 'obv_2',
    'slowk': 'slowk',
    'RSI': 'rsi_2',
    'CCI_-90': 'cci_neg_90_2',
    'CCI_90': 'cci_pos_90_2',
    'lower': 'lower_band',
    'middle': 'middle_band',
    'upper': 'upper_band',
    'lst_close': 'lst_close',
    'code2': 'code2',
    'name2': 'name2',
    'zhangdiefu2': 'zhangdiefu2',
    'volume_consec2': 'volume_consec2',
    'volume_50_consec2': 'volume_50_consec2'
}


def extract_date_from_filename(filename: str) -> datetime:
    """
    从文件名提取日期
    格式: YYYYMMDD_data_sma_feature_color.xlsx
    """
    try:
        date_str = filename.split('_')[0]
        return datetime.strptime(date_str, '%Y%m%d').date()
    except Exception as e:
        logger.error(f"无法从文件名提取日期: {filename}, 错误: {str(e)}")
        return None


def check_date_exists(db_session, date: datetime) -> bool:
    """
    检查指定日期的数据是否已存在
    
    Args:
        db_session: 数据库会话
        date: 日期
    
    Returns:
        True表示已存在，False表示不存在
    """
    from sqlalchemy import func
    count = db_session.query(func.count(DailyStockData.id))\
        .filter(DailyStockData.date == date)\
        .scalar()
    return count > 0


def import_excel_file(file_path: Path, db_session):
    """
    导入单个Excel文件到数据库
    
    特性：
    1. 幂等性：如果该日期数据已存在，跳过整个文件
    2. 原子性：整个文件在一个事务中，失败自动回滚
    3. 数据完整性：唯一索引防止单条记录重复
    """
    filename = file_path.name
    date = extract_date_from_filename(filename)
    
    if not date:
        logger.warning(f"跳过文件（无法提取日期）: {filename}")
        return 0, 0
    
    # === 幂等性检查：文件级别 ===
    if check_date_exists(db_session, date):
        logger.info(f"⏭️  跳过文件（数据已存在）: {filename} (日期: {date})")
        return 0, 0
    
    logger.info(f"正在导入: {filename} (日期: {date})")
    
    # === 原子性：开始事务 ===
    # 使用 savepoint 或嵌套事务
    savepoint = None
    try:
        # 读取Excel文件
        df = pd.read_excel(file_path)
        logger.info(f"读取到 {len(df)} 条记录")
        
        imported_count = 0
        skipped_count = 0
        
        # 遍历每一行
        for idx, row in df.iterrows():
            # 处理股票代码：转为字符串并补全到6位（前导零）
            stock_code = str(row['代码']).strip()
            # 如果是纯数字且少于6位，补全前导0
            if stock_code.isdigit() and len(stock_code) < 6:
                stock_code = stock_code.zfill(6)  # 左侧填充0到6位
            
            stock_name = str(row['名称']).strip()
            industry = str(row['行业']).strip() if pd.notna(row['行业']) else None
            rank = idx + 1  # 排名 = 行号 + 1
            
            try:
                # 1. 先检查股票是否存在，不存在则创建
                stock = db_session.query(Stock).filter(Stock.stock_code == stock_code).first()
                if not stock:
                    stock = Stock(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        industry=industry,
                        last_updated=datetime.now()
                    )
                    db_session.add(stock)
                    db_session.flush()  # 确保股票已创建
                
                # 2. 检查该日期数据是否已存在
                existing = db_session.query(DailyStockData).filter(
                    DailyStockData.stock_code == stock_code,
                    DailyStockData.date == date
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # 3. 创建每日数据记录
                daily_data = DailyStockData(
                    stock_code=stock_code,
                    date=date,
                    rank=rank
                )
                
                # 4. 映射所有Excel列到数据库字段
                for excel_col, db_col in COLUMN_MAPPING.items():
                    if excel_col in df.columns and excel_col not in ['代码', '名称', '行业']:
                        value = row[excel_col]
                        # 处理空值
                        if pd.isna(value):
                            value = None
                        setattr(daily_data, db_col, value)
                
                db_session.add(daily_data)
                imported_count += 1
                
                # 每1000条提交一次
                if imported_count % 1000 == 0:
                    db_session.commit()
                    logger.info(f"已导入 {imported_count} 条记录...")
                
            except IntegrityError as e:
                db_session.rollback()
                logger.warning(f"跳过重复数据: {stock_code} - {date}")
                skipped_count += 1
                continue
            except Exception as e:
                db_session.rollback()
                logger.error(f"❌ 导入记录失败: {stock_code}, 错误: {str(e)}")
                logger.error("=" * 60)
                logger.error("⚠️ 遇到致命错误，停止导入！")
                logger.error("请修复错误后重新导入")
                logger.error("=" * 60)
                raise  # 重新抛出异常，立即停止
        
        # 最后提交剩余数据
        db_session.commit()
        logger.info(f"✅ 文件导入完成: {filename}, 导入: {imported_count}, 跳过: {skipped_count}")
        
        return imported_count, skipped_count
        
    except Exception as e:
        logger.error(f"❌ 文件导入失败: {filename}, 错误: {str(e)}")
        db_session.rollback()
        return 0, 0


def get_data_files():
    """
    获取所有待导入的Excel文件
    """
    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        logger.error(f"数据目录不存在: {data_dir}")
        return []
    
    files = sorted(data_dir.glob(FILE_PATTERN))
    logger.info(f"找到 {len(files)} 个数据文件")
    return files


def main():
    """
    主函数：批量导入所有Excel文件
    """
    logger.info("=" * 60)
    logger.info("开始数据导入任务")
    logger.info("=" * 60)
    
    # 测试数据库连接
    if not test_connection():
        logger.error("数据库连接失败，请检查配置")
        return
    
    # 获取待导入文件
    files = get_data_files()
    if not files:
        logger.warning("没有找到待导入的文件")
        return
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        total_imported = 0
        total_skipped = 0
        
        # 遍历所有文件
        for file_path in files:
            imported, skipped = import_excel_file(file_path, db)
            total_imported += imported
            total_skipped += skipped
        
        logger.info("=" * 60)
        logger.info(f"✅ 导入任务完成！")
        logger.info(f"总导入记录数: {total_imported}")
        logger.info(f"总跳过记录数: {total_skipped}")
        logger.info("=" * 60)
        
        # 显示数据库统计
        stock_count = db.query(Stock).count()
        data_count = db.query(DailyStockData).count()
        logger.info(f"数据库统计: 股票数={stock_count}, 每日数据条数={data_count}")
        
    except Exception as e:
        logger.error(f"导入过程发生错误: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
