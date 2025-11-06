"""
健壮的数据导入脚本
使用状态管理器实现原子性、幂等性和完整的回滚机制

核心特性：
1. 【幂等性】基于状态文件判断是否需要导入
2. 【原子性】整个文件在一个事务中，失败自动回滚
3. 【状态管理】本地JSON文件记录所有导入状态
4. 【文件校验】MD5哈希检测文件变化
5. 【错误恢复】失败后可安全重试
6. 【无侵入性】不修改原始Excel和数据库结构
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging
import time
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal, test_connection
from app.db_models import Stock, DailyStockData
from app.config import DATA_DIR, FILE_PATTERN
from import_state_manager import get_state_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Excel列名到数据库字段的映射
COLUMN_MAPPING = {
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


def extract_date_from_filename(filename: str) -> str:
    """
    从文件名提取日期字符串
    格式: YYYYMMDD_data_sma_feature_color.xlsx
    返回: '20251103'
    """
    try:
        return filename.split('_')[0]
    except Exception as e:
        logger.error(f"无法从文件名提取日期: {filename}, 错误: {str(e)}")
        return None


def normalize_stock_code(code_str: str) -> str:
    """
    规范化股票代码：补全前导零到6位
    """
    code = str(code_str).strip()
    if code.isdigit() and len(code) < 6:
        code = code.zfill(6)
    return code


def import_excel_file(file_path: Path, state_manager) -> tuple:
    """
    导入单个Excel文件
    
    事务设计：
    - 每个文件独立的数据库会话（事务）
    - 所有数据在一个事务中
    - 成功则commit，失败则rollback
    
    Returns:
        (imported_count, skipped_count, success)
    """
    filename = file_path.name
    date_str = extract_date_from_filename(filename)
    
    if not date_str:
        logger.warning(f"⏭️  跳过文件（无法提取日期）: {filename}")
        return 0, 0, False
    
    # === 幂等性检查：基于状态文件 ===
    if not state_manager.should_reimport(date_str, file_path):
        logger.info(f"⏭️  跳过文件（已成功导入）: {filename}")
        import_info = state_manager.get_import_info(date_str)
        return import_info.get('imported_count', 0), 0, True
    
    # 记录开始导入
    state_manager.start_import(date_str, filename, file_path)
    start_time = time.time()
    
    # === 创建独立的数据库会话（事务边界） ===
    db_session = SessionLocal()
    
    try:
        # 转换日期格式
        target_date = datetime.strptime(date_str, '%Y%m%d').date()
        logger.info(f"📂 正在导入: {filename} (日期: {target_date})")
        
        # 读取Excel文件
        df = pd.read_excel(file_path)
        total_rows = len(df)
        logger.info(f"📊 读取到 {total_rows} 条记录")
        
        imported_count = 0
        skipped_count = 0
        
        # === 批量导入（在同一个事务中） ===
        for idx, row in df.iterrows():
            try:
                # 1. 处理股票代码
                stock_code = normalize_stock_code(row['代码'])
                stock_name = str(row['名称']).strip()
                industry = str(row['行业']).strip() if pd.notna(row['行业']) else None
                rank = idx + 1
                
                # 2. 确保股票记录存在
                stock = db_session.query(Stock).filter(
                    Stock.stock_code == stock_code
                ).first()
                
                if not stock:
                    stock = Stock(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        industry=industry,
                        last_updated=datetime.now()
                    )
                    db_session.add(stock)
                    # 不要立即flush，等待整体提交
                
                # 3. 创建每日数据记录
                daily_data = DailyStockData(
                    stock_code=stock_code,
                    date=target_date,
                    rank=rank
                )
                
                # 4. 映射所有Excel列到数据库字段
                for excel_col, db_col in COLUMN_MAPPING.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.isna(value):
                            value = None
                        setattr(daily_data, db_col, value)
                
                db_session.add(daily_data)
                imported_count += 1
                
                # 每1000条显示进度（但不提交）
                if imported_count % 1000 == 0:
                    logger.info(f"  进度: {imported_count}/{total_rows} ({imported_count/total_rows*100:.1f}%)")
                
            except IntegrityError as e:
                # 唯一索引冲突：该股票该日期已存在
                db_session.rollback()
                logger.warning(f"  跳过重复数据: {stock_code} - {target_date}")
                skipped_count += 1
                # 重新开始当前行的小事务
                db_session = SessionLocal()
                continue
            
            except Exception as e:
                # 其他错误：立即回滚并抛出
                db_session.rollback()
                error_msg = f"导入记录失败: {stock_code}, 错误: {str(e)}"
                logger.error(f"❌ {error_msg}")
                state_manager.mark_failed(date_str, error_msg, imported_count)
                raise
        
        # === 关键：整个文件成功后才提交事务 ===
        db_session.commit()
        duration = time.time() - start_time
        
        logger.info(f"✅ 文件导入完成: {filename}")
        logger.info(f"   导入: {imported_count} 条, 跳过: {skipped_count} 条, 耗时: {duration:.1f}秒")
        
        # 更新状态文件
        state_manager.mark_success(date_str, imported_count, skipped_count, duration)
        
        return imported_count, skipped_count, True
        
    except Exception as e:
        # === 任何错误都回滚整个事务 ===
        db_session.rollback()
        error_msg = f"文件导入失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        # 记录回滚状态
        state_manager.mark_rolled_back(date_str, error_msg)
        
        return 0, 0, False
        
    finally:
        db_session.close()


def get_data_files():
    """获取所有待导入的Excel文件"""
    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        logger.error(f"数据目录不存在: {data_dir}")
        return []
    
    files = sorted(data_dir.glob(FILE_PATTERN))
    logger.info(f"找到 {len(files)} 个数据文件")
    return files


def main():
    """主函数：批量导入所有Excel文件"""
    logger.info("=" * 60)
    logger.info("开始数据导入任务（健壮版）")
    logger.info("=" * 60)
    
    # 测试数据库连接
    if not test_connection():
        logger.error("数据库连接失败，请检查配置")
        return
    
    # 获取状态管理器
    state_manager = get_state_manager()
    
    # 获取待导入文件
    files = get_data_files()
    if not files:
        logger.warning("没有找到待导入的文件")
        return
    
    # 统计
    total_imported = 0
    total_skipped = 0
    success_files = 0
    failed_files = 0
    
    # 遍历所有文件
    for file_path in files:
        imported, skipped, success = import_excel_file(file_path, state_manager)
        total_imported += imported
        total_skipped += skipped
        
        if success:
            success_files += 1
        else:
            failed_files += 1
    
    # 打印总结
    logger.info("=" * 60)
    logger.info("✅ 导入任务完成！")
    logger.info(f"文件统计: 成功={success_files}, 失败={failed_files}")
    logger.info(f"数据统计: 导入={total_imported}, 跳过={total_skipped}")
    logger.info("=" * 60)
    
    # 打印状态摘要
    state_manager.print_summary()


if __name__ == "__main__":
    main()
