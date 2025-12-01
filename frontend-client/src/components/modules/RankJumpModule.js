/**
 * 排名跳变分析模块 - 完整版
 */
import React, { useState, useEffect, useMemo } from 'react';
import { RefreshCw, TrendingUp, ChevronDown, ChevronUp, Filter, Search, X, Info } from 'lucide-react';
import apiClient from '../../services/api';
import { API_BASE_URL } from '../../constants/config';
import { formatDate } from '../../utils';
import StockDetailPopup from '../common/StockDetailPopup';

const sigmaMultipliers = [1.0, 0.75, 0.5, 0.3, 0.15];

export default function RankJumpModule({ jumpBoardType, jumpThreshold, selectedDate }) {
  const [rankJumpData, setRankJumpData] = useState(null);
  const [rankJumpLoading, setRankJumpLoading] = useState(false);
  const [rankJumpError, setRankJumpError] = useState(null);
  const [jumpSortReverse, setJumpSortReverse] = useState(false);
  const [jumpShowSigma, setJumpShowSigma] = useState(false);
  const [jumpSigmaMultiplier, setJumpSigmaMultiplier] = useState(1.0);
  const [searchQuery, setSearchQuery] = useState('');
  const [detailPopup, setDetailPopup] = useState({ isOpen: false, stockCode: null, stockName: null });

  // 获取排名跳变数据
  useEffect(() => {
    const fetchRankJumpData = async () => {
      setRankJumpLoading(true);
      setRankJumpError(null);
      try {
        let url = `/api/rank-jump?board_type=${jumpBoardType}&jump_threshold=${jumpThreshold}&sigma_multiplier=${jumpSigmaMultiplier}`;
        if (selectedDate) {
          url += `&date=${selectedDate}`;
        }
        const response = await apiClient.get(url);
        setRankJumpData(response);
      } catch (err) {
        console.error('获取排名跳变数据失败:', err);
        setRankJumpError(err.response?.data?.detail || '获取数据失败');
      } finally {
        setRankJumpLoading(false);
      }
    };

    fetchRankJumpData();
  }, [jumpBoardType, jumpThreshold, jumpSigmaMultiplier, selectedDate]);

  // 搜索过滤逻辑
  const filteredStocks = useMemo(() => {
    if (!rankJumpData || !rankJumpData.stocks) return [];
    
    const displayStocks = jumpShowSigma ? rankJumpData.sigma_stocks : rankJumpData.stocks;
    
    if (!searchQuery.trim()) {
      return displayStocks;
    }
    
    const query = searchQuery.toLowerCase().trim();
    return displayStocks.filter(stock => 
      stock.code.toLowerCase().includes(query) || 
      stock.name.toLowerCase().includes(query)
    );
  }, [rankJumpData, jumpShowSigma, searchQuery]);

  return (
    <div className="space-y-6 mb-6">
      {rankJumpError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 font-medium">错误: {rankJumpError}</p>
        </div>
      )}

      {rankJumpLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 text-indigo-600 animate-spin" />
          <span className="ml-3 text-lg text-gray-600">分析中...</span>
        </div>
      )}

      {!rankJumpLoading && rankJumpData && (
        <>
          {/* 统计信息 */}
          <div className="bg-gradient-to-r from-orange-500 to-red-500 rounded-lg shadow-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h2 className="text-2xl font-bold">排名跳变筛选</h2>
                <p className="mt-1 text-orange-100">
                  {formatDate(rankJumpData.previous_date)} → {formatDate(rankJumpData.latest_date)}
                </p>
                {rankJumpData.mean_rank_change && (
                  <div className="mt-3 text-sm opacity-90">
                    <p>平均跳变: {rankJumpData.mean_rank_change.toFixed(1)}名 | 标准差: {rankJumpData.std_rank_change.toFixed(1)}</p>
                    {rankJumpData.sigma_range && (
                      <p>±1σ范围: [{rankJumpData.sigma_range[0].toFixed(0)}, {rankJumpData.sigma_range[1].toFixed(0)}]名 ({rankJumpData.sigma_stocks?.length || 0}只)</p>
                    )}
                  </div>
                )}
              </div>
              <div className="text-right">
                <p className="text-sm opacity-90">跳变股票数量</p>
                <p className="text-4xl font-bold">{rankJumpData.total_count}</p>
                <p className="text-sm opacity-90 mt-1">向前跳变 ≥{rankJumpData.jump_threshold}名</p>
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
                className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
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
                找到 <span className="font-bold text-orange-600">{filteredStocks.length}</span> 只股票
              </div>
            )}
          </div>

          {/* 控制按钮 */}
          <div className="flex justify-between items-center">
            <button
              onClick={() => setJumpSortReverse(!jumpSortReverse)}
              className="flex items-center space-x-2 px-4 py-2 bg-white border border-orange-300 rounded-lg hover:bg-orange-50 transition-colors"
            >
              {jumpSortReverse ? (
                <>
                  <ChevronDown className="h-4 w-4 text-orange-600" />
                  <span className="text-sm font-medium text-orange-700">倒序显示</span>
                </>
              ) : (
                <>
                  <ChevronUp className="h-4 w-4 text-orange-600" />
                  <span className="text-sm font-medium text-orange-700">正序显示</span>
                </>
              )}
            </button>
            
            {/* σ范围筛选控制 */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setJumpShowSigma(!jumpShowSigma)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  jumpShowSigma
                    ? 'bg-orange-600 text-white'
                    : 'bg-white border border-orange-300 text-orange-700 hover:bg-orange-50'
                }`}
              >
                <Filter className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {jumpShowSigma ? `±${jumpSigmaMultiplier}σ筛选 (${rankJumpData.sigma_stocks?.length || 0}只)` : '显示±σ范围'}
                </span>
              </button>
              
              {/* σ倍数选择按钮组 */}
              <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
                {sigmaMultipliers.map((multiplier) => (
                  <button
                    key={multiplier}
                    onClick={() => setJumpSigmaMultiplier(multiplier)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      jumpSigmaMultiplier === multiplier
                        ? 'bg-orange-600 text-white'
                        : 'text-gray-600 hover:bg-white'
                    }`}
                  >
                    ±{multiplier}σ
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 股票列表 */}
          {filteredStocks.length > 0 ? (
            <div className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gradient-to-r from-orange-50 to-red-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">序号</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">股票代码</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">股票名称</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">行业</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">前一天排名</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">最新排名</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">排名跳变</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">涨跌幅</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">换手率</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">波动率</th>
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">操作</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {(() => {
                      const sortedStocks = jumpSortReverse ? [...filteredStocks].reverse() : filteredStocks;
                      return sortedStocks.map((stock, index) => (
                      <tr key={index} className="hover:bg-orange-50 transition-colors">
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
                          第 {stock.previous_rank} 名
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm font-bold text-orange-600">
                            第 {stock.latest_rank} 名
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center">
                            <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                            <span className="text-sm font-bold text-green-600">
                              +{stock.rank_change}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`text-sm font-medium ${stock.price_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {stock.price_change >= 0 ? '+' : ''}{stock.price_change?.toFixed(2)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {stock.turnover_rate?.toFixed(2)}%
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
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => setDetailPopup({ isOpen: true, stockCode: stock.code, stockName: stock.name })}
                            className="p-1.5 text-orange-600 hover:bg-orange-50 rounded transition-colors"
                            title="查看详情"
                          >
                            <Info className="h-4 w-4" />
                          </button>
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
              <p className="text-yellow-600 text-sm mt-2">尝试降低跳变阈值或选择不同的板块类型</p>
            </div>
          )}
        </>
      )}
      
      {/* 股票详情弹窗 */}
      <StockDetailPopup
        stockCode={detailPopup.stockCode}
        stockName={detailPopup.stockName}
        isOpen={detailPopup.isOpen}
        onClose={() => setDetailPopup({ isOpen: false, stockCode: null, stockName: null })}
        selectedDate={selectedDate}
      />
    </div>
  );
}



