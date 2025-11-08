/**
 * 主应用组件 - 模块化重构版
 * 整合所有功能模块，提供统一的导航和布局
 */
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  TrendingUp, Calendar, Activity, BarChart2, Search, 
  TrendingUp as TrendingUpIcon, TrendingDown, ChevronUp, ChevronDown, RefreshCw 
} from 'lucide-react';
import { API_BASE_URL } from './constants/config';
import { formatDate } from './utils';
import {
  HotSpotsModule,
  StockQueryModule,
  IndustryTrendModule,
  IndustryWeightedModule,
  SectorTrendModule,
  RankJumpModule,
  SteadyRiseModule
} from './components/modules';

function App() {
  // 全局状态
  const [activeModule, setActiveModule] = useState('hot-spots');
  const [expandedMenu, setExpandedMenu] = useState('hot-spots');
  const [availableDates, setAvailableDates] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null); // 用户选择的日期

  // 最新热点模块状态
  const [boardType, setBoardType] = useState('main');
  const [selectedPeriod, setSelectedPeriod] = useState(2);
  const [topN, setTopN] = useState(100); // 新增：前N个股票
  const [loading, setLoading] = useState(false);

  // 股票查询模块状态
  const [stockCode, setStockCode] = useState('');
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState(null);
  const [queryTrigger, setQueryTrigger] = useState(0);

  // 排名跳变模块状态
  const [jumpBoardType, setJumpBoardType] = useState('main');
  const [jumpThreshold, setJumpThreshold] = useState(2000);

  // 稳步上升模块状态
  const [riseBoardType, setRiseBoardType] = useState('main');
  const [risePeriod, setRisePeriod] = useState(3);
  const [minRankImprovement, setMinRankImprovement] = useState(100);

  // 行业趋势分析模块状态
  const [topNLimit, setTopNLimit] = useState(1000);

  const periods = [2, 3, 5, 7, 14];

  // 获取可用日期
  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/dates`);
        setAvailableDates(response.data);
        // 默认选择最新日期
        if (response.data && response.data.latest_date) {
          setSelectedDate(response.data.latest_date);
        }
      } catch (err) {
        console.error('获取日期失败:', err);
      }
    };
    fetchAvailableDates();
  }, []);

  // 查询股票 - 触发查询
  const handleStockQuery = () => {
    if (!stockCode.trim()) {
      setStockError('请输入股票代码');
      return;
    }
    setStockError(null);
    setQueryTrigger(prev => prev + 1); // 触发查询
  };

  // 刷新数据（用于最新热点模块）
  const handleRefresh = () => {
    // 触发子组件刷新
    setLoading(true);
    setTimeout(() => setLoading(false), 100);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <TrendingUp className="h-8 w-8 text-indigo-600" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  潘哥的底裤
                </h1>
                <p className="text-xs text-gray-500 mt-1">
                  一个兴趣使然的股票分析系统
                </p>
              </div>
            </div>
            {availableDates && selectedDate && (
              <div className="flex items-center space-x-3 bg-white rounded-lg px-4 py-2 shadow-sm border border-gray-200">
                <Calendar className="h-5 w-5 text-indigo-600" />
                <div className="flex items-center space-x-2">
                  <label className="text-sm font-medium text-gray-700">数据日期:</label>
                  <select
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="px-3 py-1.5 border-0 bg-transparent text-base font-semibold text-gray-900 focus:outline-none focus:ring-0 cursor-pointer"
                    style={{ minWidth: '160px' }}
                  >
                    {availableDates.dates.map((date) => (
                      <option key={date} value={date}>
                        {formatDate(date)}
                        {date === availableDates.latest_date && ' ⭐'}
                      </option>
                    ))}
                  </select>
                  {selectedDate === availableDates.latest_date && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      最新
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex gap-6">
          {/* Left Sidebar - Modular Navigation */}
          <aside className="w-72 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-md overflow-hidden sticky top-8">
              <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 text-white">
                <h3 className="text-lg font-bold flex items-center space-x-2">
                  <Activity className="h-5 w-5" />
                  <span>功能导航</span>
                </h3>
              </div>

              <nav className="p-2">
                {/* 最新热点模块 */}
                <div className="mb-2">
                  <button
                    onClick={() => {
                      setExpandedMenu(expandedMenu === 'hot-spots' ? null : 'hot-spots');
                      setActiveModule('hot-spots');
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${
                      activeModule === 'hot-spots'
                        ? 'bg-indigo-50 text-indigo-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <BarChart2 className="h-5 w-5" />
                      <span>最新热点</span>
                    </div>
                    {expandedMenu === 'hot-spots' ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>

                  {/* 最新热点子菜单 */}
                  {expandedMenu === 'hot-spots' && (
                    <div className="mt-2 ml-4 space-y-2 border-l-2 border-indigo-200 pl-3">
                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2">板块类型</div>
                      <button
                        onClick={() => setBoardType('main')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          boardType === 'main'
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        主板 <span className="text-xs opacity-75">(排除双创)</span>
                      </button>
                      <button
                        onClick={() => setBoardType('all')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          boardType === 'all'
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        全部 <span className="text-xs opacity-75">(含双创)</span>
                      </button>
                      <button
                        onClick={() => setBoardType('bjs')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          boardType === 'bjs'
                            ? 'bg-indigo-100 text-indigo-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        北交所 <span className="text-xs opacity-75">(920开头)</span>
                      </button>

                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">分析周期</div>
                      <div className="grid grid-cols-2 gap-2">
                        {periods.map((period) => (
                          <button
                            key={period}
                            onClick={() => setSelectedPeriod(period)}
                            className={`py-2 px-2 rounded text-sm font-medium transition-colors ${
                              selectedPeriod === period
                                ? 'bg-indigo-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            {period}天
                          </button>
                        ))}
                      </div>

                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">分析股票数</div>
                      <div className="grid grid-cols-2 gap-2">
                        {[100, 200, 400, 600, 800, 1000].map((n) => (
                          <button
                            key={n}
                            onClick={() => setTopN(n)}
                            className={`py-2 px-2 rounded text-sm font-medium transition-colors ${
                              topN === n
                                ? 'bg-indigo-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            前{n}个
                          </button>
                        ))}
                      </div>

                      <button
                        onClick={handleRefresh}
                        disabled={loading}
                        className="mt-4 w-full flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white py-2 px-3 rounded text-sm font-medium transition-colors disabled:opacity-50"
                      >
                        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                        <span>{loading ? '分析中...' : '刷新数据'}</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* 股票查询模块 */}
                <div className="mb-2">
                  <button
                    onClick={() => {
                      setExpandedMenu(expandedMenu === 'stock-query' ? null : 'stock-query');
                      setActiveModule('stock-query');
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${
                      activeModule === 'stock-query'
                        ? 'bg-purple-50 text-purple-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <Search className="h-5 w-5" />
                      <span>股票查询</span>
                    </div>
                    {expandedMenu === 'stock-query' ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>

                  {/* 股票查询子菜单 */}
                  {expandedMenu === 'stock-query' && (
                    <div className="mt-2 ml-4 space-y-2 border-l-2 border-purple-200 pl-3">
                      <div className="text-xs text-gray-600 mb-2">
                        查询个股历史排名及数据变化
                      </div>
                      <div className="flex space-x-2">
                        <input
                          type="text"
                          value={stockCode}
                          onChange={(e) => setStockCode(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleStockQuery()}
                          placeholder="股票代码"
                          className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                        />
                        <button
                          onClick={handleStockQuery}
                          disabled={stockLoading}
                          className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded text-sm font-medium transition-colors disabled:opacity-50"
                        >
                          <Search className={`h-4 w-4 ${stockLoading ? 'animate-pulse' : ''}`} />
                        </button>
                      </div>
                      {stockError && (
                        <p className="text-xs text-red-600 mt-1">{stockError}</p>
                      )}
                    </div>
                  )}
                </div>

                {/* 行业趋势分析模块 */}
                <div className="mb-2">
                  <button
                    onClick={() => {
                      setExpandedMenu(expandedMenu === 'industry-trend' ? null : 'industry-trend');
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${
                      (activeModule === 'industry-trend' || activeModule === 'industry-weighted' || activeModule === 'sector-trend')
                        ? 'bg-green-50 text-green-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <TrendingUpIcon className="h-5 w-5" />
                      <span>行业趋势分析</span>
                    </div>
                    {expandedMenu === 'industry-trend' ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>

                  {/* 行业趋势子菜单 */}
                  {expandedMenu === 'industry-trend' && (
                    <div className="mt-2 ml-4 space-y-3 border-l-2 border-green-200 pl-3">
                      {/* 原版：数量统计（保留前1000/2000/3000，删除5000） */}
                      <div>
                        <button
                          onClick={() => setActiveModule('industry-trend')}
                          className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                            activeModule === 'industry-trend'
                              ? 'bg-green-100 text-green-700'
                              : 'text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          📊 股票板块-直接数量统计
                        </button>
                        {activeModule === 'industry-trend' && (
                          <div className="mt-2 ml-2 space-y-2">
                            <div className="text-xs text-gray-600 mb-2">
                              分析前N名行业分布及变化趋势
                            </div>
                            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">数据范围</div>
                            <div className="grid grid-cols-3 gap-2">
                              {[1000, 2000, 3000].map((limit) => (
                                <button
                                  key={limit}
                                  onClick={() => setTopNLimit(limit)}
                                  className={`py-2 px-2 rounded text-sm font-medium transition-colors ${
                                    topNLimit === limit
                                      ? 'bg-green-600 text-white'
                                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                  }`}
                                >
                                  前{limit}名
                                </button>
                              ))}
                            </div>
                            <div className="text-xs text-green-600 font-medium mt-3">
                              • 今日前{topNLimit}名行业统计
                            </div>
                            <div className="text-xs text-green-600 font-medium">
                              • 全部数据行业趋势
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {/* 加权版：股票热度分析 */}
                      <div>
                        <button
                          onClick={() => setActiveModule('industry-weighted')}
                          className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                            activeModule === 'industry-weighted'
                              ? 'bg-gradient-to-r from-green-100 to-indigo-100 text-indigo-700 border-2 border-indigo-300'
                              : 'text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          🔥 股票板块-权值热度
                        </button>
                        {activeModule === 'industry-weighted' && (
                          <div className="mt-2 ml-2">
                            <div className="text-xs text-indigo-600 font-medium">
                              • 从5000+股票聚合
                            </div>
                            <div className="text-xs text-indigo-600 font-medium">
                              • k值调节聚焦程度
                            </div>
                            <div className="text-xs text-indigo-600 font-medium">
                              • 4个维度立体分析
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {/* 新版：板块趋势分析 */}
                      <div>
                        <button
                          onClick={() => setActiveModule('sector-trend')}
                          className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                            activeModule === 'sector-trend'
                              ? 'bg-gradient-to-r from-blue-100 to-cyan-100 text-cyan-700 border-2 border-cyan-300'
                              : 'text-gray-600 hover:bg-gray-50'
                          }`}
                        >
                          📈 dc板块数据分析（偷偷看）
                        </button>
                        {activeModule === 'sector-trend' && (
                          <div className="mt-2 ml-2">
                            <div className="text-xs text-cyan-600 font-medium">
                              • 直接查询板块数据
                            </div>
                            <div className="text-xs text-cyan-600 font-medium">
                              • 趋势变化图
                            </div>
                            <div className="text-xs text-cyan-600 font-medium">
                              • 排名变化统计
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* 排名跳变模块 */}
                <div className="mb-2">
                  <button
                    onClick={() => {
                      setExpandedMenu(expandedMenu === 'rank-jump' ? null : 'rank-jump');
                      setActiveModule('rank-jump');
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${
                      activeModule === 'rank-jump'
                        ? 'bg-orange-50 text-orange-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="h-5 w-5" />
                      <span>排名跳变</span>
                    </div>
                    {expandedMenu === 'rank-jump' ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>

                  {/* 排名跳变子菜单 */}
                  {expandedMenu === 'rank-jump' && (
                    <div className="mt-2 ml-4 space-y-2 border-l-2 border-orange-200 pl-3">
                      <div className="text-xs text-gray-600 mb-2">
                        筛选排名突然大幅向前跳变的股票
                      </div>
                      
                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2">板块类型</div>
                      <button
                        onClick={() => setJumpBoardType('main')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          jumpBoardType === 'main'
                            ? 'bg-orange-100 text-orange-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        主板
                      </button>
                      <button
                        onClick={() => setJumpBoardType('all')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          jumpBoardType === 'all'
                            ? 'bg-orange-100 text-orange-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        全部
                      </button>
                      <button
                        onClick={() => setJumpBoardType('bjs')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          jumpBoardType === 'bjs'
                            ? 'bg-orange-100 text-orange-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        北交所
                      </button>

                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">跳变阈值</div>
                      <div className="space-y-2">
                        {[1000, 1500, 2000, 2500, 3000, 3500].map((threshold) => (
                          <button
                            key={threshold}
                            onClick={() => setJumpThreshold(threshold)}
                            className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                              jumpThreshold === threshold
                                ? 'bg-orange-100 text-orange-700'
                                : 'text-gray-600 hover:bg-gray-50'
                            }`}
                          >
                            向前跳变 ≥{threshold}名
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 稳步上升模块 */}
                <div className="mb-2">
                  <button
                    onClick={() => {
                      setExpandedMenu(expandedMenu === 'steady-rise' ? null : 'steady-rise');
                      setActiveModule('steady-rise');
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${
                      activeModule === 'steady-rise'
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <TrendingDown className="h-5 w-5 rotate-180" />
                      <span>稳步上升</span>
                    </div>
                    {expandedMenu === 'steady-rise' ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </button>

                  {/* 稳步上升子菜单 */}
                  {expandedMenu === 'steady-rise' && (
                    <div className="mt-2 ml-4 space-y-2 border-l-2 border-blue-200 pl-3">
                      <div className="text-xs text-gray-600 mb-2">
                        筛选连续多天排名持续上升的股票
                      </div>
                      
                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2">板块类型</div>
                      <button
                        onClick={() => setRiseBoardType('main')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          riseBoardType === 'main'
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        主板
                      </button>
                      <button
                        onClick={() => setRiseBoardType('all')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          riseBoardType === 'all'
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        全部
                      </button>
                      <button
                        onClick={() => setRiseBoardType('bjs')}
                        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                          riseBoardType === 'bjs'
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        北交所
                      </button>

                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">分析周期</div>
                      <div className="grid grid-cols-2 gap-2">
                        {periods.map((period) => (
                          <button
                            key={period}
                            onClick={() => setRisePeriod(period)}
                            className={`py-2 px-2 rounded text-sm font-medium transition-colors ${
                              risePeriod === period
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            {period}天
                          </button>
                        ))}
                      </div>

                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">最小提升幅度</div>
                      <div className="space-y-2">
                        {[100, 500, 1000, 2000].map((improvement) => (
                          <button
                            key={improvement}
                            onClick={() => setMinRankImprovement(improvement)}
                            className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${
                              minRankImprovement === improvement
                                ? 'bg-blue-100 text-blue-700'
                                : 'text-gray-600 hover:bg-gray-50'
                            }`}
                          >
                            提升≥{improvement}名
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 未来扩展预留 */}
                <div className="mt-4 p-3 bg-gray-50 rounded-lg text-center text-xs text-gray-500">
                  更多功能即将推出...
                </div>
              </nav>
            </div>
          </aside>

          {/* Right Content Area */}
          <div className="flex-1 min-w-0">
            {activeModule === 'hot-spots' && (
              <HotSpotsModule 
                boardType={boardType} 
                selectedPeriod={selectedPeriod}
                topN={topN}
                selectedDate={selectedDate}
              />
            )}
            {activeModule === 'stock-query' && (
              <StockQueryModule 
                stockCode={stockCode}
                queryTrigger={queryTrigger}
                selectedDate={selectedDate}
              />
            )}
            {activeModule === 'industry-trend' && (
              <IndustryTrendModule 
                topNLimit={topNLimit}
                selectedDate={selectedDate}
              />
            )}
            {activeModule === 'industry-weighted' && (
              <IndustryWeightedModule 
                selectedDate={selectedDate}
              />
            )}
            {activeModule === 'sector-trend' && (
              <SectorTrendModule 
                selectedDate={selectedDate}
              />
            )}
            {activeModule === 'rank-jump' && (
              <RankJumpModule 
                jumpBoardType={jumpBoardType}
                jumpThreshold={jumpThreshold}
                selectedDate={selectedDate}
              />
            )}
            {activeModule === 'steady-rise' && (
              <SteadyRiseModule 
                risePeriod={risePeriod}
                riseBoardType={riseBoardType}
                minRankImprovement={minRankImprovement}
                selectedDate={selectedDate}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
