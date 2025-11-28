"""
测试脚本：分析三只股票的形态

核心逻辑：
1. 空中加油：红线在高位(60+)，白线从高位下杀
2. 双底共振：红线在中位(30-60)，白线从高位下杀  
3. 红线太低(<30) = 低优先级（不排除）
4. BBI回踩破了就不显示

测试股票：
- 超卓航科 688237 - 红线低，应该低优先级
- 平潭发展 000592 - 标准洗盘
- 国机精工 002046 - 空中加油
"""
import sys
sys.path.insert(0, '.')
import asyncio

from app.services.strategies.common.position_calculator import PositionCalculator
from app.services.memory_cache import MemoryCacheManager

def get_stock_data_sync(stock_code: str):
    """从内存缓存获取股票历史数据"""
    cache = MemoryCacheManager()
    cache.load_all_data()
    
    # 获取股票基本信息
    stock = cache.stocks.get(stock_code)
    if not stock:
        return None, None
    
    stock_name = stock.stock_name
    
    # 获取该股票的所有每日数据
    daily_dict = cache.daily_data_by_stock.get(stock_code, {})
    if not daily_dict:
        return None, None
    
    # 按日期排序（升序）
    sorted_dates = sorted(daily_dict.keys())
    
    # 构建数据列表
    data = []
    for d in sorted_dates:
        day_data = daily_dict[d]
        # BBI不存在，用middle_band代替
        bbi_val = 0
        if hasattr(day_data, 'middle_band') and day_data.middle_band:
            bbi_val = float(day_data.middle_band)
        data.append({
            'trade_date': str(d),  # 转为字符串便于匹配
            'close': float(day_data.close_price) if day_data.close_price else 0,
            'high': float(day_data.high_price) if day_data.high_price else 0,
            'low': float(day_data.low_price) if day_data.low_price else 0,
            'bbi': bbi_val,
        })
    
    return data, stock_name

