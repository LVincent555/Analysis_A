"""
数据导入任务调度器
提供统一的导入接口，可被主程序调用或独立运行
"""
import sys
from pathlib import Path
import logging
import subprocess

logger = logging.getLogger(__name__)


class DataImporter:
    """数据导入调度器"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.backend_scripts = Path(__file__).parent
    
    def import_all(self, skip_scan=False):
        """
        导入所有数据（股票+板块）
        
        Args:
            skip_scan: 是否跳过文件扫描
        
        Returns:
            dict: {
                'stock_success': bool,
                'sector_success': bool,
                'stock_stats': dict,
                'sector_stats': dict
            }
        """
        results = {
            'stock_success': False,
            'sector_success': False,
            'stock_stats': {},
            'sector_stats': {}
        }
        
        # 导入股票数据
        logger.info("=" * 70)
        logger.info("开始股票数据导入")
        logger.info("=" * 70)
        
        stock_result = self._run_import_script(
            "import_data_robust.py",
            "股票数据导入"
        )
        results['stock_success'] = stock_result['success']
        results['stock_stats'] = stock_result.get('stats', {})
        
        logger.info("")
        
        # 导入板块数据
        logger.info("=" * 70)
        logger.info("开始板块数据导入")
        logger.info("=" * 70)
        
        sector_result = self._run_import_script(
            "import_sectors_robust.py",
            "板块数据导入"
        )
        results['sector_success'] = sector_result['success']
        results['sector_stats'] = sector_result.get('stats', {})
        
        # 文件扫描
        if not skip_scan:
            logger.info("")
            logger.info("=" * 70)
            logger.info("检查文件完整性")
            logger.info("=" * 70)
            
            try:
                from data_scanner import DataScanner
                scanner = DataScanner(self.data_dir)
                scanner.scan_all()
            except Exception as e:
                logger.error(f"文件扫描失败: {str(e)}")
        
        return results
    
    def _run_import_script(self, script_name: str, description: str):
        """运行导入脚本（支持Windows/Linux）"""
        script_path = self.backend_scripts / script_name
        # 使用项目根目录作为工作目录，避免路径冲突
        project_root = self.backend_scripts.parent.parent
        
        try:
            import platform
            is_windows = platform.system() == 'Windows'
            encoding = 'gbk' if is_windows else 'utf-8'
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                encoding=encoding,
                errors='replace'
            )
            
            # 输出日志（通过WARNING级别避免被过滤）
            for line in result.stdout.splitlines():
                logger.warning(line)
            
            if result.stderr:
                for line in result.stderr.splitlines():
                    logger.error(line)
            
            if result.returncode == 0:
                logger.info(f"✅ {description}完成")
                return {'success': True}
            else:
                logger.error(f"❌ {description}失败 (退出码: {result.returncode})")
                return {'success': False}
                
        except Exception as e:
            logger.error(f"❌ {description}失败: {str(e)}")
            return {'success': False}


def main():
    """独立运行"""
    import argparse
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 添加路径
    sys.path.insert(0, str(Path(__file__).parent))
    
    parser = argparse.ArgumentParser(description='数据导入任务')
    parser.add_argument('--skip-scan', action='store_true', help='跳过文件扫描')
    args = parser.parse_args()
    
    from app.config import DATA_DIR
    importer = DataImporter(Path(DATA_DIR))
    results = importer.import_all(skip_scan=args.skip_scan)
    
    # 返回退出码
    if results['stock_success'] and results['sector_success']:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
