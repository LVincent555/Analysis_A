/**
 * 单针下二十策略模块
 * Needle Under 20 Strategy Module
 * 
 * 捕捉主力洗盘后的拉升机会
 * 通过多周期位置指标识别"指标快速下杀但股价坚挺+缩量"的信号
 */
import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../../services/api';
import { 
  Target, TrendingUp, ArrowUp, ArrowDown, Search, RefreshCw,
  Star, Award, Zap, BarChart2
} from 'lucide-react';
import { API_BASE_URL } from '../../constants/config';
import { useSignalConfig } from '../../contexts/SignalConfigContext';
import BoardSignalBadge from '../BoardSignalBadge';
import boardHeatService from '../../services/boardHeatService';

// 形态配置
const PATTERN_CONFIG = {
  sky_refuel: { name: '空中加油', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' },
  double_bottom: { name: '双底共振', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200' },
  low_washout: { name: '低位洗盘', color: 'text-green-600', bg: 'bg-green-50', border: 'border-green-200' },
  general_needle: { name: '一般单针', color: 'text-gray-600', bg: 'bg-gray-50', border: 'border-gray-200' },
};

// 信号等级配置
const SIGNAL_LEVEL_CONFIG = {
  strong: { name: '强烈', color: 'text-red-600', bg: 'bg-red-100', icon: Star },
  normal: { name: '普通', color: 'text-orange-600', bg: 'bg-orange-100', icon: Award },
  weak: { name: '弱', color: 'text-gray-600', bg: 'bg-gray-100', icon: Zap },
};

function NeedleUnder20Module({ selectedDate, days = 5, minScore = 0 }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPattern, setSelectedPattern] = useState(null);
  const [industryDistribution, setIndustryDistribution] = useState({});
  const [dateRange, setDateRange] = useState([]);
  const [boardSignals, setBoardSignals] = useState({});
  
  // 参数状态
  const [analysisDays, setAnalysisDays] = useState(days);
  const [scoreThreshold, setScoreThreshold] = useState(minScore);
  const [bbiFilter, setBbiFilter] = useState(true); // BBI破位筛选
  const [maxDropPct, setMaxDropPct] = useState(null); // 股价跌幅阈值，默认不限
  const [longPeriod, setLongPeriod] = useState(10); // 计算周期：10天或21天
  
  const { signalThresholds } = useSignalConfig();
  const isEastmoneyMode = signalThresholds?.boardDataSource === 'eastmoney';

  // 数据充足信息
  const [dataDays, setDataDays] = useState(0);
  const [requiredDays, setRequiredDays] = useState(0);
  const [dataSufficient, setDataSufficient] = useState(true);

  // 获取数据
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        days: analysisDays,
        min_score: scoreThreshold,
        bbi_filter: bbiFilter,
        long_period: longPeriod,
      });
      
      if (selectedDate) {
        params.append('date', selectedDate);
      }
      if (selectedPattern) {
        params.append('pattern', selectedPattern);
      }
      if (maxDropPct !== null) {
        params.append('max_drop_pct', maxDropPct);
      }
      
      const response = await apiClient.get(
        `/api/strategies/needle-under-20?${params}`
      );
      
      const stocks = response?.data || response?.stocks || (Array.isArray(response) ? response : []);
      setData(stocks);
      setIndustryDistribution(response?.industry_distribution || {});
      setDateRange(response?.date_range || []);
      setDataDays(response?.data_days || 0);
      setRequiredDays(response?.required_days || 0);
      setDataSufficient(response?.data_sufficient !== false);
    } catch (err) {
      console.error('获取单针下二十数据失败:', err);
      setError(err.response?.data?.detail || '获取数据失败');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, analysisDays, scoreThreshold, selectedPattern, bbiFilter, maxDropPct, longPeriod]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 批量获取板块信号
  useEffect(() => {
    const fetchSignals = async () => {
      if (!isEastmoneyMode || !data || data.length === 0) return;
      
      try {
        const codes = data.map(s => s.stock_code);
        if (codes.length === 0) return;

        // 分批处理，防止URL过长（虽然POST没问题，但习惯性优化）
        const result = await boardHeatService.getStockSignalsBatch(codes, selectedDate);
        const signalMap = {};
        result.stocks?.forEach(s => {
          signalMap[s.stock_code] = s;
        });
        setBoardSignals(signalMap);
      } catch (err) {
        console.error("Failed to load signals", err);
      }
    };
    
    fetchSignals();
  }, [isEastmoneyMode, data, selectedDate]);

  // 过滤数据
  const filteredData = data.filter(item => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.stock_code?.toLowerCase().includes(term) ||
      item.stock_name?.toLowerCase().includes(term) ||
      item.industry?.toLowerCase().includes(term)
    );
  });

  // 渲染评分详情
  const renderScoreDetails = (details) => {
    if (!details || Object.keys(details).length === 0) return null;
    
    // 递归渲染值（处理嵌套对象）
    const renderValue = (value) => {
      if (value === null || value === undefined) return '-';
      if (typeof value === 'object') {
        // 嵌套对象：展开显示
        return (
          <div className="ml-2 text-left">
            {Object.entries(value).map(([k, v]) => (
              <div key={k} className="text-gray-600">
                {k}: {typeof v === 'number' ? v.toFixed(1) : v}
              </div>
            ))}
          </div>
        );
      }
      // 简单值
      const numValue = typeof value === 'number' ? value : parseFloat(value);
      if (!isNaN(numValue)) {
        return numValue >= 0 ? `+${numValue}` : numValue;
      }
      return value;
    };
    
    return (
      <div className="mt-2 space-y-1">
        {Object.entries(details).map(([key, value]) => (
          <div key={key} className="flex justify-between text-xs">
            <span className="text-gray-500">{key}</span>
            <span className="text-green-600 font-medium">{renderValue(value)}</span>
          </div>
        ))}
      </div>
    );
  };

  // 渲染标签
  const renderLabels = (labels) => {
    if (!labels || labels.length === 0) return null;
    
    return (
      <div className="flex flex-wrap gap-1 mt-1">
        {labels.map((label, index) => (
          <span
            key={index}
            className="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700"
          >
            {label}
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-rose-600 to-pink-600 p-4 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Target className="h-6 w-6" />
            <div>
              <h2 className="text-xl font-bold">单针下二十策略</h2>
              <p className="text-sm text-rose-100 mt-1">
                捕捉主力洗盘后的拉升机会 · 九维评分系统
              </p>
            </div>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
          >
            <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 策略介绍卡片 */}
      <div className="p-4 bg-gradient-to-r from-rose-50 to-pink-50 border-b">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* 九维信号评分系统 */}
          <div className="bg-white rounded-lg p-3 shadow-sm border border-rose-100">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 bg-rose-100 rounded-lg">
                <Star className="h-4 w-4 text-rose-600" />
              </div>
              <span className="font-semibold text-gray-800">九维信号评分</span>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              综合<span className="text-rose-600 font-medium">位置指标、形态识别、量价配合、技术指标、趋势强度、波动特征、排名变化、历史表现、风险评估</span>九个维度，科学量化信号质量
            </p>
          </div>
          
          {/* 空中加油/双底共振形态 */}
          <div className="bg-white rounded-lg p-3 shadow-sm border border-blue-100">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 bg-blue-100 rounded-lg">
                <TrendingUp className="h-4 w-4 text-blue-600" />
              </div>
              <span className="font-semibold text-gray-800">形态识别</span>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              <span className="text-red-600 font-medium">空中加油</span>：长期位置高位+短期急跌，主力洗盘后拉升；
              <span className="text-blue-600 font-medium">双底共振</span>：长短期均处低位，底部共振反弹
            </p>
          </div>
          
          {/* 主力洗盘信号捕捉 */}
          <div className="bg-white rounded-lg p-3 shadow-sm border border-purple-100">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 bg-purple-100 rounded-lg">
                <Zap className="h-4 w-4 text-purple-600" />
              </div>
              <span className="font-semibold text-gray-800">主力洗盘捕捉</span>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              核心公式：<code className="bg-gray-100 px-1 rounded text-purple-600">位置≤20% + 缩量 + 股价坚挺</code>，识别主力借利空洗盘、即将拉升的买入时机
            </p>
          </div>
        </div>
      </div>

      {/* 参数控制区 */}
      <div className="p-4 bg-gray-50 border-b">
        <div className="flex flex-wrap gap-4 items-center">
          {/* 分析天数 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">分析天数:</span>
            <div className="flex gap-1">
              {[2, 3, 5].map(d => (
                <button
                  key={d}
                  onClick={() => setAnalysisDays(d)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    analysisDays === d
                      ? 'bg-rose-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border'
                  }`}
                >
                  {d}天
                </button>
              ))}
            </div>
          </div>

          {/* 评分阈值 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">最低评分:</span>
            <div className="flex gap-1">
              {[0, 20, 40, 60, 80].map(s => (
                <button
                  key={s}
                  onClick={() => setScoreThreshold(s)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    scoreThreshold === s
                      ? 'bg-rose-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border'
                  }`}
                >
                  {s}分
                </button>
              ))}
            </div>
          </div>

          {/* 形态筛选 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">形态:</span>
            <div className="flex gap-1">
              <button
                onClick={() => setSelectedPattern(null)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  !selectedPattern
                    ? 'bg-rose-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
              >
                全部
              </button>
              <button
                onClick={() => setSelectedPattern('sky_refuel')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  selectedPattern === 'sky_refuel'
                    ? 'bg-red-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
              >
                空中加油
              </button>
              <button
                onClick={() => setSelectedPattern('bottom_volume')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  selectedPattern === 'bottom_volume'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
              >
                底部放量
              </button>
            </div>
          </div>

          {/* BBI筛选 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">BBI破位:</span>
            <div className="flex gap-1">
              <button
                onClick={() => setBbiFilter(true)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  bbiFilter
                    ? 'bg-rose-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
              >
                排除
              </button>
              <button
                onClick={() => setBbiFilter(false)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  !bbiFilter
                    ? 'bg-rose-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
              >
                不排除
              </button>
            </div>
          </div>

          {/* 跌幅筛选 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">跌幅≤:</span>
            <div className="flex gap-1">
              {[null, 1, 3, 5, 6, 8, 10].map(p => (
                <button
                  key={p ?? 'all'}
                  onClick={() => setMaxDropPct(p)}
                  className={`px-3 py-1 text-sm rounded transition-colors ${
                    maxDropPct === p
                      ? 'bg-orange-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border'
                  }`}
                >
                  {p === null ? '不限' : `${p}%`}
                </button>
              ))}
            </div>
          </div>

          {/* 计算周期 */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">周期:</span>
            <div className="flex gap-1">
              <button
                onClick={() => setLongPeriod(10)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  longPeriod === 10
                    ? 'bg-purple-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
              >
                10天
              </button>
              <button
                onClick={() => setLongPeriod(21)}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  longPeriod === 21
                    ? 'bg-purple-600 text-white'
                    : dataDays < 28
                      ? 'bg-gray-100 text-gray-400 border cursor-not-allowed'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border'
                }`}
                disabled={dataDays < 28}
                title={dataDays < 28 ? `需要28天数据，当前${dataDays}天` : '对齐同花顺'}
              >
                21天
              </button>
            </div>
          </div>

          {/* 搜索 */}
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="搜索股票代码或名称..."
                className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
              />
            </div>
          </div>
        </div>

        {/* 统计信息 */}
        <div className="mt-3 flex items-center gap-4 text-sm flex-wrap">
          <span className="text-gray-600">
            共找到 <span className="font-bold text-rose-600">{filteredData.length}</span> 只股票
          </span>
          {dateRange.length > 0 && (
            <span className="text-gray-500">
              分析日期: {dateRange.join(' ~ ')}
            </span>
          )}
          {/* 数据状态提示 */}
          <span className={`px-2 py-0.5 rounded text-xs ${
            dataDays >= 28 
              ? 'bg-green-100 text-green-700' 
              : 'bg-yellow-100 text-yellow-700'
          }`}>
            数据{dataDays}天 {dataDays >= 28 ? '✓ 可用21天周期' : `(需28天才能用21天周期)`}
          </span>
        </div>
      </div>

      {/* 内容区 */}
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-rose-600" />
            <span className="ml-3 text-gray-600">加载中...</span>
          </div>
        ) : error ? (
          <div className="text-center py-12 text-red-600">
            <p>{error}</p>
            <button
              onClick={fetchData}
              className="mt-4 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
            >
              重试
            </button>
          </div>
        ) : filteredData.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Target className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>暂无符合条件的单针下二十信号</p>
            <p className="text-sm mt-2">尝试调低评分阈值或增加分析天数</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 股票列表 */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 text-sm text-gray-600">
                    <th className="px-4 py-3 text-left">排名</th>
                    <th className="px-4 py-3 text-left">股票</th>
                    <th className="px-4 py-3 text-left">行业</th>
                    {isEastmoneyMode && (
                      <th className="px-4 py-3 text-left">板块信号</th>
                    )}
                    <th className="px-4 py-3 text-center">形态</th>
                    <th className="px-4 py-3 text-center">评分</th>
                    <th className="px-4 py-3 text-center">涨跌幅</th>
                    <th className="px-4 py-3 text-center">白线下杀</th>
                    <th className="px-4 py-3 text-left">洗盘详情</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredData.map((item, index) => {
                    const patternConfig = PATTERN_CONFIG[item.pattern] || PATTERN_CONFIG.general_needle;
                    const levelConfig = SIGNAL_LEVEL_CONFIG[item.signal_level] || SIGNAL_LEVEL_CONFIG.weak;
                    const LevelIcon = levelConfig.icon;
                    
                    return (
                      <tr 
                        key={`${item.stock_code}-${index}`}
                        className="border-b hover:bg-gray-50 transition-colors"
                      >
                        {/* 排名 */}
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                            item.rank <= 3 ? 'bg-yellow-100 text-yellow-700' :
                            item.rank <= 10 ? 'bg-gray-100 text-gray-700' :
                            'text-gray-500'
                          }`}>
                            {item.rank}
                          </span>
                        </td>
                        
                        {/* 股票 */}
                        <td className="px-4 py-3">
                          <div>
                            <div className="font-medium text-gray-900">{item.stock_name}</div>
                            <div className="text-xs text-gray-500">{item.stock_code}</div>
                          </div>
                        </td>
                        
                        {/* 行业 */}
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {item.industry || '-'}
                        </td>
                        
                        {/* 板块信号 */}
                        {isEastmoneyMode && (
                          <td className="px-4 py-3">
                            {boardSignals[item.stock_code] && boardSignals[item.stock_code].board_signal_level !== 'NONE' ? (
                              <BoardSignalBadge
                                level={boardSignals[item.stock_code].board_signal_level}
                                label={boardSignals[item.stock_code].board_signal_label}
                                type={boardSignals[item.stock_code].max_concept_board_type}
                                heatPct={boardSignals[item.stock_code].max_concept_heat_pct}
                                size="sm"
                              />
                            ) : (
                              <span className="text-xs text-gray-400">-</span>
                            )}
                          </td>
                        )}

                        {/* 形态 */}
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-block px-2 py-1 text-xs rounded-lg ${patternConfig.bg} ${patternConfig.color} ${patternConfig.border} border`}>
                            {item.pattern_name || patternConfig.name}
                          </span>
                        </td>
                        
                        {/* 评分 */}
                        <td className="px-4 py-3 text-center">
                          <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold ${
                            item.total_score >= 80 ? 'bg-red-100 text-red-700' :
                            item.total_score >= 60 ? 'bg-orange-100 text-orange-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {item.total_score}
                          </div>
                        </td>
                        
                        {/* 涨跌幅 */}
                        <td className="px-4 py-3 text-center">
                          {item.washout_analysis?.['股价涨跌'] ? (
                            <span className={`font-medium ${
                              item.washout_analysis['股价涨跌'].startsWith('-') 
                                ? 'text-green-600' 
                                : 'text-red-600'
                            }`}>
                              {item.washout_analysis['股价涨跌']}
                            </span>
                          ) : '-'}
                        </td>
                        
                        {/* 白线下杀 */}
                        <td className="px-4 py-3 text-center">
                          <span className="font-medium text-purple-600">
                            {item.washout_analysis?.['白线下杀']?.toFixed(1) || '-'}
                          </span>
                        </td>
                        
                        {/* 洗盘详情 */}
                        <td className="px-4 py-3 text-xs">
                          {item.washout_analysis ? (
                            <details className="cursor-pointer">
                              <summary className="text-indigo-600 hover:text-indigo-800">
                                查看详情
                              </summary>
                              <div className="mt-2 space-y-1 text-left">
                                <div className="flex justify-between">
                                  <span className="text-gray-500">白线(短期):</span>
                                  <span className="font-medium">{item.washout_analysis['白线(短期)']}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">红线(长期):</span>
                                  <span className="font-medium">{item.washout_analysis['红线(长期)']}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">白线前高:</span>
                                  <span className="font-medium">{item.washout_analysis['白线前高']}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">洗盘效率:</span>
                                  <span className="font-medium text-purple-600">{item.washout_analysis['洗盘效率']}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-gray-500">BBI状态:</span>
                                  <span className={`font-medium ${item.washout_analysis['BBI站上'] ? 'text-green-600' : 'text-red-600'}`}>
                                    {item.washout_analysis['BBI站上'] ? '站上' : '破位'}
                                  </span>
                                </div>
                              </div>
                            </details>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* 行业分布 */}
            {Object.keys(industryDistribution).length > 0 && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                  <BarChart2 className="h-4 w-4" />
                  行业分布统计
                </h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(industryDistribution)
                    .sort((a, b) => b[1] - a[1])
                    .map(([industry, count]) => (
                      <span
                        key={industry}
                        className="px-3 py-1 bg-white rounded-full text-sm border border-gray-200"
                      >
                        {industry}: <span className="font-bold text-rose-600">{count}</span>
                      </span>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default NeedleUnder20Module;




