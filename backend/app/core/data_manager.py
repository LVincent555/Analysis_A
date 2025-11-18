"""
数据管理核心模块
负责数据导入、一致性检验、自动更新

在应用启动前自动执行：
1. 数据导入（幂等性）
2. 数据一致性检验
3. 数据库健康检查
"""
import sys
from pathlib import Path
import logging
from typing import Tuple, Dict

# 添加scripts目录到路径
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

from scripts.import_state_manager import get_state_manager, ImportStateManager
from scripts.import_data_robust import get_data_files, import_excel_file
from scripts.import_sectors_robust import get_sector_data_files, import_sector_excel_file
from ..database import SessionLocal, test_connection
from ..db_models import Stock, DailyStockData
from ..config import DATA_DIR
from sqlalchemy import func, text

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器"""
    
    def __init__(self):
        """初始化"""
        self.state_manager = get_state_manager()
    
    def auto_import_data(self) -> Tuple[int, int, int, int, int]:
        """
        自动导入新数据（股票+板块）
        
        Returns:
            (成功文件数, 失败文件数, 总导入记录数, 股票导入数, 板块导入数)
        """
        logger.info("=" * 60)
        logger.info("🔄 检查并导入新数据...")
        logger.info("=" * 60)
        
        # 1. 导入股票数据
        logger.info("📊 检查股票数据...")
        stock_files = get_data_files()
        if not stock_files:
            logger.info("📂 data目录中没有股票数据文件")
        
        success_count = 0
        failed_count = 0
        stock_imported = 0
        sector_imported = 0
        
        for file_path in stock_files:
            imported, skipped, success = import_excel_file(file_path, self.state_manager)
            stock_imported += imported
            
            if success:
                success_count += 1
            else:
                failed_count += 1
        
        # 2. 导入板块数据（允许失败）
        logger.info("📊 检查板块数据...")
        sector_state_manager = ImportStateManager(state_file="sector_import_state.json")
        sector_files = get_sector_data_files(DATA_DIR)
        
        if not sector_files:
            logger.info("📂 data目录中没有板块数据文件")
        
        sector_failed = 0
        for file_path in sector_files:
            try:
                imported, skipped, success = import_sector_excel_file(file_path, sector_state_manager)
                sector_imported += imported
                
                if success:
                    success_count += 1
                else:
                    sector_failed += 1
            except Exception as e:
                logger.warning(f"⚠️  板块数据导入失败（非致命）: {e}")
                sector_failed += 1
        
        # 板块数据失败不计入总失败数（允许只有股票数据）
        if sector_failed > 0:
            logger.warning(f"⚠️  板块数据导入失败 {sector_failed} 个文件（系统仍可正常运行）")
        
        # 3. 汇总结果
        total_imported = stock_imported + sector_imported
        if total_imported > 0:
            logger.info(f"✅ 新导入 {total_imported} 条记录（股票: {stock_imported}, 板块: {sector_imported}）")
        else:
            logger.info("✅ 所有数据已是最新")
        
        return success_count, failed_count, total_imported, stock_imported, sector_imported
    
    def verify_data_consistency(self) -> Dict:
        """
        数据一致性检验
        
        检查项：
        1. 数据库连接
        2. 股票总数
        3. 每日数据总数
        4. 日期连续性
        5. ID序列完整性
        
        Returns:
            检验结果字典
        """
        logger.info("=" * 60)
        logger.info("🔍 数据一致性检验...")
        logger.info("=" * 60)
        
        result = {
            "db_connection": False,
            "stock_count": 0,
            "daily_data_count": 0,
            "date_count": 0,
            "id_sequence_ok": False,
            "issues": []
        }
        
        # 1. 检查数据库连接
        if not test_connection():
            result["issues"].append("❌ 数据库连接失败")
            logger.error("❌ 数据库连接失败")
            return result
        
        result["db_connection"] = True
        logger.info("✅ 数据库连接正常")
        
        db = SessionLocal()
        try:
            # 2. 股票总数
            stock_count = db.query(func.count(Stock.stock_code)).scalar()
            result["stock_count"] = stock_count
            logger.info(f"✅ 股票总数: {stock_count}")
            
            # 3. 每日数据总数
            daily_count = db.query(func.count(DailyStockData.id)).scalar()
            result["daily_data_count"] = daily_count
            logger.info(f"✅ 每日数据记录: {daily_count}")
            
            # 4. 日期数量
            date_count = db.query(func.count(func.distinct(DailyStockData.date))).scalar()
            result["date_count"] = date_count
            logger.info(f"✅ 股票数据日期数: {date_count} 天")
            
            # 5. ID序列检查
            if daily_count > 0:
                min_id_result = db.query(func.min(DailyStockData.id)).scalar()
                max_id_result = db.query(func.max(DailyStockData.id)).scalar()
                
                if min_id_result == 1 and max_id_result == daily_count:
                    result["id_sequence_ok"] = True
                    logger.info(f"✅ 股票ID序列完整: 1 到 {max_id_result}")
                else:
                    result["issues"].append(f"⚠️  股票ID序列异常: {min_id_result} 到 {max_id_result}")
                    logger.warning(f"⚠️  股票ID序列异常")
            
            # 6. 板块数据检查
            from ..db_models import SectorDailyData
            sector_count = db.query(func.count(SectorDailyData.id)).scalar()
            result["sector_data_count"] = sector_count
            logger.info(f"✅ 板块数据记录: {sector_count}")
            
            # 7. 板块日期数量
            sector_date_count = db.query(func.count(func.distinct(SectorDailyData.date))).scalar()
            result["sector_date_count"] = sector_date_count
            logger.info(f"✅ 板块数据日期数: {sector_date_count} 天")
            
            # 8. 板块ID序列检查
            if sector_count > 0:
                min_sector_id = db.query(func.min(SectorDailyData.id)).scalar()
                max_sector_id = db.query(func.max(SectorDailyData.id)).scalar()
                
                if min_sector_id == 1 and max_sector_id == sector_count:
                    result["sector_id_sequence_ok"] = True
                    logger.info(f"✅ 板块ID序列完整: 1 到 {max_sector_id}")
                else:
                    result["issues"].append(f"⚠️  板块ID序列异常: {min_sector_id} 到 {max_sector_id}")
                    logger.warning(f"⚠️  板块ID序列异常")
            
            # 汇总
            if len(result["issues"]) == 0:
                logger.info("=" * 60)
                logger.info("✅ 数据一致性检验通过")
                logger.info("=" * 60)
            else:
                logger.warning("=" * 60)
                logger.warning("⚠️  发现 {} 个问题".format(len(result["issues"])))
                for issue in result["issues"]:
                    logger.warning(f"  {issue}")
                logger.warning("=" * 60)
            
            return result
            
        finally:
            db.close()
    
    def run_startup_checks(self) -> bool:
        """
        启动前检查
        执行：数据导入 + 一致性检验
        
        Returns:
            True表示通过，False表示有问题
        """
        logger.info("\n")
        logger.info("🚀 " + "=" * 56 + " 🚀")
        logger.info("🚀   应用启动前数据检查")
        logger.info("🚀 " + "=" * 56 + " 🚀")
        logger.info("\n")
        
        # 1. 自动导入新数据
        success, failed, total_imported, stock_imported, sector_imported = self.auto_import_data()
        
        # 只要有股票数据就允许启动（板块数据是可选的）
        if failed > 0:
            logger.warning(f"⚠️  数据导入部分失败: {failed} 个文件")
            logger.info(f"📊 已导入数据: 股票 {stock_imported} 条, 板块 {sector_imported} 条")
            
            # 检查是否有股票数据
            if stock_imported == 0 and total_imported == 0:
                logger.error("❌ 没有股票数据导入成功，无法启动")
                return False
            else:
                logger.info("✅ 股票数据导入成功，允许启动（板块数据可选）")
        
        # 2. 数据一致性检验
        result = self.verify_data_consistency()
        
        if not result["db_connection"]:
            return False
        
        if result["daily_data_count"] == 0:
            logger.warning("⚠️  数据库为空，请检查data目录中是否有数据文件")
            return False
        
        if len(result["issues"]) > 0:
            logger.warning("⚠️  数据一致性检验发现问题，但允许启动")
        
        logger.info("\n")
        logger.info("✅ " + "=" * 56 + " ✅")
        logger.info("✅   启动检查通过")
        logger.info("✅ " + "=" * 56 + " ✅")
        logger.info("\n")
        
        return True


# 全局单例
_data_manager = None


def get_data_manager() -> DataManager:
    """获取数据管理器单例"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager


def run_startup_checks() -> bool:
    """便捷函数：运行启动检查"""
    return get_data_manager().run_startup_checks()
