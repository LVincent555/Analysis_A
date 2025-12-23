/**
 * 板块完整分析页面
 * 展示多维度信号说明、历史趋势、板块对比
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  ArrowLeft, Flame, TrendingUp, BarChart2, GitCompare, 
  ChevronDown, ChevronUp, Users, Target, Zap, Activity,
  Award, RefreshCw
} from 'lucide-react';
import boardHeatService from '../services/boardHeatService';
import BoardSignalBadge from '../components/BoardSignalBadge';
import BoardHistoryChart from '../components/board-heat/BoardHistoryChart';
import BoardComparison from '../components/board-heat/BoardComparison';
import StockDNADialog from '../components/board-heat/StockDNADialog';

// 多维度信号配置 - 基于设计简稿中的板块信号系统
const SIGNAL_DIMENSIONS = [
  {
    id: 'T1',
    name: '热点榜',
    color: 'red',
    icon: Flame,
    description: '总分TOP: 基于当日综合排名，信号如"热点榜TOP100"',
    subDesc: '最新热点TOP: 基于14天聚合数据，信号如"TOP100·5次"',
    weight: '权重: 25%基础 · 排位倍数TOP100(1.5×)~TOP3000(0.5×) · 第一层'
  },
  {
    id: 'T2',
    name: '排名跳变',
    color: 'orange',
    icon: TrendingUp,
    description: '排名相比前一天大幅提升(≥2000)，说明热度快速上升',
    subDesc: '信号: 跳变↑2207',
    weight: '权重: 20% · 第二层 (市场关注)'
  },
  {
    id: 'T3',
    name: '波动率上升',
    color: 'yellow',
    icon: Activity,
    description: '波动率自分位≥30%，说明价格波动加剧 (计算方式：当前-前一天/前一天×100%)',
    subDesc: '信号: 波动率↑小幅↑24.7%',
    weight: '权重: 20% · 第二层 (市场关注)'
  },
  {
    id: 'T4',
    name: '稳步上升',
    color: 'green',
    icon: Target,
    description: '连续多天排名持续上升，说明趋势稳定向好',
    subDesc: '信号: 换手率↑12.7%',
    weight: '权重: 15% · 第三层 (持续性)'
  },
  {
    id: 'T5',
    name: '涨幅榜',
    color: 'purple',
    icon: Award,
    description: '涨跌幅超过阈值(如≥5%)，说明价格异动明显',
    subDesc: '信号: 涨幅↑7.7%',
    weight: '权重: 10% · 第四层 (短期活跃)',
  },
  {
    id: 'T6',
    name: '成交量榜',
    color: 'blue',
    icon: BarChart2,
    description: '成交量相对历史放大，说明资金关注度提升',
    subDesc: '信号: 成交量↑放大',
    weight: '权重: 10% · 第四层 (短期活跃)',
  }
];

export default function BoardAnalysisPage({ board, selectedDate, onBack }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('stocks'); // 'stocks', 'history', 'compare'
  const [showSignalGuide, setShowSignalGuide] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  
  // 加载板块详情
  useEffect(() => {
    if (!board?.board_id) return;
    
    const loadDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await boardHeatService.getBoardDetail(board.board_id, selectedDate);
        setDetail(result);
      } catch (err) {
        setError(err.response?.data?.detail || err.message || '加载失败');
      } finally {
        setLoading(false);
      }
    };
    
    loadDetail();
  }, [board?.board_id, selectedDate]);

  // 加载历史数据
  useEffect(() => {
    if (activeTab === 'history' && board?.board_id) {
      // Clear previous data if date changed (optional, but good for consistency)
      // setHistoryData([]); 
      
      const loadHistory = async () => {
        setHistoryLoading(true);
        try {
          if (boardHeatService.getBoardHistory) {
             const result = await boardHeatService.getBoardHistory(board.board_id, 30, selectedDate);
             setHistoryData(result);
          }
        } catch (err) {
          console.error("Failed to load history", err);
        } finally {
          setHistoryLoading(false);
        }
      };
      loadHistory();
    }
  }, [activeTab, board?.board_id, selectedDate]);
  
  if (!board) return null;
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* 面包屑导航 */}
      <div className="bg-white border-b px-6 py-3">
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={onBack}
            className="flex items-center gap-1 text-gray-500 hover:text-gray-700"
          >
            <ArrowLeft className="w-4 h-4" />
            返回
          </button>
          <span className="text-gray-300">/</span>
          <span className="text-gray-500">行业趋势分析</span>
          <span className="text-gray-300">/</span>
          <span className="font-medium text-gray-900">{board.board_name}</span>
        </div>
      </div>
      
      {/* 统计卡片区 */}
      <div className="px-6 py-4 bg-white border-b">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <StatCard label="成分股" value={`${detail?.stock_count || board.stock_count || 0}只`} color="purple" />
          <StatCard label="TOP100" value={`${detail?.top100_count || 0}只`} color="blue" />
          <StatCard label="热点榜" value={`${detail?.hotlist_count || 0}只`} color="green" />
          <StatCard label="多信号" value={`${detail?.multi_signal_count || 0}只`} color="orange" />
          <StatCard 
            label="B2涨跌幅" 
            value={detail?.avg_price_change != null ? `${detail.avg_price_change > 0 ? '+' : ''}${detail.avg_price_change.toFixed(2)}%` : '-'} 
            color="red"
            highlight={detail?.avg_price_change > 0}
          />
          <StatCard 
            label="信号强度" 
            value={`${detail?.signal_strength || 0}%`} 
            color="indigo"
          />
        </div>
      </div>
      
      {/* 4维指标说明（可折叠） */}
      <div className="px-6 py-3 bg-gray-100 border-b">
        <button
          onClick={() => setShowSignalGuide(!showSignalGuide)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <TrendingUp className="w-4 h-4" />
          <span>4维指标说明</span>
          {showSignalGuide ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          <span className="text-gray-400 ml-2">展开</span>
        </button>
      </div>
      
      {/* Tab 切换 */}
      <div className="px-6 py-3 bg-white border-b">
        <div className="flex gap-2">
          <TabButton 
            active={activeTab === 'stocks'} 
            onClick={() => setActiveTab('stocks')}
            color="orange"
          >
            成分股分析
          </TabButton>
          <TabButton 
            active={activeTab === 'history'} 
            onClick={() => setActiveTab('history')}
            color="gray"
          >
            历史趋势
          </TabButton>
          <TabButton 
            active={activeTab === 'compare'} 
            onClick={() => setActiveTab('compare')}
            color="gray"
          >
            板块对比
          </TabButton>
        </div>
      </div>
      
      {/* 多维度信号说明区 */}
      {activeTab === 'stocks' && (
        <div className="px-6 py-4 bg-gradient-to-r from-purple-50 to-pink-50 border-b">
          <h3 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4" />
            多维度信号说明
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {SIGNAL_DIMENSIONS.map(dim => (
              <SignalDimensionCard key={dim.id} dimension={dim} />
            ))}
          </div>
          
          {/* 综合使用建议 */}
          <div className="mt-4 p-3 bg-white/50 rounded-lg text-xs text-gray-600">
            <div className="font-semibold text-gray-700 mb-1">💡 综合使用建议:</div>
            <div className="grid md:grid-cols-2 gap-2">
              <div>• <strong>信号数量</strong>: 信号越多说明该股票越值得关注</div>
              <div>• <strong>信号组合</strong>: 多个信号叠加通常意味着更强的市场信号</div>
              <div>• <strong>信号强度</strong>: 综合反映了各个信号的权重得分 (0-100%)</div>
              <div>• <strong>权重分层</strong>: T1热点榜25% &gt; T2排名跳变/波动率20% &gt; T3稳步上升15% &gt; T4涨幅/成交量10%</div>
            </div>
          </div>
        </div>
      )}
      
      {/* 内容区 */}
      <div className="px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-10 h-10 animate-spin text-orange-500" />
          </div>
        ) : error ? (
          <div className="text-center py-16 text-red-500">{error}</div>
        ) : activeTab === 'stocks' ? (
          <StocksTable
            stocks={detail?.top_stocks || []}
            board={board}
            onStockClick={(stockCode) => setSelectedStock(stockCode)}
          />
        ) : activeTab === 'history' ? (
          <div className="py-4">
             <BoardHistoryChart data={historyData} loading={historyLoading} />
             
             {/* 简单的历史统计 */}
             <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-white border rounded-lg">
                   <div className="text-xs text-gray-500">30天平均热度</div>
                   <div className="text-xl font-bold text-gray-900">
                      {historyData.length > 0 
                        ? (historyData.reduce((acc, cur) => acc + cur.heat_pct, 0) / historyData.length * 100).toFixed(1) + '%' 
                        : '-'}
                   </div>
                </div>
                <div className="p-4 bg-white border rounded-lg">
                   <div className="text-xs text-gray-500">最近趋势</div>
                   <div className="text-sm font-medium text-gray-700 mt-1">
                      {historyData.length >= 2 
                        ? (historyData[historyData.length-1].heat_pct > historyData[historyData.length-2].heat_pct ? '📈 上升中' : '📉 下降中') 
                        : '-'}
                   </div>
                </div>
                <div className="p-4 bg-white border rounded-lg">
                   <div className="text-xs text-gray-500">资金峰值</div>
                   <div className="text-xl font-bold text-blue-600">
                      {historyData.length > 0 
                        ? Math.max(...historyData.map(d => d.funds)).toFixed(0)
                        : '-'}
                   </div>
                </div>
             </div>
          </div>
        ) : (
          <BoardComparison 
            currentBoard={board} 
            tradeDate={detail?.trade_date} 
          />
        )}
      </div>

      {selectedStock && (
        <StockDNADialog
          stockCode={selectedStock}
          selectedDate={selectedDate}
          onClose={() => setSelectedStock(null)}
        />
      )}
    </div>
  );
}

