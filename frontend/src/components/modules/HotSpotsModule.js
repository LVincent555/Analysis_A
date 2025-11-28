/**
 * 最新热点分析模块 - 完整版
 */
import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, RefreshCw, Calendar, BarChart3, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { API_BASE_URL, COLORS } from '../../constants';
import { formatDate } from '../../utils';
import SearchBar from '../common/SearchBar';
import HighlightText from '../common/HighlightText';

export default function HotSpotsModule({ boardType, selectedPeriod, topN, selectedDate, refreshTrigger }) {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10); // 默认每页10条
  const [top1000Industry, setTop1000Industry] = useState(null);
  const [sortBy, setSortBy] = useState('hit_count'); // 'hit_count', 'rank', 'price_change'
  const [searchQuery, setSearchQuery] = useState(''); // 搜索关键词

  // 获取分析数据
  useEffect(() => {
    const fetchData = async () => {
      if (!selectedPeriod || !boardType || !topN || !selectedDate) return;
      
      setLoading(true);
      setError(null);
      setAnalysisData(null);
      try {
        let url = `${API_BASE_URL}/api/analyze/${selectedPeriod}?board_type=${boardType}&top_n=${topN}`;
        if (selectedDate) {
          url += `&date=${selectedDate}`;
        }
        // 加上时间戳防止缓存
        url += `&_t=${Date.now()}`;
        
        const response = await axios.get(url);
        setAnalysisData(response.data);
      } catch (err) {
        console.error('获取分析数据失败:', err);
        const errorMsg = err.code === 'ERR_NETWORK' 
          ? '无法连接到后端服务，请确保后端服务正在运行'
          : (err.response?.data?.detail || '获取数据失败，请稍后重试');
        setError(errorMsg);
        setAnalysisData(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedPeriod, boardType, topN, selectedDate, refreshTrigger]);

  // 获取前1000名行业数据
  useEffect(() => {
    const fetchTop1000Industry = async () => {
      if (!selectedDate) return;
      try {
        let url = `${API_BASE_URL}/api/industry/top1000?limit=1000`;
        if (selectedDate) {
          url += `&date=${selectedDate}`;
        }
        const response = await axios.get(url);
        setTop1000Industry(response.data);
      } catch (err) {
        console.error('获取前1000名行业数据失败:', err);
      }
    };
    fetchTop1000Industry();
  }, [selectedDate]);


  // 统计行业分布
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

  // 排序后的股票列表（带固定排名）
  const sortedStocks = useMemo(() => {
    if (!analysisData || !analysisData.stocks || !Array.isArray(analysisData.stocks)) return [];
    
    // 先按命中次数排序并添加固定排名
    const stocksWithFixedRank = [...analysisData.stocks]
      .sort((a, b) => (b.appearances || 0) - (a.appearances || 0)) // 使用 appearances 字段
      .map((stock, index) => ({
        ...stock,
        fixed_rank: index + 1 // 固定排名（按命中次数）
      }));
    
    // 根据sortBy进行二次排序
    switch (sortBy) {
      case 'rank':
        return stocksWithFixedRank.sort((a, b) => (a.latest_rank || 0) - (b.latest_rank || 0)); // 按最新排名升序
      case 'price_change':
        return stocksWithFixedRank.sort((a, b) => (b.price_change || 0) - (a.price_change || 0)); // 按涨跌幅降序
      case 'hit_count':
      default:
        return stocksWithFixedRank; // 保持按命中次数排序（已经排序过了）
    }
  }, [analysisData, sortBy]);

  // 搜索过滤后的股票列表
  const filteredStocks = useMemo(() => {
    if (!searchQuery.trim()) {
      return sortedStocks;
    }
    
    const query = searchQuery.toLowerCase().trim();
    return sortedStocks.filter(stock => {
      const code = (stock.stock_code || '').toLowerCase();
      const name = (stock.stock_name || stock.name || '').toLowerCase();
      return code.includes(query) || name.includes(query);
    });
  }, [sortedStocks, searchQuery]);

  // 搜索后重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  // 分页数据（使用过滤后的列表）
  const paginatedStocks = useMemo(() => {
    if (!filteredStocks || filteredStocks.length === 0) return [];
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filteredStocks.slice(start, end);
  }, [filteredStocks, currentPage, pageSize]);

  // 总页数（使用过滤后的列表）
  const totalPages = useMemo(() => {
    if (!filteredStocks) return 0;
    return Math.ceil(filteredStocks.length / pageSize);
  }, [filteredStocks, pageSize]);

  // 切换周期、板块或排序方式时重置到第一页
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedPeriod, boardType, sortBy]);

  return (
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

          {/* 搜索框和排序按钮 */}
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200 space-y-3">
            {/* 搜索框 */}
            <div className="flex items-center space-x-3">
              <SearchBar
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder="搜索股票代码或名称..."
                className="flex-1 max-w-md"
              />
              {searchQuery && (
                <div className="text-sm text-gray-600">
                  找到 <span className="font-semibold text-indigo-600">{filteredStocks.length}</span> 只股票
                </div>
              )}
            </div>
            
            {/* 排序按钮 */}
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600 font-medium">排序方式:</span>
              <button
                onClick={() => setSortBy('hit_count')}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  sortBy === 'hit_count'
                    ? 'bg-indigo-600 text-white font-medium'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                按命中次数
              </button>
              <button
                onClick={() => setSortBy('rank')}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  sortBy === 'rank'
                    ? 'bg-indigo-600 text-white font-medium'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                按排名
              </button>
              <button
                onClick={() => setSortBy('price_change')}
                className={`px-3 py-1 rounded text-sm transition-colors ${
                  sortBy === 'price_change'
                    ? 'bg-indigo-600 text-white font-medium'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                按涨跌幅
              </button>
            </div>
          </div>

          {/* Table View (Desktop) */}
          {analysisData.stocks && Array.isArray(analysisData.stocks) && analysisData.stocks.length > 0 ? (
            <>
              {/* Desktop Table View */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        序号
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
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        涨跌幅
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        波动率
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
                          {stock.fixed_rank}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-semibold text-indigo-600">
                            <HighlightText text={stock.stock_code} highlight={searchQuery} />
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm font-medium text-gray-900">
                            <HighlightText text={stock?.stock_name || stock?.name || '-'} highlight={searchQuery} />
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
                        <td className="px-6 py-4 whitespace-nowrap text-right">
                          {stock.price_change !== null && stock.price_change !== undefined ? (
                            <span className={`text-sm font-medium ${
                              stock.price_change > 0 ? 'text-red-600' : 
                              stock.price_change < 0 ? 'text-green-600' : 
                              'text-gray-600'
                            }`}>
                              {stock.price_change > 0 ? '+' : ''}{stock.price_change.toFixed(2)}%
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right">
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
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {stock.date_rank_info && Array.isArray(stock.date_rank_info) && stock.date_rank_info.length > 0
                            ? stock.date_rank_info.map((info, idx) => (
                                <div key={idx} className="text-xs">
                                  {formatDate(info.date)}(第{info.rank}名)
                                </div>
                              ))
                            : '-'
                          }
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Card View */}
              <div className="md:hidden space-y-4 p-4 bg-gray-50">
                {paginatedStocks.map((stock, index) => (
                  <div key={stock.stock_code} className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg font-bold text-gray-900">
                          <HighlightText text={stock?.stock_name || stock?.name || '-'} highlight={searchQuery} />
                        </span>
                        <span className="text-xs font-mono text-gray-500">
                          <HighlightText text={stock.stock_code} highlight={searchQuery} />
                        </span>
                      </div>
                      <div className="flex flex-col items-end">
                         {stock.price_change !== null && stock.price_change !== undefined ? (
                            <span className={`text-sm font-bold ${
                              stock.price_change > 0 ? 'text-red-600' : 
                              stock.price_change < 0 ? 'text-green-600' : 
                              'text-gray-600'
                            }`}>
                              {stock.price_change > 0 ? '+' : ''}{stock.price_change.toFixed(2)}%
                            </span>
                          ) : null}
                          <span className="text-xs text-gray-400 mt-1">最新排名 #{stock.latest_rank}</span>
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span className="text-xs text-gray-600 bg-purple-50 px-2 py-1 rounded">
                        {stock.industry}
                      </span>
                      <span className="text-xs font-medium bg-green-100 text-green-800 px-2 py-1 rounded-full">
                        命中 {stock.appearances} 次
                      </span>
                      <span className="text-xs font-medium bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                         最新第 {stock.latest_rank} 名
                      </span>
                      {stock.volatility !== null && stock.volatility !== undefined && (
                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                          stock.volatility > 5 ? 'bg-orange-100 text-orange-700' : 
                          stock.volatility > 3 ? 'bg-yellow-100 text-yellow-700' : 
                          'bg-gray-100 text-gray-600'
                        }`}>
                          波动 {stock.volatility.toFixed(1)}%
                        </span>
                      )}
                    </div>
                    
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-xs text-gray-500 mb-1">历史排名:</p>
                      <div className="flex flex-wrap gap-2">
                         {stock.date_rank_info && Array.isArray(stock.date_rank_info) && stock.date_rank_info.slice(0, 4).map((info, idx) => (
                            <span key={idx} className="text-xs text-gray-600 bg-gray-50 px-1.5 py-0.5 rounded border border-gray-200">
                              {formatDate(info.date).slice(5)}: #{info.rank}
                            </span>
                          ))
                        }
                        {(stock.date_rank_info?.length || 0) > 4 && (
                          <span className="text-xs text-gray-400">...</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="px-6 py-12 text-center text-gray-500">
              {searchQuery ? (
                <>
                  <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                  <p className="text-lg font-medium">未找到包含 "{searchQuery}" 的股票</p>
                  <p className="text-sm mt-1 text-gray-400">
                    该股票可能不在当前热点榜中，请尝试其他关键词
                  </p>
                </>
              ) : (
                <>
                  <BarChart3 className="mx-auto h-12 w-12 text-gray-400 mb-3" />
                  <p className="text-lg font-medium">未找到符合条件的股票</p>
                  <p className="text-sm mt-1">尝试选择其他分析周期</p>
                </>
              )}
            </div>
          )}
          
          {/* Pagination */}
          <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-700">
                显示 {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, filteredStocks.length)} 条，共 {filteredStocks.length} 条
                {searchQuery && <span className="text-indigo-600 ml-1">（搜索结果）</span>}
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
      {analysisData && analysisData.stocks && analysisData.stocks.length > 0 && !loading && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center space-x-2 mb-4">
            <BarChart3 className="h-5 w-5 text-indigo-600" />
            <h3 className="text-lg font-bold text-gray-900">当前行业分布统计 (共{analysisData.stocks.length}只股票)</h3>
          </div>
          {industryStats && industryStats.length > 0 ? (
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
          ) : (
            <div className="text-center py-8 text-gray-500">
              <p>暂无行业数据</p>
            </div>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center mb-6">
          <RefreshCw className="mx-auto h-12 w-12 text-indigo-600 animate-spin mb-4" />
          <p className="text-gray-600 text-lg">正在分析数据...</p>
        </div>
      )}
    </>
  );
}
