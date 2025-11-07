#!/usr/bin/env python3
"""
每日数据更新工具 - 统一入口
支持子命令模式和直接调用

使用方法：
    python update_daily_data.py                    # 导入数据（默认）
    python update_daily_data.py import             # 导入数据
    python update_daily_data.py scan               # 扫描文件
    python update_daily_data.py clean --scan       # 查看警告
    python update_daily_data.py clean --dry-run    # 预演清理
    python update_daily_data.py clean              # 执行清理
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

# 配置日志
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"update_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 添加backend/scripts和backend到路径
backend_scripts = Path(__file__).parent / "backend" / "scripts"
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_scripts))
sys.path.insert(0, str(backend_dir))


def cmd_import(args):
    """导入数据"""
    from data_importer import DataImporter
    from app.config import DATA_DIR
    
    start_time = datetime.now()
    logger.info("🚀 每日数据更新任务开始")
    logger.info(f"📅 执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📝 日志文件: {log_file}")
    logger.info("")
    
    importer = DataImporter(Path(DATA_DIR))
    results = importer.import_all(skip_scan=args.skip_scan)
    
    # 总结
    logger.info("")
    logger.info("=" * 70)
    logger.info("📊 数据更新任务完成")
    logger.info("=" * 70)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"⏱️  总耗时: {duration:.1f}秒")
    logger.info(f"📝 日志文件: {log_file}")
    logger.info("")
    
    if results['stock_success'] and results['sector_success']:
        logger.info("✅ 所有数据导入成功！")
        return 0
    else:
        logger.warning("⚠️  部分数据导入失败")
        return 1


def cmd_scan(args):
    """扫描文件完整性"""
    from data_scanner import DataScanner
    from app.config import DATA_DIR
    
    logger.info("🔍 开始扫描文件完整性...")
    logger.info("")
    
    scanner = DataScanner(Path(DATA_DIR))
    
    if args.type in ['stock', 'all']:
        scanner.scan_stock_files()
    
    if args.type in ['sector', 'all']:
        scanner.scan_sector_files()
    
    logger.info("")
    logger.info("✅ 扫描完成")
    return 0


def cmd_clean(args):
    """清理孤儿数据"""
    from data_cleaner import DataCleaner
    
    logger.info("🗑️  孤儿数据清理工具")
    logger.info("")
    
    dates = None
    if args.dates:
        dates = [d.strip() for d in args.dates.split(',')]
    
    # 扫描模式
    if args.scan:
        if args.type in ['stock', 'all']:
            logger.info("📊 扫描股票数据...")
            cleaner = DataCleaner('stock')
            cleaner.scan_warnings()
        
        if args.type in ['sector', 'all']:
            logger.info("\n📊 扫描板块数据...")
            cleaner = DataCleaner('sector')
            cleaner.scan_warnings()
        
        logger.info("\n💡 使用以下命令清理数据：")
        logger.info("   预演: python update_daily_data.py clean --dry-run")
        logger.info("   执行: python update_daily_data.py clean")
        return 0
    
    # 清理模式
    if not args.dry_run:
        logger.warning("⚠️  警告：即将删除数据库数据！")
        response = input("确认继续？(yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("❌ 已取消")
            return 1
    
    if args.type in ['stock', 'all']:
        logger.info("📊 清理股票数据...")
        cleaner = DataCleaner('stock')
        cleaner.clean_warnings(dry_run=args.dry_run, dates=dates)
    
    if args.type in ['sector', 'all']:
        logger.info("\n📊 清理板块数据...")
        cleaner = DataCleaner('sector')
        cleaner.clean_warnings(dry_run=args.dry_run, dates=dates)
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='每日数据更新和维护工具',
        epilog='示例: python update_daily_data.py import'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 导入命令（默认）
    import_parser = subparsers.add_parser('import', help='导入数据')
    import_parser.add_argument(
        '--skip-scan', 
        action='store_true', 
        help='跳过文件扫描'
    )
    
    # 扫描命令
    scan_parser = subparsers.add_parser('scan', help='扫描文件完整性')
    scan_parser.add_argument(
        '--type',
        choices=['stock', 'sector', 'all'],
        default='all',
        help='数据类型'
    )
    
    # 清理命令
    clean_parser = subparsers.add_parser('clean', help='清理孤儿数据')
    clean_parser.add_argument('--scan', action='store_true', help='只扫描不清理')
    clean_parser.add_argument('--dry-run', action='store_true', help='预演模式')
    clean_parser.add_argument(
        '--type',
        choices=['stock', 'sector', 'all'],
        default='all',
        help='数据类型'
    )
    clean_parser.add_argument('--dates', type=str, help='指定日期（逗号分隔）')
    
    args = parser.parse_args()
    
    # 默认命令为import
    if not args.command:
        args.command = 'import'
        args.skip_scan = False
    
    try:
        if args.command == 'import':
            return cmd_import(args)
        elif args.command == 'scan':
            return cmd_scan(args)
        elif args.command == 'clean':
            return cmd_clean(args)
    except KeyboardInterrupt:
        logger.info("\n\n❌ 用户中断")
        return 1
    except Exception as e:
        logger.error(f"\n❌ 错误: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
