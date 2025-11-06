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
        """加载状态文件"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"状态文件读取失败，创建新文件: {str(e)}")
                return self._create_empty_state()
        else:
            return self._create_empty_state()
    
    def _create_empty_state(self) -> Dict:
        """创建空状态"""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "database": "unknown",
            "imports": {}
        }
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            logger.debug(f"状态文件已保存: {self.state_file}")
        except Exception as e:
            logger.error(f"状态文件保存失败: {str(e)}")
    
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
        
        Args:
            date_str: 日期字符串
            file_path: 文件路径
        
        Returns:
            True表示需要导入，False表示跳过
        """
        if date_str not in self.state["imports"]:
            return True  # 从未导入
        
        import_info = self.state["imports"][date_str]
        
        # 上次失败，需要重新导入
        if import_info.get("status") != "success":
            return True
        
        # 检查文件是否变化
        current_hash = self.calculate_file_hash(file_path)
        if current_hash and current_hash != import_info.get("file_hash", ""):
            logger.info(f"检测到文件变化: {file_path.name}，将重新导入")
            return True
        
        return False  # 已成功导入且文件未变
    
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
            "attempt_count": self.state["imports"].get(date_str, {}).get("attempt_count", 0) + 1
        }
        self._save_state()
        logger.info(f"开始导入: {date_str} - {filename}")
    
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
        failed = sum(1 for i in imports.values() if i.get("status") == "failed")
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
    
    def reset(self):
        """重置所有状态（慎用）"""
        self.state = self._create_empty_state()
        self._save_state()
        logger.warning("⚠️  状态文件已重置")


# 全局单例
_state_manager = None


def get_state_manager() -> ImportStateManager:
    """获取状态管理器单例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = ImportStateManager()
    return _state_manager
