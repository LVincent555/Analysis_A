# -*- coding: utf-8 -*-
"""
API 集成测试 - 统一缓存系统验收测试

测试所有 API 接口和参数，验证:
1. 接口正常响应
2. 缓存系统工作正常
3. 性能指标达标

运行方式:
    cd backend
    python tests/test_api_integration.py
    
或指定后端地址:
    python tests/test_api_integration.py --host 127.0.0.1 --port 8000
"""

import sys
import time
import json
import argparse
import requests
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TestResult:
    """测试结果"""
    name: str
    endpoint: str
    params: Dict[str, Any]
    success: bool
    status_code: int
    response_time_ms: float
    error: Optional[str] = None
    data_size: int = 0
    cache_hit: bool = False


class APITester:
    """API 测试器"""
    
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.results: List[TestResult] = []
        self.session = requests.Session()
        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'
    
    def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None,
        json_data: Dict = None,
        timeout: int = 30
    ) -> Tuple[int, Any, float]:
        """发送请求并返回 (状态码, 响应数据, 耗时ms)"""
        url = f"{self.base_url}{endpoint}"
        start = time.time()
        
        try:
            if method.upper() == 'GET':
                resp = self.session.get(url, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                resp = self.session.post(url, params=params, json=json_data, timeout=timeout)
            elif method.upper() == 'DELETE':
                resp = self.session.delete(url, params=params, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            elapsed_ms = (time.time() - start) * 1000
            
            try:
                data = resp.json()
            except:
                data = resp.text
            
            return resp.status_code, data, elapsed_ms
            
        except requests.exceptions.Timeout:
            elapsed_ms = (time.time() - start) * 1000
            return 0, {"error": "Timeout"}, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            return 0, {"error": str(e)}, elapsed_ms
    
    def test(
        self,
        name: str,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        expected_status: int = 200,
        timeout: int = 30
    ) -> TestResult:
        """执行单个测试"""
        status_code, data, elapsed_ms = self._request(
            method, endpoint, params, json_data, timeout
        )
        
        success = status_code == expected_status
        error = None
        data_size = 0
        
        if not success:
            if isinstance(data, dict):
                error = data.get('detail') or data.get('error') or str(data)
            else:
                error = str(data)[:200]
        
        if isinstance(data, (dict, list)):
            data_size = len(json.dumps(data, ensure_ascii=False))
        
        result = TestResult(
            name=name,
            endpoint=endpoint,
            params=params or {},
            success=success,
            status_code=status_code,
            response_time_ms=elapsed_ms,
            error=error,
            data_size=data_size
        )
        
        self.results.append(result)
        return result
    
    def login(self, username: str, password: str) -> bool:
        """登录获取 Token"""
        status, data, _ = self._request(
            'POST', '/api/auth/login',
            json_data={'username': username, 'password': password, 'device_id': 'test'}
        )
        
        if status == 200 and 'token' in data:
            self.token = data['token']
            self.session.headers['Authorization'] = f'Bearer {self.token}'
            return True
        return False
    
    def print_result(self, result: TestResult):
        """打印单个测试结果"""
        status = "✅" if result.success else "❌"
        time_color = ""
        if result.response_time_ms > 1000:
            time_color = "⚠️"
        elif result.response_time_ms > 3000:
            time_color = "🔴"
        
        print(f"  {status} {result.name}")
        print(f"     {result.endpoint} | {result.status_code} | {result.response_time_ms:.0f}ms {time_color} | {result.data_size} bytes")
        if result.error:
            print(f"     ❌ Error: {result.error[:100]}")
    
    def test_with_cache(
        self,
        name: str,
        method: str,
        endpoint: str,
        params: Dict = None,
        json_data: Dict = None,
        expected_status: int = 200,
        timeout: int = 30,
        rounds: int = 3
    ) -> List[TestResult]:
        """执行多轮测试，统计缓存效果"""
        results = []
        for i in range(rounds):
            label = ["首次(冷)", "二次(热)", "三次(热)"][i] if i < 3 else f"第{i+1}次"
            result = self.test(
                f"{name} [{label}]",
                method, endpoint, params, json_data, expected_status, timeout
            )
            results.append(result)
        return results
    
    def print_cache_stats(self, results: List[TestResult], name: str):
        """打印缓存统计"""
        if len(results) < 2:
            return
        
        times = [r.response_time_ms for r in results if r.success]
        if len(times) < 2:
            return
        
        first = times[0]
        cached_avg = sum(times[1:]) / len(times[1:])
        speedup = first / cached_avg if cached_avg > 0 else 0
        
        print(f"     📊 {name}: 首次={first:.0f}ms → 缓存={cached_avg:.0f}ms (加速 {speedup:.1f}x)")
    
    def print_summary(self):
        """打印测试总结"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed
        
        avg_time = sum(r.response_time_ms for r in self.results) / total if total > 0 else 0
        max_time = max((r.response_time_ms for r in self.results), default=0)
        
        # 统计缓存命中的测试（排除首次）
        cached_results = [r for r in self.results if "热]" in r.name]
        cached_avg = sum(r.response_time_ms for r in cached_results) / len(cached_results) if cached_results else 0
        
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"总计: {total} | 通过: {passed} | 失败: {failed}")
        print(f"平均响应时间: {avg_time:.0f}ms | 缓存命中平均: {cached_avg:.0f}ms")
        print(f"最大响应时间: {max_time:.0f}ms")
        
        if failed > 0:
            print("\n失败的测试:")
            for r in self.results:
                if not r.success:
                    print(f"  ❌ {r.name}: {r.error}")
        
        # 性能警告（只看缓存命中的）
        slow_cached = [r for r in cached_results if r.response_time_ms > 100]
        if slow_cached:
            print(f"\n⚠️ 缓存命中但响应 > 100ms ({len(slow_cached)} 个):")
            for r in sorted(slow_cached, key=lambda x: -x.response_time_ms)[:10]:
                print(f"  {r.name}: {r.response_time_ms:.0f}ms")
        
        print("=" * 60)
        return failed == 0


def run_all_tests(base_url: str, username: str = None, password: str = None):
    """运行所有测试"""
    tester = APITester(base_url)
    
    print("=" * 60)
    print("API 集成测试 - 统一缓存系统验收")
    print(f"目标: {base_url}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # ==================== 1. 健康检查 ====================
    print("\n📋 1. 健康检查")
    
    tester.print_result(tester.test(
        "健康检查", "GET", "/health"
    ))
    
    # ==================== 2. 认证接口 (需要账号) ====================
    if username and password:
        print("\n📋 2. 认证接口")
        
        # 登录
        login_result = tester.test(
            "用户登录", "POST", "/api/auth/login",
            json_data={'username': username, 'password': password, 'device_id': 'test_device'}
        )
        tester.print_result(login_result)
        
        if login_result.success:
            # 从响应中提取 token
            status, data, _ = tester._request(
                'POST', '/api/auth/login',
                json_data={'username': username, 'password': password, 'device_id': 'test_device'}
            )
            if status == 200 and 'token' in data:
                tester.token = data['token']
                tester.session.headers['Authorization'] = f'Bearer {tester.token}'
                print(f"     ✅ Token 获取成功")
            
            # 获取当前用户
            tester.print_result(tester.test(
                "获取当前用户", "GET", "/api/auth/me"
            ))
            
            # 获取会话列表
            tester.print_result(tester.test(
                "获取会话列表", "GET", "/api/auth/sessions"
            ))
    else:
        print("\n📋 2. 认证接口 (跳过 - 未提供账号)")
    
    # ==================== 3. 缓存管理接口 ====================
    print("\n📋 3. 缓存管理接口")
    
    tester.print_result(tester.test(
        "缓存统计", "GET", "/api/cache/stats"
    ))
    
    tester.print_result(tester.test(
        "缓存健康检查", "GET", "/api/cache/health"
    ))
    
    # ==================== 4. 行业分析接口 (3轮测试 + 多日期) ====================
    print("\n📋 4. 行业分析接口 (每接口3轮，验证缓存)")
    
    # 测试两个日期：最新日期 + 11月20日
    test_dates = [None, '20251120']  # None表示最新日期
    
    for test_date in test_dates:
        date_label = test_date or "最新"
        print(f"\n  --- 日期: {date_label} ---")
        
        # /api/industry/stats - 3轮测试
        results = tester.test_with_cache(
            f"行业统计({date_label})", "GET", "/api/industry/stats",
            params={'period': 3, 'top_n': 20, 'date': test_date} if test_date else {'period': 3, 'top_n': 20}
        )
        for r in results:
            tester.print_result(r)
        tester.print_cache_stats(results, f"行业统计({date_label})")
        
        # /api/industry/weighted - 3轮测试
        results = tester.test_with_cache(
            f"加权行业({date_label})", "GET", "/api/industry/weighted",
            params={'k': 0.618, 'metric': 'B1', 'date': test_date} if test_date else {'k': 0.618, 'metric': 'B1'}
        )
        for r in results:
            tester.print_result(r)
        tester.print_cache_stats(results, f"加权行业({date_label})")
    
    # ==================== 5. 股票查询接口 ====================
    print("\n📋 5. 股票查询接口")
    
    # 测试几个常见股票代码
    test_stocks = ['000001', '600519', '300750']
    for code in test_stocks:
        tester.print_result(tester.test(
            f"股票查询 {code}",
            "GET", "/api/stock/search",
            params={'q': code}  # 参数名是 q 不是 keyword
        ))
    
    # ==================== 6. 排名跳变接口 (3轮测试) ====================
    print("\n📋 6. 排名跳变接口 (3轮测试)")
    
    results = tester.test_with_cache(
        "排名跳变", "GET", "/api/rank-jump",
        params={'jump_threshold': 2500, 'board_type': 'main'}
    )
    for r in results:
        tester.print_result(r)
    tester.print_cache_stats(results, "排名跳变")
    
    # ==================== 7. 稳步上升接口 (3轮测试) ====================
    print("\n📋 7. 稳步上升接口 (3轮测试)")
    
    results = tester.test_with_cache(
        "稳步上升", "GET", "/api/steady-rise",
        params={'period': 3, 'board_type': 'main'}
    )
    for r in results:
        tester.print_result(r)
    tester.print_cache_stats(results, "稳步上升")
    
    # ==================== 8. 板块成分股接口 (3轮测试) ====================
    print("\n📋 8. 板块成分股接口 (3轮测试)")
    
    # 路由格式: /api/industry/{industry_name}/stocks
    # 使用实际存在的板块名，这里用“半导体”示例
    results = tester.test_with_cache(
        "板块成分股(半导体)", "GET", "/api/industry/半导体/stocks",
        params={'sort_mode': 'rank'}
    )
    for r in results:
        tester.print_result(r)
    tester.print_cache_stats(results, "板块成分股")
    
    # ==================== 9. 策略接口 (3轮测试) ====================
    print("\n📋 9. 策略接口 (3轮测试，首次较慢)")
    
    results = tester.test_with_cache(
        "单针下二十", "GET", "/api/strategies/needle-under-20",
        params={'long_period': 10, 'bbi_filter': True},
        timeout=60
    )
    for r in results:
        tester.print_result(r)
    tester.print_cache_stats(results, "单针下二十")
    
    # ==================== 10. 热点分析接口 (3轮测试 + 多日期) ====================
    print("\n📋 10. 热点分析接口 (3轮测试)")
    
    # 测试两个日期
    for test_date in [None, '20251120']:
        date_label = test_date or "最新"
        print(f"\n  --- 日期: {date_label} ---")
        
        # 热点榜完整数据
        results = tester.test_with_cache(
            f"热点榜({date_label})", "GET", "/api/hot-spots/full",
            params={'date': test_date} if test_date else {}
        )
        for r in results:
            tester.print_result(r)
        tester.print_cache_stats(results, f"热点榜({date_label})")
        
        # 周期分析
        results = tester.test_with_cache(
            f"周期分析({date_label})", "GET", "/api/analyze/3",
            params={'top_n': 100, 'target_date': test_date} if test_date else {'top_n': 100}
        )
        for r in results:
            tester.print_result(r)
        tester.print_cache_stats(results, f"周期分析({date_label})")
    
    # ==================== 总结 ====================
    return tester.print_summary()


def main():
    parser = argparse.ArgumentParser(description='API 集成测试')
    parser.add_argument('--host', default='127.0.0.1', help='后端主机')
    parser.add_argument('--port', default=8000, type=int, help='后端端口')
    parser.add_argument('--username', default='admin', help='测试用户名')
    parser.add_argument('--password', default='bVlNVcFBHfNu$XZG', help='测试密码')
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    
    success = run_all_tests(base_url, args.username, args.password)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
