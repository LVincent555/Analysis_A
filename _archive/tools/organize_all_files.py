#!/usr/bin/env python3
"""
文件整理脚本 - 整理所有根目录的文档和测试脚本
"""
import os
import shutil
from pathlib import Path
import glob

# 当前目录
ROOT_DIR = Path(__file__).parent

# 目标目录
DOCS_DIR = ROOT_DIR / "docs" / "optimization"
SCRIPTS_DIR = ROOT_DIR / "scripts" / "tests"

# 创建目标目录
DOCS_DIR.mkdir(parents=True, exist_ok=True)
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("="*60)
    print("📁 文件整理脚本（完整版）")
    print("="*60)
    print()
    
    # 1. 移动优化相关的md文档
    print("📄 移动优化文档到 docs/optimization/")
    print("-"*60)
    
    md_patterns = [
        "*优化*.md",
        "*问题*.md",
        "*信号*.md",
        "*接口*.md",
        "*性能*.md",
        "*POOL*.md",
        "*修复*.md"
    ]
    
    docs_moved = 0
    for pattern in md_patterns:
        for md_file in ROOT_DIR.glob(pattern):
            if md_file.is_file():
                try:
                    target = DOCS_DIR / md_file.name
                    shutil.move(str(md_file), str(target))
                    print(f"  ✅ {md_file.name}")
                    docs_moved += 1
                except Exception as e:
                    print(f"  ❌ {md_file.name}: {e}")
    
    print(f"小计: {docs_moved} 个文档已移动")
    print()
    
    # 2. 移动所有test_开头的py文件
    print("🧪 移动测试脚本到 scripts/tests/")
    print("-"*60)
    
    test_moved = 0
    for test_file in ROOT_DIR.glob("test_*.py"):
        if test_file.is_file():
            try:
                target = SCRIPTS_DIR / test_file.name
                shutil.move(str(test_file), str(target))
                print(f"  ✅ {test_file.name}")
                test_moved += 1
            except Exception as e:
                print(f"  ❌ {test_file.name}: {e}")
    
    print(f"小计: {test_moved} 个测试脚本已移动")
    print()
    
    # 3. 移动其他优化相关的脚本
    print("🔧 移动其他优化脚本到 scripts/tests/")
    print("-"*60)
    
    other_scripts = [
        "快速修复脚本.py",
        "database_优化版.py",
        "database_服务器优化版.py",
        "analyze_yuanshen_pattern.py",
        "export_stocks_data.py",
    ]
    
    other_moved = 0
    for script in other_scripts:
        script_path = ROOT_DIR / script
        if script_path.exists():
            try:
                target = SCRIPTS_DIR / script
                shutil.move(str(script_path), str(target))
                print(f"  ✅ {script}")
                other_moved += 1
            except Exception as e:
                print(f"  ❌ {script}: {e}")
        else:
            print(f"  ⚠️  {script} (不存在)")
    
    print(f"小计: {other_moved} 个脚本已移动")
    print()
    
    # 4. 移动数据文件
    print("📦 移动数据文件到 data/exports/")
    print("-"*60)
    
    data_dir = ROOT_DIR / "data" / "exports"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    data_files = ["stocks_full_data.txt"]
    data_moved = 0
    
    for data_file in data_files:
        data_path = ROOT_DIR / data_file
        if data_path.exists():
            try:
                target = data_dir / data_file
                shutil.move(str(data_path), str(target))
                print(f"  ✅ {data_file}")
                data_moved += 1
            except Exception as e:
                print(f"  ❌ {data_file}: {e}")
        else:
            print(f"  ⚠️  {data_file} (不存在)")
    
    print(f"小计: {data_moved} 个数据文件已移动")
    print()
    
    print("="*60)
    print("✅ 文件整理完成！")
    print("="*60)
    print()
    print("📂 整理结果：")
    print(f"   docs/optimization/  - {docs_moved} 个优化文档")
    print(f"   scripts/tests/      - {test_moved + other_moved} 个测试脚本")
    print(f"   data/exports/       - {data_moved} 个数据文件")
    print()
    print("💡 下一步：")
    print("   1. 查看整理后的目录结构")
    print("   2. git add .")
    print("   3. git commit -m 'chore: 整理优化文档和测试脚本到专门目录'")
    print("   4. git push")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
