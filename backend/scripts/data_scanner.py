"""
文件完整性扫描器
检测文件缺失和变更，标记warning状态
"""
import sys
import logging
from pathlib import Path
from import_state_manager import ImportStateManager

logger = logging.getLogger(__name__)


class DataScanner:
    """文件扫描器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
    
    def scan_all(self):
        """扫描所有数据类型"""
        stock_warnings = self.scan_stock_files()
        sector_warnings = self.scan_sector_files()
        
        total_warnings = (
            stock_warnings['file_missing'] + stock_warnings['file_changed'] +
            stock_warnings.get('rolled_back', 0) +
            sector_warnings['file_missing'] + sector_warnings['file_changed'] +
            sector_warnings.get('rolled_back', 0)
        )
        
        if total_warnings > 0:
            logger.warning("")
            logger.warning("⚠️  发现文件异常！")
            logger.warning(f"   运行清理工具查看详情: python update_daily_data.py clean --scan")
            logger.warning(f"   删除孤儿数据: python update_daily_data.py clean")
        
        return {
            'stock': stock_warnings,
            'sector': sector_warnings,
            'total_warnings': total_warnings
        }
    
    def scan_stock_files(self):
        """扫描股票数据文件"""
        logger.info("🔍 扫描股票数据文件...")
        state_manager = ImportStateManager("data_import_state.json")
        result = state_manager.scan_file_changes(
            self.data_dir, 
            "*_data_sma_feature_color.xlsx"
        )
        self._report_result(result, "股票")
        return result
    
    def scan_sector_files(self):
        """扫描板块数据文件"""
        logger.info("🔍 扫描板块数据文件...")
        state_manager = ImportStateManager("sector_import_state.json")
        result = state_manager.scan_file_changes(
            self.data_dir,
            "*_allbk_sma_feature_color.xlsx"
        )
        self._report_result(result, "板块")
        return result
    
    def _report_result(self, result: dict, data_type: str):
        """报告扫描结果"""
        logger.info(f"  ✅ 正常: {result['file_ok']} 个")
        
        if result.get('rolled_back', 0) > 0:
            logger.warning(
                f"  ⚠️  回滚残留: {result['rolled_back']} 个"
                f"（已标记为warning）"
            )
        
        if result['file_missing'] > 0:
            logger.warning(
                f"  ⚠️  缺失: {result['file_missing']} 个"
                f"（已标记为warning）"
            )
        
        if result['file_changed'] > 0:
            logger.warning(
                f"  ⚠️  变更: {result['file_changed']} 个"
                f"（已标记为warning）"
            )


def main():
    """独立运行"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 添加路径
    sys.path.insert(0, str(Path(__file__).parent))
    
    from app.config import DATA_DIR
    scanner = DataScanner(Path(DATA_DIR))
    scanner.scan_all()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