def analyze_stock(stock_code: str, stock_name: str, daily_data: list, target_date: str = None):
    """分析单只股票"""
    print(f"\n{'='*70}")
    print(f"分析: {stock_name} ({stock_code})")
    print(f"{'='*70}")
    
    # 提取数据（处理数据库字段名）
    def get_val(d, *keys):
        for k in keys:
            if k in d and d[k] is not None:
                return float(d[k])
        return 0.0
    
    closes = [get_val(d, 'close', 'close_price') for d in daily_data]
    highs = [get_val(d, 'high', 'high_price') for d in daily_data]
    lows = [get_val(d, 'low', 'low_price') for d in daily_data]
    bbis = [get_val(d, 'bbi', 'middle_band') for d in daily_data]
    dates = [str(d.get('trade_date', d.get('date', ''))) for d in daily_data]
    
    # 如果指定了目标日期，截取到该日期
    if target_date:
        target_idx = None
        # 格式化目标日期以便匹配
        target_normalized = target_date.replace('-', '')
        for i, dt in enumerate(dates):
            dt_normalized = str(dt).replace('-', '')
            if target_normalized in dt_normalized:
                target_idx = i
                break
        if target_idx is not None:
            closes = closes[:target_idx+1]
            highs = highs[:target_idx+1]
            lows = lows[:target_idx+1]
            bbis = bbis[:target_idx+1]
            dates = dates[:target_idx+1]
            print(f"截取到目标日期: {dates[-1]}")
        else:
            print(f"⚠️ 未找到目标日期 {target_date}，使用全部数据")
    
    print(f"获取到 {len(closes)} 天数据，日期范围: {dates[0]} -> {dates[-1]}")
    
    # 计算位置指标（使用10天长期周期适配数据量）
    long_period = min(10, len(closes) - 5)
    if long_period < 5:
        print("数据不足")
        return
    calculator = PositionCalculator(short_period=3, long_period=long_period)
    
    # 计算最近7天的位置
    print(f"\n【位置指标走势（最近7天）】（长期周期={long_period}天）")
    positions = []
    for i in range(len(closes)-7, len(closes)+1):
        if i < long_period:
            continue
        pos = calculator.calculate_all_positions(closes[:i], highs[:i], lows[:i])
        idx = i - 1
        positions.append({
            'date': dates[idx],
            'close': closes[idx],
            'bbi': bbis[idx] if idx < len(bbis) else 0,
            'short': pos.short_term,
            'long': pos.long_term
        })
    
    for p in positions[-7:]:
        bbi_status = '站上' if p['close'] >= p['bbi'] else '破位'
        print(f"  {p['date']}: 白线={p['short']:5.1f}, 红线={p['long']:5.1f}, 收盘={p['close']:.2f}, BBI={p['bbi']:.2f}({bbi_status})")
    
    if len(positions) < 4:
        print("数据不足")
        return
    
    # 关键数据
    curr = positions[-1]      # 今天
    prev1 = positions[-2]     # 昨天
    prev2 = positions[-3]     # 前天
    prev3 = positions[-4]     # 大前天
    
    # ========== 核心判断逻辑 ==========
    print(f"\n{'='*70}")
    print(f"【核心判断】")
    print(f"{'='*70}")
    
    # 1. 红线位置（长期趋势）
    curr_long = curr['long']
    print(f"\n1. 红线位置: {curr_long:.1f}")
    if curr_long >= 60:
        long_status = "高位(60+) → 空中加油条件 ✓"
    elif curr_long >= 30:
        long_status = "中位(30-60) → 双底共振条件 ✓"
    else:
        long_status = "低位(<30) → 整体趋势差 ✗"
    print(f"   判断: {long_status}")
    
    # 2. 白线下杀（必须从高位下杀）
    # 检查前几天是否有高位（白线>=80）
    prev_short_max = max(prev1['short'], prev2['short'], prev3['short'])
    short_drop = prev_short_max - curr['short']  # 下杀幅度
    
    print(f"\n2. 白线下杀:")
    print(f"   前几天白线最高: {prev_short_max:.1f}")
    print(f"   当前白线: {curr['short']:.1f}")
    print(f"   下杀幅度: {short_drop:.1f}")
    
    if prev_short_max >= 80 and short_drop >= 30:
        short_status = "从高位急跌 ✓"
    elif prev_short_max >= 60 and short_drop >= 20:
        short_status = "从中高位下跌 ✓"
    else:
        short_status = "下杀不明显 ✗"
    print(f"   判断: {short_status}")
    
    # 3. BBI支撑
    bbi_break = curr['close'] < curr['bbi']
    print(f"\n3. BBI支撑:")
    print(f"   收盘: {curr['close']:.2f}, BBI: {curr['bbi']:.2f}")
    print(f"   判断: {'破位 ✗ (不显示)' if bbi_break else '站上 ✓'}")
    
    # ========== 最终判断 ==========
    print(f"\n{'='*70}")
    print(f"【最终结论】")
    print(f"{'='*70}")
    
    # 唯一排除条件：BBI破位
    if bbi_break:
        print(f"❌ 排除: BBI破位（回踩破了，不显示）")
        return
    
    # 计算优先级分数
    score = 0
    pattern = None
    
    # 白线下杀条件（必须满足）
    if prev_short_max >= 80 and short_drop >= 30:
        score += 30  # 从高位急跌
    elif prev_short_max >= 60 and short_drop >= 20:
        score += 20  # 从中高位下跌
    elif short_drop >= 15:
        score += 10  # 有一定下跌
    else:
        print(f"❌ 排除: 白线下杀不明显")
        print(f"   白线前高={prev_short_max:.1f}, 下杀={short_drop:.1f}")
        return
    
    # 红线位置决定形态和优先级
    if curr_long >= 60:
        pattern = "空中加油"
        score += 40  # 最高优先级
    elif curr_long >= 30:
        pattern = "双底共振"
        score += 25  # 中等优先级
    else:
        pattern = "低位洗盘"
        score += 10  # 低优先级（但不排除）
    
    print(f"✅ 入选: {pattern}")
    print(f"   优先级分数: {score}")
    print(f"   红线={curr_long:.1f}, 白线前高={prev_short_max:.1f}, 下杀={short_drop:.1f}")

def main():
    # 测试股票和目标日期
    stocks = [
        ('688237', '超卓航科', '20251121'),  # 红线低，应低优先级
        ('000592', '平潭发展', '20251124'),  # 11/24跌停那天
        ('002046', '国机精工', '20251121'),  # 11/21白线下杀
    ]
    
    for code, name, target_date in stocks:
        try:
            data, actual_name = get_stock_data_sync(code)
            if data:
                analyze_stock(code, actual_name or name, data, target_date)
            else:
                print(f"获取 {name}({code}) 数据失败")
        except Exception as e:
            print(f"分析 {name}({code}) 出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    main()
