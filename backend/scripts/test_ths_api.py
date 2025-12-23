#!/usr/bin/env python3
"""
测试同花顺成分股替代方案
"""
import time

print("=" * 60)
print("测试方案一：pywencai (问财)")
print("=" * 60)

try:
    import pywencai
    
    board_name = "海峡两岸"
    query = f"{board_name}概念成分股"
    
    print(f"查询: {query}")
    start = time.time()
    
    df = pywencai.get(question=query, loop=True)
    
    elapsed = time.time() - start
    print(f"耗时: {elapsed:.2f}秒")
    
    if df is not None and not df.empty:
        print(f"✅ 成功！获取到 {len(df)} 条记录")
        print(f"列名: {df.columns.tolist()}")
        print("\n前5条数据:")
        print(df.head())
    else:
        print("❌ 返回空数据")
        
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
