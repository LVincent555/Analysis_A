import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis
} from 'recharts';
import { RefreshCw, GitCompare, AlertCircle } from 'lucide-react';
import boardHeatService from '../../services/boardHeatService';

const BoardComparison = ({ currentBoard, tradeDate }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  
  useEffect(() => {
    if (!currentBoard?.board_id) return;
    
    const fetchComparisonData = async () => {
      setLoading(true);
      setError(null);
      try {
        const currentDetail = await boardHeatService.getBoardDetail(currentBoard.board_id, tradeDate);

        const rankingRes = await boardHeatService.getRanking({
          trade_date: tradeDate,
          board_type: currentDetail?.board_type || currentBoard?.board_type,
          limit: 5
        });
        const rankingItems = rankingRes?.items || [];

        const currentId = currentDetail?.board_id || currentBoard?.board_id;
        const top1Item = rankingItems.find((it) => it?.board_id && it.board_id !== currentId) || (rankingItems.length > 0 ? rankingItems[0] : null);
        let top1Detail = null;
        if (top1Item?.board_id) {
          top1Detail = await boardHeatService.getBoardDetail(top1Item.board_id, tradeDate);
        }

        setComparisonData({
          current: currentDetail,
          top1: top1Detail,
          ranking: rankingItems
        });
      } catch (err) {
        console.error("Failed to load comparison data", err);
        setError("无法加载对比数据");
      } finally {
        setLoading(false);
      }
    };
    
    fetchComparisonData();
  }, [currentBoard, tradeDate]);

  if (loading) return <div className="h-96 flex items-center justify-center"><RefreshCw className="animate-spin text-gray-400 w-8 h-8" /></div>;
  if (error) return <div className="h-96 flex items-center justify-center text-red-500"><AlertCircle className="w-5 h-5 mr-2" /> {error}</div>;
  if (!comparisonData) return null;

  const { current, top1, ranking } = comparisonData;

  const safeNum = (v, fallback = 0) => {
    if (v === null || v === undefined) return fallback;
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  };

  const safePct = (v) => `${(safeNum(v, 0) * 100).toFixed(1)}%`;

  const fundsMax = Math.max(safeNum(current?.c1_score_sum), safeNum(top1?.c1_score_sum), 1);
  const qualityMax = Math.max(safeNum(current?.c2_score_avg), safeNum(top1?.c2_score_avg), 1);

  // Prepare Radar Data
  const radarData = [
    { subject: '热度分位', A: safeNum(current?.heat_pct) * 100, B: safeNum(top1?.heat_pct) * 100, fullMark: 100 },
    { subject: '资金总量', A: (safeNum(current?.c1_score_sum) / fundsMax) * 100, B: (safeNum(top1?.c1_score_sum) / fundsMax) * 100, fullMark: 100 },
    { subject: '平均质量', A: (safeNum(current?.c2_score_avg) / qualityMax) * 100, B: (safeNum(top1?.c2_score_avg) / qualityMax) * 100, fullMark: 100 },
    { subject: '多信号密度', A: current?.stock_count ? (safeNum(current?.multi_signal_count) / safeNum(current?.stock_count, 1)) * 100 : 0, B: top1?.stock_count ? (safeNum(top1?.multi_signal_count) / safeNum(top1?.stock_count, 1)) * 100 : 0, fullMark: 100 },
    { subject: '信号强度', A: safeNum(current?.signal_strength), B: safeNum(top1?.signal_strength), fullMark: 100 },
  ];

  return (
    <div className="py-4 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Radar Chart */}
        <div className="bg-white p-4 rounded-lg border shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-indigo-600" />
            能力雷达对比 (VS 榜首)
          </h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} />
                <Radar
                  name={current.board_name}
                  dataKey="A"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
                <Radar
                  name={top1 ? top1.board_name : '榜首'}
                  dataKey="B"
                  stroke="#82ca9d"
                  fill="#82ca9d"
                  fillOpacity={0.6}
                />
                <Legend />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top 5 Comparison Bar Chart */}
        <div className="bg-white p-4 rounded-lg border shadow-sm">
          <h3 className="text-lg font-bold text-gray-900 mb-4">
            TOP 5 板块热度对比
          </h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={ranking.slice(0, 5)}
                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 1]} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                <YAxis 
                  dataKey="board_name" 
                  type="category" 
                  width={100} 
                  tick={{ fontSize: 12, fill: '#374151' }} 
                />
                <Tooltip 
                  formatter={(value, name) => [
                    `${(value * 100).toFixed(1)}%`, 
                    name === 'heat_pct' ? '热度' : name
                  ]}
                />
                <Bar dataKey="heat_pct" fill="#f97316" name="热度" barSize={20} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Key Metrics Table */}
      <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b bg-gray-50">
          <h3 className="font-bold text-gray-900">关键指标横向对比</h3>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
              <th className="px-6 py-3 text-left">指标</th>
              <th className="px-6 py-3 text-center text-indigo-700 bg-indigo-50 font-bold">{current.board_name} (当前)</th>
              <th className="px-6 py-3 text-center">{top1?.board_name || '榜首'}</th>
              <th className="px-6 py-3 text-center text-gray-400">差值</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-sm">
            <tr>
              <td className="px-6 py-4 font-medium text-gray-900">热度分位 (Heat Pct)</td>
              <td className="px-6 py-4 text-center font-bold text-indigo-600">{safePct(current.heat_pct)}</td>
              <td className="px-6 py-4 text-center">{top1 ? safePct(top1.heat_pct) : '-'}</td>
              <td className="px-6 py-4 text-center font-mono">
                {top1 ? `${((safeNum(current.heat_pct) - safeNum(top1.heat_pct)) * 100).toFixed(1)}%` : '-'}
              </td>
            </tr>
            <tr>
              <td className="px-6 py-4 font-medium text-gray-900">资金总量 (Score Sum)</td>
              <td className="px-6 py-4 text-center font-bold text-indigo-600">{safeNum(current.c1_score_sum).toLocaleString()}</td>
              <td className="px-6 py-4 text-center">{top1 ? safeNum(top1.c1_score_sum).toLocaleString() : '-'}</td>
              <td className="px-6 py-4 text-center font-mono text-gray-500">
                {top1 ? (safeNum(current.c1_score_sum) - safeNum(top1.c1_score_sum)).toLocaleString() : '-'}
              </td>
            </tr>
            <tr>
              <td className="px-6 py-4 font-medium text-gray-900">成分股数量</td>
              <td className="px-6 py-4 text-center font-bold text-indigo-600">{current.stock_count}</td>
              <td className="px-6 py-4 text-center">{top1?.stock_count ?? '-'}</td>
              <td className="px-6 py-4 text-center font-mono">
                {top1 ? safeNum(current.stock_count) - safeNum(top1.stock_count) : '-'}
              </td>
            </tr>
            <tr>
              <td className="px-6 py-4 font-medium text-gray-900">平均涨幅</td>
              <td className="px-6 py-4 text-center font-bold text-indigo-600">
                {current.avg_price_change != null ? `${safeNum(current.avg_price_change) > 0 ? '+' : ''}${safeNum(current.avg_price_change).toFixed(2)}%` : '-'}
              </td>
              <td className="px-6 py-4 text-center">
                {top1?.avg_price_change != null ? `${safeNum(top1.avg_price_change) > 0 ? '+' : ''}${safeNum(top1.avg_price_change).toFixed(2)}%` : '-'}
              </td>
              <td className="px-6 py-4 text-center font-mono">
                {top1 ? `${(safeNum(current.avg_price_change) - safeNum(top1.avg_price_change)).toFixed(2)}%` : '-'}
              </td>
            </tr>
            <tr>
              <td className="px-6 py-4 font-medium text-gray-900">多信号股票</td>
              <td className="px-6 py-4 text-center font-bold text-indigo-600">{safeNum(current.multi_signal_count)}</td>
              <td className="px-6 py-4 text-center">{top1 ? safeNum(top1.multi_signal_count) : '-'}</td>
              <td className="px-6 py-4 text-center font-mono">
                {top1 ? safeNum(current.multi_signal_count) - safeNum(top1.multi_signal_count) : '-'}
              </td>
            </tr>
            <tr>
              <td className="px-6 py-4 font-medium text-gray-900">信号强度</td>
              <td className="px-6 py-4 text-center font-bold text-indigo-600">{safeNum(current.signal_strength).toFixed(1)}%</td>
              <td className="px-6 py-4 text-center">{top1 ? `${safeNum(top1.signal_strength).toFixed(1)}%` : '-'}</td>
              <td className="px-6 py-4 text-center font-mono">
                {top1 ? `${(safeNum(current.signal_strength) - safeNum(top1.signal_strength)).toFixed(1)}%` : '-'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default BoardComparison;
