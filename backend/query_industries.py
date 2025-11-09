"""直接查询数据库中的行业名称"""
import psycopg2

# 连接数据库（使用固定配置）
conn = psycopg2.connect(
    host="192.168.182.128",
    port=5432,
    database="db_20251106_analysis_a",
    user="postgres",
    password="123456"
)

cursor = conn.cursor()

# 查询所有行业名称
print("查询 stocks 表中的所有行业...")
cursor.execute("""
    SELECT DISTINCT industry, COUNT(*) as count
    FROM stocks
    WHERE industry IS NOT NULL AND industry != ''
    GROUP BY industry
    ORDER BY count DESC
""")

industries = cursor.fetchall()
print(f"\n数据库中共有 {len(industries)} 个行业\n")

# 显示前20个
print("前20个行业（按股票数量排序）：")
for ind, count in industries[:20]:
    print(f"  {ind}: {count}只")

# 查找包含"通"的行业
print("\n\n包含'通'字的行业：")
for ind, count in industries:
    if '通' in ind:
        print(f"  - {ind}: {count}只")

# 查找包含"信"的行业
print("\n包含'信'字的行业：")
for ind, count in industries:
    if '信' in ind:
        print(f"  - {ind}: {count}只")

# 精确查找
cursor.execute("""
    SELECT industry, COUNT(*) as count
    FROM stocks
    WHERE industry = '通信设备'
    GROUP BY industry
""")
result1 = cursor.fetchone()

cursor.execute("""
    SELECT industry, COUNT(*) as count
    FROM stocks
    WHERE industry = '通讯设备'
    GROUP BY industry
""")
result2 = cursor.fetchone()

print("\n\n精确匹配：")
if result1:
    print(f"  ✅ '通信设备' 存在，有 {result1[1]} 只股票")
else:
    print(f"  ❌ '通信设备' 不存在")

if result2:
    print(f"  ✅ '通讯设备' 存在，有 {result2[1]} 只股票")
else:
    print(f"  ❌ '通讯设备' 不存在")

cursor.close()
conn.close()
