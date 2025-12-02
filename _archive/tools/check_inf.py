import pandas as pd
import numpy as np

# 读取20251119数据
df = pd.read_excel('data/20251119_data_sma_feature_color.xlsx')

print(f"总行数: {len(df)}")
print(f"总列数: {len(df.columns)}")
print()

# 检查每列是否有无穷大值
inf_cols = []
for col in df.columns:
    try:
        if df[col].dtype in ['float64', 'int64']:
            inf_count = np.isinf(df[col]).sum()
            if inf_count > 0:
                inf_cols.append((col, inf_count))
    except:
        pass

if inf_cols:
    print(f"❌ 发现 {len(inf_cols)} 个列包含无穷大值:")
    for col, count in inf_cols:
        print(f"  - {col}: {count} 个无穷大值")
        # 显示前5个包含无穷大值的股票代码
        inf_rows = df[np.isinf(df[col])]
        if '代码' in df.columns:
            codes = inf_rows['代码'].tolist()[:5]
            print(f"    股票代码: {codes}")
else:
    print("✅ 没有发现无穷大值")
