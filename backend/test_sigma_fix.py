"""
测试σ筛选修复
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("测试排名跳变σ筛选修复")
print("=" * 60 + "\n")

# 测试不同σ倍数
sigma_values = [0.15, 0.3, 0.5, 0.75, 1.0]

for sigma in sigma_values:
    print(f"\n{'='*60}")
    print(f"测试 σ = {sigma}")
    print('='*60)
    
    try:
        r = requests.get(
            f"{BASE_URL}/rank-jump?jump_threshold=2000&filter_stocks=true&sigma_multiplier={sigma}",
            timeout=10
        )
        
        if r.status_code == 200:
            data = r.json()
            total = data.get('total_count', 0)
            sigma_count = len(data.get('sigma_stocks', []))
            mean = data.get('mean_rank_change', 0)
            std = data.get('std_rank_change', 0)
            sigma_range = data.get('sigma_range', [0, 0])
            
            print(f"✅ 状态码: 200")
            print(f"   总股票数: {total}只")
            print(f"   均值(绝对值): {mean:.1f}")
            print(f"   标准差: {std:.1f}")
            print(f"   ±{sigma}σ范围: [{sigma_range[0]:.1f}, {sigma_range[1]:.1f}]")
            print(f"   ±{sigma}σ筛选结果: {sigma_count}只 ({sigma_count/total*100:.1f}%)")
            
            # 验证逻辑正确性
            if sigma_count > 0:
                print(f"   ✅ σ筛选正常工作！")
            else:
                print(f"   ⚠️  σ筛选无结果")
        else:
            print(f"❌ 状态码: {r.status_code}")
            
    except Exception as e:
        print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60 + "\n")
