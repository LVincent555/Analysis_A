"""临时脚本：检查数据库中的行业名称"""
import sys
sys.path.insert(0, '.')

from app.services.memory_cache import memory_cache

# 获取所有行业名称
industries = set()
for stock in memory_cache.get_all_stocks().values():
    if stock.industry:
        industries.add(stock.industry)

# 筛选包含"通"或"信"的行业
matching_industries = sorted([ind for ind in industries if '通' in ind or '信' in ind])

print("包含'通'或'信'的行业名称：")
for ind in matching_industries:
    print(f"  - {ind}")

print(f"\n总共找到 {len(matching_industries)} 个匹配的行业")

# 检查具体的"通信设备"
if "通信设备" in industries:
    print("\n✅ 找到'通信设备'")
elif "通讯设备" in industries:
    print("\n⚠️  数据库中是'通讯设备'（讯），不是'通信设备'（信）")
else:
    print("\n❌ 没有找到'通信设备'或'通讯设备'")

# 显示所有行业
print(f"\n数据库中共有 {len(industries)} 个行业")
