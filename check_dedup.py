"""检查去重详情"""
import json

with open('data/data_import_state.json', 'r', encoding='utf-8') as f:
    state = json.load(f)

dedup_info = state['imports'].get('20251107', {}).get('dedup_info', {})

print("=" * 70)
print("去重详情")
print("=" * 70)
print(f"检测到重复的代码: {dedup_info.get('detected_duplicates', [])}")
print(f"删除数量: {dedup_info.get('removed_count', 0)}")
print()
print("删除详情:")
for detail in dedup_info.get('removed_details', []):
    print(f"  • {detail['code']}({detail['name']}) 行{detail['rank']}")
    
    # 兼容新旧格式
    if 'global_mean' in detail:
        # 新格式：全局均值
        print(f"    分数: {detail['total_score']:.2f}, 全局均值: {detail['global_mean']:.2f}")
        print(f"    距离: {detail['distance_from_mean']:.2f}, Z-score: {detail['z_score']:.2f}")
    else:
        # 旧格式：周围均值
        print(f"    分数: {detail['total_score']:.2f}, 周围均值: {detail.get('context_mean', 'N/A'):.2f}")
        print(f"    偏离: {detail.get('deviation', 'N/A'):.2f}σ")
    
    print(f"    原因: {detail['reason']}")
    print()

print("=" * 70)
print(f"错误信息: {state['imports'].get('20251107', {}).get('error', 'N/A')}")
