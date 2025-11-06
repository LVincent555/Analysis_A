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

from scripts.import_state_manager import get_state_manager
from scripts.import_data_robust import get_data_files, import_excel_file
from ..database import SessionLocal, test_connection
from ..db_models import Stock, DailyStockData
from sqlalchemy import func, text

logger = logging.getLogger(__name__)


class DataManager:
    """数据管理器"""
    
    def __init__(self):
        """初始化"""
        self.state_manager = get_state_manager()
    
    def auto_import_data(self) -> Tuple[int, int, int]:
        """
        自动导入新数据
        
        Returns:
            (成功文件数, 失败文件数, 总导入记录数)
        """
        logger.info("=" * 60)
        logger.info("🔄 检查并导入新数据...")
        logger.info("=" * 60)
        
        files = get_data_files()
        if not files:
            logger.info("📂 data目录中没有数据文件")
            return 0, 0, 0
        
        success_count = 0
        failed_count = 0
        total_imported = 0
        
        for file_path in files:
            imported, skipped, success = import_excel_file(file_path, self.state_manager)
            total_imported += imported
            
            if success:
                success_count += 1
            else:
                failed_count += 1
        
        if total_imported > 0:
            logger.info(f"✅ 新导入 {total_imported} 条记录")
        else:
            logger.info("✅ 所有数据已是最新")
        
        return success_count, failed_count, total_imported
    
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
            logger.info(f"✅ 数据日期数: {date_count} 天")
            
            # 5. ID序列检查
            if daily_count > 0:
                min_id_result = db.query(func.min(DailyStockData.id)).scalar()
                max_id_result = db.query(func.max(DailyStockData.id)).scalar()
                
                if min_id_result == 1 and max_id_result == daily_count:
                    result["id_sequence_ok"] = True
                    logger.info(f"✅ ID序列完整: 1 到 {max_id_result}")
                else:
                    result["issues"].append(f"⚠️  ID序列异常: {min_id_result} 到 {max_id_result}")
                    logger.warning(f"⚠️  ID序列异常")
            
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
        success, failed, imported = self.auto_import_data()
        
        if failed > 0:
            logger.error(f"❌ 数据导入失败: {failed} 个文件")
            return False
        
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
