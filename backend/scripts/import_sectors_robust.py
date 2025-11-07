"""
板块数据健壮导入脚本
使用状态管理器实现原子性、幂等性和完整的回滚机制

核心特性：
1. 【幂等性】基于状态文件判断是否需要导入
2. 【原子性】整个文件在一个事务中，失败自动回滚
3. 【状态管理】本地JSON文件记录所有导入状态
4. 【文件校验】MD5哈希检测文件变化
5. 【错误恢复】失败后可安全重试
6. 【无侵入性】不修改原始Excel和数据库结构

与股票导入的区别：
- 使用 Sector 和 SectorDailyData 模型
- 板块名称（代码列）作为唯一标识
- 不包含 jump 和 市值 字段
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
from app.db_models import Sector, SectorDailyData
from app.config import DATA_DIR
from import_state_manager import ImportStateManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Excel列名到数据库字段的映射（板块数据不包含jump和市值）
SECTOR_COLUMN_MAPPING = {
    '总分': 'total_score',
    '开盘': 'open_price',
    '最高': 'high_price',
    '最低': 'low_price',
    'close': 'close_price',
    # 注意：板块数据没有 'jump' 和 '总市值(亿)'
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
    格式: YYYYMMDD_allbk_sma_feature_color.xlsx
    返回: '20251105'
    """
    try:
        return filename.split('_')[0]
    except Exception as e:
        logger.error(f"无法从文件名提取日期: {filename}, 错误: {str(e)}")
        return None