// 统计卡片
function StatCard({ label, value, color, highlight }) {
  const colorMap = {
    purple: 'bg-purple-100 text-purple-700',
    blue: 'bg-blue-100 text-blue-700',
    green: 'bg-green-100 text-green-700',
    orange: 'bg-orange-100 text-orange-700',
    red: 'bg-red-100 text-red-700',
    indigo: 'bg-indigo-100 text-indigo-700',
  };
  
  return (
    <div className={`rounded-lg p-3 ${colorMap[color]}`}>
      <div className="text-xs opacity-80">{label}</div>
      <div className={`text-xl font-bold ${highlight ? 'text-red-600' : ''}`}>{value}</div>
    </div>
  );
}

// Tab 按钮
function TabButton({ active, onClick, color, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
        active 
          ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white' 
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      {children}
    </button>
  );
}

// 信号维度卡片
function SignalDimensionCard({ dimension }) {
  const colorMap = {
    red: 'border-red-300 bg-red-50',
    orange: 'border-orange-300 bg-orange-50',
    yellow: 'border-yellow-300 bg-yellow-50',
    green: 'border-green-300 bg-green-50',
    purple: 'border-purple-300 bg-purple-50',
    blue: 'border-blue-300 bg-blue-50',
  };
  
  const textColorMap = {
    red: 'text-red-700',
    orange: 'text-orange-700',
    yellow: 'text-yellow-700',
    green: 'text-green-700',
    purple: 'text-purple-700',
    blue: 'text-blue-700',
  };
  
  const Icon = dimension.icon;
  
  return (
    <div className={`border rounded-lg p-3 ${colorMap[dimension.color]}`}>
      <div className={`flex items-center gap-2 font-semibold text-sm ${textColorMap[dimension.color]}`}>
        <Icon className="w-4 h-4" />
        {dimension.name}
        <span className="ml-auto text-xs bg-white/50 px-1.5 py-0.5 rounded">{dimension.id}</span>
      </div>
      <div className="text-xs text-gray-600 mt-2 leading-relaxed">
        {dimension.description}
      </div>
      <div className="text-xs text-gray-500 mt-1 italic">
        {dimension.subDesc}
      </div>
      <div className="text-xs text-gray-400 mt-2 border-t border-gray-200 pt-2">
        {dimension.weight}
      </div>
    </div>
  );
}

