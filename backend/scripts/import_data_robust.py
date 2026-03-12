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
import numpy as np
import logging
import time
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal, test_connection
from app.db_models import Stock, DailyStockData
from app.config import DATA_DIR, FILE_PATTERNS
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


def import_excel_file(file_path: Path, state_manager, progress_callback=None) -> tuple:
    """
    导入单个Excel文件
    
    事务设计：
    - 每个文件独立的数据库会话（事务）
    - 所有数据在一个事务中
    - 成功则commit，失败则rollback
    
    Args:
        file_path: Excel文件路径
        state_manager: 状态管理器
        progress_callback: 进度回调函数 (msg, progress_pct)
    
    Returns:
        (imported_count, skipped_count, success)
    """
    def report_progress(msg: str, pct: int = None):
        """报告进度"""
        if progress_callback:
            progress_callback(msg, pct)
        if msg:
            logger.info(msg)
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
        
        # === 清理旧数据（如果状态是deleted/rolled_back，确保数据库干净） ===
        import_info = state_manager.state["imports"].get(date_str, {})
        # === 清理旧数据（防止主键冲突） ===
        # 无论之前状态如何，都先尝试清理该日期的数据，确保幂等性
        if True:
            from sqlalchemy import func
            old_count = db_session.query(func.count(DailyStockData.id)).filter(
                func.to_char(DailyStockData.date, 'YYYYMMDD') == date_str
            ).scalar()
            
            if old_count > 0:
                logger.info(f"🔄 检测到 {old_count} 条旧数据，正在清理以确保幂等性...")
                db_session.query(DailyStockData).filter(
                    func.to_char(DailyStockData.date, 'YYYYMMDD') == date_str
                ).delete(synchronize_session=False)
                # 必须立即Flush，否则后续插入可能仍报错
                db_session.flush() 
                logger.info(f"✅ 已清理旧数据")
        logger.info(f"📂 正在导入: {filename} (日期: {target_date})")
        
        # 读取Excel文件
        df = pd.read_excel(file_path)
        total_rows = len(df)
        logger.info(f"📊 读取到 {total_rows} 条记录")
        
        # === 智能去重（只去除明显异常的重复）===
        from deduplicate_helper import DataDeduplicator, print_dedup_summary
        
        deduplicator = DataDeduplicator()
        df, dedup_stats = deduplicator.deduplicate_stock_data(df)
        
        # 记录去重信息到JSON
        state_manager.record_dedup_info(date_str, dedup_stats)
        
        # 打印去重摘要
        if dedup_stats.get('removed_count', 0) > 0:
            print_dedup_summary(dedup_stats)
            logger.info(f"📊 去重后剩余 {len(df)} 条记录")
        elif dedup_stats.get('has_duplicates') and dedup_stats.get('removed_count', 0) == 0:
            logger.warning(f"⚠️  检测到重复但未去重（条件不满足），将在后续检查中处理")
        
        # === 数据修补：换手率 ===
        from data_fixer import TurnoverRateFixer
        
        # 初始化换手率修补器（注入state_manager以避免状态竞态）
        turnover_fixer = TurnoverRateFixer(date_str, data_type='stock', state_manager=state_manager)
        fix_config = state_manager.state.get('fix_config', {}).get('turnover_rate_fix', {})
        
        if fix_config.get('enabled', True) and fix_config.get('auto_fix', True):
            logger.info("🔧 开始换手率数据检测...")
            df, fix_info = turnover_fixer.fix_dataframe(df)
            
            if fix_info.get('applied'):
                logger.info(
                    f"✅ 换手率已修补！"
                    f"影响行数={fix_info['affected_rows']}, "
                    f"平均值: {fix_info['avg_before']:.6f} → {fix_info['avg_after']:.4f}"
                )
                # 记录修补信息（暂时保存在内存中，成功导入后再写入状态文件）
                turnover_fix_info = fix_info
            else:
                logger.info("ℹ️  换手率数据正常，无需修补")
                turnover_fix_info = None
        else:
            logger.info("ℹ️  换手率修补已禁用")
            turnover_fix_info = None
        
        # === 检查是否还有重复（严格检查，触发ERROR）===
        # ⚠️ 重要：确保临时列不存在，避免"灯下黑"
        if '代码_normalized' in df.columns:
            df = df.drop(columns=['代码_normalized'])
        
        # 重新标准化检查
        df['代码_normalized'] = df['代码'].apply(normalize_stock_code)
        duplicates = df[df.duplicated(subset=['代码_normalized'], keep=False)]
        
        if not duplicates.empty:
            dup_codes = duplicates['代码_normalized'].unique()
            logger.error(f"❌ Excel文件中存在重复的股票代码（去重后仍存在）: {', '.join(dup_codes)}")
            logger.error(f"   重复记录数: {len(duplicates)}")
            for code in dup_codes:
                dup_rows = df[df['代码_normalized'] == code]
                logger.error(f"   股票 {code} 出现了 {len(dup_rows)} 次，在行: {list(dup_rows.index + 2)}")  # +2因为Excel从1开始且有表头
            
            # 清理临时列
            df = df.drop(columns=['代码_normalized'])
            
            error_msg = f"Excel文件包含重复的股票代码: {', '.join(dup_codes)}"
            state_manager.mark_failed(date_str, error_msg, 0)
            raise ValueError(error_msg)
        
        imported_count = 0
        skipped_count = 0
        
        # === 批量导入（在同一个事务中） ===
        for idx, row in df.iterrows():
            try:
                stock_code = normalize_stock_code(row['代码'])
                stock_name = str(row['名称']).strip()
                # Industry column might be missing in new data (2026-01-20+)
                if '行业' in row and pd.notna(row['行业']):
                    industry = str(row['行业']).strip()
                else:
                    industry = None
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
                        # 处理空值和无穷大值
                        if pd.isna(value):
                            value = None
                        elif isinstance(value, (int, float)) and np.isinf(value):
                            logger.warning(f"⚠️  股票 {stock_code} 的 {excel_col} 字段包含无穷大值，设为None")
                            value = None
                        setattr(daily_data, db_col, value)
                
                db_session.add(daily_data)
                imported_count += 1
                
                # 每1000条显示进度（但不提交）
                if imported_count % 1000 == 0:
                    pct = int(imported_count / total_rows * 100)
                    report_progress(f"  进度: {imported_count}/{total_rows} ({pct}%)", pct)
                
            except IntegrityError as e:
                # 唯一索引冲突：数据库中已存在该日期数据
                # 这说明状态文件和数据库不一致，需要手动清理
                db_session.rollback()
                error_msg = f"数据库中已存在 {stock_code} - {target_date}，请先删除该日期数据"
                logger.error(f"❌ {error_msg}")
                logger.error(f"   提示：运行 python update_daily_data.py delete --dates {date_str}")
                state_manager.mark_failed(date_str, error_msg, imported_count)
                raise Exception(error_msg) from e
            
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
        
        # 记录修补信息到状态文件
        if turnover_fix_info and turnover_fix_info.get('applied'):
            turnover_fixer.record_fix_to_state(turnover_fix_info)
        
        return imported_count, skipped_count, True
        
    except IntegrityError as e:
        # === 唯一性约束冲突 (Commit Stage Capture) ===
        db_session.rollback()
        error_msg = f"唯一性约束冲突 (Commit Stage): {str(e.orig) if hasattr(e, 'orig') else str(e)}"
        logger.error(f"❌ {error_msg}")
        
        # 标记为 rolled_back 并归类原因
        state_manager.mark_rolled_back(date_str, f"Duplicate Key Violation: {error_msg}")
        
        return 0, 0, False

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
    """获取所有待导入的Excel文件（支持多种模式）"""
    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        logger.error(f"数据目录不存在: {data_dir}")
        return []
    
    # 扫描所有模式的文件
    all_files = []
    for pattern in FILE_PATTERNS:
        files = list(data_dir.glob(pattern))
        all_files.extend(files)
        logger.info(f"模式 '{pattern}': 找到 {len(files)} 个文件")
    
    # 去重并排序
    unique_files = sorted(set(all_files))
    logger.info(f"总计: {len(unique_files)} 个数据文件")
    return unique_files


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
    
    # === 收敛超时任务 (Option A Requirement) ===
    converged_count = state_manager.converge_in_progress_tasks(timeout_minutes=60)
    if converged_count > 0:
        logger.info(f"🔄 已自动回滚 {converged_count} 个超时/未完成的任务")
    
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
