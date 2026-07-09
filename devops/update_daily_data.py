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
    python update_daily_data.py delete --dates 20251117 --dry-run  # 预演删除指定日期
    python update_daily_data.py delete --dates 20251117            # 删除指定日期数据
    python update_daily_data.py fix --scan         # 查看修补历史
    python update_daily_data.py fix --dates 20251117 --dry-run     # 预演修补指定日期
    python update_daily_data.py fix --dates 20251117               # 修补指定日期
    python update_daily_data.py fix --rollback --dates 20251117    # 回滚修补
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 配置日志
log_dir = PROJECT_ROOT / "logs"
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
backend_scripts = PROJECT_ROOT / "backend" / "scripts"
backend_dir = PROJECT_ROOT / "backend"
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


def cmd_delete(args):
    """主动删除指定日期的数据（强制删除）"""
    from data_cleaner import DataCleaner
    
    if not args.dates:
        logger.error("❌ 错误：必须指定 --dates 参数")
        logger.info("示例: python update_daily_data.py delete --dates 20251117")
        logger.info("多个日期: python update_daily_data.py delete --dates 20251117,20251116")
        return 1
    
    dates = [d.strip() for d in args.dates.split(',')]
    
    logger.info("🔥 主动删除数据工具")
    logger.info("")
    logger.warning("⚠️  此命令将强制删除指定日期的数据，无论其状态如何")
    logger.warning("⚠️  适用场景：数据源有问题，需要重新导入")
    logger.info("")
    logger.info(f"📅 目标日期: {', '.join(dates)}")
    logger.info(f"📊 数据类型: {args.type}")
    logger.info("")
    
    # 确认模式
    if not args.dry_run:
        logger.warning("⚠️  警告：即将永久删除数据库数据！")
        logger.warning("   删除后需要重新导入Excel文件才能恢复数据")
        logger.info("")
        response = input("确认删除？输入日期以确认 (或输入 no 取消): ")
        
        # 验证用户输入的日期
        if response.lower() in ['no', 'n']:
            logger.info("❌ 已取消")
            return 1
        
        if len(dates) == 1 and response != dates[0]:
            logger.error("❌ 日期不匹配，已取消")
            return 1
        
        if len(dates) > 1 and response.lower() not in ['yes', 'y']:
            logger.error("❌ 请输入 yes 确认删除多个日期")
            return 1
    
    # 执行删除
    if args.type in ['stock', 'all']:
        logger.info("📊 删除股票数据...")
        cleaner = DataCleaner('stock')
        cleaner.clean_warnings(dry_run=args.dry_run, dates=dates, force=True)
    
    if args.type in ['sector', 'all']:
        logger.info("\n📊 删除板块数据...")
        cleaner = DataCleaner('sector')
        cleaner.clean_warnings(dry_run=args.dry_run, dates=dates, force=True)
    
    if not args.dry_run:
        logger.info("")
        logger.info("✅ 删除完成！")
        logger.info("💡 提示：如需恢复数据，请将对应日期的Excel文件放入data目录，然后运行：")
        logger.info("   python update_daily_data.py import")
    
    return 0


