/**
 * 最新热点分析模块 - 完整版
 */
import React, { useState, useEffect, useMemo } from 'react';
import { TrendingUp, RefreshCw, Calendar, BarChart3, ChevronLeft, ChevronRight } from 'lucide-react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { API_BASE_URL, COLORS } from '../../constants';
import { formatDate } from '../../utils';

export default function HotSpotsModule({ boardType, selectedPeriod, topN }) {
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [top1000Industry, setTop1000Industry] = useState(null);

  // 获取分析数据
  useEffect(() => {
    const fetchData = async () => {
      if (!selectedPeriod || !boardType || !topN) return;
      
      setLoading(true);
      setError(null);
      setAnalysisData(null);
      try {
        const response = await axios.get(
          `${API_BASE_URL}/api/analyze/${selectedPeriod}?board_type=${boardType}&top_n=${topN}`
        );
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
  }, [selectedPeriod, boardType, topN]);

  // 获取前1000名行业数据
  useEffect(() => {
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
  }, [top1000Industry]);


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

  // 分页数据
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
                          {stock?.stock_name || stock?.name || '-'}
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

      {/* 今日全部行业分布统计 (前20名) */}
      {!loading && top1000Industry && top1000Industry.stats && (
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
  );
}
