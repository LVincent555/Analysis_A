"""
清理项目中的旧文件和不需要的文件

此脚本会删除：
1. 旧的基于Excel的服务文件（已被_db版本替代）
2. 临时测试文件
3. 临时检查脚本
4. 旧的文档文件
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
    
    # 临时检查脚本
    "check_bjs_data.py",
    "check_latest_date.py",
    "check_stock_603262.py",
    
    # 旧的文档和记录
    "修复总结.md",
    "修复记录.md",
    "导入系统设计文档.md",
    "数据导入指南.md",
]

# 要保留的文件（安全检查）
KEEP_FILES = [
    "app/services/analysis_service_db.py",
    "app/services/db_data_loader.py",
    "app/services/industry_service_db.py",
    "app/services/rank_jump_service_db.py",
    "app/services/steady_rise_service_db.py",
    "app/services/stock_service_db.py",
    "clear_cache.py",
]

def main():
    print("=" * 60)
    print("🧹 开始清理旧文件")
    print("=" * 60)
    
    deleted_count = 0
    skipped_count = 0
    total_size = 0
    
    print("\n📋 将要删除的文件：\n")
    
    for file_path in FILES_TO_DELETE:
        full_path = BASE_DIR / file_path
        
        if full_path.exists():
            file_size = full_path.stat().st_size
            print(f"  ✓ {file_path} ({file_size} bytes)")
        else:
            print(f"  ⚠ {file_path} (不存在)")
    
    print("\n" + "=" * 60)
    confirm = input("确认删除以上文件？(yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("\n❌ 取消删除操作")
        return
    
    print("\n开始删除...\n")
    
    for file_path in FILES_TO_DELETE:
        full_path = BASE_DIR / file_path
        
        if full_path.exists():
            try:
                file_size = full_path.stat().st_size
                full_path.unlink()
                deleted_count += 1
                total_size += file_size
                print(f"  ✅ 已删除: {file_path}")
            except Exception as e:
                print(f"  ❌ 删除失败: {file_path} - {e}")
                skipped_count += 1
        else:
            skipped_count += 1
    
    print("\n" + "=" * 60)
    print("📊 清理统计：")
    print(f"  已删除文件: {deleted_count} 个")
    print(f"  跳过文件: {skipped_count} 个")
    print(f"  释放空间: {total_size / 1024:.2f} KB")
    print("=" * 60)
    
    # 显示保留的重要文件
    print("\n✅ 以下重要文件已保留：")
    for file_path in KEEP_FILES:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
    
    print("\n🎉 清理完成！\n")

if __name__ == "__main__":
    main()
