"""
孤儿数据清理器
处理warning状态的数据，删除对应的数据库记录
"""
import sys
import logging
from pathlib import Path
from typing import List, Optional
from import_state_manager import ImportStateManager
from app.database import SessionLocal
from app.db_models import DailyStockData, SectorDailyData
from sqlalchemy import func

logger = logging.getLogger(__name__)


class DataCleaner:
    """数据清理器"""
    
    def __init__(self, data_type='stock'):
        """
        Args:
            data_type: 'stock' 或 'sector'
        """
        self.data_type = data_type
        state_file = (
            "data_import_state.json" if data_type == 'stock' 
            else "sector_import_state.json"
        )
        self.state_manager = ImportStateManager(state_file)
        self.model = DailyStockData if data_type == 'stock' else SectorDailyData
    
    def scan_warnings(self) -> dict:
        """扫描警告"""
        warnings = self.state_manager.get_warnings()
        
        if not warnings:
            logger.info(f"✅ {self.data_type.upper()} 数据没有警告")
            return {}
        
        logger.warning(
            f"⚠️  发现 {len(warnings)} 个警告状态的"
            f" {self.data_type.upper()} 数据："
        )
        logger.warning("=" * 80)
        
        for date_str, import_info in sorted(warnings.items()):
            self._print_warning_detail(date_str, import_info)
        
        logger.warning("=" * 80)
        return warnings
    
    def clean_warnings(
        self, 
        dry_run=False, 
        dates: Optional[List[str]] = None,
        force=False
    ) -> dict:
        """
        清理警告数据
        
        Args:
            dry_run: 预演模式
            dates: 指定日期列表
            force: 强制清理指定日期（忽略状态）
        """
        if force and dates:
            # 强制清理模式：直接删除指定日期的数据
            logger.warning("🔥 强制清理模式：忽略状态，直接删除指定日期")
            return self._force_clean_dates(dates, dry_run)
        
        warnings = self.state_manager.get_warnings()
        
        if not warnings:
            logger.info(f"✅ {self.data_type.upper()} 数据没有警告")
            return {'success': 0, 'failed': 0}
        
        # 过滤日期
        if dates:
            warnings = {d: w for d, w in warnings.items() if d in dates}
            if not warnings:
                logger.warning("⚠️  指定的日期没有警告状态")
                return {'success': 0, 'failed': 0}
        
        mode = "[预演模式]" if dry_run else "[执行模式]"
        logger.info(f"\n{mode} 处理 {len(warnings)} 个警告...")
        logger.info("=" * 80)
        
        success_count = 0
        failed_count = 0
        
        for date_str, import_info in sorted(warnings.items()):
            if self._clean_single_date(date_str, import_info, dry_run):
                success_count += 1
            else:
                failed_count += 1
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ 清理完成: 成功 {success_count}, 失败 {failed_count}")
        
        if dry_run:
            logger.info("\n💡 这是预演模式，没有真正删除数据")
            logger.info("   运行 'python update_daily_data.py clean' 执行真实删除")
        
        return {'success': success_count, 'failed': failed_count}
    
    def _clean_single_date(
        self, 
        date_str: str, 
        import_info: dict, 
        dry_run: bool
    ) -> bool:
        """清理单个日期的数据"""
        warning_info = import_info.get('warning_info', {}) or {}
        warning_type = warning_info.get('warning_type', 'unknown')
        
        logger.info(f"\n📅 处理日期: {date_str}")
        logger.info(f"   问题类型: {warning_type}")
        logger.info(f"   文件: {import_info.get('filename')}")
        
        # 删除数据库数据
        db_session = SessionLocal()
        try:
            count = db_session.query(func.count(self.model.id)).filter(
                func.to_char(self.model.date, 'YYYYMMDD') == date_str
            ).scalar()
            
            if count == 0:
                logger.info("  数据库中没有数据")
                return True
            
            if dry_run:
                logger.info(f"  [预演] 将删除 {count} 条记录")
                return True
            
            # 真实删除（硬删除）
            logger.warning(f"  🗑️  删除 {count} 条记录...")
            deleted = db_session.query(self.model).filter(
                func.to_char(self.model.date, 'YYYYMMDD') == date_str
            ).delete(synchronize_session=False)
            
            db_session.commit()
            logger.info(f"  ✅ 已删除 {deleted} 条记录")
            
            # 更新状态
            self.state_manager.mark_deleted(
                date_str,
                delete_reason=f"orphan_cleanup_{warning_type}",
                deleted_by="clean_script"
            )
            
            return True
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"  ❌ 删除失败: {str(e)}")
            return False
        finally:
            db_session.close()
    
    def _force_clean_dates(self, dates: List[str], dry_run: bool) -> dict:
        """
        强制清理指定日期的数据（忽略状态）
        用于处理 rolled_back 等特殊情况
        """
        mode = "[预演模式]" if dry_run else "[执行模式]"
        logger.warning(f"\n{mode} 强制清理 {len(dates)} 个日期...")
        logger.warning("=" * 80)
        
        success_count = 0
        failed_count = 0
        
        for date_str in dates:
            # 获取导入信息（如果有的话）
            import_info = self.state_manager.state["imports"].get(date_str, {
                "filename": f"{date_str}_*.xlsx",
                "status": "unknown"
            })
            
            if self._clean_single_date(date_str, import_info, dry_run):
                success_count += 1
            else:
                failed_count += 1
        
        logger.warning("\n" + "=" * 80)
        logger.warning(f"✅ 强制清理完成: 成功 {success_count}, 失败 {failed_count}")
        
        if dry_run:
            logger.info("\n💡 这是预演模式，没有真正删除数据")
            logger.info("   运行 'python update_daily_data.py clean --force --dates YYYYMMDD' 执行真实删除")
        
        return {'success': success_count, 'failed': failed_count}
    
    def _print_warning_detail(self, date_str: str, import_info: dict):
        """打印警告详情"""
        warning_info = import_info.get('warning_info', {}) or {}
        warning_type = warning_info.get('warning_type', 'unknown')
        detected_at = warning_info.get('detected_at', 'unknown')
        status = import_info.get('status', 'unknown')
        
        logger.warning(f"\n📅 日期: {date_str}")
        logger.warning(f"   文件: {import_info.get('filename', 'N/A')}")
        logger.warning(f"   状态: {status}")
        logger.warning(f"   问题: {warning_type}")
        logger.warning(f"   检测时间: {detected_at}")
        logger.warning(f"   导入记录数: {import_info.get('imported_count', 0)}")
        
        if warning_type == 'file_missing':
            logger.warning("⚠️  Excel文件已缺失，数据库中仍有数据")
        elif warning_type == 'file_changed':
            logger.warning("⚠️  Excel文件已变更，与导入时不一致")
            logger.warning(f"   原始Hash: {warning_info.get('original_hash', 'N/A')[:16]}...")
            current_hash = warning_info.get('current_hash')
            if current_hash:
                logger.warning(f"   当前Hash: {current_hash[:16]}...")
        elif warning_type == 'rollback_residue':
            logger.warning("⚠️  导入失败已回滚，但可能有数据库残留")
            rollback_reason = import_info.get('rollback_reason', '')
            if rollback_reason:
                # 只显示第一行错误信息
                first_line = rollback_reason.split('\n')[0]
                logger.warning(f"   回滚原因: {first_line}")


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
    
    parser = argparse.ArgumentParser(description='孤儿数据清理工具')
    parser.add_argument('--scan', action='store_true', help='扫描警告')
    parser.add_argument('--clean', action='store_true', help='清理警告数据')
    parser.add_argument('--dry-run', action='store_true', help='预演模式')
    parser.add_argument('--force', action='store_true', help='强制清理（忽略状态，需配合 --dates 使用）')
    parser.add_argument(
        '--type', 
        choices=['stock', 'sector', 'all'], 
        default='all',
        help='数据类型'
    )
    parser.add_argument('--dates', type=str, help='指定日期（逗号分隔，如: 20251111 或 20251111,20251112）')
    
    args = parser.parse_args()
    
    # 解析日期
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
        
        return 0
    
    # 清理模式
    if args.clean or args.dry_run or args.force:
        # 强制模式需要指定日期
        if args.force and not dates:
            logger.error("❌ 强制清理模式必须指定 --dates 参数")
            return 1
        
        if not args.dry_run:
            logger.warning("⚠️  警告：即将删除数据库数据！")
            if args.force:
                logger.warning("🔥 强制模式：将忽略状态直接删除指定日期的数据")
            response = input("确认删除数据？(yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("❌ 已取消")
                return 1
        
        if args.type in ['stock', 'all']:
            logger.info("📊 清理股票数据...")
            cleaner = DataCleaner('stock')
            cleaner.clean_warnings(dry_run=args.dry_run, dates=dates, force=args.force)
        
        if args.type in ['sector', 'all']:
            logger.info("\n📊 清理板块数据...")
            cleaner = DataCleaner('sector')
            cleaner.clean_warnings(dry_run=args.dry_run, dates=dates, force=args.force)
        
        return 0
    
    # 默认显示帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
