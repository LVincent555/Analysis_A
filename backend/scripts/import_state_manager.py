"""
导入状态管理器
维护数据导入的原子性、幂等性和回滚机制
使用本地JSON文件存储导入状态，无侵入性设计
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ImportStateManager:
    """导入状态管理器"""
    
    def __init__(self, state_file: str = "data_import_state.json"):
        """
        初始化状态管理器
        
        Args:
            state_file: 状态文件名（存储在data目录下）
        """
        # 状态文件存储在data目录
        from app.config import DATA_DIR
        self.state_file = Path(DATA_DIR) / state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态文件（兼容老版本）"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # === 兼容性处理 ===
                # 确保version字段存在
                if "version" not in state:
                    state["version"] = "1.0"
                    logger.info("检测到老版本JSON，已自动升级")
                
                # 为每个导入记录添加默认字段（如果不存在）
                for date_str, import_info in state.get("imports", {}).items():
                    # warning_info字段
                    if "warning_info" not in import_info:
                        import_info["warning_info"] = None
                    
                    # deletion_info字段
                    if "deletion_info" not in import_info:
                        import_info["deletion_info"] = None
                    
                    # dedup_info字段
                    if "dedup_info" not in import_info:
                        import_info["dedup_info"] = None
                    
                    # data_fixes字段（新增）
                    if "data_fixes" not in import_info:
                        import_info["data_fixes"] = {}
                
                # 确保fix_config存在（向前兼容）
                if "fix_config" not in state:
                    state["fix_config"] = {
                        "turnover_rate_fix": {
                            "enabled": True,
                            "auto_fix": True,
                            "threshold": 0.01,
                            "multiplier": 10000
                        }
                    }
                
                return state
                
            except Exception as e:
                logger.warning(f"状态文件读取失败，创建新文件: {str(e)}")
                return self._create_empty_state()
        else:
            return self._create_empty_state()
    
    def _create_empty_state(self) -> Dict:
        """创建空状态"""
        return {
            "version": "1.1",  # 升级版本号以支持修补功能
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "database": "unknown",
            "imports": {},
            "fix_config": {
                "turnover_rate_fix": {
                    "enabled": True,
                    "auto_fix": True,
                    "threshold": 0.01,
                    "multiplier": 10000
                }
            }
        }
    
    def _save_state(self):
        """保存状态到文件（内部方法）"""
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            logger.debug(f"状态文件已保存: {self.state_file}")
        except Exception as e:
            logger.error(f"状态文件保存失败: {str(e)}")
    
    def save(self):
        """保存状态到文件（公开方法）"""
        self._save_state()
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """
        计算文件MD5哈希值
        用于检测文件是否变化
        """
        try:
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                # 分块读取，避免大文件内存问题
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            logger.warning(f"文件哈希计算失败: {str(e)}")
            return ""
    
    def is_imported(self, date_str: str) -> bool:
        """
        检查指定日期是否已成功导入
        
        Args:
            date_str: 日期字符串，格式：'20251103'
        
        Returns:
            True表示已成功导入，False表示未导入或失败
        """
        if date_str not in self.state["imports"]:
            return False
        
        import_info = self.state["imports"][date_str]
        return import_info.get("status") == "success"
    
    def should_reimport(self, date_str: str, file_path: Path) -> bool:
        """
        判断是否需要重新导入
        
        场景：
        1. 从未导入过 -> 需要导入
        2. 上次失败 -> 需要重新导入
        3. 文件已变化（哈希不同）-> 需要重新导入
        4. 上次成功且文件未变 -> 不需要导入
        5. 已删除(deleted) -> 需要导入（数据库已清理）
        6. 已回滚(rolled_back) -> 需要导入（数据库已回滚）
        
        Args:
            date_str: 日期字符串
            file_path: 文件路径
        
        Returns:
            True表示需要导入，False表示跳过
        """
        if date_str not in self.state["imports"]:
            return True  # 从未导入
        
        import_info = self.state["imports"][date_str]
        status = import_info.get("status")
        
        # 成功导入的，检查文件是否变化
        if status == "success":
            current_hash = self.calculate_file_hash(file_path)
            if current_hash and current_hash != import_info.get("file_hash", ""):
                logger.info(f"检测到文件变化: {file_path.name}，将重新导入")
                return True
            return False  # 已成功导入且文件未变
        
        # deleted/rolled_back状态：数据库应该已经清理，可以重新导入
        if status in ["deleted", "rolled_back"]:
            return True
        
        # 其他失败状态（in_progress, failed等）：需要重新导入
        return True
    
    def start_import(self, date_str: str, filename: str, file_path: Path):
        """
        开始导入，记录初始状态
        
        Args:
            date_str: 日期字符串
            filename: 文件名
            file_path: 文件路径
        """
        file_hash = self.calculate_file_hash(file_path)
        
        self.state["imports"][date_str] = {
            "filename": filename,
            "status": "in_progress",
            "file_hash": file_hash,
            "start_time": datetime.now().isoformat(),
            "imported_count": 0,
            "skipped_count": 0,
            "attempt_count": self.state["imports"].get(date_str, {}).get("attempt_count", 0) + 1,
            "dedup_info": None,  # 去重信息
            "data_fixes": {}     # 修补信息（新增）
        }
        self._save_state()
        logger.info(f"开始导入: {date_str} - {filename}")
    
    def record_dedup_info(self, date_str: str, dedup_stats: dict):
        """
        记录去重信息
        
        Args:
            date_str: 日期字符串
            dedup_stats: 去重统计信息
        """
        if date_str in self.state["imports"]:
            if dedup_stats.get('has_duplicates'):
                self.state["imports"][date_str]["dedup_info"] = {
                    "detected_duplicates": dedup_stats.get('duplicate_codes', []),
                    "removed_count": dedup_stats.get('removed_count', 0),
                    "removed_details": dedup_stats.get('removed_details', []),
                    "dedup_time": datetime.now().isoformat()
                }
                self._save_state()
                logger.info(f"📝 已记录去重信息: {date_str}")
    
    def mark_success(
        self,
        date_str: str,
        imported_count: int,
        skipped_count: int = 0,
        duration_seconds: float = 0
    ):
        """
        标记导入成功
        
        Args:
            date_str: 日期字符串
            imported_count: 导入记录数
            skipped_count: 跳过记录数
            duration_seconds: 耗时（秒）
        """
        if date_str in self.state["imports"]:
            self.state["imports"][date_str].update({
                "status": "success",
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "end_time": datetime.now().isoformat(),
                "duration_seconds": round(duration_seconds, 2),
                "error": None  # 清除之前的错误
            })
            self._save_state()
            logger.info(f"✅ 导入成功: {date_str}, 导入{imported_count}条, 跳过{skipped_count}条")
    
    def mark_failed(self, date_str: str, error: str, imported_count: int = 0):
        """
        标记导入失败
        
        Args:
            date_str: 日期字符串
            error: 错误信息
            imported_count: 已导入记录数（失败前）
        """
        if date_str in self.state["imports"]:
            self.state["imports"][date_str].update({
                "status": "failed",
                "error": error,
                "imported_count": imported_count,
                "end_time": datetime.now().isoformat()
            })
            self._save_state()
            logger.error(f"❌ 导入失败: {date_str}, 错误: {error}")
    
    def mark_rolled_back(self, date_str: str, reason: str):
        """
        标记已回滚
        
        Args:
            date_str: 日期字符串
            reason: 回滚原因
        """
        if date_str in self.state["imports"]:
            self.state["imports"][date_str].update({
                "status": "rolled_back",
                "rollback_reason": reason,
                "rollback_time": datetime.now().isoformat()
            })
            self._save_state()
            logger.warning(f"🔄 已回滚: {date_str}, 原因: {reason}")
    
    def get_import_info(self, date_str: str) -> Optional[Dict]:
        """获取导入信息"""
        return self.state["imports"].get(date_str)
    
    def get_all_imports(self) -> Dict:
        """获取所有导入记录"""
        return self.state["imports"]
    
    def get_statistics(self) -> Dict:
        """
        获取导入统计信息
        
        Returns:
            统计字典
        """
        imports = self.state["imports"]
        total = len(imports)
        success = sum(1 for i in imports.values() if i.get("status") == "success")
        # "failed"统计包含 explicit "failed" 和 "rolled_back"
        failed = sum(1 for i in imports.values() if i.get("status") in ["failed", "rolled_back"])
        in_progress = sum(1 for i in imports.values() if i.get("status") == "in_progress")
        
        total_records = sum(i.get("imported_count", 0) for i in imports.values() if i.get("status") == "success")
        
        return {
            "total_files": total,
            "success_count": success,
            "failed_count": failed,
            "in_progress_count": in_progress,
            "total_records_imported": total_records,
            "success_rate": f"{success/total*100:.1f}%" if total > 0 else "0%"
        }
    
    def converge_in_progress_tasks(self, timeout_minutes: int = 60) -> int:
        """
        收敛超时任务：将长时间处于in_progress的任务标记为rolled_back
        
        Args:
            timeout_minutes: 超时分钟数
            
        Returns:
            收敛的任务数量
        """
        count = 0
        now = datetime.now()
        updates = False
        
        for date_str, info in self.state["imports"].items():
            if info.get("status") == "in_progress":
                start_time_str = info.get("start_time")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        delta = now - start_time
                        if delta.total_seconds() > timeout_minutes * 60:
                            # 超时，标记为 rolled_back (User Option A requirement)
                            info["status"] = "rolled_back"
                            info["rollback_reason"] = f"Timeout ({timeout_minutes}m) - Process likely crashed"
                            info["rollback_time"] = now.isoformat()
                            count += 1
                            updates = True
                            logger.warning(f"🔄 自动收敛超时任务: {date_str} -> rolled_back")
                    except ValueError:
                        pass
        
        if updates:
            self._save_state()
            
        return count
    
    def print_summary(self):
        """打印导入摘要"""
        stats = self.get_statistics()
        print("\n" + "=" * 60)
        print("导入状态摘要")
        print("=" * 60)
        print(f"总文件数: {stats['total_files']}")
        print(f"成功: {stats['success_count']}")
        print(f"失败: {stats['failed_count']}")
        print(f"进行中: {stats['in_progress_count']}")
        print(f"总导入记录: {stats['total_records_imported']}")
        print(f"成功率: {stats['success_rate']}")
        print("=" * 60)
    
    def mark_warning(self, date_str: str, warning_type: str, current_hash: Optional[str] = None):
        """
        标记为警告状态
        
        Args:
            date_str: 日期字符串
            warning_type: 警告类型 (file_missing/file_changed)
            current_hash: 当前文件hash（如果文件还存在）
        """
        if date_str in self.state["imports"]:
            import_info = self.state["imports"][date_str]
            original_status = import_info.get("status")
            
            # 只有成功状态才能标记为warning
            if original_status == "success":
                import_info["status"] = "warning"
                import_info["warning_info"] = {
                    "detected_at": datetime.now().isoformat(),
                    "warning_type": warning_type,
                    "original_hash": import_info.get("file_hash"),
                    "current_hash": current_hash,
                    "suggest_action": "delete_db_data" if warning_type == "file_missing" else "reimport_or_delete"
                }
                self._save_state()
                logger.warning(f"⚠️  标记为警告: {date_str}, 类型: {warning_type}")
    
    def clear_warning(self, date_str: str):
        """清除警告状态（恢复为success）"""
        if date_str in self.state["imports"]:
            import_info = self.state["imports"][date_str]
            if import_info.get("status") == "warning":
                import_info["status"] = "success"
                import_info.pop("warning_info", None)
                self._save_state()
                logger.info(f"✅ 清除警告: {date_str}")
    
    def mark_deleted(self, date_str: str, delete_reason: str, deleted_by: str = "manual"):
        """
        标记为已删除状态
        
        Args:
            date_str: 日期字符串
            delete_reason: 删除原因
            deleted_by: 删除方式 (manual/clean_script/auto)
        """
        if date_str in self.state["imports"]:
            import_info = self.state["imports"][date_str]
            
            # 记录删除信息
            import_info["status"] = "deleted"
            import_info["deletion_info"] = {
                "deleted_at": datetime.now().isoformat(),
                "deleted_by": deleted_by,
                "delete_reason": delete_reason,
                "original_imported_count": import_info.get("imported_count", 0),
                "original_status": import_info.get("status", "unknown")
            }
            
            # 清除警告信息（如果有）
            import_info.pop("warning_info", None)
            
            self._save_state()
            logger.info(f"🗑️  标记为已删除: {date_str}, 原因: {delete_reason}")
    
    def get_warnings(self) -> Dict:
        """
        获取所有警告状态的记录
        
        Returns:
            警告记录字典 {date: import_info}
        """
        warnings = {}
        for date_str, import_info in self.state["imports"].items():
            if import_info.get("status") == "warning":
                warnings[date_str] = import_info
        return warnings
    
    def scan_file_changes(self, data_dir: Path, file_pattern: str = "*_data_sma_feature_color.xlsx") -> Dict:
        """
        扫描文件变化，标记缺失或变更的文件
        同时检测 rolled_back 状态的残留数据
        
        Args:
            data_dir: 数据目录
            file_pattern: 文件匹配模式
        
        Returns:
            扫描结果统计
        """
        file_missing_count = 0
        file_changed_count = 0
        file_ok_count = 0
        rolled_back_count = 0
        
        for date_str, import_info in self.state["imports"].items():
            status = import_info.get("status")
            
            # 检测 rolled_back 状态（可能有数据库残留）
            if status == "rolled_back":
                self.mark_warning(date_str, "rollback_residue", None)
                rolled_back_count += 1
                logger.warning(
                    f"⚠️  回滚状态: {import_info.get('filename')} "
                    f"（可能有数据库残留）"
                )
                continue
            
            # 只检查成功导入的记录
            if status != "success":
                continue
            
            filename = import_info.get("filename")
            if not filename:
                continue
            
            file_path = data_dir / filename
            original_hash = import_info.get("file_hash")
            
            # 检查文件是否存在
            if not file_path.exists():
                self.mark_warning(date_str, "file_missing", None)
                file_missing_count += 1
                logger.warning(f"⚠️  文件缺失: {filename}")
                continue
            
            # 检查文件是否变化
            current_hash = self.calculate_file_hash(file_path)
            if current_hash and original_hash and current_hash != original_hash:
                self.mark_warning(date_str, "file_changed", current_hash)
                file_changed_count += 1
                logger.warning(f"⚠️  文件已变化: {filename}")
                continue
            
            file_ok_count += 1
        
        return {
            "file_missing": file_missing_count,
            "file_changed": file_changed_count,
            "file_ok": file_ok_count,
            "rolled_back": rolled_back_count,
            "total_checked": file_missing_count + file_changed_count + file_ok_count + rolled_back_count
        }
    
    def reset(self):
        """重置所有状态（慎用）"""
        self.state = self._create_empty_state()
        self._save_state()
        logger.warning("⚠️  状态文件已重置")


# 全局单例
_state_manager = None
_sector_state_manager = None


def get_state_manager() -> ImportStateManager:
    """获取状态管理器单例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = ImportStateManager()
    return _state_manager


def get_sector_state_manager() -> ImportStateManager:
    """获取板块状态管理器单例"""
    global _sector_state_manager
    if _sector_state_manager is None:
        _sector_state_manager = ImportStateManager("sector_import_state.json")
    return _sector_state_manager


def reload_state_managers():
    """重新加载所有状态管理器（删除数据后调用）"""
    global _state_manager, _sector_state_manager
    if _state_manager is not None:
        _state_manager.state = _state_manager._load_state()
        logger.info("✅ 股票状态管理器已刷新")
    if _sector_state_manager is not None:
        _sector_state_manager.state = _sector_state_manager._load_state()
        logger.info("✅ 板块状态管理器已刷新")
