"""
单针下二十策略配置
Needle Under 20 Strategy Configuration
"""

# 完整参数配置
NEEDLE_UNDER_20_CONFIG = {
    # ========== 核心指标参数 ==========
    "N1_SHORT": 3,              # 短期周期（白线）同花顺默认=3
    "N2_LONG": 21,              # 长期周期（红线）同花顺默认=21
    "NEEDLE_THRESHOLD": 20,     # 单针触发阈值（白线）
    
    # ========== 形态判定参数 ==========
    "SKY_REFUEL_LONG_MIN": 60,      # 空中加油：红线最小值
    "DOUBLE_BOTTOM_LONG_MAX": 30,   # 双底共振：红线最大值
    "DOUBLE_BOTTOM_DIFF": 15,       # 双底共振：红白线最大差值
    
    # ========== 时间窗口参数 ==========
    "DROP_WINDOW_DAYS": 3,      # 允许下杀持续的最长天数
    "LOOKBACK_DAYS": 10,        # 回溯多少天判断红线趋势
    "CONFIRM_NEXT_DAY": True,   # 是否需要次日确认
    
    # ========== 评分阈值参数 ==========
    "RANK_DELTA_THRESHOLD": -500,   # 排名进步名次阈值（负数表示进步）
    "BOLL_BIAS_MIN": -8.0,      # 乖离率下限 (%)
    "BOLL_BIAS_MAX": -3.0,      # 乖离率上限 (%)
    "TURNOVER_LIMIT": 5.0,      # 缩量换手率上限 (%)
    "KDJ_LIMIT": 20.0,          # KDJ共振阈值
    "CORRELATION_LIMIT": 0.3,   # 独立行情相关性上限
    "ADX_TREND_MIN": 25,        # ADX趋势有效最小值
    
    # ========== 波动率参数 ==========
    "VOL_WINDOW": 20,           # 波动率均值窗口
    "VOL_COMPRESSION_RATIO": 1.0,  # 波动率压缩比上限
    
    # ========== 量能参数 ==========
    "VOLUME_AMPLIFY_RATIO": 1.5,   # 启动日放量倍数
    
    # ========== 幅度限制 ==========
    "MAX_DROP_PCT": -5.0,       # 下杀期间最大允许跌幅（跌太多就是真跌）
    
    # ========== 信号分级阈值 ==========
    "SCORE_STRONG": 50,         # 强烈信号阈值
    "SCORE_NORMAL": 30,         # 普通信号阈值
    "SCORE_WEAK": 15,           # 弱信号阈值
}

# 九维评分权重配置
SCORING_WEIGHTS = {
    # 维度: (分数, 说明)
    "rank_contrarian": (15, "排名逆势跃升"),
    "boll_support": (12, "布林中轨支撑"),
    "volume_shrink": (10, "极度缩量"),
    "kdj_resonance": (10, "KDJ共振超卖"),
    "independent_stock": (8, "独立妖股"),
    "adx_trend": (8, "ADX趋势有效"),
    "obv_divergence": (8, "OBV底背离"),
    "shadow_support": (6, "下影线支撑"),
    "macd_ready": (5, "MACD金叉预备"),
}

# 形态加分配置
PATTERN_BONUS = {
    "sky_refuel": (10, "空中加油"),
    "double_bottom": (8, "双底共振"),
    "single_day_drop": (5, "单日急跌"),
    "next_day_confirm": (5, "次日高开确认"),
}

# 形态名称映射
PATTERN_NAMES = {
    'sky_refuel': '空中加油',
    'double_bottom': '双底共振',
    'low_golden_cross': '低位金叉',
    'slow_drop': '缓慢下杀',
    'general_needle': '一般单针',
}
