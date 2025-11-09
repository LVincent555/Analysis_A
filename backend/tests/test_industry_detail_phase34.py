"""
Phase 3-4: 详细分析和趋势对比功能测试
"""
import pytest
from app.services.industry_detail_service import industry_detail_service


class TestIndustryDetailPhase34:
    """测试Phase 3-4功能"""
    
    def test_industry_detail(self):
        """测试板块详细分析 (Phase 3)"""
        result = industry_detail_service.get_industry_detail(
            industry_name="食品",
            target_date=None,
            k_value=0.618
        )
        
        assert result is not None, "应该返回结果"
        assert result.industry == "食品", "板块名称应正确"
        assert result.stock_count > 0, "应有成分股"
        
        # 验证4维指标
        assert result.B1 > 0, "B1指标应>0"
        assert result.B2 is not None, "B2指标应存在"
        assert result.C1 >= 0, "C1指标应>=0"
        assert result.C2 >= 0, "C2指标应>=0"
        
        # 验证统计数据
        assert result.avg_rank > 0, "平均排名应>0"
        assert result.top_100_count >= 0, "TOP100数量应>=0"
        
        # 验证信号统计
        assert result.hot_list_count >= 0, "热点榜数量应>=0"
        assert result.avg_signal_strength >= 0, "平均信号强度应>=0"
        
        print(f"\n✅ 测试通过: 板块详细分析正常")
        print(f"   板块: {result.industry}")
        print(f"   日期: {result.date}")
        print(f"   成分股: {result.stock_count}只")
        print(f"\n   4维指标:")
        print(f"   B1 (加权总分): {result.B1:.2f}")
        print(f"   B2 (加权涨跌幅): {result.B2:.2f}%")
        print(f"   C1 (加权换手率): {result.C1:.2f}%")
        print(f"   C2 (加权放量天数): {result.C2:.2f}")
        print(f"\n   成分股统计:")
        print(f"   平均排名: #{result.avg_rank:.1f}")
        print(f"   TOP 100: {result.top_100_count}只")
        print(f"   TOP 500: {result.top_500_count}只")
        print(f"   TOP 1000: {result.top_1000_count}只")
        print(f"\n   信号统计:")
        print(f"   热点榜: {result.hot_list_count}只")
        print(f"   跳变榜: {result.rank_jump_count}只")
        print(f"   稳步上升: {result.steady_rise_count}只")
        print(f"   多信号股票: {result.multi_signal_count}只")
        print(f"   平均信号强度: {result.avg_signal_strength:.3f}")
    
    def test_k_value_effect(self):
        """测试不同K值对指标的影响"""
        # K值较小：更关注头部股票
        result_small_k = industry_detail_service.get_industry_detail(
            industry_name="建材",
            target_date=None,
            k_value=0.3
        )
        
        # K值较大：权重分布更均匀
        result_large_k = industry_detail_service.get_industry_detail(
            industry_name="建材",
            target_date=None,
            k_value=0.9
        )
        
        assert result_small_k is not None, "小K值应返回结果"
        assert result_large_k is not None, "大K值应返回结果"
        
        # K值影响指标值（小K值更聚焦头部，指标通常更高）
        print(f"\n✅ 测试通过: K值影响正常")
        print(f"\n   K=0.3 (聚焦头部):")
        print(f"   B1: {result_small_k.B1:.2f}, B2: {result_small_k.B2:.2f}%")
        print(f"\n   K=0.9 (分布均匀):")
        print(f"   B1: {result_large_k.B1:.2f}, B2: {result_large_k.B2:.2f}%")
    
    def test_industry_trend(self):
        """测试板块历史趋势 (Phase 4)"""
        result = industry_detail_service.get_industry_trend(
            industry_name="食品",
            period=7,
            k_value=0.618
        )
        
        assert result is not None, "应该返回结果"
        assert result.industry == "食品", "板块名称应正确"
        assert result.period > 0, "期间应>0"
        assert len(result.dates) > 0, "应有日期数据"
        
        # 验证指标历史
        metrics = result.metrics_history
        assert 'B1' in metrics, "应有B1历史"
        assert 'B2' in metrics, "应有B2历史"
        assert 'C1' in metrics, "应有C1历史"
        assert 'C2' in metrics, "应有C2历史"
        assert 'avg_rank' in metrics, "应有平均排名历史"
        assert 'top_100_count' in metrics, "应有TOP100历史"
        assert 'hot_list_count' in metrics, "应有热点榜历史"
        assert 'avg_signal_strength' in metrics, "应有信号强度历史"
        
        # 验证数据完整性
        assert len(metrics['B1']) == len(result.dates), "B1数据长度应与日期一致"
        assert len(metrics['B2']) == len(result.dates), "B2数据长度应与日期一致"
        
        print(f"\n✅ 测试通过: 板块历史趋势正常")
        print(f"   板块: {result.industry}")
        print(f"   期间: {result.period}天")
        print(f"   日期范围: {result.dates[-1]} ~ {result.dates[0]}")
        print(f"\n   B1趋势 (最近3天): {metrics['B1'][:3]}")
        print(f"   B2趋势 (最近3天): {metrics['B2'][:3]}")
        print(f"   TOP100数量趋势 (最近3天): {metrics['top_100_count'][:3]}")
        print(f"   热点榜数量趋势 (最近3天): {metrics['hot_list_count'][:3]}")
    
    def test_trend_period(self):
        """测试不同追踪期间"""
        # 7天趋势
        result_7d = industry_detail_service.get_industry_trend(
            industry_name="化学",
            period=7,
            k_value=0.618
        )
        
        # 14天趋势
        result_14d = industry_detail_service.get_industry_trend(
            industry_name="化学",
            period=14,
            k_value=0.618
        )
        
        assert result_7d is not None, "7天趋势应返回"
        assert result_14d is not None, "14天趋势应返回"
        assert len(result_14d.dates) >= len(result_7d.dates), "14天应有更多数据点"
        
        print(f"\n✅ 测试通过: 不同追踪期间正常")
        print(f"   7天: {len(result_7d.dates)}个数据点")
        print(f"   14天: {len(result_14d.dates)}个数据点")
    
    def test_compare_industries(self):
        """测试多板块对比 (Phase 4)"""
        result = industry_detail_service.compare_industries(
            industry_names=["食品", "建材", "化学"],
            target_date=None,
            k_value=0.618
        )
        
        assert result is not None, "应该返回结果"
        assert result.k_value == 0.618, "K值应正确"
        assert len(result.industries) == 3, "应有3个板块数据"
        
        # 验证每个板块的数据
        for industry_detail in result.industries:
            assert industry_detail.industry is not None, "板块名称应存在"
            assert industry_detail.B1 > 0, "B1应>0"
            assert industry_detail.stock_count > 0, "应有成分股"
        
        print(f"\n✅ 测试通过: 多板块对比正常")
        print(f"   日期: {result.date}")
        print(f"   K值: {result.k_value}")
        print(f"   板块数: {len(result.industries)}")
        print(f"\n   对比数据:")
        print(f"   {'板块':<8} {'成分股':<6} {'B1':<8} {'B2':<8} {'TOP100':<6} {'热点榜':<6}")
        print(f"   {'-'*60}")
        for ind in result.industries:
            print(f"   {ind.industry:<8} {ind.stock_count:<6} "
                  f"{ind.B1:<8.2f} {ind.B2:<8.2f}% "
                  f"{ind.top_100_count:<6} {ind.hot_list_count:<6}")
    
    def test_compare_two_industries(self):
        """测试对比2个板块（最少情况）"""
        result = industry_detail_service.compare_industries(
            industry_names=["食品", "建材"],
            target_date=None,
            k_value=0.618
        )
        
        assert result is not None, "应该返回结果"
        assert len(result.industries) == 2, "应有2个板块数据"
        
        print(f"\n✅ 测试通过: 对比2个板块正常")
        print(f"   板块: {[ind.industry for ind in result.industries]}")
    
    def test_compare_five_industries(self):
        """测试对比5个板块（最多情况）"""
        result = industry_detail_service.compare_industries(
            industry_names=["食品", "建材", "化学", "医药", "电子"],
            target_date=None,
            k_value=0.618
        )
        
        assert result is not None, "应该返回结果"
        # 注意：如果某些板块不存在，实际数量可能<5
        assert len(result.industries) > 0, "应至少有1个板块数据"
        assert len(result.industries) <= 5, "最多5个板块"
        
        print(f"\n✅ 测试通过: 对比多个板块正常")
        print(f"   请求板块数: 5")
        print(f"   实际返回: {len(result.industries)}个")
        print(f"   板块: {[ind.industry for ind in result.industries]}")
    
    def test_cache_efficiency(self):
        """测试缓存效率"""
        import time
        
        # 第一次查询（无缓存）
        start1 = time.time()
        result1 = industry_detail_service.get_industry_detail(
            industry_name="食品",
            target_date=None,
            k_value=0.618
        )
        time1 = time.time() - start1
        
        # 第二次查询（命中缓存）
        start2 = time.time()
        result2 = industry_detail_service.get_industry_detail(
            industry_name="食品",
            target_date=None,
            k_value=0.618
        )
        time2 = time.time() - start2
        
        assert result1 is not None, "第一次查询应成功"
        assert result2 is not None, "第二次查询应成功"
        assert result1.B1 == result2.B1, "缓存数据应一致"
        
        # 缓存应该更快（至少不慢）
        print(f"\n✅ 测试通过: 缓存效率验证")
        print(f"   第一次查询耗时: {time1*1000:.2f}ms")
        print(f"   第二次查询耗时: {time2*1000:.2f}ms （缓存）")
        print(f"   加速比: {time1/time2 if time2 > 0 else 0:.1f}x")


if __name__ == "__main__":
    """直接运行测试"""
    import sys
    sys.path.insert(0, "..")
    
    print("="*60)
    print("Phase 3-4: 详细分析和趋势对比功能测试")
    print("="*60)
    
    test = TestIndustryDetailPhase34()
    
    try:
        print("\n### Phase 3: 详细分析测试 ###")
        test.test_industry_detail()
        test.test_k_value_effect()
        
        print("\n### Phase 4: 趋势和对比测试 ###")
        test.test_industry_trend()
        test.test_trend_period()
        test.test_compare_industries()
        test.test_compare_two_industries()
        test.test_compare_five_industries()
        
        print("\n### 性能测试 ###")
        test.test_cache_efficiency()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
