/**
 * 板块详情弹窗组件
 * 显示板块的热度指标、统计数据和成分股列表
 */
import React, { useState, useEffect } from 'react';
import { X, Flame, Users, TrendingUp, Target, Zap, BarChart2, ExternalLink, RefreshCw } from 'lucide-react';
import boardHeatService from '../services/boardHeatService';
import BoardSignalBadge from './BoardSignalBadge';

export default function BoardDetailDialog({ board, selectedDate, minPrice = null, onClose, onStockClick, onViewFullAnalysis }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);
  const [page, setPage] = useState(0);
  const pageSize = 20;
  
  useEffect(() => {
    if (!board?.board_id) return;
    
    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await boardHeatService.getBoardDetail(board.board_id, selectedDate, minPrice, pageSize, page * pageSize);
        setDetail(result);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || '加载失败');
      } finally {
        setLoading(false);
      }
    };
    
    loadDetail();
  }, [board?.board_id, selectedDate, minPrice, page]);

  useEffect(() => {
    setPage(0);
  }, [board?.board_id, selectedDate, minPrice]);
  
  if (!board) return null;
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 遮罩层 */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* 弹窗内容 */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* 头部 - 红色渐变 */}
        <div className="bg-gradient-to-r from-red-600 to-orange-500 text-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{board.board_name}</h2>
              <p className="text-white/80 text-sm mt-1">板块成分股详细分析</p>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>
        
        {/* 内容区 */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <RefreshCw className="w-10 h-10 animate-spin text-orange-500" />
            </div>
          ) : error ? (
            <div className="text-center py-16 text-red-500">
              {error}
            </div>
          ) : detail ? (
            <>
              {/* 统计卡片 - 4个彩色卡片 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <StatCard 
                  label="成分股数量" 
                  value={`${detail.stock_count}只`}
                  color="purple"
                />
                <StatCard 
                  label="TOP 100" 
                  value={`${detail.top100_count}只`}
                  color="blue"
                />
                <StatCard 
                  label="热点榜" 
                  value={`${detail.hotlist_count}只`}
                  color="green"
                />
                <StatCard 
                  label="多信号股票" 
                  value={`${detail.multi_signal_count}只`}
                  color="orange"
                />
              </div>
              
              {/* 4维指标 */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" />
                  4维指标
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <MetricCard 
                    label="B1 - 加权总分" 
                    value={detail.b1_rank_sum?.toFixed(2)}
                    color="red"
                  />
                  <MetricCard 
                    label="B2 - 加权涨跌幅" 
                    value={detail.avg_price_change ? `${detail.avg_price_change > 0 ? '↗' : '↘'}${detail.avg_price_change.toFixed(2)}%` : '-'}
                    color="blue"
                    highlight={detail.avg_price_change > 0}
                  />
                  <MetricCard 
                    label="C1 - 加权换手率" 
                    value={detail.avg_turnover ? `${detail.avg_turnover.toFixed(2)}%` : '-'}
                    color="green"
                  />
                  <MetricCard 
                    label="C2 - 加权放量" 
                    value={detail.c2_score_avg?.toFixed(2) || '-'}
                    color="purple"
                  />
                </div>
              </div>
              
              {/* 成分股列表 */}
              <div>
                <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  成分股列表 (分页)
                </h3>
                
                <div className="border rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500">排名</th>
                        <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500">股票</th>
                        <th className="px-3 py-2.5 text-left text-xs font-semibold text-gray-500">信号</th>
                        <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500">贡献度</th>
                        <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500">涨跌幅</th>
                        <th className="px-3 py-2.5 text-right text-xs font-semibold text-gray-500">市场排名</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {detail.top_stocks?.map((stock, idx) => (
                        <tr 
                          key={stock.stock_code}
                          onClick={() => onStockClick?.(stock.stock_code)}
                          className="hover:bg-gray-50 cursor-pointer transition-colors"
                        >
                          <td className="px-3 py-2.5 text-gray-500 font-medium">
                            #{page * pageSize + idx + 1}
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="font-medium text-gray-900">{stock.stock_name}</div>
                            <div className="text-xs text-gray-400">{stock.stock_code}</div>
                          </td>
                          <td className="px-3 py-2.5">
                            <div className="flex flex-wrap items-center gap-1">
                              {/* 板块信号标签 [S级｜板块名] */}
                              {stock.signal_level && stock.signal_level !== 'NONE' ? (
                                <BoardSignalBadge
                                  level={stock.signal_level}
                                  label={board.board_name}
                                  type={board.board_type}
                                  size="sm"
                                />
                              ) : stock.market_rank && stock.market_rank <= 100 ? (
                                <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-700 font-medium">TOP100</span>
                              ) : (
                                <span className="text-xs text-gray-400">-</span>
                              )}
                            </div>
                            {stock.final_score && stock.final_score > 0 && (
                              <div className="text-xs text-gray-400 mt-0.5">
                                强度: {Math.min(100, Math.round(stock.final_score))}%
                              </div>
                            )}
                          </td>
                          <td className="px-3 py-2.5 text-right">
                             {stock.contribution_score > 0 ? (
                               <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                                 {stock.contribution_score.toFixed(1)}
                               </span>
                             ) : (
                               <span className="text-xs text-gray-300">-</span>
                             )}
                          </td>
                          <td className="px-3 py-2.5 text-right">
                            <span className={`font-medium ${
                              stock.price_change > 0 ? 'text-red-600' :
                              stock.price_change < 0 ? 'text-green-600' :
                              'text-gray-600'
                            }`}>
                              {stock.price_change != null ? `${stock.price_change > 0 ? '+' : ''}${stock.price_change.toFixed(2)}%` : '-'}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-right text-gray-500">
                            #{stock.market_rank || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="flex items-center justify-between mt-3 text-sm">
                  <span className="text-gray-500">
                    当前页: {page + 1}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0 || loading}
                      className="px-3 py-1.5 rounded border bg-white hover:bg-gray-50 disabled:opacity-50"
                    >
                      上一页
                    </button>
                    <button
                      type="button"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={loading || !detail?.top_stocks || detail.top_stocks.length < pageSize}
                      className="px-3 py-1.5 rounded border bg-white hover:bg-gray-50 disabled:opacity-50"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
        
        {/* 底部操作栏 */}
        <div className="border-t px-5 py-4 bg-gray-50 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            日期: {detail?.trade_date || board.trade_date || '-'}
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            >
              关闭
            </button>
            <button
              onClick={() => onViewFullAnalysis?.(board)}
              className="px-4 py-2 bg-gradient-to-r from-orange-500 to-red-500 text-white rounded-lg hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              查看完整分析
              <ExternalLink className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// 统计卡片组件
function StatCard({ label, value, color }) {
  const colorMap = {
    purple: 'bg-purple-100 text-purple-700 border-purple-200',
    blue: 'bg-blue-100 text-blue-700 border-blue-200',
    green: 'bg-green-100 text-green-700 border-green-200',
    orange: 'bg-orange-100 text-orange-700 border-orange-200',
  };
  
  return (
    <div className={`rounded-lg p-4 border ${colorMap[color]}`}>
      <div className="text-xs opacity-80 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}

// 指标卡片组件
function MetricCard({ label, value, color, highlight }) {
  const colorMap = {
    red: 'bg-red-50 border-red-200',
    blue: 'bg-blue-50 border-blue-200',
    green: 'bg-green-50 border-green-200',
    purple: 'bg-purple-50 border-purple-200',
  };
  
  return (
    <div className={`rounded-lg p-3 border ${colorMap[color]}`}>
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${highlight ? 'text-red-600' : 'text-gray-900'}`}>
        {value || '-'}
      </div>
    </div>
  );
}
