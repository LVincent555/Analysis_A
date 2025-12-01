/**
 * 股票详情弹窗组件
 * 可在各个列表模块中复用
 */
import React, { useState, useEffect } from 'react';
import { X, TrendingUp, TrendingDown, Activity, BarChart2, Info } from 'lucide-react';
import apiClient from '../../services/api';
import { API_BASE_URL } from '../../constants/config';
import { formatDate } from '../../utils';

// 迷你图表组件
const MiniChart = ({ data, dataKey, color = '#4F46E5', height = 40 }) => {
  if (!data || data.length === 0) return null;
  
  const values = data.map(d => d[dataKey]).filter(v => v !== null && v !== undefined);
  if (values.length === 0) return null;
  
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * 100;
    const y = height - ((v - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
  
  return (
    <svg width="100%" height={height} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default function StockDetailPopup({ 
  stockCode, 
  stockName,
  isOpen, 
  onClose,
  selectedDate 
}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && stockCode) {
      fetchStockDetail();
    }
  }, [isOpen, stockCode, selectedDate]);

  const fetchStockDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/api/stock/${stockCode}`, {
        params: { date: selectedDate }
      });
      setData(response);
    } catch (err) {
      setError(err.response?.data?.detail || '获取详情失败');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const latestData = data?.date_rank_info?.[data.date_rank_info.length - 1];
  const priceChange = latestData?.price_change;
  const isUp = priceChange > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-gradient-to-r from-indigo-500 to-purple-500 text-white">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <span className="font-bold">{stockName || stockCode}</span>
            <span className="text-sm opacity-80">({stockCode})</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/20 rounded">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 内容 */}
        <div className="p-4 overflow-y-auto max-h-[calc(80vh-60px)]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              <span className="ml-2 text-gray-600">加载中...</span>
            </div>
          ) : error ? (
            <div className="text-center py-8 text-red-500">{error}</div>
          ) : data ? (
            <div className="space-y-4">
              {/* 基本信息 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-500">行业</div>
                  <div className="font-medium text-gray-900">{data.industry || '-'}</div>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="text-xs text-gray-500">最新排名</div>
                  <div className="font-medium text-indigo-600">第 {latestData?.rank || '-'} 名</div>
                </div>
              </div>

              {/* 涨跌幅 */}
              <div className={`rounded-lg p-4 ${isUp ? 'bg-red-50' : 'bg-green-50'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-gray-500">今日涨跌幅</div>
                    <div className={`text-2xl font-bold ${isUp ? 'text-red-600' : 'text-green-600'}`}>
                      {priceChange !== null ? `${priceChange > 0 ? '+' : ''}${priceChange.toFixed(2)}%` : '-'}
                    </div>
                  </div>
                  {isUp ? <TrendingUp className="h-8 w-8 text-red-400" /> : <TrendingDown className="h-8 w-8 text-green-400" />}
                </div>
              </div>

              {/* 关键指标 */}
              <div className="grid grid-cols-2 gap-3">
                <div className="border rounded-lg p-3">
                  <div className="text-xs text-gray-500">换手率</div>
                  <div className="font-medium">{latestData?.turnover_rate?.toFixed(2) || '-'}%</div>
                </div>
                <div className="border rounded-lg p-3">
                  <div className="text-xs text-gray-500">波动率</div>
                  <div className="font-medium">{latestData?.volatility?.toFixed(2) || '-'}%</div>
                </div>
                <div className="border rounded-lg p-3">
                  <div className="text-xs text-gray-500">放量天数</div>
                  <div className="font-medium">{latestData?.volume_days || '-'}天</div>
                </div>
                <div className="border rounded-lg p-3">
                  <div className="text-xs text-gray-500">量比(50日)</div>
                  <div className="font-medium">{latestData?.avg_volume_ratio_50?.toFixed(2) || '-'}</div>
                </div>
              </div>

              {/* 信号标签 */}
              {data.signals && data.signals.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">信号标签</div>
                  <div className="flex flex-wrap gap-2">
                    {data.signals.map((signal, idx) => (
                      <span key={idx} className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs rounded-full">
                        {signal}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 排名趋势图 */}
              {data.date_rank_info && data.date_rank_info.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">排名趋势 (近{data.date_rank_info.length}天)</div>
                  <div className="h-12 bg-gray-50 rounded p-2">
                    <MiniChart data={data.date_rank_info} dataKey="rank" color="#4F46E5" height={32} />
                  </div>
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>{formatDate(data.date_rank_info[0]?.date)}</span>
                    <span>{formatDate(data.date_rank_info[data.date_rank_info.length - 1]?.date)}</span>
                  </div>
                </div>
              )}

              {/* 历史数据表格 */}
              <div>
                <div className="text-xs text-gray-500 mb-2">历史数据</div>
                <div className="max-h-40 overflow-y-auto border rounded">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-2 py-1 text-left">日期</th>
                        <th className="px-2 py-1 text-right">排名</th>
                        <th className="px-2 py-1 text-right">涨跌幅</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...data.date_rank_info].reverse().slice(0, 10).map((item, idx) => (
                        <tr key={idx} className="border-t hover:bg-gray-50">
                          <td className="px-2 py-1">{formatDate(item.date)}</td>
                          <td className="px-2 py-1 text-right text-indigo-600">#{item.rank}</td>
                          <td className={`px-2 py-1 text-right ${item.price_change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                            {item.price_change?.toFixed(2) || '-'}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// 悬停预览小窗口
export function StockHoverPreview({ stockCode, position, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await apiClient.get(`/api/stock/${stockCode}`);
        setData(response);
      } catch (err) {
        console.error('获取预览失败', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [stockCode]);

  const latestData = data?.date_rank_info?.[data.date_rank_info.length - 1];

  return (
    <div 
      className="fixed z-40 bg-white shadow-lg rounded-lg border p-3 w-64"
      style={{ top: position.y, left: position.x }}
      onMouseLeave={onClose}
    >
      {loading ? (
        <div className="text-center py-2 text-gray-500 text-sm">加载中...</div>
      ) : data ? (
        <div className="space-y-2 text-sm">
          <div className="font-bold text-gray-900">{data.stock_name}</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-gray-500">排名:</span>
              <span className="ml-1 font-medium">#{latestData?.rank}</span>
            </div>
            <div>
              <span className="text-gray-500">涨跌:</span>
              <span className={`ml-1 font-medium ${latestData?.price_change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                {latestData?.price_change?.toFixed(2)}%
              </span>
            </div>
            <div>
              <span className="text-gray-500">行业:</span>
              <span className="ml-1">{data.industry}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-2 text-red-500 text-sm">加载失败</div>
      )}
    </div>
  );
}

