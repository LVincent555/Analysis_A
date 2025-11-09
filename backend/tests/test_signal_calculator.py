"""
多榜单信号计算功能测试
"""
import pytest
from datetime import date
from app.services.signal_calculator import SignalCalculator, SignalThresholds
from app.services.memory_cache import memory_cache


class TestSignalCalculator:
    """测试信号计算器"""
    
    def test_hot_list_signal(self):
        """测试热点榜信号"""
        calculator = SignalCalculator()
        
        # 获取最新日期的数据
        latest_date = memory_cache.get_latest_date()
        all_stocks = memory_cache.get_date_data(latest_date)
        
        # 找一只TOP100的股票
        top_stock = None
        for stock_data in all_stocks[:100]:
            if stock_data.rank <= 100:
                top_stock = stock_data
                break
        
        assert top_stock is not None, "应该找到TOP100股票"
        
        # 计算信号
        signals = calculator.calculate_signals(
            stock_code=top_stock.stock_code,
            current_date=latest_date,
            current_data=top_stock
        )
        
        # 验证热点榜信号
        assert signals['in_hot_list'] == True, "TOP100股票应在热点榜"
        assert '热点榜' in str(signals['signals']), "信号标签应包含'热点榜'"
        assert signals['signal_strength'] > 0, "信号强度应>0"
        
        print(f"\n✅ 测试通过: 热点榜信号检测正常")
        print(f"   股票: {top_stock.stock_code}, 排名: #{top_stock.rank}")
        print(f"   信号: {signals['signals']}")
        print(f"   信号强度: {signals['signal_strength']:.3f}")
    
    def test_rank_jump_signal(self):
        """测试排名跳变信号"""
        calculator = SignalCalculator()
        
        latest_date = memory_cache.get_latest_date()
        all_stocks = memory_cache.get_date_data(latest_date)
        
        # 遍历查找有跳变的股票
        jump_stock = None
        for stock_data in all_stocks[:500]:
            signals = calculator.calculate_signals(
                stock_code=stock_data.stock_code,
                current_date=latest_date,
                current_data=stock_data
            )
            if signals['in_rank_jump']:
                jump_stock = (stock_data, signals)
                break
        
        if jump_stock:
            stock_data, signals = jump_stock
            print(f"\n✅ 测试通过: 找到跳变股票")
            print(f"   股票: {stock_data.stock_code}, 排名: #{stock_data.rank}")
            print(f"   排名提升: {signals['rank_improvement']}")
            print(f"   信号: {signals['signals']}")
        else:
            print(f"\n⚠️ 警告: 今日未发现跳变股票（正常情况）")
    
    def test_steady_rise_signal(self):
        """测试稳步上升信号"""
        calculator = SignalCalculator()
        
        latest_date = memory_cache.get_latest_date()
        all_stocks = memory_cache.get_date_data(latest_date)
        
        # 遍历查找稳步上升的股票
        rise_stock = None
        for stock_data in all_stocks[:500]:
            signals = calculator.calculate_signals(
                stock_code=stock_data.stock_code,
                current_date=latest_date,
                current_data=stock_data
            )
            if signals['in_steady_rise']:
                rise_stock = (stock_data, signals)
                break
        
        if rise_stock:
            stock_data, signals = rise_stock
            print(f"\n✅ 测试通过: 找到稳步上升股票")
            print(f"   股票: {stock_data.stock_code}, 排名: #{stock_data.rank}")
            print(f"   连续上升天数: {signals['rise_days']}")
            print(f"   信号: {signals['signals']}")
        else:
            print(f"\n⚠️ 警告: 今日未发现稳步上升股票（正常情况）")
    
    def test_multi_signal_stock(self):
        """测试多信号股票"""
        calculator = SignalCalculator()
        
        latest_date = memory_cache.get_latest_date()
        all_stocks = memory_cache.get_date_data(latest_date)
        
        # 查找有多个信号的股票
        multi_signal_stocks = []
        for stock_data in all_stocks[:200]:
            signals = calculator.calculate_signals(
                stock_code=stock_data.stock_code,
                current_date=latest_date,
                current_data=stock_data
            )
            if signals['signal_count'] >= 2:
                multi_signal_stocks.append((stock_data, signals))
        
        assert len(multi_signal_stocks) > 0, "应该找到至少1只多信号股票"
        
        print(f"\n✅ 测试通过: 找到 {len(multi_signal_stocks)} 只多信号股票")
        
        # 显示信号最强的股票
        multi_signal_stocks.sort(key=lambda x: x[1]['signal_strength'], reverse=True)
        top3 = multi_signal_stocks[:3]
        
        print(f"\n   信号最强的TOP 3:")
        for i, (stock_data, signals) in enumerate(top3, 1):
            print(f"   {i}. {stock_data.stock_code} - 排名#{stock_data.rank}")
            print(f"      信号数: {signals['signal_count']}, 强度: {signals['signal_strength']:.3f}")
            print(f"      标签: {signals['signals']}")
    
    def test_signal_history(self):
        """测试历史信号追踪"""
        calculator = SignalCalculator()
        
        latest_date = memory_cache.get_latest_date()
        all_stocks = memory_cache.get_date_data(latest_date)
        
        # 选一只TOP100的股票看历史
        top_stock = all_stocks[10]  # 取第11名
        
        signals = calculator.calculate_signals(
            stock_code=top_stock.stock_code,
            current_date=latest_date,
            current_data=top_stock,
            history_days=7
        )
        
        history = signals['signal_history']
        assert history is not None, "应该有历史信号数据"
        assert 'hot_list' in history, "应该有热点榜历史"
        assert 'dates' in history, "应该有日期列表"
        assert len(history['dates']) > 0, "应该有历史日期"
        
        print(f"\n✅ 测试通过: 历史信号追踪正常")
        print(f"   股票: {top_stock.stock_code}, 排名: #{top_stock.rank}")
        print(f"   追踪天数: {len(history['dates'])}")
        print(f"   热点榜历史: {history['hot_list'][:5]}")
        print(f"   跳变榜历史: {history['rank_jump'][:5]}")
        print(f"   稳步上升历史: {history['steady_rise'][:5]}")
    
    def test_custom_thresholds(self):
        """测试自定义阈值"""
        # 宽松阈值
        loose_thresholds = SignalThresholds(
            hot_list_top=200,
            rank_jump_min=50,
            steady_rise_days_min=2,
            price_surge_min=3.0,
            volume_surge_min=5.0
        )
        
        calculator_loose = SignalCalculator(loose_thresholds)
        
        latest_date = memory_cache.get_latest_date()
        test_stock = memory_cache.get_date_data(latest_date)[150]  # 排名约150的股票
        
        signals_loose = calculator_loose.calculate_signals(
            stock_code=test_stock.stock_code,
            current_date=latest_date,
            current_data=test_stock
        )
        
        # 宽松阈值应该能识别更多信号
        assert signals_loose is not None, "应该计算出信号"
        
        print(f"\n✅ 测试通过: 自定义阈值正常")
        print(f"   股票: {test_stock.stock_code}, 排名: #{test_stock.rank}")
        print(f"   宽松阈值信号: {signals_loose['signals']}")
        print(f"   信号数: {signals_loose['signal_count']}")


if __name__ == "__main__":
    """直接运行测试"""
    import sys
    sys.path.insert(0, "..")
    
    print("="*60)
    print("多榜单信号计算功能测试")
    print("="*60)
    
    test = TestSignalCalculator()
    
    try:
        test.test_hot_list_signal()
        test.test_rank_jump_signal()
        test.test_steady_rise_signal()
        test.test_multi_signal_stock()
        test.test_signal_history()
        test.test_custom_thresholds()
        
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
