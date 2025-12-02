#!/usr/bin/env python3
"""
API性能压测脚本
测试优化后的API性能，每个接口压测10000次
"""
import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json

# 配置
BASE_URL = "http://localhost:8000"
TOTAL_REQUESTS = 10000  # 每个API测试1万次
CONCURRENT_WORKERS = 50  # 并发线程数

# 测试的API列表
TEST_APIS = [
    {
        "name": "行业TOP1000统计",
        "url": f"{BASE_URL}/api/industry/top1000",
        "params": {"limit": 1000, "date": "20251120"}
    },
    {
        "name": "行业加权分析",
        "url": f"{BASE_URL}/api/industry/weighted",
        "params": {"k": 1, "metric": "B1", "date": "20251120"}
    },
    {
        "name": "排名跳跃分析",
        "url": f"{BASE_URL}/api/rank-jump",
        "params": {"board_type": "main", "jump_threshold": 2000, "sigma_multiplier": 1, "date": "20251120"}
    },
    {
        "name": "综合分析",
        "url": f"{BASE_URL}/api/analyze/2",
        "params": {"board_type": "main", "top_n": 100, "date": "20251120"}
    }
]


class APIBenchmark:
    """API压测工具"""
    
    def __init__(self, api_config):
        self.name = api_config["name"]
        self.url = api_config["url"]
        self.params = api_config["params"]
        self.response_times = []
        self.errors = []
        self.success_count = 0
        self.error_count = 0
    
    def single_request(self, request_id):
        """单次请求"""
        try:
            start_time = time.time()
            response = requests.get(self.url, params=self.params, timeout=30)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                self.success_count += 1
                return {
                    "success": True,
                    "time": elapsed,
                    "request_id": request_id
                }
            else:
                self.error_count += 1
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "request_id": request_id
                }
        except Exception as e:
            self.error_count += 1
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id
            }
    
    def run_benchmark(self, total_requests, workers):
        """运行压测"""
        print(f"\n{'='*80}")
        print(f"🚀 开始压测: {self.name}")
        print(f"{'='*80}")
        print(f"📊 目标URL: {self.url}")
        print(f"📝 参数: {self.params}")
        print(f"🔢 总请求数: {total_requests:,}")
        print(f"⚡ 并发数: {workers}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # 使用线程池并发请求
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self.single_request, i) 
                for i in range(total_requests)
            ]
            
            # 进度显示
            completed = 0
            for future in as_completed(futures):
                result = future.result()
                completed += 1
                
                if result["success"]:
                    self.response_times.append(result["time"])
                else:
                    self.errors.append(result["error"])
                
                # 每1000次显示进度
                if completed % 1000 == 0:
                    progress = (completed / total_requests) * 100
                    print(f"⏳ 进度: {completed:,}/{total_requests:,} ({progress:.1f}%) - "
                          f"成功: {self.success_count:,}, 失败: {self.error_count:,}")
        
        total_time = time.time() - start_time
        
        # 计算统计数据
        self.print_results(total_time)
    
    def print_results(self, total_time):
        """打印测试结果"""
        print(f"\n{'='*80}")
        print(f"✅ 压测完成: {self.name}")
        print(f"{'='*80}\n")
        
        print(f"📊 总体统计:")
        print(f"   ✅ 成功请求: {self.success_count:,}")
        print(f"   ❌ 失败请求: {self.error_count:,}")
        print(f"   📈 成功率: {(self.success_count / (self.success_count + self.error_count) * 100):.2f}%")
        print(f"   ⏱️  总耗时: {total_time:.2f}秒")
        print(f"   🚀 QPS: {(self.success_count + self.error_count) / total_time:.2f} 请求/秒\n")
        
        if self.response_times:
            print(f"⏱️  响应时间统计:")
            print(f"   最小值: {min(self.response_times)*1000:.2f}ms")
            print(f"   最大值: {max(self.response_times)*1000:.2f}ms")
            print(f"   平均值: {statistics.mean(self.response_times)*1000:.2f}ms")
            print(f"   中位数: {statistics.median(self.response_times)*1000:.2f}ms")
            
            if len(self.response_times) > 1:
                print(f"   标准差: {statistics.stdev(self.response_times)*1000:.2f}ms")
            
            # 百分位数
            sorted_times = sorted(self.response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p90 = sorted_times[int(len(sorted_times) * 0.90)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            
            print(f"\n📊 百分位数:")
            print(f"   P50: {p50*1000:.2f}ms")
            print(f"   P90: {p90*1000:.2f}ms")
            print(f"   P95: {p95*1000:.2f}ms")
            print(f"   P99: {p99*1000:.2f}ms")
        
        if self.errors:
            print(f"\n❌ 错误统计:")
            error_types = {}
            for error in self.errors:
                error_types[error] = error_types.get(error, 0) + 1
            
            for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {error}: {count}次")
        
        print(f"\n{'='*80}\n")
        
        return {
            "name": self.name,
            "total_requests": self.success_count + self.error_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / (self.success_count + self.error_count) * 100),
            "total_time": total_time,
            "qps": (self.success_count + self.error_count) / total_time,
            "avg_response_time": statistics.mean(self.response_times) * 1000 if self.response_times else 0,
            "p50": sorted(self.response_times)[int(len(self.response_times) * 0.50)] * 1000 if self.response_times else 0,
            "p95": sorted(self.response_times)[int(len(self.response_times) * 0.95)] * 1000 if self.response_times else 0,
            "p99": sorted(self.response_times)[int(len(self.response_times) * 0.99)] * 1000 if self.response_times else 0,
        }


def main():
    """主函数"""
    print("\n" + "="*80)
    print("🔥 API性能压测工具")
    print("="*80)
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 目标服务器: {BASE_URL}")
    print(f"🔢 每个API测试: {TOTAL_REQUESTS:,} 次")
    print(f"⚡ 并发线程数: {CONCURRENT_WORKERS}")
    print(f"📊 测试API数量: {len(TEST_APIS)}")
    print("="*80)
    
    # 先测试连接
    print("\n🔍 测试服务器连接...")
    try:
        response = requests.get(f"{BASE_URL}/api/dates", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器连接正常\n")
        else:
            print(f"❌ 服务器响应异常: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return
    
    # 运行所有压测
    all_results = []
    
    for api_config in TEST_APIS:
        benchmark = APIBenchmark(api_config)
        result = benchmark.run_benchmark(TOTAL_REQUESTS, CONCURRENT_WORKERS)
        all_results.append(result)
        
        # 每个API测试之间休息2秒
        time.sleep(2)
    
    # 打印总结
    print("\n" + "="*80)
    print("📊 压测总结")
    print("="*80)
    print(f"{'API名称':<20} {'总请求':<10} {'成功率':<10} {'QPS':<10} {'平均响应':<12} {'P95':<10} {'P99':<10}")
    print("-"*80)
    
    for result in all_results:
        print(f"{result['name']:<20} "
              f"{result['total_requests']:<10,} "
              f"{result['success_rate']:<10.2f}% "
              f"{result['qps']:<10.2f} "
              f"{result['avg_response_time']:<12.2f}ms "
              f"{result['p95']:<10.2f}ms "
              f"{result['p99']:<10.2f}ms")
    
    print("="*80)
    
    # 保存结果到JSON
    output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "config": {
                "base_url": BASE_URL,
                "total_requests": TOTAL_REQUESTS,
                "concurrent_workers": CONCURRENT_WORKERS
            },
            "results": all_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 测试结果已保存到: {output_file}\n")


if __name__ == "__main__":
    main()
