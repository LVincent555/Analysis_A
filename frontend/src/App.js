import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, RefreshCw, Calendar, BarChart3, ChevronLeft, ChevronRight, Search, TrendingDown, ChevronDown, ChevronUp, BarChart2, Activity, TrendingUp as TrendingUpIcon } from 'lucide-react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line, Legend as RechartsLegend, AreaChart, Area } from 'recharts';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // 导航和模块状态
  const [activeModule, setActiveModule] = useState('hot-spots'); // 'hot-spots', 'stock-query', 'industry-trend'
  const [expandedMenu, setExpandedMenu] = useState('hot-spots'); // 展开的菜单项
  
  // 最新热点模块状态
  const [boardType, setBoardType] = useState('main');
  const [selectedPeriod, setSelectedPeriod] = useState(2);
  const [analysisData, setAnalysisData] = useState(null);
  const [availableDates, setAvailableDates] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  
  // 股票查询模块状态
  const [stockCode, setStockCode] = useState('');
  const [stockHistory, setStockHistory] = useState(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState(null);
  
  // 行业趋势模块状态
  const [top1000Industry, setTop1000Industry] = useState(null);
  const [industryTrend, setIndustryTrend] = useState(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState(null);
  const [trendTopN, setTrendTopN] = useState(10); // 行业趋势显示的行业数量
  const [trendChartType, setTrendChartType] = useState('area'); // 'line' 或 'area'，默认堆叠面积图
  const [hiddenIndustries, setHiddenIndustries] = useState([]); // 隐藏的行业列表
  const [highlightedIndustry, setHighlightedIndustry] = useState(null); // 高亮的行业

  const periods = [2, 3, 5, 7, 14];

  // 获取可用日期
  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/dates`);
        setAvailableDates(response.data);
      } catch (err) {
        console.error('获取日期失败:', err);
      }
    };
    fetchAvailableDates();
  }, []);

  // 获取分析数据
  useEffect(() => {
    const fetchData = async () => {
      if (!selectedPeriod || !boardType) return;
      
      setLoading(true);
      setError(null);
      setAnalysisData(null); // 清空旧数据避免渲染错误
      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/analyze/${selectedPeriod}?board_type=${boardType}`
        );
        setAnalysisData(response.data);
      } catch (err) {
        console.error('获取分析数据失败:', err);
        const errorMsg = err.code === 'ERR_NETWORK' 
          ? '无法连接到后端服务，请确保后端服务正在运行 (http://localhost:8000)'
          : (err.response?.data?.detail || '获取数据失败，请稍后重试');
        setError(errorMsg);
        setAnalysisData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedPeriod, boardType]);

  // 手动刷新函数
  const handleRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/analyze/${selectedPeriod}?board_type=${boardType}`
      );
      setAnalysisData(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || '获取数据失败');
      console.error('获取分析数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return `${dateStr.slice(0, 4)}年${dateStr.slice(4, 6)}月${dateStr.slice(6, 8)}日`;
  };

  // 查询股票
  const handleStockQuery = async () => {
    if (!stockCode.trim()) {
      setStockError('请输入股票代码');
      return;
    }

    setStockLoading(true);
    setStockError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/stock/${stockCode.trim()}`);
      setStockHistory(response.data);
    } catch (err) {
      setStockError(err.response?.data?.detail || '查询失败，请检查股票代码');
      setStockHistory(null);
    } finally {
      setStockLoading(false);
    }
  };

  // 获取前1000名行业数据（在最新热点和行业趋势模块都需要）
  useEffect(() => {
    if (activeModule === 'hot-spots' || activeModule === 'industry-trend') {
      if (!top1000Industry) {
        const fetchTop1000Industry = async () => {
          try {
            const response = await axios.get(`${API_BASE_URL}/api/industry/top1000`);
            setTop1000Industry(response.data);
          } catch (err) {
            console.error('获取前1000名行业数据失败:', err);
          }
        };
        fetchTop1000Industry();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeModule]);

  // 获取行业趋势数据
  useEffect(() => {
    if (activeModule === 'industry-trend') {
      const fetchIndustryTrend = async () => {
        setTrendLoading(true);
        setTrendError(null);
        try {
          const response = await axios.get(`${API_BASE_URL}/api/industry/trend`);
          setIndustryTrend(response.data);
        } catch (err) {
          console.error('获取行业趋势数据失败:', err);
          setTrendError(err.response?.data?.detail || '获取行业趋势数据失败');
        } finally {
          setTrendLoading(false);
        }
      };
      fetchIndustryTrend();
    }
  }, [activeModule]);

  // 当切换图表类型或显示数量时，重置隐藏状态
  useEffect(() => {
    setHiddenIndustries([]);
    setHighlightedIndustry(null);
  }, [trendChartType, trendTopN]);

  // 统计行业分布
  const industryStats = useMemo(() => {
    if (!analysisData || !analysisData.stocks) return [];
    
    const industryCount = {};
    analysisData.stocks.forEach(stock => {
      const industry = stock.industry || '未知';
      industryCount[industry] = (industryCount[industry] || 0) + 1;
    });
    
    // 转换为柱状图数据格式并排序
    return Object.entries(industryCount)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [analysisData]);

  // 分页数据（带安全检查）
  const paginatedStocks = useMemo(() => {
    if (!analysisData || !analysisData.stocks || !Array.isArray(analysisData.stocks)) return [];
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return analysisData.stocks.slice(start, end);
  }, [analysisData, currentPage, pageSize]);

  // 总页数
  const totalPages = useMemo(() => {
    if (!analysisData || !analysisData.stocks) return 0;
    return Math.ceil(analysisData.stocks.length / pageSize);
  }, [analysisData, pageSize]);

  // 切换周期或板块时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedPeriod, boardType]);

  // 柱状图颜色
  const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#14b8a6'];


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
                  股票重复出现分析系统
                </h1>
                {window.location.port !== '3002' && (
                  <p className="text-xs text-orange-600 mt-1">
                    ⚠️ 建议访问: http://localhost:3002
                  </p>
                )}
              </div>
            </div>
            {availableDates && (
              <div className="flex items-center space-x-2 text-gray-600">
                <Calendar className="h-5 w-5" />
                <span>最新数据: {formatDate(availableDates.latest_date)}</span>
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
                      setActiveModule('industry-trend');
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${
                      activeModule === 'industry-trend'
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
                    <div className="mt-2 ml-4 space-y-2 border-l-2 border-green-200 pl-3">
                      <div className="text-xs text-gray-600 mb-2">
                        分析前1000名行业分布及变化趋势
                      </div>
                      <div className="text-xs text-green-600 font-medium">
                        • 今日前1000名行业统计
                      </div>
                      <div className="text-xs text-green-600 font-medium">
                        • 全部数据行业趋势
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
            {/* 最新热点模块 */}
            {activeModule === 'hot-spots' && (
              <>
                {/* Error Messages */}
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <p className="text-red-800 font-medium">错误: {error}</p>
                  </div>
                )}

        {/* Analysis Results */}
        {analysisData && !loading && (
          <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
            {/* Stats Header */}
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 px-6 py-4">
              <div className="flex items-center justify-between text-white">
                <div className="flex items-center space-x-3">
                  <BarChart3 className="h-6 w-6" />
                  <h2 className="text-xl font-bold">
                    {analysisData.period} 分析结果
                  </h2>
                </div>
                <div className="text-lg font-semibold">
                  共找到 {analysisData.total_stocks} 只股票
                </div>
              </div>
              <p className="text-indigo-100 text-sm mt-2">
                分析日期: {analysisData.analysis_dates.map(formatDate).join(', ')}
              </p>
            </div>

            {/* Table */}
            {analysisData.stocks && Array.isArray(analysisData.stocks) && analysisData.stocks.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        排名
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票代码
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        股票名称
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        行业
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        命中次数
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        最新排名
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        出现日期及排名
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {paginatedStocks.map((stock, index) => (
                      <tr
                        key={stock.stock_code}
                        className="hover:bg-gray-50 transition-colors"
                      >
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {(currentPage - 1) * pageSize + index + 1}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-semibold text-indigo-600">
                            {stock.stock_code}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-medium text-gray-900">
                            {stock.stock_name}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-xs text-gray-600 bg-purple-50 px-2 py-1 rounded">
                            {stock.industry}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            {stock.appearances} 次
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            第 {stock.latest_rank} 名
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {stock.date_rank_info && Array.isArray(stock.date_rank_info) 
                            ? stock.date_rank_info.map((info, idx) => (
                                <span key={idx} className="inline-block mr-2">
                                  {formatDate(info.date)}(第{info.rank}名){idx < stock.date_rank_info.length - 1 ? ',' : ''}
                                </span>
                              ))
                            : stock.date_rank_info}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="px-6 py-12 text-center text-gray-500">
                <BarChart3 className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                <p className="text-lg font-medium">未找到符合条件的股票</p>
                <p className="text-sm mt-1">尝试选择其他分析周期</p>
              </div>
            )}
            
            {/* Pagination */}
            <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-700">
                  显示 {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, analysisData.total_stocks)} 条，共 {analysisData.total_stocks} 条
                </span>
              </div>
              <div className="flex items-center space-x-4">
                {/* Page Size Selector */}
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-700">每页显示:</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value={10}>10</option>
                    <option value={20}>20</option>
                    <option value={30}>30</option>
                    <option value={50}>50</option>
                  </select>
                </div>
                
                {/* Page Navigation */}
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="p-1 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <span className="text-sm text-gray-700">
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage >= totalPages}
                    className="p-1 rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Industry Bar Chart */}
        {analysisData && !loading && industryStats.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center space-x-2 mb-4">
              <BarChart3 className="h-5 w-5 text-indigo-600" />
              <h3 className="text-lg font-bold text-gray-900">当前行业分布统计</h3>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={industryStats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip formatter={(value) => [`${value}个`, '股票数量']} />
                <Bar dataKey="value" fill="#8884d8">
                  {industryStats.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg shadow-md p-12 text-center mb-6">
            <RefreshCw className="mx-auto h-12 w-12 text-indigo-600 animate-spin mb-4" />
            <p className="text-gray-600 text-lg">正在分析数据...</p>
          </div>
        )}

        {/* 今日全部行业分布统计 (前20名) */}
        {!loading && top1000Industry && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5 text-indigo-600" />
                <h3 className="text-lg font-bold text-gray-900">今日全部行业分布统计</h3>
                <span className="text-sm text-gray-500">(前20个行业)</span>
              </div>
              <div className="text-sm text-gray-600">
                基于前1000名股票 · {formatDate(top1000Industry.date)}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={top1000Industry.stats.slice(0, 20)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="industry" angle={-45} textAnchor="end" height={120} tick={{ fontSize: 11 }} />
                <YAxis label={{ value: '股票数量', angle: -90, position: 'insideLeft' }} />
                <Tooltip formatter={(value, name, props) => [`${value}个 (${props.payload.percentage}%)`, '股票数量']} />
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

            {/* 股票查询模块 */}
            {activeModule === 'stock-query' && stockHistory && !stockLoading && (
              <div className="space-y-6 mb-6">
                {/* Stock Info Card */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-2xl font-bold text-gray-900">
                        {stockHistory[0].stock_name} ({stockHistory[0].stock_code})
                      </h3>
                      <p className="text-sm text-gray-600 mt-1">行业: {stockHistory[0].industry}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">最新排名</p>
                      <p className="text-3xl font-bold text-indigo-600">#{stockHistory[0].rank}</p>
                    </div>
                  </div>
                  
                  {/* Latest Data */}
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
                      <p className="text-xs text-gray-600 mb-1">涨跌幅</p>
                      <p className={`text-lg font-bold ${stockHistory[0].price_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {stockHistory[0].price_change >= 0 ? '+' : ''}{stockHistory[0].price_change.toFixed(2)}%
                      </p>
                    </div>
                    <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
                      <p className="text-xs text-gray-600 mb-1">换手率</p>
                      <p className="text-lg font-bold text-purple-600">{stockHistory[0].turnover_rate.toFixed(2)}%</p>
                    </div>
                    <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
                      <p className="text-xs text-gray-600 mb-1">放量天数</p>
                      <p className="text-lg font-bold text-green-600">{stockHistory[0].volume_days.toFixed(1)}</p>
                    </div>
                    <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 p-4 rounded-lg">
                      <p className="text-xs text-gray-600 mb-1">平均量比_50天</p>
                      <p className="text-lg font-bold text-yellow-600">{stockHistory[0].avg_volume_ratio_50.toFixed(2)}</p>
                    </div>
                    <div className="bg-gradient-to-br from-pink-50 to-pink-100 p-4 rounded-lg">
                      <p className="text-xs text-gray-600 mb-1">波动率</p>
                      <p className="text-lg font-bold text-pink-600">{stockHistory[0].volatility.toFixed(2)}%</p>
                    </div>
                  </div>
                </div>

                {/* Rank Trend Chart */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex items-center space-x-2 mb-4">
                    <TrendingDown className="h-5 w-5 text-indigo-600" />
                    <h3 className="text-lg font-bold text-gray-900">排名变化趋势</h3>
                    <span className="text-sm text-gray-500">（排名越小越靠前）</span>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={[...stockHistory].reverse()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="date" 
                        tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                      />
                      <YAxis reversed={true} label={{ value: '排名', angle: -90, position: 'insideLeft' }} />
                      <Tooltip 
                        labelFormatter={(value) => formatDate(value)}
                        formatter={(value) => [`第${value}名`, '排名']}
                      />
                      <RechartsLegend />
                      <Line 
                        type="monotone" 
                        dataKey="rank" 
                        stroke="#6366f1" 
                        strokeWidth={2}
                        dot={{ fill: '#6366f1', r: 4 }}
                        name="排名"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* 行业趋势分析模块 */}
            {activeModule === 'industry-trend' && (
              <>
                {trendError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <p className="text-red-800 font-medium">错误: {trendError}</p>
                  </div>
                )}

                {trendLoading && (
                  <div className="bg-white rounded-lg shadow-md p-12 text-center mb-6">
                    <RefreshCw className="mx-auto h-12 w-12 text-green-600 animate-spin mb-4" />
                    <p className="text-gray-600 text-lg">正在加载行业数据...</p>
                  </div>
                )}

                {!trendLoading && top1000Industry && (
                  <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-2">
                        <BarChart3 className="h-5 w-5 text-green-600" />
                        <h3 className="text-lg font-bold text-gray-900">今日前1000名行业分布</h3>
                        <span className="text-sm text-gray-500">(前30个行业)</span>
                      </div>
                      <div className="text-sm text-gray-600">
                        共 {top1000Industry.total_stocks} 只股票，{top1000Industry.stats.length} 个行业 · {formatDate(top1000Industry.date)}
                      </div>
                    </div>
                    <ResponsiveContainer width="100%" height={600}>
                      <BarChart data={top1000Industry.stats.slice(0, 30)} layout="vertical" margin={{ left: 100, right: 50 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" label={{ value: '股票数量', position: 'bottom' }} />
                        <YAxis 
                          type="category" 
                          dataKey="industry" 
                          width={90}
                          tick={{ fontSize: 11 }}
                        />
                        <Tooltip 
                          formatter={(value, name, props) => [`${value}个 (${props.payload.percentage}%)`, '股票数量']} 
                        />
                        <Bar dataKey="count" fill="#10b981" label={{ position: 'right', fontSize: 11, fill: '#666' }}>
                          {top1000Industry.stats.slice(0, 30).map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {!trendLoading && industryTrend && (() => {
                  // 动态计算每个行业的总数量，按总数量排序，取前N个
                  const industryTotals = {};
                  industryTrend.data.forEach(dateData => {
                    Object.entries(dateData.industry_counts).forEach(([industry, count]) => {
                      industryTotals[industry] = (industryTotals[industry] || 0) + count;
                    });
                  });
                  const topNIndustries = Object.entries(industryTotals)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, trendTopN)
                    .map(([industry]) => industry);

                  // 图例点击事件处理
                  const handleLegendClick = (industry) => {
                    setHiddenIndustries(prev => 
                      prev.includes(industry) 
                        ? prev.filter(ind => ind !== industry)
                        : [...prev, industry]
                    );
                  };

                  // 自定义图例渲染
                  const renderLegend = (props) => {
                    const { payload } = props;
                    return (
                      <div className="pt-4">
                        <div className="flex flex-wrap justify-center gap-3" style={{ fontSize: '11px' }}>
                          {payload.map((entry, index) => {
                            const isHidden = hiddenIndustries.includes(entry.value);
                            const isHighlighted = highlightedIndustry === entry.value;
                            
                            return (
                              <div
                                key={`legend-${index}`}
                                className="flex items-center select-none transition-all duration-200 px-2 py-1 rounded"
                                style={{ 
                                  opacity: isHidden ? 0.4 : 1,
                                  fontWeight: isHighlighted ? 'bold' : 'normal',
                                  backgroundColor: isHighlighted ? '#f0f9ff' : 'transparent',
                                  cursor: 'pointer',
                                  border: isHighlighted ? '1px solid #0ea5e9' : '1px solid transparent'
                                }}
                                onClick={() => {
                                  console.log('Clicked:', entry.value);
                                  handleLegendClick(entry.value);
                                }}
                                onMouseEnter={() => setHighlightedIndustry(entry.value)}
                                onMouseLeave={() => setHighlightedIndustry(null)}
                              >
                                <div
                                  className="w-3 h-3 mr-1.5 rounded-sm flex-shrink-0"
                                  style={{ 
                                    backgroundColor: entry.color,
                                    opacity: isHidden ? 0.3 : 1
                                  }}
                                />
                                <span style={{ 
                                  textDecoration: isHidden ? 'line-through' : 'none',
                                  color: isHidden ? '#999' : '#333'
                                }}>
                                  {entry.value}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                        {hiddenIndustries.length > 0 && (
                          <div className="text-center mt-2">
                            <button
                              onClick={() => setHiddenIndustries([])}
                              className="text-xs text-blue-600 hover:text-blue-800 underline"
                            >
                              显示全部 ({hiddenIndustries.length}个已隐藏)
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  };

                  // 自定义Tooltip
                  const CustomTooltip = ({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      // 按数量降序排序
                      const sortedPayload = [...payload].sort((a, b) => b.value - a.value);
                      const total = sortedPayload.reduce((sum, entry) => sum + entry.value, 0);
                      
                      return (
                        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                          <p className="font-bold mb-2 text-gray-800">{formatDate(label)}</p>
                          <p className="text-sm text-gray-600 mb-2">总计: {total}只</p>
                          <div className="space-y-1">
                            {sortedPayload.map((entry, index) => (
                              <div key={index} className="flex items-center justify-between text-xs">
                                <div className="flex items-center">
                                  <div 
                                    className="w-3 h-3 rounded-sm mr-2" 
                                    style={{ backgroundColor: entry.color }}
                                  />
                                  <span className="text-gray-700">{entry.name}</span>
                                </div>
                                <span className="font-semibold ml-4 text-gray-900">
                                  {entry.value}只 ({((entry.value / total) * 100).toFixed(1)}%)
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    }
                    return null;
                  };

                  return (
                    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                          <TrendingUpIcon className="h-5 w-5 text-green-600" />
                          <h3 className="text-lg font-bold text-gray-900">行业趋势变化（前1000名）</h3>
                          <span className="text-sm text-gray-500">(前{trendTopN}个行业)</span>
                        </div>
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-600">图表类型：</span>
                            <select
                              value={trendChartType}
                              onChange={(e) => setTrendChartType(e.target.value)}
                              className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                            >
                              <option value="line">折线图</option>
                              <option value="area">堆叠面积图</option>
                            </select>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-600">显示数量：</span>
                            <select
                              value={trendTopN}
                              onChange={(e) => setTrendTopN(Number(e.target.value))}
                              className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                            >
                              <option value={5}>前5个</option>
                              <option value={10}>前10个</option>
                              <option value={15}>前15个</option>
                              <option value={20}>前20个</option>
                            </select>
                          </div>
                          <span className="text-sm text-gray-500">
                            (共 {industryTrend.industries.length} 个行业)
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">
                        {trendChartType === 'line' 
                          ? '展示主要行业在不同日期的股票数量变化趋势' 
                          : '堆叠展示各行业数量变化，更直观地看出占比和总量'}
                      </p>
                      <p className="text-xs text-gray-500 mb-4">
                        💡 提示：点击图例可切换显示/隐藏行业，鼠标悬停查看详细数据
                      </p>
                      <ResponsiveContainer width="100%" height={500}>
                        {trendChartType === 'line' ? (
                          <LineChart 
                            data={industryTrend.data} 
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            onMouseLeave={() => setHighlightedIndustry(null)}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                              dataKey="date" 
                              tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                            />
                            <YAxis label={{ value: '股票数量', angle: -90, position: 'insideLeft' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <RechartsLegend content={renderLegend} />
                            {topNIndustries.map((industry, index) => {
                              const isHidden = hiddenIndustries.includes(industry);
                              const isHighlighted = highlightedIndustry === industry;
                              const isDimmed = highlightedIndustry && !isHighlighted;
                              
                              return (
                                <Line
                                  key={industry}
                                  type="monotone"
                                  dataKey={(data) => data.industry_counts[industry] || 0}
                                  name={industry}
                                  stroke={COLORS[index % COLORS.length]}
                                  strokeWidth={isHighlighted ? 4 : 2.5}
                                  strokeOpacity={isHidden ? 0 : (isDimmed ? 0.2 : 1)}
                                  dot={{ r: isHighlighted ? 5 : 4 }}
                                  activeDot={{ r: 7 }}
                                  hide={isHidden}
                                />
                              );
                            })}
                          </LineChart>
                        ) : (
                          <AreaChart 
                            data={industryTrend.data} 
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                            onMouseLeave={() => setHighlightedIndustry(null)}
                          >
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis 
                              dataKey="date" 
                              tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                            />
                            <YAxis label={{ value: '股票数量', angle: -90, position: 'insideLeft' }} />
                            <Tooltip content={<CustomTooltip />} />
                            <RechartsLegend content={renderLegend} />
                            {topNIndustries.map((industry, index) => {
                              const isHidden = hiddenIndustries.includes(industry);
                              const isHighlighted = highlightedIndustry === industry;
                              const isDimmed = highlightedIndustry && !isHighlighted;
                              
                              return (
                                <Area
                                  key={industry}
                                  type="monotone"
                                  dataKey={(data) => data.industry_counts[industry] || 0}
                                  name={industry}
                                  stackId="1"
                                  stroke={COLORS[index % COLORS.length]}
                                  fill={COLORS[index % COLORS.length]}
                                  fillOpacity={isHidden ? 0 : (isDimmed ? 0.15 : (isHighlighted ? 0.8 : 0.6))}
                                  strokeOpacity={isHidden ? 0 : (isDimmed ? 0.2 : 1)}
                                  strokeWidth={isHighlighted ? 2.5 : 1}
                                  hide={isHidden}
                                />
                              );
                            })}
                          </AreaChart>
                        )}
                      </ResponsiveContainer>
                    </div>
                  );
                })()}
              </>
            )}
          </div>
          {/* End of Right Content Area */}
        </div>
        {/* End of flex container */}
      </main>

      {/* Footer */}
      <footer className="mt-12 pb-6 text-center text-gray-600 text-sm">
        <p>© 2025 股票分析系统 | 数据实时更新</p>
      </footer>
    </div>
  );
}

export default App;
