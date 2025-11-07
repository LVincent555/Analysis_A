#!/usr/bin/env python3
"""
清理冗余文件脚本
分析并删除项目中的冗余文件，包括已被Python脚本替代的bat文件、临时文档等
"""

import os
import sys
from pathlib import Path
from typing import List, Dict

class RedundantFileCleaner:
    """冗余文件清理器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.redundant_files = self._identify_redundant_files()
        
    def _identify_redundant_files(self) -> Dict[str, List[str]]:
        """识别冗余文件"""
        return {
            "已被Python脚本替代的bat文件": [
                "start_backend.bat",
                "start_frontend.bat",
                "restart_backend.bat",
                "cleanup_old_files.bat",
                "backend/import_data.bat",
                "backend/import_data_robust.bat",
                "backend/test_db.bat"
            ],
            "临时文档和记录": [
                "前端修复说明.md",
                "浏览器访问地址.txt",
                "北交所功能进度.txt"
            ],
            "自动生成的大文件": [
                "PROJECT_STRUCTURE.txt"
            ],
            "空配置文件": [
                "package-lock.json"
            ],
            "可能冗余的文档（需确认）": [
                "QUICK_START.md"  # 与快速开始.md内容重复
            ]
        }
    
    def analyze(self) -> Dict[str, Dict]:
        """分析冗余文件"""
        analysis = {}
        
        for category, files in self.redundant_files.items():
            analysis[category] = {
                "files": [],
                "total_size": 0
            }
            
            for file_path in files:
                full_path = self.project_root / file_path
                if full_path.exists():
                    size = full_path.stat().st_size
                    analysis[category]["files"].append({
                        "path": file_path,
                        "size": size,
                        "size_str": self._format_size(size)
                    })
                    analysis[category]["total_size"] += size
        
        return analysis
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def print_analysis(self, analysis: Dict):
        """打印分析结果"""
        print("=" * 70)
        print("🔍 冗余文件分析报告")
        print("=" * 70)
        print()
        
        total_files = 0
        total_size = 0
        
        for category, data in analysis.items():
            if data["files"]:
                print(f"📂 {category}")
                print("-" * 70)
                
                for file_info in data["files"]:
                    print(f"   ✓ {file_info['path']:<50} {file_info['size_str']:>10}")
                    total_files += 1
                    total_size += file_info["size"]
                
                print(f"   小计: {len(data['files'])} 个文件, "
                      f"{self._format_size(data['total_size'])}")
                print()
        
        print("=" * 70)
        print(f"📊 总计: {total_files} 个冗余文件, "
              f"占用空间: {self._format_size(total_size)}")
        print("=" * 70)
        print()
    
    def delete_files(self, analysis: Dict, skip_categories: List[str] = None):
        """删除文件"""
        if skip_categories is None:
            skip_categories = []
        
        deleted_count = 0
        deleted_size = 0
        errors = []
        
        print("🗑️  开始删除文件...")
        print("-" * 70)
        
        for category, data in analysis.items():
            # 跳过需要确认的类别
            if category in skip_categories:
                print(f"⏭️  跳过类别: {category}")
                continue
            
            if data["files"]:
                print(f"\n📂 {category}")
                
                for file_info in data["files"]:
                    file_path = self.project_root / file_info["path"]
                    
                    try:
                        if file_path.exists():
                            file_path.unlink()
                            print(f"   ✅ 已删除: {file_info['path']}")
                            deleted_count += 1
                            deleted_size += file_info["size"]
                        else:
                            print(f"   ⚠️  不存在: {file_info['path']}")
                    except Exception as e:
                        error_msg = f"删除失败: {file_info['path']} - {e}"
                        print(f"   ❌ {error_msg}")
                        errors.append(error_msg)
        
        print()
        print("=" * 70)
        print(f"✅ 删除完成!")
        print(f"   - 成功删除: {deleted_count} 个文件")
        print(f"   - 释放空间: {self._format_size(deleted_size)}")
        
        if errors:
            print(f"   - 失败: {len(errors)} 个文件")
            print("\n错误详情:")
            for error in errors:
                print(f"   ❌ {error}")
        
        print("=" * 70)
    
    def interactive_clean(self):
        """交互式清理"""
        print()
        print("=" * 70)
        print("🧹 股票分析系统 - 冗余文件清理工具")
        print("=" * 70)
        print()
        
        # 分析文件
        analysis = self.analyze()
        
        if not any(data["files"] for data in analysis.values()):
            print("✅ 没有发现冗余文件，项目已经很干净了！")
            return
        
        # 打印分析结果
        self.print_analysis(analysis)
        
        # 询问是否删除
        print("⚠️  警告：文件删除后无法恢复！")
        print()
        print("删除选项:")
        print("  1 - 删除所有冗余文件（推荐）")
        print("  2 - 保留'可能冗余的文档'，删除其他文件")
        print("  3 - 仅删除bat文件")
        print("  4 - 取消操作")
        print()
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == "1":
            confirm = input("\n确认删除所有冗余文件? (yes/no): ").strip().lower()
            if confirm == "yes":
                self.delete_files(analysis)
            else:
                print("❌ 操作已取消")
        
        elif choice == "2":
            confirm = input("\n确认删除（保留可能冗余的文档）? (yes/no): ").strip().lower()
            if confirm == "yes":
                self.delete_files(analysis, skip_categories=["可能冗余的文档（需确认）"])
            else:
                print("❌ 操作已取消")
        
        elif choice == "3":
            confirm = input("\n确认仅删除bat文件? (yes/no): ").strip().lower()
            if confirm == "yes":
                # 只保留bat文件类别
                bat_only = {
                    k: v for k, v in analysis.items() 
                    if "bat" in k.lower()
                }
                self.delete_files(bat_only)
            else:
                print("❌ 操作已取消")
        
        else:
            print("❌ 操作已取消")


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    
    # 创建清理器
    cleaner = RedundantFileCleaner(script_dir)
    
    # 交互式清理
    cleaner.interactive_clean()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)
