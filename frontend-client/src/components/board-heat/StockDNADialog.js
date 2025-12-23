import React, { useState, useEffect } from 'react';
import { X, Activity, AlertCircle, CheckCircle2, TrendingUp, BarChart2 } from 'lucide-react';
import boardHeatService from '../../services/boardHeatService';
import BoardSignalBadge from '../BoardSignalBadge';

export default function StockDNADialog({ stockCode, selectedDate, minPrice = null, onClose }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [showAllBoards, setShowAllBoards] = useState(false);

  useEffect(() => {
    if (!stockCode) return;

    const loadDNA = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await boardHeatService.getStockDNA(stockCode, selectedDate, minPrice);
        setData(result);
      } catch (err) {
        console.error('加载DNA失败:', err);
        setError(err.response?.data?.detail || err.message || '加载失败');
      } finally {
        setLoading(false);
      }
    };

    loadDNA();
  }, [stockCode, selectedDate, minPrice]);

  if (!stockCode) return null;

  // Helper to render score bars
  const ScoreBar = ({ label, score, weight, color = 'bg-blue-500' }) => (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium text-gray-900">{(score ?? 0).toFixed(1)} <span className="text-xs text-gray-400">({weight}%)</span></span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full ${color}`} 
          style={{ width: `${Math.min(100, score ?? 0)}%` }}
        />
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-blue-500 text-white p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Activity className="w-6 h-6" />
                个股DNA透视
              </h2>
              <p className="text-white/80 text-sm mt-1">
                {data ? `${data.stock_name} (${data.stock_code})` : '加载中...'}
              </p>
            </div>
            <button 
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600" />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-500 flex flex-col items-center">
              <AlertCircle className="w-10 h-10 mb-2" />
              {error}
            </div>
          ) : data ? (
            <div className="space-y-6">
              
              {/* 核心结论 */}
              <div className="bg-gray-50 rounded-lg p-4 border flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-500 mb-1">最终评级</div>
                  <div className="flex items-center gap-2">
                     {data.signal_level === 'NONE' ? (
                        <span className="px-3 py-1.5 rounded-full text-sm bg-gray-100 text-gray-600 font-medium border">
                          普通观察
                        </span>
                     ) : (
                        <BoardSignalBadge level={data.signal_level} label={data.signal_level === 'S' ? '强力进攻' : data.signal_level === 'A' ? '积极关注' : '普通观察'} size="lg" />
                     )}
                     {data.fallback_reason && (
                        <span className="text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded border border-orange-100">
                          {data.fallback_reason}
                        </span>
                     )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm text-gray-500 mb-1">综合得分</div>
                  <div className="text-3xl font-bold text-indigo-600">{data.final_score?.toFixed(1)}</div>
                  <div className="text-xs text-gray-400">击败了 {(data.final_score_pct * 100).toFixed(1)}% 的股票</div>
                </div>
              </div>

              {/* 维度拆解 (From dna_json) */}
              {data.dna_json && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* 板块驱动力 */}
                  <div className="border rounded-lg p-4">
                    <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-orange-500" />
                      板块驱动力 (40%)
                    </h3>
                    <div className="space-y-4">
                       <div>
                         <span className="text-xs text-gray-500 block mb-1">最强概念</span>
                         <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
                            <span className="font-medium">{data.dna_json.max_concept_name || '无'}</span>
                            <span className="text-orange-600 font-bold">{((data.dna_json.max_concept_heat || 0) * 100).toFixed(0)}% <span className="text-xs text-gray-400 font-normal">热度</span></span>
                         </div>
                       </div>
                       <div>
                         <span className="text-xs text-gray-500 block mb-1">所属行业</span>
                         <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
                            <span className="font-medium">{data.dna_json.industry_name || '无'}</span>
                            <span className="text-blue-600 font-bold">{((data.dna_json.industry_heat || 0) * 100).toFixed(0)}% <span className="text-xs text-gray-400 font-normal">热度</span></span>
                         </div>
                       </div>
                       {/* 行业安全检查 */}
                       <div className="flex items-center gap-2 text-sm mt-2">
                          {data.dna_json.industry_safe ? (
                            <span className="text-green-600 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> 行业共振安全</span>
                          ) : (
                            <span className="text-gray-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> 行业未共振 (降权)</span>
                          )}
                       </div>

                      {Array.isArray(data.all_related_boards) && data.all_related_boards.length > 0 && (
                        <div className="mt-4 pt-4 border-t">
                          <button
                            type="button"
                            onClick={() => setShowAllBoards((v) => !v)}
                            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                          >
                            {showAllBoards ? '收起完整板块链条' : '展开完整板块链条'} ({data.all_related_boards.length})
                          </button>
                          {showAllBoards && (
                            <div className="mt-3 max-h-56 overflow-y-auto border rounded">
                              {data.all_related_boards.map((b, i) => (
                                <div key={`${b.board_id || i}-${i}`} className="flex items-center justify-between px-3 py-2 border-b last:border-b-0 text-sm">
                                  <div className="flex items-center gap-2">
                                    <span className={`px-2 py-0.5 rounded text-xs ${b.board_type === 'industry' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'}`}>
                                      {b.board_type === 'industry' ? '行业' : '概念'}
                                    </span>
                                    <span className="text-gray-800">{b.board_name}</span>
                                  </div>
                                  <div className="text-gray-500">
                                    {b.heat_pct != null ? `${(b.heat_pct * 100).toFixed(1)}%` : '-'}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 个股硬实力 */}
                  <div className="border rounded-lg p-4">
                    <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                      <BarChart2 className="w-4 h-4 text-indigo-500" />
                      个股硬实力 (60%)
                    </h3>
                    {data.dna_json.stock_details ? (
                      <div>
                        <ScoreBar label="量能爆发 (C2)" score={data.dna_json.stock_details.vol_score ?? 0} weight={40} color="bg-indigo-500" />
                        <ScoreBar label="资金强度 (C1)" score={data.dna_json.stock_details.turnover_score ?? 0} weight={30} color="bg-blue-500" />
                        <ScoreBar label="趋势形态 (B2)" score={data.dna_json.stock_details.trend_score ?? 0} weight={30} color="bg-purple-500" />
                        
                        <div className="mt-4 pt-4 border-t grid grid-cols-2 gap-4 text-center">
                          <div>
                            <div className="text-xs text-gray-500">市场排名</div>
                            <div className="font-bold">#{data.dna_json.stock_details.rank || '-'}</div>
                          </div>
                          <div>
                             <div className="text-xs text-gray-500">板块贡献</div>
                             <div className="font-bold text-indigo-600">{(data.dna_json.contribution_score ?? 0).toFixed(1)}</div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-gray-400 text-sm text-center py-4">暂无个股硬实力因子数据</div>
                    )}
                  </div>
                </div>
              )}
              
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
