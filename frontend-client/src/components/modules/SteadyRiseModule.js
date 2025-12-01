/**
 * 稳步上升分析模块 - 完整版
 */
import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw, TrendingUp, ChevronDown, ChevronUp, Filter, Search, X } from 'lucide-react';
import apiClient from '../../services/api';
import { API_BASE_URL } from '../../constants/config';
import { formatDate } from '../../utils';

const sigmaMultipliers = [1.0, 0.75, 0.5, 0.3, 0.15];

export default function SteadyRiseModule({ risePeriod, riseBoardType, minRankImprovement, selectedDate }) {
  const [steadyRiseData, setSteadyRiseData] = useState(null);
  const [steadyRiseLoading, setSteadyRiseLoading] = useState(false);
  const [steadyRiseError, setSteadyRiseError] = useState(null);
  const [riseSortReverse, setRiseSortReverse] = useState(false);
  const [riseShowSigma, setRiseShowSigma] = useState(false);
  const [riseSigmaMultiplier, setRiseSigmaMultiplier] = useState(1.0);
  const [searchQuery, setSearchQuery] = useState('');

  // 获取稳步上升数据
  useEffect(() => {
    const fetchSteadyRiseData = async () => {
      setSteadyRiseLoading(true);
      setSteadyRiseError(null);
      try {
        let url = `/api/steady-rise?period=${risePeriod}&board_type=${riseBoardType}&min_rank_improvement=${minRankImprovement}&sigma_multiplier=${riseSigmaMultiplier}`;
        if (selectedDate) {
          url += `&date=${selectedDate}`;
        }
        const response = await apiClient.get(url);
        setSteadyRiseData(response);
      } catch (err) {
        console.error('获取稳步上升数据失败:', err);
        setSteadyRiseError(err.response?.data?.detail || '获取数据失败');
      } finally {
        setSteadyRiseLoading(false);
      }
    };

    fetchSteadyRiseData();
  }, [risePeriod, riseBoardType, minRankImprovement, riseSigmaMultiplier, selectedDate]);

  // 搜索过滤逻辑
  const filteredStocks = useMemo(() => {
    if (!steadyRiseData || !steadyRiseData.stocks) return [];
    
    const displayStocks = riseShowSigma ? steadyRiseData.sigma_stocks : steadyRiseData.stocks;
    
    if (!searchQuery.trim()) {
      return displayStocks;
    }
    
    const query = searchQuery.toLowerCase().trim();
    return displayStocks.filter(stock => 
      stock.code.toLowerCase().includes(query) || 
      stock.name.toLowerCase().includes(query)
    );
  }, [steadyRiseData, riseShowSigma, searchQuery]);

  return (
    <div className="space-y-6 mb-6">
      {steadyRiseError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">错误: {steadyRiseError}</p>
        </div>
      )}

      {steadyRiseLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
          <span className="ml-3 text-lg text-gray-600">分析中...</span>
        </div>
      )}

      {!steadyRiseLoading && steadyRiseData && (
        <>
          {/* 统计信息 */}
          <div className="bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h2 className="text-2xl font-bold">稳步上升筛选</h2>
                <p className="mt-1 text-blue-100">
                  {steadyRiseData.dates.map((d, i) => formatDate(d) + (i < steadyRiseData.dates.length - 1 ? ' → ' : ''))}
                </p>
                {steadyRiseData.mean_improvement && (
                  <div className="mt-3 text-sm opacity-90">
                    <p>平均提升: {steadyRiseData.mean_improvement.toFixed(1)}名 | 标准差: {steadyRiseData.std_improvement.toFixed(1)}</p>
                    {steadyRiseData.sigma_range && (
                      <p>±1σ范围: [{steadyRiseData.sigma_range[0].toFixed(0)}, {steadyRiseData.sigma_range[1].toFixed(0)}]名 ({steadyRiseData.sigma_stocks?.length || 0}只)</p>
                    )}
                  </div>
                )}
              </div>
              <div className="text-right">
                <p className="text-sm opacity-90">稳步上升股票</p>
                <p className="text-4xl font-bold">{steadyRiseData.total_count}</p>
                <p className="text-sm opacity-90 mt-1">连续{steadyRiseData.period}天上升</p>
              </div>
            </div>
          </div>

          {/* 搜索框 */}
          <div className="flex items-center space-x-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索股票代码或名称..."
                className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
            {searchQuery && (
              <div className="text-sm text-gray-600 whitespace-nowrap">
                找到 <span className="font-bold text-blue-600">{filteredStocks.length}</span> 只股票
              </div>
            )}
          </div>

          {/* 控制按钮 */}
          <div className="flex justify-between items-center">
            <button
              onClick={() => setRiseSortReverse(!riseSortReverse)}
              className="flex items-center space-x-2 px-4 py-2 bg-white border border-blue-300 rounded-lg hover:bg-blue-50 transition-colors"
            >
              {riseSortReverse ? (
                <>
                  <ChevronDown className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-700">倒序显示</span>
                </>
              ) : (
                <>
                  <ChevronUp className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-700">正序显示</span>
                </>
              )}
            </button>
            
            {/* σ范围筛选控制 */}
            {steadyRiseData.sigma_stocks && steadyRiseData.sigma_stocks.length > 0 && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setRiseShowSigma(!riseShowSigma)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    riseShowSigma
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-blue-300 text-blue-700 hover:bg-blue-50'
                  }`}
                >
                  <Filter className="h-4 w-4" />
                  <span className="text-sm font-medium">
                    {riseShowSigma ? `±${riseSigmaMultiplier}σ筛选 (${steadyRiseData.sigma_stocks.length}只)` : '显示±σ范围'}
                  </span>
                </button>
                
                {/* σ倍数选择 */}
                <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
                  {sigmaMultipliers.map((multiplier) => (
                    <button
                      key={multiplier}
                      onClick={() => setRiseSigmaMultiplier(multiplier)}
                      className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                        riseSigmaMultiplier === multiplier
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-600 hover:bg-white'
                      }`}
                    >
                      ±{multiplier}σ
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 股票列表 */}
          {filteredStocks.length > 0 ? (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gradient-to-r from-blue-50 to-indigo-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">序号</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">股票代码</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">股票名称</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">行业</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">起始排名</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">最新排名</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">总提升</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">日均提升</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">波动率</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">排名历史</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {(() => {
                      const sortedStocks = riseSortReverse ? [...filteredStocks].reverse() : filteredStocks;
                      return sortedStocks.map((stock, index) => (
                      <tr key={index} className="hover:bg-blue-50 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                          {index + 1}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-indigo-600">
                          {stock.code}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm font-medium text-gray-900">{stock.name}</span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                          {stock.industry}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          第 {stock.start_rank} 名
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm font-bold text-blue-600">
                            第 {stock.end_rank} 名
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                            <span className="text-sm font-bold text-green-600">
                              +{stock.total_improvement}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          +{stock.avg_daily_improvement.toFixed(1)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
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
                        <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-600">
                          {stock.rank_history.join(' → ')}
                        </td>
                      </tr>
                    ));
                    })()}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
              <p className="text-yellow-800 font-medium">暂无符合条件的股票</p>
              <p className="text-yellow-600 text-sm mt-2">尝试降低提升幅度阈值、减少分析天数或选择不同的板块类型</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}