def cmd_fix(args):
    """数据修补工具（换手率等）"""
    from data_fixer import TurnoverRateFixer
    from import_state_manager import ImportStateManager
    
    # 扫描模式
    if args.scan:
        logger.info("🔍 扫描修补历史...")
        logger.info("")
        
        if args.type in ['stock', 'all']:
            logger.info("📊 股票数据修补历史：")
            logger.info("=" * 70)
            state_mgr = ImportStateManager("data_import_state.json")
            _print_fix_history(state_mgr)
        
        if args.type in ['sector', 'all']:
            logger.info("\n📊 板块数据修补历史：")
            logger.info("=" * 70)
            state_mgr = ImportStateManager("sector_import_state.json")
            _print_fix_history(state_mgr)
        
        return 0
    
    # 回滚模式
    if args.rollback:
        if not args.dates:
            logger.error("❌ 错误：回滚操作必须指定 --dates 参数")
            return 1
        
        dates = [d.strip() for d in args.dates.split(',')]
        
        logger.info("🔄 回滚换手率修补")
        logger.info("")
        logger.info(f"📅 目标日期: {', '.join(dates)}")
        logger.info(f"📊 数据类型: {args.type}")
        logger.info("")
        
        if not args.dry_run:
            logger.warning("⚠️  警告：将撤销换手率修补，恢复原始数据！")
            response = input("确认回滚？(yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("❌ 已取消")
                return 1
        
        # 执行回滚
        success_count = 0
        for date_str in dates:
            if args.type in ['stock', 'all']:
                logger.info(f"\n📊 回滚股票数据 {date_str}...")
                fixer = TurnoverRateFixer(date_str, 'stock')
                result = fixer.rollback_database(dry_run=args.dry_run)
                if result.get('success') or result.get('dry_run'):
                    if not args.dry_run:
                        fixer.record_rollback_to_state(result)
                    success_count += 1
        
        if not args.dry_run:
            logger.info(f"\n✅ 回滚完成！成功 {success_count} 个日期")
        
        return 0
    
    # 修补模式
    if not args.dates:
        logger.error("❌ 错误：修补操作必须指定 --dates 参数")
        logger.info("示例: python update_daily_data.py fix --dates 20251117")
        return 1
    
    dates = [d.strip() for d in args.dates.split(',')]
    
    logger.info("🔧 数据修补工具")
    logger.info("")
    logger.info(f"📅 目标日期: {', '.join(dates)}")
    logger.info(f"📊 数据类型: {args.type}")
    logger.info("")
    
    if not args.dry_run:
        logger.warning("⚠️  警告：将对数据库数据执行修补操作！")
        response = input("确认修补？(yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("❌ 已取消")
            return 1
    
    # 执行修补
    success_count = 0
    for date_str in dates:
        if args.type in ['stock', 'all']:
            logger.info(f"\n📊 修补股票数据 {date_str}...")
            fixer = TurnoverRateFixer(date_str, 'stock')
            result = fixer.fix_database(dry_run=args.dry_run)
            if result.get('applied') or result.get('dry_run'):
                if not args.dry_run:
                    fixer.record_fix_to_state(result)
                success_count += 1
    
    if not args.dry_run:
        logger.info(f"\n✅ 修补完成！成功 {success_count} 个日期")
    
    return 0


def _print_fix_history(state_mgr: 'ImportStateManager'):
    """打印修补历史"""
    imports = state_mgr.state.get('imports', {})
    
    has_fixes = False
    for date_str in sorted(imports.keys(), reverse=True):
        import_info = imports[date_str]
        data_fixes = import_info.get('data_fixes', {})
        turnover_fix = data_fixes.get('turnover_rate_fix')
        
        if turnover_fix and turnover_fix.get('applied'):
            has_fixes = True
            logger.info(f"\n📅 {date_str}:")
            logger.info(f"   状态: ✅ 已修补")
            logger.info(f"   倍数: {turnover_fix.get('multiplier', 10000)}")
            logger.info(f"   影响行数: {turnover_fix.get('affected_rows', 0)}")
            logger.info(f"   修补前平均: {turnover_fix.get('avg_before', 0):.6f}")
            logger.info(f"   修补后平均: {turnover_fix.get('avg_after', 0):.4f}")
            logger.info(f"   修补时间: {turnover_fix.get('fixed_at', 'N/A')}")
    
    if not has_fixes:
        logger.info("   没有修补记录")
    
    logger.info("")


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
    
    # 删除命令（主动删除）
    delete_parser = subparsers.add_parser('delete', help='主动删除指定日期的数据')
    delete_parser.add_argument(
        '--dates',
        type=str,
        required=True,
        help='要删除的日期（逗号分隔，如: 20251117 或 20251117,20251116）'
    )
    delete_parser.add_argument('--dry-run', action='store_true', help='预演模式（不真正删除）')
    delete_parser.add_argument(
        '--type',
        choices=['stock', 'sector', 'all'],
        default='all',
        help='数据类型（默认: all）'
    )
    
    # 修补命令（数据修补）
    fix_parser = subparsers.add_parser('fix', help='数据修补工具（换手率等）')
    fix_parser.add_argument('--scan', action='store_true', help='查看修补历史')
    fix_parser.add_argument('--rollback', action='store_true', help='回滚修补操作')
    fix_parser.add_argument('--dates', type=str, help='要修补/回滚的日期（逗号分隔）')
    fix_parser.add_argument('--dry-run', action='store_true', help='预演模式（不真正修补）')
    fix_parser.add_argument(
        '--type',
        choices=['stock', 'sector', 'all'],
        default='stock',
        help='数据类型（默认: stock，板块暂不支持）'
    )
    
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
        elif args.command == 'delete':
            return cmd_delete(args)
        elif args.command == 'fix':
            return cmd_fix(args)
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
