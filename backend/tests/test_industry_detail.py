"""
板块成分股详细分析功能测试
"""
import pytest
from app.services.industry_detail_service import industry_detail_service


class TestIndustryDetailService:
    """测试板块成分股详细分析服务"""
    
    def test_get_industry_stocks_basic(self):
        """测试基础成分股查询"""
        # 查询食品板块
        result = industry_detail_service.get_industry_stocks(
            industry_name="食品",
            target_date=None,  # 使用最新日期
            sort_mode="rank"
        )
        
        # 验证结果
        assert result is not None, "应该返回结果"
        assert result.industry == "食品", "板块名称应正确"
        assert result.stock_count > 0, "应该有成分股"
        assert len(result.stocks) == result.stock_count, "股票数量应一致"
        
        # 验证股票数据
        first_stock = result.stocks[0]
        assert first_stock.stock_code, "应有股票代码"
        assert first_stock.stock_name, "应有股票名称"
        assert first_stock.rank > 0, "排名应大于0"
        assert first_stock.total_score >= 0, "总分应>=0"
        
        print(f"\n✅ 测试通过: 查询到 {result.stock_count} 只食品板块成分股")
        print(f"   TOP 3: ")
        for i, stock in enumerate(result.stocks[:3], 1):
            print(f"   {i}. {stock.stock_name} ({stock.stock_code}) - 排名#{stock.rank}, 分数{stock.total_score:.2f}")
    
    def test_sort_by_score(self):
        """测试按总分排序"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="食品",
            target_date=None,
            sort_mode="score"
        )
        
        assert result is not None, "应该返回结果"
        
        # 验证排序：总分应降序
        scores = [s.total_score for s in result.stocks]
        assert scores == sorted(scores, reverse=True), "总分应降序排列"
        
        print(f"\n✅ 测试通过: 按总分排序正确")
        print(f"   最高分: {scores[0]:.2f}")
        print(f"   最低分: {scores[-1]:.2f}")
    
    def test_sort_by_rank(self):
        """测试按排名排序"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="建材",
            target_date=None,
            sort_mode="rank"
        )
        
        assert result is not None, "应该返回结果"
        
        # 验证排序：排名应升序
        ranks = [s.rank for s in result.stocks]
        assert ranks == sorted(ranks), "排名应升序排列"
        
        print(f"\n✅ 测试通过: 按排名排序正确")
        print(f"   最佳排名: #{ranks[0]}")
        print(f"   最差排名: #{ranks[-1]}")
    
    def test_statistics(self):
        """测试统计信息计算"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="化学",
            target_date=None,
            sort_mode="rank"
        )
        
        assert result is not None, "应该返回结果"
        stats = result.statistics
        
        # 验证统计数据
        assert "avg_rank" in stats, "应有平均排名"
        assert "top_100_count" in stats, "应有TOP100统计"
        assert "top_500_count" in stats, "应有TOP500统计"
        assert stats["top_100_count"] <= stats["top_500_count"], "TOP100应<=TOP500"
        
        print(f"\n✅ 测试通过: 统计信息正确")
        print(f"   平均排名: #{stats['avg_rank']:.1f}")
        print(f"   TOP 100: {stats['top_100_count']}只")
        print(f"   TOP 500: {stats['top_500_count']}只")
        print(f"   TOP 1000: {stats['top_1000_count']}只")
    
    def test_nonexistent_industry(self):
        """测试不存在的板块"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="不存在的板块xxx",
            target_date=None,
            sort_mode="rank"
        )
        
        assert result is None, "不存在的板块应返回None"
        print(f"\n✅ 测试通过: 不存在的板块正确返回None")
    
    def test_cache(self):
        """测试缓存功能"""
        # 第一次查询
        result1 = industry_detail_service.get_industry_stocks(
            industry_name="食品",
            target_date=None,
            sort_mode="rank"
        )
        
        # 第二次查询（应命中缓存）
        result2 = industry_detail_service.get_industry_stocks(
            industry_name="食品",
            target_date=None,
            sort_mode="rank"
        )
        
        assert result1 is not None, "第一次查询应成功"
        assert result2 is not None, "第二次查询应成功"
        assert result1.stock_count == result2.stock_count, "缓存数据应一致"
        
        print(f"\n✅ 测试通过: 缓存功能正常")
    
    def test_signal_calculation(self):
        """测试信号计算功能 (Phase 2)"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="食品",
            target_date=None,
            sort_mode="signal",
            calculate_signals=True
        )
        
        assert result is not None, "应该返回结果"
        
        # 检查信号统计
        stats = result.statistics
        assert "hot_list_count" in stats, "应有热点榜统计"
        assert "rank_jump_count" in stats, "应有跳变榜统计"
        assert "steady_rise_count" in stats, "应有稳步上升统计"
        assert "multi_signal_count" in stats, "应有多信号统计"
        assert "avg_signal_strength" in stats, "应有平均信号强度"
        
        # 检查股票信号数据
        multi_signal_stocks = [s for s in result.stocks if s.signal_count >= 2]
        
        print(f"\n✅ 测试通过: 信号计算正常")
        print(f"   热点榜股票: {stats['hot_list_count']}只")
        print(f"   跳变榜股票: {stats['rank_jump_count']}只")
        print(f"   稳步上升: {stats['steady_rise_count']}只")
        print(f"   多信号股票: {stats['multi_signal_count']}只")
        print(f"   平均信号强度: {stats['avg_signal_strength']:.3f}")
        
        if multi_signal_stocks:
            print(f"\n   多信号股票TOP 3:")
            for i, stock in enumerate(multi_signal_stocks[:3], 1):
                print(f"   {i}. {stock.stock_name} ({stock.stock_code})")
                print(f"      排名#{stock.rank}, 信号数:{stock.signal_count}, 强度:{stock.signal_strength:.3f}")
                print(f"      标签: {stock.signals}")
    
    def test_signal_sort_mode(self):
        """测试按信号强度排序 (Phase 2)"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="建材",
            target_date=None,
            sort_mode="signal",
            calculate_signals=True
        )
        
        assert result is not None, "应该返回结果"
        
        # 验证排序：信号强度应降序
        for i in range(len(result.stocks) - 1):
            curr = result.stocks[i]
            next_stock = result.stocks[i + 1]
            
            # 排序规则：信号数量 > 信号强度 > 排名
            if curr.signal_count == next_stock.signal_count:
                if curr.signal_strength == next_stock.signal_strength:
                    assert curr.rank <= next_stock.rank, "同信号数和强度时，排名应升序"
                else:
                    assert curr.signal_strength >= next_stock.signal_strength, "同信号数时，强度应降序"
            else:
                assert curr.signal_count >= next_stock.signal_count, "信号数量应降序"
        
        print(f"\n✅ 测试通过: 信号强度排序正确")
        print(f"   TOP 5:")
        for i, stock in enumerate(result.stocks[:5], 1):
            print(f"   {i}. {stock.stock_name} - 排名#{stock.rank}")
            print(f"      信号: {stock.signal_count}个, 强度{stock.signal_strength:.3f}")
            print(f"      标签: {stock.signals}")
    
    def test_signal_history(self):
        """测试历史信号追踪 (Phase 2)"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="食品",
            target_date=None,
            sort_mode="signal",
            calculate_signals=True
        )
        
        assert result is not None, "应该返回结果"
        
        # 找一只有信号的股票
        signal_stock = None
        for stock in result.stocks:
            if stock.signal_count > 0 and stock.signal_history:
                signal_stock = stock
                break
        
        if signal_stock:
            history = signal_stock.signal_history
            assert 'dates' in history, "应有日期列表"
            assert 'hot_list' in history, "应有热点榜历史"
            assert len(history['dates']) > 0, "应有历史记录"
            
            print(f"\n✅ 测试通过: 历史信号追踪正常")
            print(f"   股票: {signal_stock.stock_name} ({signal_stock.stock_code})")
            print(f"   追踪天数: {len(history['dates'])}")
            print(f"   最近3天热点榜: {history['hot_list'][:3]}")
            print(f"   最近3天跳变: {history['rank_jump'][:3]}")
        else:
            print(f"\n⚠️ 警告: 当前板块无信号股票（数据相关）")
    
    def test_without_signals(self):
        """测试不计算信号（仅基础数据）"""
        result = industry_detail_service.get_industry_stocks(
            industry_name="化学",
            target_date=None,
            sort_mode="rank",
            calculate_signals=False
        )
        
        assert result is not None, "应该返回结果"
        
        # 验证信号字段为空
        for stock in result.stocks:
            assert stock.signal_count == 0, "不计算信号时signal_count应为0"
            assert stock.signal_strength == 0.0, "不计算信号时signal_strength应为0"
            assert len(stock.signals) == 0, "不计算信号时signals应为空"
        
        print(f"\n✅ 测试通过: 不计算信号模式正常")
        print(f"   成功返回 {result.stock_count} 只股票（无信号数据）")


if __name__ == "__main__":
    """直接运行测试"""
    import sys
    sys.path.insert(0, "..")
    
    print("="*60)
    print("板块成分股详细分析功能测试")
    print("="*60)
    
    test = TestIndustryDetailService()
    
    try:
        print("\n### Phase 1: 基础功能测试 ###")
        test.test_get_industry_stocks_basic()
        test.test_sort_by_score()
        test.test_sort_by_rank()
        test.test_statistics()
        test.test_nonexistent_industry()
        test.test_cache()
        
        print("\n### Phase 2: 信号功能测试 ###")
        test.test_signal_calculation()
        test.test_signal_sort_mode()
        test.test_signal_history()
        test.test_without_signals()
        
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
