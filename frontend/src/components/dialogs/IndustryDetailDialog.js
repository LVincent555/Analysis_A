/**
 * 板块详情对话框组件 - 快速预览
 * Phase 5: 显示板块基本信息、4维指标、TOP10成分股
 */
import React, { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, ExternalLink, AlertCircle, Loader } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../../constants';
import { useSignalConfig } from '../../contexts/SignalConfigContext';

export default function IndustryDetailDialog({ 
  industryName, 
  onClose, 
  onViewDetails 
}) {
  // 使用全局信号配置
  const { signalThresholds } = useSignalConfig();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [stocksData, setStocksData] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // 并行获取板块详情和成分股列表
        const [detailResponse, stocksResponse] = await Promise.all([
          axios.get(`${API_BASE_URL}/api/industry/${encodeURIComponent(industryName)}/detail`),
          axios.get(`${API_BASE_URL}/api/industry/${encodeURIComponent(industryName)}/stocks`, {
            params: {
              sort_mode: 'signal',
              calculate_signals: true,
              hot_list_mode: signalThresholds.hotListMode || 'instant',
              hot_list_top: signalThresholds.hotListTop,
              rank_jump_min: signalThresholds.rankJumpMin,
              steady_rise_days: signalThresholds.steadyRiseDays,
              price_surge_min: signalThresholds.priceSurgeMin,
              volume_surge_min: signalThresholds.volumeSurgeMin,
              volatility_surge_min: signalThresholds.volatilitySurgeMin
            }
          })
        ]);
        
        setDetailData(detailResponse.data);
        setStocksData(stocksResponse.data);
      } catch (err) {
        console.error('获取板块数据失败:', err);
        setError(err.response?.data?.detail || '获取板块数据失败');
      } finally {
        setLoading(false);
      }
    };

    if (industryName) {
      fetchData();
    }
  }, [industryName, signalThresholds.hotListMode, signalThresholds.hotListTop, signalThresholds.rankJumpMin, signalThresholds.steadyRiseDays, signalThresholds.priceSurgeMin, signalThresholds.volumeSurgeMin, signalThresholds.volatilitySurgeMin]);

  // 点击背景关闭
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // 格式化指标值
  const formatMetric = (value, suffix = '') => {
    if (value === null || value === undefined) return '-';
    return `${value.toFixed(2)}${suffix}`;
  };

  // 获取信号标签颜色
  const getSignalColor = (signalCount) => {
    if (signalCount >= 3) return 'bg-red-100 text-red-800';
    if (signalCount >= 2) return 'bg-orange-100 text-orange-800';
    if (signalCount >= 1) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-600';
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{industryName}</h2>
            <p className="text-green-100 text-sm mt-1">板块成分股详细分析</p>
          </div>
          <button
            onClick={onClose}
            className="text-white hover:bg-green-800 rounded-full p-2 transition-colors"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* 内容区域 */}
        <div className="overflow-y-auto max-h-[calc(90vh-140px)]">
          {loading && (
            <div className="p-12 text-center">
              <Loader className="h-12 w-12 text-green-600 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">正在加载板块数据...</p>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 mr-3 flex-shrink-0" />
                <div>
                  <p className="text-red-800 font-medium">加载失败</p>
                  <p className="text-red-700 text-sm mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && detailData && stocksData && (
            <div className="p-6 space-y-6">
              {/* 板块概览 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-blue-600 text-sm font-medium">成分股数量</p>
                  <p className="text-2xl font-bold text-blue-900 mt-1">
                    {detailData.stock_count}只
                  </p>
                </div>
                <div className="bg-green-50 rounded-lg p-4">
                  <p className="text-green-600 text-sm font-medium">TOP 100</p>
                  <p className="text-2xl font-bold text-green-900 mt-1">
                    {detailData.top_100_count}只
                  </p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <p className="text-purple-600 text-sm font-medium">热点榜</p>
                  <p className="text-2xl font-bold text-purple-900 mt-1">
                    {detailData.hot_list_count}只
                  </p>
                </div>
                <div className="bg-orange-50 rounded-lg p-4">
                  <p className="text-orange-600 text-sm font-medium">多信号股票</p>
                  <p className="text-2xl font-bold text-orange-900 mt-1">
                    {detailData.multi_signal_count}只
                  </p>
                </div>
              </div>

              {/* 4维指标 */}
              <div>
                <h3 className="text-lg font-bold text-gray-800 mb-3 flex items-center">
                  <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
                  4维指标
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
                    <p className="text-blue-700 text-sm font-medium mb-1">B1 - 加权总分</p>
                    <p className="text-3xl font-bold text-blue-900">
                      {formatMetric(detailData.B1)}
                    </p>
                  </div>
                  <div className={`bg-gradient-to-br rounded-lg p-4 border ${
                    detailData.B2 >= 0 
                      ? 'from-green-50 to-green-100 border-green-200' 
                      : 'from-red-50 to-red-100 border-red-200'
                  }`}>
                    <p className={`text-sm font-medium mb-1 ${
                      detailData.B2 >= 0 ? 'text-green-700' : 'text-red-700'
                    }`}>
                      B2 - 加权涨跌幅
                    </p>
                    <p className={`text-3xl font-bold flex items-center ${
                      detailData.B2 >= 0 ? 'text-green-900' : 'text-red-900'
                    }`}>
                      {detailData.B2 >= 0 ? (
                        <TrendingUp className="h-6 w-6 mr-1" />
                      ) : (
                        <TrendingDown className="h-6 w-6 mr-1" />
                      )}
                      {formatMetric(detailData.B2, '%')}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 border border-purple-200">
                    <p className="text-purple-700 text-sm font-medium mb-1">C1 - 加权换手率</p>
                    <p className="text-3xl font-bold text-purple-900">
                      {formatMetric(detailData.C1, '%')}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4 border border-orange-200">
                    <p className="text-orange-700 text-sm font-medium mb-1">C2 - 加权放量</p>
                    <p className="text-3xl font-bold text-orange-900">
                      {formatMetric(detailData.C2)}
                    </p>
                  </div>
                </div>
              </div>

              {/* TOP 10 成分股 */}
              <div>
                <h3 className="text-lg font-bold text-gray-800 mb-3">
                  TOP 10 成分股 (按信号强度排序)
                </h3>
                <div className="bg-gray-50 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-200">
                      <tr>
                        <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">排名</th>
                        <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">股票</th>
                        <th className="px-4 py-2 text-center text-sm font-semibold text-gray-700">信号</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold text-gray-700">涨跌幅</th>
                        <th className="px-4 py-2 text-right text-sm font-semibold text-gray-700">市场排名</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {stocksData.stocks.slice(0, 10).map((stock, index) => (
                        <tr key={stock.stock_code} className="hover:bg-white transition-colors">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">
                            #{index + 1}
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="text-sm font-medium text-gray-900">
                                {stock.stock_name}
                              </p>
                              <p className="text-xs text-gray-500">{stock.stock_code}</p>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-center gap-1">
                              {stock.signal_count > 0 ? (
                                <>
                                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSignalColor(stock.signal_count)}`}>
                                    {stock.signal_count}个信号
                                  </span>
                                  <span className="text-xs text-gray-500">
                                    {(stock.signal_strength * 100).toFixed(0)}%
                                  </span>
                                </>
                              ) : (
                                <span className="text-xs text-gray-400">-</span>
                              )}
                            </div>
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
                          <td className="px-4 py-3 text-right text-sm text-gray-700">
                            #{stock.rank}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 更多统计 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div className="bg-gray-50 rounded p-3">
                  <p className="text-gray-600">平均排名</p>
                  <p className="font-semibold text-gray-900 mt-1">
                    #{detailData.avg_rank.toFixed(0)}
                  </p>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <p className="text-gray-600">TOP 500</p>
                  <p className="font-semibold text-gray-900 mt-1">
                    {detailData.top_500_count}只
                  </p>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <p className="text-gray-600">跳变榜</p>
                  <p className="font-semibold text-gray-900 mt-1">
                    {detailData.rank_jump_count}只
                  </p>
                </div>
                <div className="bg-gray-50 rounded p-3">
                  <p className="text-gray-600">稳步上升</p>
                  <p className="font-semibold text-gray-900 mt-1">
                    {detailData.steady_rise_count}只
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        {!loading && !error && (
          <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex items-center justify-between">
            <p className="text-sm text-gray-600">
              日期: {detailData?.date ? `${detailData.date.slice(0,4)}-${detailData.date.slice(4,6)}-${detailData.date.slice(6,8)}` : '-'}
            </p>
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              >
                关闭
              </button>
              <button
                onClick={() => onViewDetails(industryName)}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2 font-medium"
              >
                查看完整分析
                <ExternalLink className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
