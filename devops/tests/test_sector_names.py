#!/usr/bin/env python3
"""测试板块名称缓存"""
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

from app.services.memory_cache import memory_cache

print("=" * 60)
print("测试板块名称缓存")
print("=" * 60)

# 加载内存缓存
if not memory_cache.is_loaded():
    print("加载内存缓存...")
    memory_cache.load_all_data()

print(f"\n板块基础信息总数: {len(memory_cache.sectors)}")

# 显示前20个板块
print("\n前20个板块信息:")
for i, (sector_id, sector) in enumerate(list(memory_cache.sectors.items())[:20], 1):
    print(f"{i:2d}. ID={sector_id:3d}, 名称={sector.sector_name}")

# 测试get_sector_info方法
print("\n" + "=" * 60)
print("测试get_sector_info方法")
print("=" * 60)

test_ids = [486, 561, 218, 532, 550]
for sector_id in test_ids:
    sector_info = memory_cache.get_sector_info(sector_id)
    if sector_info:
        print(f"ID {sector_id}: {sector_info.sector_name}")
    else:
        print(f"ID {sector_id}: ❌ 未找到")

# 测试板块排名API
print("\n" + "=" * 60)
print("测试板块排名数据")
print("=" * 60)

latest_date = memory_cache.get_sector_latest_date()
print(f"最新日期: {latest_date}")

if latest_date:
    top_sectors = memory_cache.get_top_n_sectors(latest_date, 10)
    print(f"\nTOP10板块:")
    for i, sector_data in enumerate(top_sectors, 1):
        sector_info = memory_cache.get_sector_info(sector_data.sector_id)
        sector_name = sector_info.sector_name if sector_info else f"ID:{sector_data.sector_id}"
        print(f"{i:2d}. {sector_name} (ID={sector_data.sector_id}, Rank={sector_data.rank})")

print("\n" + "=" * 60)
