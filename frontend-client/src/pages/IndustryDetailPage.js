/**
 * 板块成分股详细分析页面 - Phase 6
 * 完整的板块分析页面，包含成分股列表、图表、对比功能
 */
import React, { useState, useEffect } from 'react';
import apiClient from '../services/api';
import { 
  ArrowLeft, TrendingUp, Download, 
  Filter, RefreshCw, BarChart3, LineChart as LineChartIcon,
  PieChart as PieChartIcon, Activity
} from 'lucide-react';
import { API_BASE_URL, COLORS } from '../constants';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, RadarChart, Radar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { useSignalConfig } from '../contexts/SignalConfigContext';

export default function IndustryDetailPage({ industryName, selectedDate, onBack }) {
  // 全局信号配置
  const { signalThresholds } = useSignalConfig();
  
  // 标签页状态
  const [activeTab, setActiveTab] = useState('stocks'); // stocks | trend | compare
  const [isExplanationExpanded, setIsExplanationExpanded] = useState(false); // 说明是否展开
  
  // 数据状态
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [stocksData, setStocksData] = useState(null);
  const [trendData, setTrendData] = useState(null);
  
  // 成分股列表控制
  const [sortMode, setSortMode] = useState('signal'); // signal | rank | score | price_change
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [showSignalsOnly, setShowSignalsOnly] = useState(false);
  
  // 移除本地配置状态，使用全局配置
  
  // 板块对比配置
  const [compareIndustries, setCompareIndustries] = useState([industryName]);
  const [compareCount, setCompareCount] = useState(3);
  const [compareData, setCompareData] = useState(null);
  const [availableIndustries, setAvailableIndustries] = useState([]);
  const [compareLoading, setCompareLoading] = useState(false);
  
  // 加载可选板块列表
  useEffect(() => {
    const fetchIndustries = async () => {
      try {
        const res = await apiClient.get(`/api/industry/top1000`, {
          params: { limit: 1000 }
        });
        if (res && res.stats) {
          // 提取所有板块名称
          const industries = res.stats.map(s => s.industry);
          setAvailableIndustries(industries);
        }
      } catch (err) {
        console.error('获取板块列表失败:', err);
      }
    };
    fetchIndustries();
  }, []);
  
  // 加载对比数据
  const loadCompareData = async () => {
    if (compareIndustries.length < 2) return;
    
    setCompareLoading(true);
    try {
      const comparePayload = {
        industries: compareIndustries
      };
      if (selectedDate) {
        comparePayload.date = selectedDate;
      }
      const res = await apiClient.post(`/api/industry/compare`, comparePayload);
      setCompareData(res);
    } catch (err) {
      console.error('获取对比数据失败:', err);
    } finally {
      setCompareLoading(false);
    }
  };
  
  // 切换到对比标签页时加载数据
  useEffect(() => {
    if (activeTab === 'compare' && compareIndustries.length >= 2) {
      loadCompareData();
    }
  }, [activeTab, compareIndustries]);
  
  // 加载板块详情和成分股数据
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const apiParams = {
          sort_mode: sortMode,
          calculate_signals: true,
          hot_list_mode: signalThresholds.hotListMode || 'frequent',
          hot_list_version: signalThresholds.hotListVersion || 'v2',
          hot_list_top: signalThresholds.hotListTop,
          rank_jump_min: signalThresholds.rankJumpMin,
          steady_rise_days: signalThresholds.steadyRiseDays,
          price_surge_min: signalThresholds.priceSurgeMin,
          volume_surge_min: signalThresholds.volumeSurgeMin,
          volatility_surge_min: signalThresholds.volatilitySurgeMin
        };
        
        // 添加日期参数
        if (selectedDate) {
          apiParams.date = selectedDate;
        }
        
        const detailParams = {};
        if (selectedDate) {
          detailParams.date = selectedDate;
        }
        
        const [detailRes, stocksRes] = await Promise.all([
          apiClient.get(`/api/industry/${encodeURIComponent(industryName)}/detail`, {
            params: detailParams
          }),
          apiClient.get(`/api/industry/${encodeURIComponent(industryName)}/stocks`, {
            params: apiParams
          })
        ]);
        
        setDetailData(detailRes);
        setStocksData(stocksRes);
      } catch (err) {
        console.error('获取数据失败:', err);
        const errorDetail = err.response?.data?.detail;
        // 确保错误信息是字符串
        const errorMsg = typeof errorDetail === 'string' 
          ? errorDetail 
          : (typeof errorDetail === 'object' 
              ? JSON.stringify(errorDetail) 
              : '获取数据失败');
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, [industryName, sortMode, signalThresholds, selectedDate]);
  
  // 加载趋势数据
  useEffect(() => {
    if (activeTab === 'trend') {
      const fetchTrend = async () => {
        try {
          const trendParams = { period: 7 };
          if (selectedDate) {
            trendParams.date = selectedDate;
          }
          const res = await apiClient.get(
            `/api/industry/${encodeURIComponent(industryName)}/trend`,
            { params: trendParams }
          );
          
          // 转换数据格式：从 metrics_history 转为图表需要的数组格式
          const rawData = res;
          const trendArray = rawData.dates.map((date, index) => ({
            date: date,
            B1: rawData.metrics_history.B1[index],
            B2: rawData.metrics_history.B2[index],
            C1: rawData.metrics_history.C1[index],
            C2: rawData.metrics_history.C2[index],
            top_100_count: rawData.metrics_history.top_100_count[index],
            hot_list_count: rawData.metrics_history.hot_list_count[index],
            multi_signal_count: (rawData.metrics_history.hot_list_count[index] || 0) + 
                                (rawData.metrics_history.top_100_count[index] || 0),
            avg_signal_strength: rawData.metrics_history.avg_signal_strength[index]
          }));
          
          setTrendData({
            ...rawData,
            trend_data: trendArray
          });
        } catch (err) {
          console.error('获取趋势数据失败:', err);
        }
      };
      fetchTrend();
    }
  }, [activeTab, industryName]);
  
  // 分页处理
  const getPaginatedStocks = () => {
    if (!stocksData) return [];
    
    let filteredStocks = stocksData.stocks;
    if (showSignalsOnly) {
      filteredStocks = filteredStocks.filter(s => s.signal_count > 0);
    }
    
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return filteredStocks.slice(startIndex, endIndex);
  };
  
  const getTotalPages = () => {
    if (!stocksData) return 0;
    let filteredStocks = stocksData.stocks;
    if (showSignalsOnly) {
      filteredStocks = filteredStocks.filter(s => s.signal_count > 0);
    }
    return Math.ceil(filteredStocks.length / pageSize);
  };
  
  // 格式化函数
  const formatMetric = (value, suffix = '') => {
    if (value === null || value === undefined) return '-';
    return `${value.toFixed(2)}${suffix}`;
  };
  
  const getSignalColor = (count) => {
    if (count >= 3) return 'bg-red-100 text-red-800 border-red-300';
    if (count >= 2) return 'bg-orange-100 text-orange-800 border-orange-300';
    if (count >= 1) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    return 'bg-gray-100 text-gray-600 border-gray-300';
  };
  
  if (loading && !detailData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-12 w-12 text-green-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg">正在加载板块数据...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h3 className="text-red-800 font-bold text-lg mb-2">加载失败</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={onBack}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              返回
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航栏 */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          {/* 面包屑 */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <button
                onClick={onBack}
                className="text-gray-600 hover:text-gray-900 transition-colors flex items-center gap-2"
              >
                <ArrowLeft className="h-5 w-5" />
                <span>返回</span>
              </button>
              <span className="text-gray-400">/</span>
              <span className="text-gray-600">行业趋势分析</span>
              <span className="text-gray-400">/</span>
              <span className="text-gray-900 font-semibold">{industryName}</span>
            </div>
          </div>
          
          {/* 板块概览 */}
          {detailData && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-3">
                <div className="bg-blue-50 rounded p-3">
                  <p className="text-blue-600 text-xs font-medium">成分股</p>
                  <p className="text-blue-900 font-bold text-lg">{detailData.stock_count}只</p>
                </div>
                <div className="bg-green-50 rounded p-3">
                  <p className="text-green-600 text-xs font-medium">TOP100</p>
                  <p className="text-green-900 font-bold text-lg">{detailData.top_100_count}只</p>
                </div>
                <div className="bg-purple-50 rounded p-3">
                  <p className="text-purple-600 text-xs font-medium">热点榜</p>
                  <p className="text-purple-900 font-bold text-lg">{detailData.hot_list_count}只</p>
                </div>
                <div className="bg-orange-50 rounded p-3">
                  <p className="text-orange-600 text-xs font-medium">多信号</p>
                  <p className="text-orange-900 font-bold text-lg">{detailData.multi_signal_count}只</p>
                </div>
                <div className={`rounded p-3 ${detailData.B2 >= 0 ? 'bg-red-50' : 'bg-green-50'}`}>
                  <p className={`text-xs font-medium ${detailData.B2 >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    B2涨跌幅
                  </p>
                  <p className={`font-bold text-lg ${detailData.B2 >= 0 ? 'text-red-900' : 'text-green-900'}`}>
                    {detailData.B2 >= 0 ? '+' : ''}{detailData.B2.toFixed(2)}%
                  </p>
                </div>
                <div className="bg-indigo-50 rounded p-3">
                  <p className="text-indigo-600 text-xs font-medium">信号强度</p>
                  <p className="text-indigo-900 font-bold text-lg">
                    {(detailData.avg_signal_strength * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
              
              {/* 4维指标详细说明 */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 mb-3 border border-indigo-200">
                <h4 
                  className="text-sm font-bold text-indigo-900 flex items-center justify-between cursor-pointer"
                  onClick={() => setIsExplanationExpanded(!isExplanationExpanded)}
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    📊 4维指标说明
                  </div>
                  <span className="text-xs text-indigo-600 font-normal">
                    {isExplanationExpanded ? '收起' : '展开'}
                  </span>
                </h4>
                
                {isExplanationExpanded && (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs mt-3 animate-fadeIn">
                    <div className="bg-white rounded p-3 border border-blue-200">
                      <div className="font-bold text-blue-900 mb-1 flex items-center justify-between">
                        <span>B1 - 加权总分</span>
                        <span className="text-lg">{detailData.B1.toFixed(2)}</span>
                      </div>
                      <p className="text-blue-700 leading-relaxed">
                        基于排名的加权累加分数。排名越靠前权重越高{detailData.k_value ? `（k=${detailData.k_value.toFixed(3)}）` : ''}。
                        <strong className="block mt-1">用途：看哪个板块精英多、当前最火</strong>
                      </p>
                    </div>
                    <div className="bg-white rounded p-3 border border-green-200">
                      <div className="font-bold text-green-900 mb-1 flex items-center justify-between">
                        <span>B2 - 加权涨跌幅</span>
                        <span className={`text-lg ${detailData.B2 >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {detailData.B2 >= 0 ? '+' : ''}{detailData.B2.toFixed(2)}%
                        </span>
                      </div>
                      <p className="text-green-700 leading-relaxed">
                        成分股涨跌幅加权平均，权重基于排名。反映板块整体涨跌趋势。
                        <strong className="block mt-1">用途：看板块当前热度和资金流向</strong>
                      </p>
                    </div>
                    <div className="bg-white rounded p-3 border border-purple-200">
                      <div className="font-bold text-purple-900 mb-1 flex items-center justify-between">
                        <span>C1 - 加权换手率</span>
                        <span className="text-lg">{detailData.C1.toFixed(2)}%</span>
                      </div>
                      <p className="text-purple-700 leading-relaxed">
                        成分股换手率加权平均，权重基于排名。反映板块交易活跃度。
                        <strong className="block mt-1">用途：看板块是否有资金关注</strong>
                      </p>
                    </div>
                    <div className="bg-white rounded p-3 border border-orange-200">
                      <div className="font-bold text-orange-900 mb-1 flex items-center justify-between">
                        <span>C2 - 加权放量</span>
                        <span className="text-lg">{detailData.C2.toFixed(2)}</span>
                      </div>
                      <p className="text-orange-700 leading-relaxed">
                        成分股放量指标加权平均。数值越大表示成交量相对历史越大。
                        <strong className="block mt-1">用途：看板块是否有异动放量</strong>
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
          
          {/* 标签页 */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('stocks')}
              className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                activeTab === 'stocks'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              成分股分析
            </button>
            <button
              onClick={() => setActiveTab('trend')}
              className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                activeTab === 'trend'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              历史趋势
            </button>
            <button
              onClick={() => setActiveTab('compare')}
              className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                activeTab === 'compare'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              板块对比
            </button>
          </div>
        </div>
      </div>
      
      {/* 本地配置面板已移除，使用全局配置 */}
      
      {/* 主内容区域 */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* 成分股分析标签页 */}
        {activeTab === 'stocks' && stocksData && (
          <div className="space-y-6">
            {/* 控制栏 */}
            <div className="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 mr-2">排序方式:</label>
                  <select
                    value={sortMode}
                    onChange={(e) => setSortMode(e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="signal">信号强度</option>
                    <option value="signal_count">信号数量</option>
                    <option value="rank">市场排名</option>
                    <option value="score">综合评分</option>
                    <option value="price_change">涨跌幅</option>
                  </select>
                </div>
                
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showSignalsOnly}
                    onChange={(e) => {
                      setShowSignalsOnly(e.target.checked);
                      setCurrentPage(1);
                    }}
                    className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                  />
                  <span className="text-sm font-medium text-gray-700">仅显示有信号股票</span>
                </label>
              </div>
              
              <div className="text-sm text-gray-600">
                显示 {getPaginatedStocks().length} / {showSignalsOnly 
                  ? stocksData.stocks.filter(s => s.signal_count > 0).length 
                  : stocksData.stock_count} 只股票
              </div>
            </div>
            
            {/* 信号说明面板 */}
            <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
              <h4 className="text-sm font-bold text-purple-900 mb-3 flex items-center gap-2">
                <Activity className="h-4 w-4" />
                🎯 多维度信号说明
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
                <div className="bg-white rounded p-2 border border-green-200 shadow-sm hover:shadow-md transition-shadow">
                  <span className="font-bold text-green-900 flex items-center gap-1">
                    <span>🥇</span> 热点榜 <span className="text-xs bg-green-100 px-2 py-0.5 rounded">T1</span>
                  </span>
                  <p className="text-green-700 mt-1 leading-relaxed">
                    <strong>总分TOP：</strong>基于当日综合排名，信号如"热点榜TOP100"<br/>
                    <strong>最新热点TOP：</strong>基于14天聚合数据，信号如"TOP100·5次"
                  </p>
                  <p className="text-green-600 mt-1 text-xs font-medium">🥇 权重: 25%基础 - 档位倍数TOP100(1.5×)→TOP3000(0.5×) - 第一层</p>
                </div>
                <div className="bg-white rounded p-2 border border-blue-200 shadow-sm hover:shadow-md transition-shadow">
                  <span className="font-bold text-blue-900 flex items-center gap-1">
                    <span>🥈</span> 排名跳变 <span className="text-xs bg-blue-100 px-2 py-0.5 rounded">T2</span>
                  </span>
                  <p className="text-blue-700 mt-1 leading-relaxed">排名相比前一天大幅提升（≥2000名），说明热度快速上升</p>
                  <p className="text-blue-600 mt-1 text-xs font-medium">🥈 权重: 20% - 第二层（市场关注度）</p>
                </div>
                <div className="bg-white rounded p-2 border border-indigo-200 shadow-sm hover:shadow-md transition-shadow">
                  <span className="font-bold text-indigo-900 flex items-center gap-1">
                    <span>🥈</span> 波动率上升 <span className="text-xs bg-indigo-100 px-2 py-0.5 rounded">T2</span>
                  </span>
                  <p className="text-indigo-700 mt-1 leading-relaxed">波动率百分比变化≥30%，说明价格波动加剧（计算方式：(当前-前一天)/前一天×100%）</p>
                  <p className="text-indigo-600 mt-1 text-xs font-medium">🥈 权重: 20% - 第二层（市场关注度）</p>
                </div>
                <div className="bg-white rounded p-2 border border-purple-200 shadow-sm hover:shadow-md transition-shadow">
                  <span className="font-bold text-purple-900 flex items-center gap-1">
                    <span>🥉</span> 稳步上升 <span className="text-xs bg-purple-100 px-2 py-0.5 rounded">T3</span>
                  </span>
                  <p className="text-purple-700 mt-1 leading-relaxed">连续多天排名持续上升，说明趋势稳定向好</p>
                  <p className="text-purple-600 mt-1 text-xs font-medium">🥉 权重: 15% - 第三层（持续性）</p>
                </div>
                <div className="bg-white rounded p-2 border border-orange-200 shadow-sm hover:shadow-md transition-shadow">
                  <span className="font-bold text-orange-900 flex items-center gap-1">
                    <span>🎖️</span> 涨幅榜 <span className="text-xs bg-orange-100 px-2 py-0.5 rounded">T4</span>
                  </span>
                  <p className="text-orange-700 mt-1 leading-relaxed">涨跌幅超过阈值（如≥5%），说明价格异动明显</p>
                  <p className="text-orange-600 mt-1 text-xs font-medium">🎖️ 权重: 10% - 第四层（短期活跃度）</p>
                </div>
                <div className="bg-white rounded p-2 border border-red-200 shadow-sm hover:shadow-md transition-shadow">
                  <span className="font-bold text-red-900 flex items-center gap-1">
                    <span>🎖️</span> 成交量榜 <span className="text-xs bg-red-100 px-2 py-0.5 rounded">T4</span>
                  </span>
                  <p className="text-red-700 mt-1 leading-relaxed">成交量相对历史放大，说明资金关注度提升</p>
                  <p className="text-red-600 mt-1 text-xs font-medium">🎖️ 权重: 10% - 第四层（短期活跃度）</p>
                </div>
              </div>
              <div className="mt-3 text-xs bg-white rounded p-3 border border-purple-100">
                <p className="text-purple-900 font-bold mb-2">💡 综合使用建议：</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-purple-700">
                  <p>• <strong>信号数量</strong>：信号越多说明该股票越值得关注</p>
                  <p>• <strong>信号组合</strong>：多个信号叠加通常意味着更强的市场信号</p>
                  <p>• <strong>信号强度</strong>：综合反映了各个信号的权重得分（0-100%）</p>
                  <p>• <strong>权重分层</strong>：T1热点榜25% &gt; T2排名跳变/波动率20% &gt; T3稳步上升15% &gt; T4涨幅/成交量10%</p>
                </div>
              </div>
            </div>
            
            {/* 成分股表格 */}
            <div className="bg-white rounded-lg shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-100 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">排名</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">股票</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase">信号</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase">综合评分</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase">涨跌幅</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase">换手率</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase">波动率</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase">市场排名</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {getPaginatedStocks().map((stock, index) => (
                      <tr key={stock.stock_code} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          #{(currentPage - 1) * pageSize + index + 1}
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{stock.stock_name}</p>
                            <p className="text-xs text-gray-500">{stock.stock_code}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col items-center gap-1">
                            {stock.signal_count > 0 ? (
                              <>
                                <span className={`px-2 py-1 rounded text-xs font-medium border ${getSignalColor(stock.signal_count)}`}>
                                  {stock.signal_count}个信号
                                </span>
                                <div className="flex flex-wrap gap-1 justify-center">
                                  {stock.signals && stock.signals.map((signal, i) => (
                                    <span key={i} className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
                                      {signal}
                                    </span>
                                  ))}
                                </div>
                                <span className="text-xs text-gray-600">
                                  强度: {(stock.signal_strength * 100).toFixed(0)}%
                                </span>
                              </>
                            ) : (
                              <span className="text-xs text-gray-400">-</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-semibold text-blue-700">
                            {stock.total_score ? stock.total_score.toFixed(2) : '-'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {stock.price_change !== null ? (
                            <span className={`text-sm font-semibold ${
                              stock.price_change >= 0 ? 'text-red-600' : 'text-green-600'
                            }`}>
                              {stock.price_change >= 0 ? '+' : ''}{stock.price_change.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {stock.turnover_rate_percent !== null ? (
                            <span className="text-sm text-gray-700">
                              {stock.turnover_rate_percent.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {stock.volatility !== null && stock.volatility !== undefined ? (
                            <span className={`text-sm font-medium ${
                              stock.volatility > 5 ? 'text-orange-600' : 
                              stock.volatility > 3 ? 'text-yellow-600' : 
                              'text-gray-600'
                            }`}>
                              {stock.volatility.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="text-sm font-medium text-gray-900">
                            #{stock.rank}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* 分页控制 */}
              {getTotalPages() > 1 && (
                <div className="bg-gray-50 px-4 py-3 border-t border-gray-200 flex items-center justify-between">
                  <div className="text-sm text-gray-700">
                    第 {currentPage} / {getTotalPages()} 页
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      上一页
                    </button>
                    <button
                      onClick={() => setCurrentPage(Math.min(getTotalPages(), currentPage + 1))}
                      disabled={currentPage === getTotalPages()}
                      className="px-3 py-1 bg-white border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            {/* 图表区域 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* 排名分布饼图 */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <PieChartIcon className="h-5 w-5 text-green-600" />
                  排名分布
                </h3>
                {detailData && (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'TOP 100', value: detailData.top_100_count, fill: '#22c55e' },
                          { name: 'TOP 500', value: detailData.top_500_count - detailData.top_100_count, fill: '#3b82f6' },
                          { name: 'TOP 1000', value: detailData.top_1000_count - detailData.top_500_count, fill: '#f59e0b' },
                          { name: '1000+', value: detailData.stock_count - detailData.top_1000_count, fill: '#9ca3af' }
                        ]}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(1)}%)`}
                        outerRadius={80}
                        dataKey="value"
                      >
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
              
              {/* 信号分布条形图 */}
              <div className="bg-white rounded-lg shadow-sm p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-green-600" />
                  信号分布
                </h3>
                {detailData && (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={[
                        { name: '热点榜', value: detailData.hot_list_count },
                        { name: '排名跳变', value: detailData.rank_jump_count },
                        { name: '稳步上升', value: detailData.steady_rise_count },
                        { name: '涨幅榜', value: detailData.price_surge_count || 0 },
                        { name: '成交量榜', value: detailData.volume_surge_count || 0 }
                      ]}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" fill="#10b981">
                        {[0, 1, 2, 3, 4].map((index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* 历史趋势标签页 */}
        {activeTab === 'trend' && (
          <div className="space-y-6">
            {!trendData ? (
              <div className="text-center py-12 bg-white rounded-lg">
                <RefreshCw className="h-12 w-12 text-green-600 animate-spin mx-auto mb-4" />
                <p className="text-gray-600">正在加载趋势数据...</p>
              </div>
            ) : (
              <>
                {/* 4维指标趋势图 */}
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <LineChartIcon className="h-5 w-5 text-green-600" />
                    4维指标历史趋势 (最近{trendData.period}天)
                  </h3>
                  <ResponsiveContainer width="100%" height={400}>
                    <LineChart
                      data={trendData.trend_data}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="date" 
                        tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                      />
                      <YAxis yAxisId="left" label={{ value: 'B1/C2', angle: -90, position: 'insideLeft' }} />
                      <YAxis yAxisId="right" orientation="right" label={{ value: 'B2/C1 (%)', angle: 90, position: 'insideRight' }} />
                      <Tooltip 
                        labelFormatter={(value) => `日期: ${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6,8)}`}
                        formatter={(value, name) => [
                          name.includes('%') ? `${value}%` : value.toFixed(2),
                          name
                        ]}
                      />
                      <Legend />
                      <Line yAxisId="left" type="monotone" dataKey="B1" stroke="#3b82f6" name="B1-加权总分" strokeWidth={2} />
                      <Line yAxisId="right" type="monotone" dataKey="B2" stroke="#22c55e" name="B2-加权涨跌幅(%)" strokeWidth={2} />
                      <Line yAxisId="right" type="monotone" dataKey="C1" stroke="#a855f7" name="C1-加权换手率(%)" strokeWidth={2} />
                      <Line yAxisId="left" type="monotone" dataKey="C2" stroke="#f59e0b" name="C2-加权放量" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                
                {/* 成分股数量趋势 */}
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-green-600" />
                    成分股数量趋势
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={trendData.trend_data}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="date" 
                        tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                      />
                      <YAxis label={{ value: '股票数量', angle: -90, position: 'insideLeft' }} />
                      <Tooltip 
                        labelFormatter={(value) => `日期: ${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6,8)}`}
                      />
                      <Legend />
                      <Bar dataKey="top_100_count" fill="#22c55e" name="TOP 100" />
                      <Bar dataKey="hot_list_count" fill="#a855f7" name="热点榜" />
                      <Bar dataKey="multi_signal_count" fill="#f59e0b" name="多信号" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                
                {/* 信号强度趋势 */}
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-green-600" />
                    平均信号强度趋势
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart
                      data={trendData.trend_data}
                      margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="date" 
                        tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                      />
                      <YAxis 
                        domain={[0, 1]}
                        tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                        label={{ value: '信号强度', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip 
                        labelFormatter={(value) => `日期: ${value.slice(0,4)}-${value.slice(4,6)}-${value.slice(6,8)}`}
                        formatter={(value) => [`${(value * 100).toFixed(2)}%`, '平均信号强度']}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="avg_signal_strength" 
                        stroke="#10b981" 
                        strokeWidth={3}
                        name="平均信号强度"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </div>
        )}
        
        {/* 板块对比标签页 */}
        {activeTab === 'compare' && (
          <div className="space-y-6">
            {/* 板块选择器 */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">选择对比板块 (2-5个)</h3>
              <div className="space-y-3">
                {[0, 1, 2, 3, 4].slice(0, compareCount).map((index) => (
                  <div key={index} className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-700 w-20">
                      板块 {index + 1}:
                    </span>
                    <select
                      value={compareIndustries[index] || ''}
                      onChange={(e) => {
                        const newIndustries = [...compareIndustries];
                        newIndustries[index] = e.target.value;
                        setCompareIndustries(newIndustries.filter(i => i));
                      }}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
                      disabled={index === 0}
                    >
                      {index === 0 ? (
                        <option value={industryName}>{industryName} (当前)</option>
                      ) : (
                        <>
                          <option value="">-- 选择板块 --</option>
                          {availableIndustries
                            .filter(ind => !compareIndustries.includes(ind) || ind === compareIndustries[index])
                            .map(ind => (
                              <option key={ind} value={ind}>{ind}</option>
                            ))}
                        </>
                      )}
                    </select>
                    {index > 0 && compareIndustries[index] && (
                      <button
                        onClick={() => {
                          const newIndustries = compareIndustries.filter((_, i) => i !== index);
                          setCompareIndustries(newIndustries);
                        }}
                        className="px-3 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200"
                      >
                        移除
                      </button>
                    )}
                  </div>
                ))}
              </div>
              
              <div className="flex items-center gap-3 mt-4">
                {compareIndustries.length < 5 && (
                  <button
                    onClick={() => setCompareCount(Math.min(5, compareCount + 1))}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    添加板块
                  </button>
                )}
                {compareIndustries.length >= 2 && (
                  <button
                    onClick={loadCompareData}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
                  >
                    <RefreshCw className={`h-4 w-4 ${compareLoading ? 'animate-spin' : ''}`} />
                    刷新对比
                  </button>
                )}
                <span className="text-sm text-gray-600">
                  已选择 {compareIndustries.length} 个板块
                </span>
              </div>
            </div>
            
            {compareLoading && (
              <div className="text-center py-12 bg-white rounded-lg">
                <RefreshCw className="h-12 w-12 text-green-600 animate-spin mx-auto mb-4" />
                <p className="text-gray-600">正在加载对比数据...</p>
              </div>
            )}
            
            {!compareLoading && compareData && compareData.industries && (
              <>
                {/* 对比雷达图 */}
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">4维指标雷达图</h3>
                  <ResponsiveContainer width="100%" height={500}>
                    <RadarChart data={[
                      {
                        metric: 'B1-加权总分',
                        ...Object.fromEntries(
                          compareData.industries.map(ind => [
                            ind.industry,
                            ind.B1 / Math.max(...compareData.industries.map(i => i.B1)) * 100
                          ])
                        )
                      },
                      {
                        metric: 'B2-加权涨跌幅',
                        ...Object.fromEntries(
                          compareData.industries.map(ind => [
                            ind.industry,
                            Math.max(0, (ind.B2 + 10) / 20 * 100) // 归一化到0-100
                          ])
                        )
                      },
                      {
                        metric: 'C1-加权换手率',
                        ...Object.fromEntries(
                          compareData.industries.map(ind => [
                            ind.industry,
                            ind.C1 / Math.max(...compareData.industries.map(i => i.C1)) * 100
                          ])
                        )
                      },
                      {
                        metric: 'C2-加权放量',
                        ...Object.fromEntries(
                          compareData.industries.map(ind => [
                            ind.industry,
                            ind.C2 / Math.max(...compareData.industries.map(i => i.C2)) * 100
                          ])
                        )
                      },
                      {
                        metric: '信号强度',
                        ...Object.fromEntries(
                          compareData.industries.map(ind => [
                            ind.industry,
                            ind.avg_signal_strength * 100
                          ])
                        )
                      }
                    ]}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="metric" />
                      <PolarRadiusAxis angle={90} domain={[0, 100]} />
                      {compareData.industries.map((ind, index) => (
                        <Radar
                          key={ind.industry}
                          name={ind.industry}
                          dataKey={ind.industry}
                          stroke={COLORS[index % COLORS.length]}
                          fill={COLORS[index % COLORS.length]}
                          fillOpacity={0.3}
                        />
                      ))}
                      <Legend />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
                
                {/* 对比表格 */}
                <div className="bg-white rounded-lg shadow-sm overflow-hidden">
                  <h3 className="text-lg font-bold text-gray-900 p-6 pb-4">详细对比数据</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-100 border-b border-gray-200">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase">指标</th>
                          {compareData.industries.map(ind => (
                            <th key={ind.industry} className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase">
                              {ind.industry}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">成分股数量</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm text-gray-700">
                              {ind.stock_count}只
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">B1 - 加权总分</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm font-semibold text-blue-700">
                              {ind.B1.toFixed(2)}
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">B2 - 加权涨跌幅</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className={`px-4 py-3 text-center text-sm font-semibold ${
                              ind.B2 >= 0 ? 'text-red-600' : 'text-green-600'
                            }`}>
                              {ind.B2 >= 0 ? '+' : ''}{ind.B2.toFixed(2)}%
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">C1 - 加权换手率</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm text-gray-700">
                              {ind.C1.toFixed(2)}%
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">C2 - 加权放量</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm text-gray-700">
                              {ind.C2.toFixed(2)}
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50 bg-yellow-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">平均信号强度</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm font-bold text-orange-700">
                              {(ind.avg_signal_strength * 100).toFixed(2)}%
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">TOP 100</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm text-gray-700">
                              {ind.top_100_count}只
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">热点榜</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm text-gray-700">
                              {ind.hot_list_count}只
                            </td>
                          ))}
                        </tr>
                        <tr className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">多信号股票</td>
                          {compareData.industries.map(ind => (
                            <td key={ind.industry} className="px-4 py-3 text-center text-sm text-gray-700">
                              {ind.multi_signal_count}只
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
                
                {/* 对比柱状图 */}
                <div className="bg-white rounded-lg shadow-sm p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">成分股数量对比</h3>
                  <ResponsiveContainer width="100%" height={350}>
                    <BarChart
                      data={compareData.industries.map(ind => ({
                        industry: ind.industry,
                        '成分股总数': ind.stock_count,
                        'TOP 100': ind.top_100_count,
                        '热点榜': ind.hot_list_count,
                        '多信号': ind.multi_signal_count
                      }))}
                      margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="industry" angle={-15} textAnchor="end" height={80} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="成分股总数" fill="#3b82f6" />
                      <Bar dataKey="TOP 100" fill="#22c55e" />
                      <Bar dataKey="热点榜" fill="#a855f7" />
                      <Bar dataKey="多信号" fill="#f59e0b" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
            
            {!compareLoading && compareIndustries.length < 2 && (
              <div className="text-center py-12 bg-white rounded-lg">
                <p className="text-gray-600">请至少选择2个板块进行对比</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}




