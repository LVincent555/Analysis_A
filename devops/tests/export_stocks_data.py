#!/usr/bin/env python3
"""
导出特定股票的全量历史数据到txt文件
"""
import requests
import json
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"
OUTPUT_FILE = "stocks_full_data.txt"

# 要查询的股票列表
STOCKS = [
    {"code": "000070", "name": "特发信息"},
    {"code": "002279", "name": "久其软件"},
    {"code": "600343", "name": "航天动力"},
    {"code": "000859", "name": "国风新材"},
    {"code": "600734", "name": "实达集团"},
    {"code": "002046", "name": "国机精工"},
]

def format_daily_data(daily_data):
    """格式化单条每日数据"""
    lines = []
    lines.append(f"    日期: {daily_data.get('date', 'N/A')}")
    lines.append(f"    排名: {daily_data.get('rank', 'N/A')}")
    lines.append(f"    总分: {daily_data.get('total_score', 'N/A')}")
    lines.append(f"    开盘: {daily_data.get('open_price', 'N/A')}")
    lines.append(f"    最高: {daily_data.get('high_price', 'N/A')}")
    lines.append(f"    最低: {daily_data.get('low_price', 'N/A')}")
    lines.append(f"    收盘: {daily_data.get('close_price', 'N/A')}")
    lines.append(f"    涨跌幅: {daily_data.get('price_change', 'N/A')}%")
    lines.append(f"    换手率: {daily_data.get('turnover_rate_percent', 'N/A')}%")
    lines.append(f"    成交量: {daily_data.get('volume', 'N/A')}")
    lines.append(f"    波动率: {daily_data.get('volatility', 'N/A')}")
    lines.append(f"    总市值(亿): {daily_data.get('market_cap_billions', 'N/A')}")
    lines.append(f"    BETA: {daily_data.get('beta', 'N/A')}")
    lines.append(f"    相关性: {daily_data.get('correlation', 'N/A')}")
    lines.append(f"    RSI: {daily_data.get('rsi', 'N/A')}")
    lines.append(f"    MACD: {daily_data.get('histgram', 'N/A')}")
    lines.append(f"    DIF: {daily_data.get('dif', 'N/A')}")
    lines.append(f"    DEA: {daily_data.get('dem', 'N/A')}")
    lines.append(f"    KDJ_K: {daily_data.get('slowk', 'N/A')}")
    lines.append(f"    ADX: {daily_data.get('adx', 'N/A')}")
    lines.append(f"    OBV: {daily_data.get('obv', 'N/A')}")
    lines.append(f"    布林带上轨: {daily_data.get('upper_band', 'N/A')}")
    lines.append(f"    布林带中轨: {daily_data.get('middle_band', 'N/A')}")
    lines.append(f"    布林带下轨: {daily_data.get('lower_band', 'N/A')}")
    lines.append("")
    return "\n".join(lines)

def export_stock_data(stock_code, stock_name):
    """导出单只股票的数据"""
    print(f"\n{'='*80}")
    print(f"正在查询: {stock_name} ({stock_code})")
    print(f"{'='*80}")
    
    try:
        # 调用API查询全量数据
        response = requests.get(
            f"{BASE_URL}/api/stock/search",
            params={"q": stock_code},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ API返回错误: {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
        
        data = response.json()
        
        if not data or len(data) == 0:
            print(f"⚠️  未找到股票数据")
            return None
        
        # 假设返回的是列表，取第一个匹配的股票
        stock_data = data[0] if isinstance(data, list) else data
        
        print(f"✅ 查询成功")
        print(f"   股票代码: {stock_data.get('code', 'N/A')}")
        print(f"   股票名称: {stock_data.get('name', 'N/A')}")
        print(f"   行业: {stock_data.get('industry', 'N/A')}")
        
        daily_data = stock_data.get('daily_data', [])
        print(f"   历史数据条数: {len(daily_data)}")
        
        return stock_data
        
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return None
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return None

def write_to_file(all_stocks_data, output_file):
    """将所有股票数据写入txt文件"""
    print(f"\n{'='*80}")
    print(f"开始写入文件: {output_file}")
    print(f"{'='*80}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入文件头
        f.write("=" * 100 + "\n")
        f.write("股票全量数据导出\n")
        f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"股票数量: {len(all_stocks_data)}\n")
        f.write("=" * 100 + "\n\n")
        
        # 写入每只股票的数据
        for i, stock_data in enumerate(all_stocks_data, 1):
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"股票 {i}/{len(all_stocks_data)}\n")
            f.write("=" * 100 + "\n\n")
            
            # 基础信息
            f.write(f"股票代码: {stock_data.get('code', 'N/A')}\n")
            f.write(f"股票名称: {stock_data.get('name', 'N/A')}\n")
            f.write(f"所属行业: {stock_data.get('industry', 'N/A')}\n")
            f.write(f"总记录数: {stock_data.get('total_count', 'N/A')}\n\n")
            
            # 历史数据
            daily_data = stock_data.get('daily_data', [])
            f.write(f"历史数据记录数: {len(daily_data)}\n")
            f.write("-" * 100 + "\n\n")
            
            if daily_data:
                for j, daily in enumerate(daily_data, 1):
                    f.write(f"  [{j}/{len(daily_data)}] ----------------\n")
                    f.write(format_daily_data(daily))
                    f.write("\n")
            else:
                f.write("  (无历史数据)\n\n")
    
    print(f"✅ 数据已成功写入: {output_file}")

def main():
    """主函数"""
    print("\n" + "=" * 100)
    print("股票全量数据导出工具")
    print("=" * 100)
    print(f"\n目标股票数量: {len(STOCKS)}")
    print(f"API地址: {BASE_URL}")
    print(f"输出文件: {OUTPUT_FILE}")
    
    # 查询所有股票
    all_stocks_data = []
    
    for stock in STOCKS:
        stock_data = export_stock_data(stock['code'], stock['name'])
        if stock_data:
            all_stocks_data.append(stock_data)
    
    # 写入文件
    if all_stocks_data:
        write_to_file(all_stocks_data, OUTPUT_FILE)
        
        print(f"\n{'='*100}")
        print("✅ 导出完成！")
        print(f"{'='*100}")
        print(f"\n成功导出 {len(all_stocks_data)}/{len(STOCKS)} 只股票的数据")
        print(f"文件保存在: {OUTPUT_FILE}")
        print("\n可以用以下命令查看文件内容:")
        print(f"  type {OUTPUT_FILE}  # Windows")
        print(f"  cat {OUTPUT_FILE}   # Linux/Mac")
    else:
        print(f"\n❌ 没有成功获取任何股票数据")

if __name__ == "__main__":
    main()
