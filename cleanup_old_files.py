"""
清理旧版本文件脚本 v0.2.0
删除重构前的单文件版本，保留模块化版本

用法:
    python cleanup_old_files.py           # 交互式确认
    python cleanup_old_files.py --yes     # 自动确认删除
    python cleanup_old_files.py --dry-run # 仅显示，不删除
"""
import os
import sys
from pathlib import Path

class Color:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header():
    """打印头部"""
    print("=" * 60)
    print(f"{Color.BOLD}清理旧版本文件脚本 v0.2.0{Color.END}")
    print("=" * 60)
    print()

def confirm_deletion():
    """确认删除"""
    print(f"{Color.YELLOW}本脚本将删除以下旧版本文件：{Color.END}")
    print(f"  - backend/main.py {Color.BLUE}(旧的单文件后端){Color.END}")
    print(f"  - frontend/src/App.v1.js {Color.BLUE}(旧版本备份){Color.END}")
    print()
    print(f"{Color.RED}注意：这些文件将被永久删除！{Color.END}")
    print()
    
    response = input(f"确认删除? (Y/N): ").strip().upper()
    return response == 'Y'

def delete_file(file_path: Path, description: str, dry_run: bool = False) -> bool:
    """删除文件"""
    if file_path.exists():
        if dry_run:
            print(f"{Color.BLUE}[模拟]{Color.END} {file_path} - {description}")
            return True
        try:
            os.remove(file_path)
            print(f"{Color.GREEN}[✓ 已删除]{Color.END} {file_path} - {description}")
            return True
        except Exception as e:
            print(f"{Color.RED}[✗ 失败]{Color.END} {file_path} - {e}")
            return False
    else:
        print(f"{Color.YELLOW}[○ 跳过]{Color.END} {file_path} - 文件不存在")
        return False

def main():
    """主函数"""
    # 解析命令行参数
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv
    dry_run = "--dry-run" in sys.argv
    
    print_header()
    
    if dry_run:
        print(f"{Color.YELLOW}[模拟模式] 仅显示将要删除的文件，不会实际删除{Color.END}")
        print()
    
    # 获取项目根目录
    script_dir = Path(__file__).parent
    
    # 定义要删除的文件
    files_to_delete = [
        (script_dir / "backend" / "main.py", "旧的单文件后端"),
        (script_dir / "frontend" / "src" / "App.v1.js", "旧版本备份"),
    ]
    
    # 确认删除
    if not auto_confirm and not dry_run:
        if not confirm_deletion():
            print()
            print(f"{Color.YELLOW}操作已取消{Color.END}")
            return
    elif auto_confirm:
        print(f"{Color.GREEN}[自动确认模式] 跳过确认步骤{Color.END}")
        print()
    
    print()
    print(f"{Color.BLUE}开始清理...{Color.END}")
    print()
    
    # 执行删除
    deleted_count = 0
    for file_path, description in files_to_delete:
        if delete_file(file_path, description, dry_run=dry_run):
            deleted_count += 1
    
    # 显示结果
    print()
    print("=" * 60)
    if dry_run:
        print(f"{Color.BLUE}✓ 模拟完成！{Color.END}")
        print("=" * 60)
        print()
        print(f"将删除 {deleted_count} 个文件（实际未删除）")
    else:
        print(f"{Color.GREEN}✓ 清理完成！{Color.END}")
        print("=" * 60)
        print()
        print(f"已删除 {deleted_count} 个文件")
    print()
    print(f"{Color.BLUE}保留的文件：{Color.END}")
    print(f"  - backend/app/ {Color.GREEN}(新的模块化后端){Color.END}")
    print(f"  - frontend/src/App.js {Color.GREEN}(当前使用版本){Color.END}")
    print(f"  - frontend/src/App.v2.js {Color.GREEN}(新的模块化版本){Color.END}")
    print()

if __name__ == "__main__":
    main()
