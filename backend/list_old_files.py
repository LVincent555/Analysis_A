"""
列出项目中的旧文件和不需要的文件（仅查看，不删除）
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent

# 要删除的文件列表
FILES_TO_DELETE = [
    # 旧的Excel版本服务文件（已被_db版本替代）
    "app/services/analysis_service.py",
    "app/services/data_loader.py",
    "app/services/industry_service.py",
    "app/services/rank_jump_service.py",
    "app/services/steady_rise_service.py",
    "app/services/stock_service.py",
    
    # 临时测试文件
    "test_all_services.py",
    "test_anchor_logic.py",
    "test_api.py",
    "test_api_response.py",
    "test_final.py",
    "test_fixes.py",
    "test_latest_only.py",
    "test_new_logic.py",
    "test_sigma_fix.py",
    "test_startup.py",
    "test_trend_api.py",
    "test_with_clear.py",
    
    # 临时检查脚本（保留clear_cache.py）
    "check_bjs_data.py",
    "check_latest_date.py",
    "check_stock_603262.py",
    
    # 旧的文档和记录
    "修复总结.md",
    "修复记录.md",
    "导入系统设计文档.md",
    "数据导入指南.md",
]

def main():
    print("=" * 80)
    print("📋 项目清理报告")
    print("=" * 80)
    
    exists_files = []
    missing_files = []
    total_size = 0
    
    print("\n🔍 扫描旧文件...\n")
    
    for file_path in FILES_TO_DELETE:
        full_path = BASE_DIR / file_path
        
        if full_path.exists():
            file_size = full_path.stat().st_size
            exists_files.append((file_path, file_size))
            total_size += file_size
        else:
            missing_files.append(file_path)
    
    # 分类显示
    print("📦 旧的Excel版本服务文件（已被_db版本替代）：")
    print("-" * 80)
    for file_path, size in exists_files:
        if "services" in file_path and not file_path.endswith("_db.py"):
            print(f"  ❌ {file_path:50s} {size:>8,} bytes")
    
    print("\n🧪 临时测试文件：")
    print("-" * 80)
    for file_path, size in exists_files:
        if file_path.startswith("test_"):
            print(f"  ❌ {file_path:50s} {size:>8,} bytes")
    
    print("\n🔧 临时检查脚本：")
    print("-" * 80)
    for file_path, size in exists_files:
        if file_path.startswith("check_"):
            print(f"  ❌ {file_path:50s} {size:>8,} bytes")
    
    print("\n📄 旧的文档文件：")
    print("-" * 80)
    for file_path, size in exists_files:
        if file_path.endswith(".md"):
            print(f"  ❌ {file_path:50s} {size:>8,} bytes")
    
    print("\n" + "=" * 80)
    print("📊 统计：")
    print(f"  找到的文件: {len(exists_files)} 个")
    print(f"  不存在的文件: {len(missing_files)} 个")
    print(f"  总大小: {total_size:,} bytes ({total_size / 1024:.2f} KB)")
    print("=" * 80)
    
    if missing_files:
        print("\n⚠️  以下文件不存在（可能已删除）：")
        for file_path in missing_files:
            print(f"  - {file_path}")
    
    print("\n✅ 保留的重要文件：")
    print("-" * 80)
    keep_files = [
        "app/services/analysis_service_db.py",
        "app/services/db_data_loader.py",
        "app/services/industry_service_db.py",
        "app/services/rank_jump_service_db.py",
        "app/services/steady_rise_service_db.py",
        "app/services/stock_service_db.py",
        "clear_cache.py",
        "scripts/import_data_robust.py",
    ]
    for file_path in keep_files:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
    
    print("\n" + "=" * 80)
    print("💡 提示：")
    print("  - 运行 'python cleanup_old_files.py' 执行清理")
    print("  - 建议先提交Git，以便需要时可以恢复")
    print("=" * 80)
    print()

if __name__ == "__main__":
    main()
