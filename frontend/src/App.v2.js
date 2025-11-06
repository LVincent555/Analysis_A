/**
 * 主应用组件 - 模块化重构版本
 */
import React, { useState, useMemo, useEffect } from 'react';
import { Sidebar, Loading, ErrorMessage } from './components/common';
import { COLORS, PERIODS, DEFAULT_PAGE_SIZE, DEFAULT_TREND_TOP_N, CHART_TYPES } from './constants';
import { formatDate, formatShortDate, calculateIndustryTotals, getTopNIndustries } from './utils';
import { useAnalysis, useAvailableDates, useTop1000Industry, useIndustryTrend } from './hooks';
import { queryStock } from './services';

// Recharts组件
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, Legend as RechartsLegend, AreaChart, Area
} from 'recharts';

// Lucide图标
import {
  TrendingUp, RefreshCw, Calendar, BarChart3, ChevronLeft, ChevronRight,
  Search, TrendingDown, Activity, TrendingUp as TrendingUpIcon
} from 'lucide-react';

function App() {
  // 导航状态
  const [activeModule, setActiveModule] = useState('hot-spots');
  const [expandedMenu, setExpandedMenu] = useState('hot-spots');

  // 最新热点模块状态
  const [selectedPeriod, setSelectedPeriod] = useState(2);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  // 股票查询模块状态
  const [stockCode, setStockCode] = useState('');
  const [stockHistory, setStockHistory] = useState(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState(null);

  // 行业趋势模块状态
  const [trendTopN, setTrendTopN] = useState(DEFAULT_TREND_TOP_N);
  const [trendChartType, setTrendChartType] = useState(CHART_TYPES.AREA);
  const [hiddenIndustries, setHiddenIndustries] = useState([]);
  const [highlightedIndustry, setHighlightedIndustry] = useState(null);

  // 使用自定义Hooks
  const { dates: availableDates } = useAvailableDates();
  const { data: analysisData, loading, error } = useAnalysis(selectedPeriod);
  const { data: top1000Industry } = useTop1000Industry(activeModule === 'hot-spots' || activeModule === 'industry-trend');
  const { data: industryTrend, loading: trendLoading, error: trendError } = useIndustryTrend(activeModule === 'industry-trend');

  // 重置交互状态
  useEffect(() => {
    setHiddenIndustries([]);
    setHighlightedIndustry(null);
  }, [trendChartType, trendTopN]);

  // 股票查询处理
  const handleStockQuery = async () => {
    if (!stockCode.trim()) return;

    setStockLoading(true);
    setStockError(null);
    try {
      const response = await queryStock(stockCode.trim());
      setStockHistory(response);
    } catch (err) {
      setStockError(err.response?.data?.detail || '查询失败');
      setStockHistory(null);
    } finally {
      setStockLoading(false);
    }
  };

  // 计算行业统计
  const industryStats = useMemo(() => {
    if (!analysisData || !analysisData.stocks) return [];

    const industryCount = {};
    analysisData.stocks.forEach(stock => {
      const industry = stock.industry || '未知';
      industryCount[industry] = (industryCount[industry] || 0) + 1;
    });

    return Object.entries(industryCount)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [analysisData]);

  // 分页数据
  const paginatedStocks = useMemo(() => {
    if (!analysisData || !analysisData.stocks) return [];
    const startIndex = (currentPage - 1) * pageSize;
    return analysisData.stocks.slice(startIndex, startIndex + pageSize);
  }, [analysisData, currentPage, pageSize]);

  const totalPages = Math.ceil((analysisData?.stocks?.length || 0) / pageSize);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* 侧边栏 */}
      <Sidebar
        activeModule={activeModule}
        setActiveModule={setActiveModule}
        expandedMenu={expandedMenu}
        setExpandedMenu={setExpandedMenu}
      />

      {/* 主内容区域 */}
      <main className="flex-1 p-8">
        {/* 最新热点模块 */}
        {activeModule === 'hot-spots' && (
          <>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">最新热点分析</h2>

            {/* 周期选择 */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <div className="flex items-center space-x-2 mb-4">
                <Calendar className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-bold text-gray-900">分析周期</h3>
              </div>
              <div className="flex space-x-2">
                {PERIODS.map(period => (
                  <button
                    key={period}
                    onClick={() => setSelectedPeriod(period)}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      selectedPeriod === period
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {period}天
                  </button>
                ))}
              </div>
            </div>

            {/* 错误提示 */}
            {error && <ErrorMessage message={error} />}

            {/* 加载中 */}
            {loading && <Loading message="正在分析数据..." />}

            {/* 分析结果 */}
            {!loading && analysisData && (
              <>
                <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-4">
                    分析结果 (共{analysisData.total_stocks}只股票)
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">股票代码</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">股票名称</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">行业</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">出现次数</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">最新排名</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {paginatedStocks.map((stock, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{stock.code}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{stock.name}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stock.industry}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{stock.count}次</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{stock.rank}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 分页控制 */}
                  <div className="mt-4 flex items-center justify-between">
                    <div className="text-sm text-gray-700">
                      显示第 {(currentPage - 1) * pageSize + 1} 到 {Math.min(currentPage * pageSize, analysisData.total_stocks)} 条，共 {analysisData.total_stocks} 条
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 rounded border disabled:opacity-50"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <span className="px-3 py-1">{currentPage} / {totalPages}</span>
                      <button
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 rounded border disabled:opacity-50"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* 行业分布图 */}
                {industryStats.length > 0 && (
                  <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4">当前行业分布统计</h3>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={industryStats}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="value" fill="#8884d8">
                          {industryStats.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* 今日全部行业分布统计 */}
                {top1000Industry && (
                  <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                    <h3 className="text-lg font-bold text-gray-900 mb-4">今日全部行业分布统计 (前20个行业)</h3>
                    <ResponsiveContainer width="100%" height={350}>
                      <BarChart data={top1000Industry.stats.slice(0, 20)}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="industry" angle={-45} textAnchor="end" height={120} />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="count" fill="#6366f1">
                          {top1000Industry.stats.slice(0, 20).map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* 股票查询模块 */}
        {activeModule === 'stock-query' && (
          <>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">股票查询</h2>
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <div className="flex space-x-4">
                <input
                  type="text"
                  value={stockCode}
                  onChange={(e) => setStockCode(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleStockQuery()}
                  placeholder="请输入股票代码..."
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-md"
                />
                <button
                  onClick={handleStockQuery}
                  disabled={stockLoading}
                  className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  {stockLoading ? '查询中...' : '查询'}
                </button>
              </div>
            </div>

            {stockError && <ErrorMessage message={stockError} />}

            {stockHistory && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">
                  {stockHistory.name} ({stockHistory.code})
                </h3>
                <p className="text-gray-600 mb-4">行业: {stockHistory.industry}</p>
                <p className="text-gray-600 mb-4">出现次数: {stockHistory.appears_count}次</p>
                
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={stockHistory.date_rank_info}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tickFormatter={formatShortDate} />
                    <YAxis reversed label={{ value: '排名', angle: -90 }} />
                    <Tooltip labelFormatter={formatDate} />
                    <Line type="monotone" dataKey="rank" stroke="#8884d8" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}

        {/* 行业趋势分析模块 */}
        {activeModule === 'industry-trend' && (
          <>
            <h2 className="text-3xl font-bold text-gray-900 mb-6">行业趋势分析</h2>
            
            {trendError && <ErrorMessage message={trendError} />}
            {trendLoading && <Loading message="正在加载行业数据..." />}

            {/* 今日前1000名行业分布 */}
            {!trendLoading && top1000Industry && (
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">
                  今日前1000名行业分布 (前30个行业)
                </h3>
                <ResponsiveContainer width="100%" height={600}>
                  <BarChart data={top1000Industry.stats.slice(0, 30)} layout="vertical" margin={{ left: 100, right: 50 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="industry" width={90} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#10b981">
                      {top1000Industry.stats.slice(0, 30).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* 行业趋势变化图 - 简化版，完整功能需要更多代码 */}
            {!trendLoading && industryTrend && (
              <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                <h3 className="text-lg font-bold text-gray-900 mb-4">行业趋势变化（前1000名）</h3>
                <p className="text-sm text-gray-600 mb-4">
                  💡 提示：完整交互功能请参考原App.js实现
                </p>
              </div>
            )}
          </>
        )}

        {/* 页脚 */}
        <footer className="mt-12 pb-6 text-center text-gray-600 text-sm">
          <p>A股数据分析系统 v0.2.0 - 模块化重构版本</p>
        </footer>
      </main>
    </div>
  );
}

export default App;