// 成分股表格
function StocksTable({ stocks, board, onStockClick }) {
  if (!stocks || stocks.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>暂无成分股数据</p>
      </div>
    );
  }
  
  return (
    <div className="bg-white rounded-lg border overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">排名</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">股票</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">信号</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">综合评分</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">涨跌幅</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">收盘价</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">换手率</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">波动率</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">市场排名</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {stocks.map((stock, idx) => (
            <tr
              key={stock.stock_code}
              className="hover:bg-gray-50 cursor-pointer"
              onClick={() => onStockClick?.(stock.stock_code)}
            >
              <td className="px-4 py-3 text-gray-500 font-medium">#{idx + 1}</td>
              <td className="px-4 py-3">
                <div className="font-medium text-gray-900">{stock.stock_name}</div>
                <div className="text-xs text-gray-400">{stock.stock_code}</div>
              </td>
              <td className="px-4 py-3">
                <div className="flex flex-wrap gap-1">
                  {/* 板块信号标签 [S级｜板块名] */}
                  {stock.signal_level && stock.signal_level !== 'NONE' ? (
                    <BoardSignalBadge
                      level={stock.signal_level}
                      label={board?.board_name || ''}
                      type={board?.board_type || 'concept'}
                      size="sm"
                    />
                  ) : stock.market_rank && stock.market_rank <= 100 ? (
                    <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-700 font-medium">TOP100</span>
                  ) : (
                    <span className="text-xs text-gray-400">-</span>
                  )}
                </div>
                {stock.final_score && stock.final_score > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    强度: {Math.min(100, Math.round(stock.final_score))}%
                  </div>
                )}
              </td>
              <td className="px-4 py-3 text-right font-medium text-gray-900">
                {stock.total_score?.toFixed(2) || '-'}
              </td>
              <td className="px-4 py-3 text-right">
                <span className={`font-medium ${
                  stock.price_change > 0 ? 'text-red-600' :
                  stock.price_change < 0 ? 'text-green-600' :
                  'text-gray-600'
                }`}>
                  {stock.price_change != null ? `${stock.price_change > 0 ? '+' : ''}${stock.price_change.toFixed(2)}%` : '-'}
                </span>
              </td>
              <td className="px-4 py-3 text-right text-gray-700">
                {stock.close_price != null ? stock.close_price.toFixed(2) : '-'}
              </td>
              <td className="px-4 py-3 text-right text-gray-600">
                {stock.turnover_rate != null ? `${stock.turnover_rate.toFixed(2)}%` : '-'}
              </td>
              <td className="px-4 py-3 text-right text-gray-600">
                {stock.volatility != null ? `${stock.volatility.toFixed(2)}%` : '-'}
              </td>
              <td className="px-4 py-3 text-right text-gray-500">
                #{stock.market_rank || '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