def import_sector_excel_file(file_path: Path, state_manager: ImportStateManager) -> tuple:
    """
    导入单个板块Excel文件
    
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
        logger.warning(f"[跳过] 文件（无法提取日期）: {filename}")
        return 0, 0, False
    
    # === 幂等性检查：基于状态文件 ===
    if not state_manager.should_reimport(date_str, file_path):
        logger.info(f"[跳过] 文件（已成功导入）: {filename}")
        # 文件已导入，计入跳过统计（导入=0，跳过=1）
        return 0, 1, True
    
    # 记录开始导入
    state_manager.start_import(date_str, filename, file_path)
    start_time = time.time()
    
    # === 创建独立的数据库会话（事务边界） ===
    db_session = SessionLocal()
    
    try:
        # 转换日期格式
        target_date = datetime.strptime(date_str, '%Y%m%d').date()
        logger.info(f"📂 正在导入板块数据: {filename} (日期: {target_date})")
        
        # 读取Excel文件
        df = pd.read_excel(file_path)
        total_rows = len(df)
        logger.info(f"📊 读取到 {total_rows} 个板块记录")
        
        # === 检查重复的板块名称 ===
        df['代码_stripped'] = df['代码'].astype(str).str.strip()
        duplicates = df[df.duplicated(subset=['代码_stripped'], keep=False)]
        if not duplicates.empty:
            dup_names = duplicates['代码_stripped'].unique()
            logger.error(f"❌ Excel文件中存在重复的板块名称: {', '.join(dup_names)}")
            logger.error(f"   重复记录数: {len(duplicates)}")
            for name in dup_names:
                dup_rows = df[df['代码_stripped'] == name]
                logger.error(f"   板块 {name} 出现了 {len(dup_rows)} 次，在行: {list(dup_rows.index + 2)}")  # +2因为Excel从1开始且有表头
            
            error_msg = f"Excel文件包含重复的板块名称: {', '.join(dup_names)}"
            state_manager.mark_failed(date_str, error_msg, 0)
            raise ValueError(error_msg)
        
        imported_count = 0
        skipped_count = 0
        
        # === 批量导入（在同一个事务中） ===
        for idx, row in df.iterrows():
            try:
                # 1. 处理板块名称（从"代码"列获取）
                sector_name = str(row['代码']).strip()
                
                # 跳过无效数据
                if not sector_name or sector_name == 'nan':
                    logger.warning(f"  跳过无效板块名称: 行 {idx + 1}")
                    skipped_count += 1
                    continue
                
                rank = idx + 1
                
                # 2. 确保板块记录存在（如果不存在则创建）
                sector = db_session.query(Sector).filter(
                    Sector.sector_name == sector_name
                ).first()
                
                if not sector:
                    sector = Sector(sector_name=sector_name)
                    db_session.add(sector)
                    db_session.flush()  # 立即获取 sector.id
                
                # 3. 创建每日数据记录
                daily_data = SectorDailyData(
                    sector_id=sector.id,
                    date=target_date,
                    rank=rank
                )
                
                # 4. 映射所有Excel列到数据库字段
                for excel_col, db_col in SECTOR_COLUMN_MAPPING.items():
                    if excel_col in df.columns:
                        value = row[excel_col]
                        if pd.isna(value):
                            value = None
                        setattr(daily_data, db_col, value)
                
                db_session.add(daily_data)
                imported_count += 1
                
                # 每100条显示进度（但不提交）
                if imported_count % 100 == 0:
                    logger.info(f"  进度: {imported_count}/{total_rows} ({imported_count/total_rows*100:.1f}%)")
                
            except IntegrityError as e:
                # 唯一索引冲突：该板块该日期已存在
                db_session.rollback()
                logger.warning(f"  跳过重复数据: {sector_name} - {target_date}")
                skipped_count += 1
                # 重新开始当前行的小事务
                db_session = SessionLocal()
                continue
            
            except Exception as e:
                # 其他错误：立即回滚并抛出
                db_session.rollback()
                error_msg = f"导入记录失败: {sector_name}, 错误: {str(e)}"
                logger.error(f"❌ {error_msg}")
                state_manager.mark_failed(date_str, error_msg, imported_count)
                raise
        
        # === 关键：整个文件成功后才提交事务 ===
        db_session.commit()
        duration = time.time() - start_time
        
        logger.info(f"[完成] 文件导入完成: {filename}")
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


def get_sector_data_files(sector_data_dir: str):
    """获取所有待导入的板块Excel文件"""
    data_dir = Path(sector_data_dir)
    if not data_dir.exists():
        logger.error(f"板块数据目录不存在: {data_dir}")
        return []
    
    # 扫描所有板块数据文件（格式：YYYYMMDD_allbk_sma_feature_color.xlsx）
    pattern = "*_allbk_sma_feature_color.xlsx"
    files = list(data_dir.glob(pattern))
    
    logger.info(f"找到 {len(files)} 个板块数据文件")
    return sorted(files)


def main():
    """主函数：批量导入所有板块Excel文件"""
    logger.info("=" * 60)
    logger.info("开始板块数据导入任务（健壮版）")
    logger.info("=" * 60)
    
    # 测试数据库连接
    if not test_connection():
        logger.error("数据库连接失败，请检查配置")
        return
    
    # 获取状态管理器（板块专用状态文件）
    state_manager = ImportStateManager(state_file="sector_import_state.json")
    
    # 获取板块数据目录（假设与股票数据在同一目录）
    sector_data_dir = DATA_DIR
    
    # 获取待导入文件
    files = get_sector_data_files(sector_data_dir)
    if not files:
        logger.warning("没有找到待导入的板块数据文件")
        logger.info("提示：板块数据文件格式应为 YYYYMMDD_allbk_sma_feature_color.xlsx")
        return
    
    # 统计
    total_imported = 0
    total_skipped = 0
    success_files = 0
    failed_files = 0
    
    # 遍历所有文件
    for file_path in files:
        imported, skipped, success = import_sector_excel_file(file_path, state_manager)
        total_imported += imported
        total_skipped += skipped
        
        if success:
            success_files += 1
        else:
            failed_files += 1
    
    # 打印总结
    logger.info("=" * 60)
    logger.info("[成功] 板块数据导入任务完成！")
    logger.info(f"文件统计: 成功={success_files}, 失败={failed_files}")
    logger.info(f"数据统计: 导入={total_imported}, 跳过={total_skipped}")
    logger.info("=" * 60)
    
    # 打印状态摘要
    state_manager.print_summary()


if __name__ == "__main__":
    main()
