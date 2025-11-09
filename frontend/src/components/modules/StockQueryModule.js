/**
 * 股票查询模块 - 完整版
 */
import React, { useState, useEffect } from 'react';
import { Search, TrendingDown, RefreshCw, Activity } from 'lucide-react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend as RechartsLegend } from 'recharts';
import { API_BASE_URL } from '../../constants/config';
import { formatDate } from '../../utils';
import { useSignalConfig } from '../../contexts/SignalConfigContext';

export default function StockQueryModule({ stockCode, queryTrigger, selectedDate }) {
  // 使用全局信号配置
  const { signalThresholds } = useSignalConfig();
  
  const [stockHistory, setStockHistory] = useState(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState(null);
  const [visibleIndicators, setVisibleIndicators] = useState({
    price_change: true,
    turnover_rate: true,
    volume_days: true,
    avg_volume_ratio_50: true,
    volatility: true
  });

  // 查询股票 - 监听queryTrigger变化
  useEffect(() => {
    const handleStockQuery = async () => {
      if (!stockCode.trim()) {
        return;
      }

      setStockLoading(true);
      setStockError(null);
      try {
        // 不使用selectedDate，始终查询全部历史数据
        const url = `${API_BASE_URL}/api/stock/${stockCode.trim()}`;
        const response = await axios.get(url);
        const data = response.data;
        
        // 保持原始升序（旧→新），图表需要这个顺序
        // 最新数据是数组最后一个元素
        const transformedData = {
          ...data,
          latestRank: data.date_rank_info[data.date_rank_info.length - 1]?.rank || 0
        };
        
        setStockHistory(transformedData);
        setStockError(null);
      } catch (err) {
        setStockError(err.response?.data?.detail || '查询失败，请检查股票代码');
        setStockHistory(null);
      } finally {
        setStockLoading(false);
      }
    };

    if (queryTrigger > 0) {
      handleStockQuery();
    }
  }, [queryTrigger, stockCode]); // 移除selectedDate依赖

  return (
    <>
      {/* 查询提示 - 当没有查询结果时显示 */}
      {!stockHistory && !stockLoading && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center mb-6">
          <Search className="mx-auto h-16 w-16 text-gray-400 mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">股票历史数据查询</h3>
          <p className="text-gray-600 mb-4">请在左侧输入股票代码进行查询</p>
          <p className="text-sm text-gray-500">查看个股的历史排名、技术指标及变化趋势</p>
        </div>
      )}

      {/* 加载状态 */}
      {stockLoading && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center mb-6">
          <RefreshCw className="mx-auto h-12 w-12 text-purple-600 animate-spin mb-4" />
          <p className="text-gray-600 text-lg">正在查询股票数据...</p>
        </div>
      )}

      {/* 错误提示 */}
      {stockError && !stockLoading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">错误: {stockError}</p>
        </div>
      )}

      {/* 查询结果 */}
      {stockHistory && !stockLoading && (
        <div className="space-y-6 mb-6">
          {/* 本地配置已删除，使用全局配置 */}
          
          {/* Stock Info Card */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-2xl font-bold text-gray-900">
                  {stockHistory.name} ({stockHistory.code})
                </h3>
                <p className="text-sm text-gray-600 mt-1">行业: {stockHistory.industry}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">最新排名</p>
                <p className="text-3xl font-bold text-indigo-600">#{stockHistory.latestRank}</p>
              </div>
            </div>
            
            {/* 最新一天的数据（高亮显示） */}
            {(() => {
              // 获取最后一个元素（最新日期）
              const latest = stockHistory.date_rank_info[stockHistory.date_rank_info.length - 1];
              const previous = stockHistory.date_rank_info.length > 1 ? stockHistory.date_rank_info[stockHistory.date_rank_info.length - 2] : null;
              
              // 简单信号判断（使用配置的阈值）
              const signals = [];
              if (latest.rank <= signalThresholds.hotListTop) {
                signals.push({ label: `🔥 热点榜TOP${signalThresholds.hotListTop}`, type: 'hot' });
              }
              if (previous && (previous.rank - latest.rank) >= signalThresholds.rankJumpMin) {
                signals.push({ label: `📈 排名跳变↑${previous.rank - latest.rank}`, type: 'jump' });
              }
              if (latest.price_change >= signalThresholds.priceSurgeMin) {
                signals.push({ label: `💰 涨幅${latest.price_change.toFixed(1)}%`, type: 'price' });
              }
              if (latest.turnover_rate >= signalThresholds.volumeSurgeMin) {
                signals.push({ label: `📦 换手率${latest.turnover_rate.toFixed(1)}%`, type: 'volume' });
              }
              if (previous && latest.volatility && previous.volatility && previous.volatility > 0) {
                const volatilityChangePercent = ((latest.volatility - previous.volatility) / previous.volatility) * 100;
                if (volatilityChangePercent >= signalThresholds.volatilitySurgeMin) {
                  signals.push({ label: `⚡ 波动率↑${volatilityChangePercent.toFixed(1)}%`, type: 'volatility' });
                }
              }
              
              return (
                <div className="mt-4 bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-bold text-gray-900">
                      {formatDate(latest.date)}
                    </h4>
                    <div className="text-right">
                      <span className="text-xl font-bold text-indigo-600">
                        第 {latest.rank} 名
                      </span>
                      {signals.length > 0 && (
                        <div className="mt-1">
                          <span className="text-xs font-medium text-purple-700 bg-purple-100 px-2 py-1 rounded">
                            {signals.length}个信号
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* 信号标识 */}
                  {signals.length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-2">
                      {signals.map((signal, idx) => (
                        <span
                          key={idx}
                          className={`text-xs font-medium px-2 py-1 rounded border ${
                            signal.type === 'hot' ? 'bg-green-100 text-green-800 border-green-300' :
                            signal.type === 'jump' ? 'bg-blue-100 text-blue-800 border-blue-300' :
                            signal.type === 'price' ? 'bg-orange-100 text-orange-800 border-orange-300' :
                            signal.type === 'volume' ? 'bg-red-100 text-red-800 border-red-300' :
                            'bg-indigo-100 text-indigo-800 border-indigo-300'
                          }`}
                        >
                          {signal.label}
                        </span>
                      ))}
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-xs text-gray-500 mb-1">涨跌幅</p>
                      <p className={`text-lg font-bold ${latest.price_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {latest.price_change >= 0 ? '+' : ''}{latest.price_change?.toFixed(2)}%
                      </p>
                    </div>
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-xs text-gray-500 mb-1">换手率</p>
                      <p className="text-lg font-bold text-gray-900">{latest.turnover_rate?.toFixed(2)}%</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-xs text-gray-500 mb-1">放量天数</p>
                      <p className="text-lg font-bold text-gray-900">{latest.volume_days?.toFixed(1)}</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-xs text-gray-500 mb-1">平均量比_50天</p>
                      <p className="text-lg font-bold text-gray-900">{latest.avg_volume_ratio_50?.toFixed(2)}</p>
                    </div>
                    <div className="bg-white rounded-lg p-3 shadow-sm">
                      <p className="text-xs text-gray-500 mb-1">波动率</p>
                      <p className="text-lg font-bold text-gray-900">{latest.volatility?.toFixed(2)}%</p>
                    </div>
                  </div>
                  
                  {/* 多维度信号说明 */}
                  <div className="mt-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-3 border border-purple-200">
                    <h4 className="text-xs font-bold text-purple-900 mb-2 flex items-center gap-2">
                      <Activity className="h-3 w-3" />
                      🎯 多维度信号说明
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
                      <div className="bg-white rounded p-2 border border-green-200 shadow-sm">
                        <span className="font-bold text-green-900 flex items-center gap-1 text-xs">
                          🔥 热点榜
                        </span>
                        <p className="text-green-700 mt-1 text-xs leading-tight">排名TOP100，市场关注度高</p>
                      </div>
                      <div className="bg-white rounded p-2 border border-blue-200 shadow-sm">
                        <span className="font-bold text-blue-900 flex items-center gap-1 text-xs">
                          📈 排名跳变
                        </span>
                        <p className="text-blue-700 mt-1 text-xs leading-tight">排名大幅提升≥2000名</p>
                      </div>
                      <div className="bg-white rounded p-2 border border-purple-200 shadow-sm">
                        <span className="font-bold text-purple-900 flex items-center gap-1 text-xs">
                          📊 稳步上升
                        </span>
                        <p className="text-purple-700 mt-1 text-xs leading-tight">连续多天排名上升</p>
                      </div>
                      <div className="bg-white rounded p-2 border border-orange-200 shadow-sm">
                        <span className="font-bold text-orange-900 flex items-center gap-1 text-xs">
                          💰 涨幅榜
                        </span>
                        <p className="text-orange-700 mt-1 text-xs leading-tight">涨跌幅≥5%</p>
                      </div>
                      <div className="bg-white rounded p-2 border border-red-200 shadow-sm">
                        <span className="font-bold text-red-900 flex items-center gap-1 text-xs">
                          📦 成交量榜
                        </span>
                        <p className="text-red-700 mt-1 text-xs leading-tight">换手率≥10%</p>
                      </div>
                      <div className="bg-white rounded p-2 border border-indigo-200 shadow-sm">
                        <span className="font-bold text-indigo-900 flex items-center gap-1 text-xs">
                          ⚡ 波动率上升
                        </span>
                        <p className="text-indigo-700 mt-1 text-xs leading-tight">波动率百分比上升≥30%</p>
                      </div>
                    </div>
                    <div className="mt-2 text-xs bg-white rounded p-2 border border-purple-100">
                      <p className="text-purple-700">
                        <strong>💡 提示：</strong>信号越多说明该股票越值得关注，多个信号叠加通常意味着更强的市场信号
                      </p>
                    </div>
                  </div>
                </div>
              );
            })()}
            
            {/* 历史数据表格 */}
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">历史数据</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日期</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">排名</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">涨跌幅</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">换手率</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">放量天数</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">平均量比_50天</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">波动率</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {/* 表格显示：降序（最新在上） */}
                    {[...stockHistory.date_rank_info].reverse().map((item, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {formatDate(item.date)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="text-sm font-bold text-indigo-600">
                            第 {item.rank} 名
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className={`text-sm font-medium ${item.price_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {item.price_change >= 0 ? '+' : ''}{item.price_change?.toFixed(2) || '0.00'}%
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {item.turnover_rate?.toFixed(2) || '0.00'}%
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {item.volume_days?.toFixed(1) || '0.0'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {item.avg_volume_ratio_50?.toFixed(2) || '0.00'}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                          {item.volatility?.toFixed(2) || '0.00'}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
              <LineChart data={stockHistory.date_rank_info}>
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

          {/* 技术指标趋势图 */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-2">
                <TrendingDown className="h-5 w-5 text-green-600" />
                <h3 className="text-lg font-bold text-gray-900">技术指标趋势</h3>
              </div>
              {/* 指标控制按钮 */}
              <div className="flex items-center flex-wrap gap-2">
                <button
                  onClick={() => setVisibleIndicators(prev => ({ ...prev, price_change: !prev.price_change }))}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    visibleIndicators.price_change
                      ? 'bg-red-100 text-red-700 border-2 border-red-400'
                      : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                  }`}
                >
                  涨跌幅
                </button>
                <button
                  onClick={() => setVisibleIndicators(prev => ({ ...prev, turnover_rate: !prev.turnover_rate }))}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    visibleIndicators.turnover_rate
                      ? 'bg-purple-100 text-purple-700 border-2 border-purple-400'
                      : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                  }`}
                >
                  换手率
                </button>
                <button
                  onClick={() => setVisibleIndicators(prev => ({ ...prev, volume_days: !prev.volume_days }))}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    visibleIndicators.volume_days
                      ? 'bg-green-100 text-green-700 border-2 border-green-400'
                      : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                  }`}
                >
                  放量天数
                </button>
                <button
                  onClick={() => setVisibleIndicators(prev => ({ ...prev, avg_volume_ratio_50: !prev.avg_volume_ratio_50 }))}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    visibleIndicators.avg_volume_ratio_50
                      ? 'bg-orange-100 text-orange-700 border-2 border-orange-400'
                      : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                  }`}
                >
                  平均量比_50天
                </button>
                <button
                  onClick={() => setVisibleIndicators(prev => ({ ...prev, volatility: !prev.volatility }))}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                    visibleIndicators.volatility
                      ? 'bg-blue-100 text-blue-700 border-2 border-blue-400'
                      : 'bg-gray-100 text-gray-400 border-2 border-gray-300'
                  }`}
                >
                  波动率
                </button>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={stockHistory.date_rank_info}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(value) => formatDate(value)}
                  formatter={(value, name) => {
                    if (name === '涨跌幅' || name === '换手率' || name === '波动率') {
                      return [`${value.toFixed(2)}%`, name];
                    }
                    return [value.toFixed(2), name];
                  }}
                />
                <RechartsLegend />
                {visibleIndicators.price_change && (
                  <Line 
                    type="monotone" 
                    dataKey="price_change" 
                    stroke="#ef4444" 
                    strokeWidth={2}
                    dot={{ fill: '#ef4444', r: 3 }}
                    name="涨跌幅"
                  />
                )}
                {visibleIndicators.turnover_rate && (
                  <Line 
                    type="monotone" 
                    dataKey="turnover_rate" 
                    stroke="#8b5cf6" 
                    strokeWidth={2}
                    dot={{ fill: '#8b5cf6', r: 3 }}
                    name="换手率"
                  />
                )}
                {visibleIndicators.volume_days && (
                  <Line 
                    type="monotone" 
                    dataKey="volume_days" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    dot={{ fill: '#10b981', r: 3 }}
                    name="放量天数"
                  />
                )}
                {visibleIndicators.avg_volume_ratio_50 && (
                  <Line 
                    type="monotone" 
                    dataKey="avg_volume_ratio_50" 
                    stroke="#f59e0b" 
                    strokeWidth={2}
                    dot={{ fill: '#f59e0b', r: 3 }}
                    name="平均量比_50天"
                  />
                )}
                {visibleIndicators.volatility && (
                  <Line 
                    type="monotone" 
                    dataKey="volatility" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6', r: 3 }}
                    name="波动率"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </>
  );
}
