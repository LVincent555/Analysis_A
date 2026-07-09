"""
后端API测试脚本
测试所有API端点的功能
"""
import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

class Color:
    """终端颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, status, message=""):
    """打印测试结果"""
    symbol = "✓" if status else "✗"
    color = Color.GREEN if status else Color.RED
    print(f"{color}{symbol}{Color.END} {name}", end="")
    if message:
        print(f" - {message}")
    else:
        print()

def test_root():
    """测试根路径"""
    try:
        response = requests.get(f"{API_BASE_URL}/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        print_test("根路径 GET /", True, f"版本: {data.get('version')}")
        return True
    except Exception as e:
        print_test("根路径 GET /", False, str(e))
        return False

def test_health():
    """测试健康检查"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print_test("健康检查 GET /health", True)
        return True
    except Exception as e:
        print_test("健康检查 GET /health", False, str(e))
        return False

def test_get_dates():
    """测试获取可用日期"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/dates")
        assert response.status_code == 200
        data = response.json()
        assert "dates" in data
        assert "latest_date" in data
        print_test("获取日期 GET /api/dates", True, f"共{len(data['dates'])}个日期")
        return True, data
    except Exception as e:
        print_test("获取日期 GET /api/dates", False, str(e))
        return False, None

def test_analyze_period(period=2):
    """测试周期分析"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/analyze/{period}")
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "total_stocks" in data
        assert "stocks" in data
        print_test(f"周期分析 GET /api/analyze/{period}", True, 
                  f"分析{period}天，找到{data['total_stocks']}只股票")
        return True, data
    except Exception as e:
        print_test(f"周期分析 GET /api/analyze/{period}", False, str(e))
        return False, None

def test_query_stock(stock_code="000001"):
    """测试股票查询"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/stock/{stock_code}")
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "name" in data
            assert "appears_count" in data
            print_test(f"股票查询 GET /api/stock/{stock_code}", True, 
                      f"{data['name']} 出现{data['appears_count']}次")
            return True, data
        elif response.status_code == 404:
            print_test(f"股票查询 GET /api/stock/{stock_code}", True, 
                      "股票不存在（正常情况）")
            return True, None
        else:
            raise Exception(f"状态码: {response.status_code}")
    except Exception as e:
        print_test(f"股票查询 GET /api/stock/{stock_code}", False, str(e))
        return False, None

def test_top1000_industry():
    """测试前1000名行业统计"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/industry/top1000")
        assert response.status_code == 200
        data = response.json()
        assert "date" in data
        assert "total_stocks" in data
        assert "stats" in data
        print_test("行业统计 GET /api/industry/top1000", True, 
                  f"共{len(data['stats'])}个行业")
        return True, data
    except Exception as e:
        print_test("行业统计 GET /api/industry/top1000", False, str(e))
        return False, None

def test_industry_trend():
    """测试行业趋势"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/industry/trend")
        assert response.status_code == 200
        data = response.json()
        assert "industries" in data
        assert "data" in data
        print_test("行业趋势 GET /api/industry/trend", True, 
                  f"共{len(data['industries'])}个行业，{len(data['data'])}天数据")
        return True, data
    except Exception as e:
        print_test("行业趋势 GET /api/industry/trend", False, str(e))
        return False, None

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  后端API测试 - A股数据分析系统 v0.2.0")
    print("="*60)
    print(f"\nAPI地址: {API_BASE_URL}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n开始测试...\n")
    
    # 检查服务器是否运行
    try:
        requests.get(API_BASE_URL, timeout=2)
    except requests.exceptions.ConnectionError:
        print(f"{Color.RED}✗ 无法连接到服务器！请先启动后端服务{Color.END}")
        print(f"  运行命令: cd backend && uvicorn app.main:app --reload")
        return
    except Exception as e:
        print(f"{Color.RED}✗ 连接错误: {e}{Color.END}")
        return
    
    results = []
    
    # 基础测试
    print(f"{Color.BLUE}=== 基础功能测试 ==={Color.END}")
    results.append(test_root())
    results.append(test_health())
    
    # 数据接口测试
    print(f"\n{Color.BLUE}=== 数据接口测试 ==={Color.END}")
    success, dates_data = test_get_dates()
    results.append(success)
    
    # 分析接口测试
    print(f"\n{Color.BLUE}=== 分析功能测试 ==={Color.END}")
    for period in [2, 3, 5, 7, 14]:
        success, _ = test_analyze_period(period)
        results.append(success)
    
    # 股票查询测试
    print(f"\n{Color.BLUE}=== 股票查询测试 ==={Color.END}")
    # 测试存在的股票
    success, _ = test_query_stock("600000")
    results.append(success)
    # 测试不存在的股票
    success, _ = test_query_stock("999999")
    results.append(success)
    
    # 行业分析测试
    print(f"\n{Color.BLUE}=== 行业分析测试 ==={Color.END}")
    success, _ = test_top1000_industry()
    results.append(success)
    success, _ = test_industry_trend()
    results.append(success)
    
    # 汇总结果
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    if passed == total:
        print(f"{Color.GREEN}✓ 所有测试通过！ ({passed}/{total}){Color.END}")
    else:
        print(f"{Color.YELLOW}⚠ 部分测试失败： {passed}/{total} 通过 ({success_rate:.1f}%){Color.END}")
    
    print("="*60)
    print()

if __name__ == "__main__":
    main()
