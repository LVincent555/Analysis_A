/**
 * 外部板块热度榜页面
 * 展示东财527板块的热度排名
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Flame, Filter, RefreshCw, ChevronLeft, ChevronRight, Building2, Lightbulb, BarChart3, LayoutGrid, Compass } from 'lucide-react';
import boardHeatService from '../services/boardHeatService';
import BoardDetailDialog from '../components/BoardDetailDialog';
import MarketSignalBar from '../components/board-heat/MarketSignalBar';
import MarketTreemap from '../components/board-heat/MarketTreemap';
import SectorMatrix from '../components/board-heat/SectorMatrix';
import MiningList from '../components/board-heat/MiningList';
import StockDNADialog from '../components/board-heat/StockDNADialog';

// 热度条组件
const HeatBar = ({ pct }) => {
  const safePct = pct || 0;
  const percentage = (safePct * 100).toFixed(1);
  const width = Math.min(100, safePct * 100);
  
  // 根据热度决定颜色
  let colorClass = 'bg-gray-400';
  if (safePct >= 0.8) colorClass = 'bg-gradient-to-r from-orange-500 to-red-500';
  else if (safePct >= 0.5) colorClass = 'bg-gradient-to-r from-yellow-400 to-orange-400';
  else if (safePct >= 0.2) colorClass = 'bg-blue-400';
  
  return (
    <div className="flex items-center gap-2">
      <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full ${colorClass}`} 
          style={{ width: `${width}%` }}
        />
      </div>
      <span className={`text-sm font-medium ${safePct >= 0.8 ? 'text-red-600' : safePct >= 0.5 ? 'text-orange-600' : 'text-gray-600'}`}>
        {percentage}%
      </span>
    </div>
  );
};

// 板块类型标签
const BoardTypeTag = ({ type }) => {
  if (type === 'industry') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
        <Building2 className="w-3 h-3" />
        行业
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-purple-100 text-purple-700">
      <Lightbulb className="w-3 h-3" />
      概念
    </span>
  );
};

const EXT_BOARD_HEAT_PERSIST_KEY = 'extBoardHeat.persist';

const readPersistedExtBoardHeatState = () => {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(EXT_BOARD_HEAT_PERSIST_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed;
  } catch (e) {
    return {};
  }
};

const writePersistedExtBoardHeatState = (state) => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(EXT_BOARD_HEAT_PERSIST_KEY, JSON.stringify(state));
  } catch (e) {
    return;
  }
};

export default function ExtBoardHeat({ selectedDate, onBoardClick, onNavigateToAnalysis }) {
  const [loading, setLoading] = useState(true);
  const [macroLoading, setMacroLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState({ items: [], total_count: 0, trade_date: '', snap_date: '' });
  
  // View State
  const [activeView, setActiveView] = useState(() => {
    const persisted = readPersistedExtBoardHeatState();
    const val = persisted?.activeView;
    if (val === 'overview' || val === 'matrix' || val === 'mining') return val;
    return 'overview';
  }); // overview, matrix, mining
  
  // V4.0 Macro Data
  const [signalBarData, setSignalBarData] = useState(null);
  const [treemapData, setTreemapData] = useState([]);
  const [matrixData, setMatrixData] = useState([]);
  const [miningResonance, setMiningResonance] = useState([]);
  const [miningHidden, setMiningHidden] = useState([]);
  
  // 筛选和分页
  const [boardType, setBoardType] = useState(() => {
    const persisted = readPersistedExtBoardHeatState();
    const val = persisted?.boardType;
    if (val === 'industry' || val === 'concept') return val;
    return null;
  }); // null=全部, 'industry', 'concept'
  const [page, setPage] = useState(0);
  const [pageSize] = useState(50);

  // 过滤“超大类”板块（成分股过多会稀释热度）
  const [excludeHugeBoards, setExcludeHugeBoards] = useState(() => {
    const persisted = readPersistedExtBoardHeatState();
    const val = persisted?.excludeHugeBoards;
    if (typeof val === 'boolean') return val;
    return true;
  });

  // 低价股过滤（默认关闭）：仅影响成分股展示/信号展示，不影响榜单热度计算
  const [excludeLowPrice, setExcludeLowPrice] = useState(() => {
    const persisted = readPersistedExtBoardHeatState();
    const val = persisted?.excludeLowPrice;
    if (typeof val === 'boolean') return val;
    return false;
  });
  const minPrice = 3.0;

  // 股票快捷查询（不影响排行榜名次/排序）
  const [stockQuery, setStockQuery] = useState('');
  
  // 弹窗状态
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [selectedStock, setSelectedStock] = useState(null);

  useEffect(() => {
    writePersistedExtBoardHeatState({
      activeView,
      boardType,
      excludeHugeBoards,
      excludeLowPrice
    });
  }, [activeView, boardType, excludeHugeBoards, excludeLowPrice]);
  
  // 加载列表数据
  const loadListData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await boardHeatService.getRanking({
        trade_date: selectedDate,
        board_type: boardType,
        max_stock_count: excludeHugeBoards ? 999 : null,
        limit: pageSize,
        offset: page * pageSize
      });
      const rawItems = result?.items || [];
      const filteredItems = excludeHugeBoards
        ? rawItems.filter((it) => Number(it?.stock_count || 0) < 1000)
        : rawItems;

      // 确保返回数据结构正确
      setData({
        items: filteredItems,
        total_count: result?.total_count || 0,
        trade_date: result?.trade_date || '',
        snap_date: result?.snap_date || ''
      });
    } catch (err) {
      console.error('加载板块热度失败:', err);
      setError(err.response?.data?.detail || err.message || '加载失败');
      setData({ items: [], total_count: 0, trade_date: '', snap_date: '' });
    } finally {
      setLoading(false);
    }
  }, [selectedDate, boardType, excludeHugeBoards, page, pageSize]);

  // Load View Data (V4.0)
  const loadViewData = useCallback(async () => {
    setMacroLoading(true);
    const tryParseStringArray = (val) => {
      if (typeof val !== 'string') return null;
      const trimmed = val.trim();
      if (!(trimmed.startsWith('[') && trimmed.endsWith(']'))) return null;
      try {
        return JSON.parse(trimmed);
      } catch (e1) {
        try {
          // 粗暴把单引号替换成双引号再尝试
          const replaced = trimmed.replace(/'/g, '"');
          return JSON.parse(replaced);
        } catch (e2) {
          console.warn('parse string array failed', e2);
          return null;
        }
      }
    };

    const unwrapList = (res) => {
      if (Array.isArray(res)) return res;
      const parsed = tryParseStringArray(res);
      if (parsed) return parsed;
      if (Array.isArray(res?.data)) return res.data;
      const parsedData = tryParseStringArray(res?.data);
      if (parsedData) return parsedData;
      if (Array.isArray(res?.items)) return res.items;
      const parsedItems = tryParseStringArray(res?.items);
      if (parsedItems) return parsedItems;
      if (Array.isArray(res?.result)) return res.result;
      const parsedResult = tryParseStringArray(res?.result);
      if (parsedResult) return parsedResult;
      if (Array.isArray(res?.data?.data)) return res.data.data;
      const parsedDataData = tryParseStringArray(res?.data?.data);
      if (parsedDataData) return parsedDataData;
      if (res && typeof res === 'object') {
        const vals = Object.values(res);
        const firstArr = vals.find(v => Array.isArray(v));
        if (firstArr) return firstArr;
        const firstParsed = vals.map(tryParseStringArray).find(v => Array.isArray(v));
        if (firstParsed) return firstParsed;
      }
      return [];
    };

    try {
      if (activeView === 'overview') {
        const [barData, treeData] = await Promise.all([
          boardHeatService.getMarketSignalBar(selectedDate),
          boardHeatService.getMarketTreemap(selectedDate, 0, excludeHugeBoards ? 999 : null) // 同步“超大类”过滤
        ]);
        console.info('overview raw treemap:', treeData);
        const treeList = unwrapList(treeData);
        console.info('overview data:', {
          signalBar: barData,
          treemapCount: treeList.length
        });
        setSignalBarData(barData);
        setTreemapData(treeList);
      } else if (activeView === 'matrix') {
        const matData = await boardHeatService.getSectorMatrix(selectedDate, 200);
        console.info('matrix raw:', matData);
        const matList = unwrapList(matData);
        console.info('matrix data count:', matList.length);
        setMatrixData(matList);
      } else if (activeView === 'mining') {
        const [resData, hidData] = await Promise.all([
          boardHeatService.getMiningResonance(selectedDate),
          boardHeatService.getMiningHiddenGems(selectedDate)
        ]);
        console.info('mining raw:', { resData, hidData });
        const resList = unwrapList(resData);
        const hidList = unwrapList(hidData);
        console.info('mining data:', {
          resonance: resList.length,
          hidden: hidList.length
        });
        setMiningResonance(resList);
        setMiningHidden(hidList);
      }
    } catch (err) {
      console.error("加载视图数据失败:", err);
    } finally {
      setMacroLoading(false);
    }
  }, [activeView, selectedDate, excludeHugeBoards]);
  
  useEffect(() => {
    loadListData();
  }, [loadListData]);
  
  useEffect(() => {
    loadViewData();
  }, [loadViewData]);
  
  // 计算分页信息（避免除零）
  const totalPages = Math.ceil((data.total_count || 0) / pageSize) || 0;
  
  // 统计各类型数量
  const industryCount = 86;  // 固定值，可从API获取
  const conceptCount = 441;
  
  return (
    <div className="p-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Flame className="w-7 h-7 text-orange-500" />
            板块热度排名
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            东财多对多版 · 共 {data.total_count} 个板块 · {data.trade_date}
            {data.snap_date !== data.trade_date && (
              <span className="text-amber-600 ml-2">(关系数据: {data.snap_date})</span>
            )}
          </p>
        </div>
        
        <div className="flex gap-2">
           <button
            onClick={() => { loadListData(); loadViewData(); }}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>
      </div>

      {/* View Tabs */}
      <div className="flex gap-4 mb-6 border-b border-gray-200">
        <button
          onClick={() => setActiveView('overview')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition-colors ${
            activeView === 'overview' 
              ? 'border-indigo-600 text-indigo-600' 
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <LayoutGrid className="w-4 h-4" />
          市场全景
        </button>
        <button
          onClick={() => setActiveView('matrix')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition-colors ${
            activeView === 'matrix' 
              ? 'border-indigo-600 text-indigo-600' 
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Compass className="w-4 h-4" />
          风格罗盘
        </button>
        <button
          onClick={() => setActiveView('mining')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 font-medium transition-colors ${
            activeView === 'mining' 
              ? 'border-indigo-600 text-indigo-600' 
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Flame className="w-4 h-4" />
          智能掘金
        </button>
      </div>

      {/* View Content */}
      <div className="mb-8">
        {activeView === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
               <MarketSignalBar data={signalBarData} loading={macroLoading} />
            </div>
            <div className="lg:col-span-2">
               <MarketTreemap 
                  data={treemapData} 
                  loading={macroLoading} 
                  onBoardClick={(node) => {
                    if (node && node.board_id) {
                      setSelectedBoard({
                        board_id: node.board_id,
                        board_name: node.name,
                        board_code: '', 
                        board_type: node.type
                      });
                    }
                  }}
               />
            </div>
          </div>
        )}

        {activeView === 'matrix' && (
           <SectorMatrix 
             data={matrixData} 
             loading={macroLoading}
             onBoardClick={(node) => {
                if (node && node.board_id) {
                  setSelectedBoard({
                    board_id: node.board_id,
                    board_name: node.name,
                    board_code: '', 
                    board_type: node.type
                  });
                }
             }}
           />
        )}

        {activeView === 'mining' && (
           <MiningList 
             resonanceData={miningResonance}
             hiddenGemsData={miningHidden}
             loading={macroLoading}
             onStockClick={(stockCode) => {
                setSelectedStock(stockCode);
             }}
           />
        )}
      </div>
      
      {/* 筛选栏 (Only for Ranking List) */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-gray-500" />
          板块排行榜
        </h2>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <input
              value={stockQuery}
              onChange={(e) => setStockQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const code = (stockQuery || '').trim();
                  if (code) setSelectedStock(code);
                }
              }}
              placeholder="查询股票(代码)"
              className="w-40 px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={() => {
                const code = (stockQuery || '').trim();
                if (code) setSelectedStock(code);
              }}
              className="px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm"
            >
              查询
            </button>
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-600 select-none">
            <input
              type="checkbox"
              checked={excludeHugeBoards}
              onChange={(e) => {
                setExcludeHugeBoards(e.target.checked);
                setPage(0);
              }}
              className="rounded"
            />
            过滤≥1000成分股
          </label>

          <label className="flex items-center gap-2 text-sm text-gray-600 select-none">
            <input
              type="checkbox"
              checked={excludeLowPrice}
              onChange={(e) => {
                setExcludeLowPrice(e.target.checked);
              }}
              className="rounded"
            />
            剔除 &lt; 3元低价股
          </label>

          <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-lg">
          <button
            onClick={() => { setBoardType(null); setPage(0); }}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
              boardType === null 
                ? 'bg-white text-indigo-600 shadow-sm' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            全部
          </button>
          
          <button
            onClick={() => { setBoardType('industry'); setPage(0); }}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
              boardType === 'industry' 
                ? 'bg-white text-blue-600 shadow-sm' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            行业
          </button>
          
          <button
            onClick={() => { setBoardType('concept'); setPage(0); }}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1 ${
              boardType === 'concept' 
                ? 'bg-white text-purple-600 shadow-sm' 
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            概念
          </button>
        </div>
        </div>
      </div>
      
      {/* 错误提示 */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}
      
      {/* 数据表格 */}
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">
                排名
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                板块名称
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-24">
                类型
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-48">
                热度
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-24">
                成分股
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-gray-500">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                  加载中...
                </td>
              </tr>
            ) : !data.items || data.items.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-gray-500">
                  暂无数据
                </td>
              </tr>
            ) : (
              data.items.map((item, idx) => (
                <tr 
                  key={item?.board_id || idx}
                  onClick={() => setSelectedBoard(item)}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                      page * pageSize + idx < 3 
                        ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white' 
                        : page * pageSize + idx < 10 
                          ? 'bg-orange-100 text-orange-700'
                          : 'bg-gray-100 text-gray-600'
                    }`}>
                      {page * pageSize + idx + 1}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col">
                       <div className="flex items-center gap-2">
                         <span className="font-medium text-gray-900">{item?.board_name || '-'}</span>
                         {item?.is_blacklisted && (
                            <span className="px-1 py-0.5 bg-gray-200 text-gray-500 text-[10px] rounded">黑/灰</span>
                         )}
                       </div>
                       <span className="text-xs text-gray-400">{item?.board_code || ''}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <BoardTypeTag type={item?.board_type} />
                  </td>
                  <td className="px-4 py-3">
                    <HeatBar pct={item?.heat_pct} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {item?.stock_count || 0} 只
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 px-2">
          <span className="text-sm text-gray-500">
            显示 {page * pageSize + 1} - {Math.min((page + 1) * pageSize, data.total_count || 0)} / 共 {data.total_count || 0} 条
          </span>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            
            <span className="px-3 py-1 text-sm">
              {page + 1} / {totalPages}
            </span>
            
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="p-2 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
      
      {/* 板块详情弹窗 */}
      {selectedBoard && (
        <BoardDetailDialog
          board={selectedBoard}
          selectedDate={selectedDate}
          minPrice={excludeLowPrice ? minPrice : null}
          onClose={() => setSelectedBoard(null)}
          onStockClick={(stockCode) => {
            setSelectedStock(stockCode);
          }}
          onViewFullAnalysis={(board) => {
            // 恢复原行为：交给上层导航到完整分析页
            onNavigateToAnalysis?.(board);
          }}
        />
      )}

      {/* 个股DNA弹窗 */}
      {selectedStock && (
        <StockDNADialog
          stockCode={selectedStock}
          selectedDate={selectedDate}
          minPrice={excludeLowPrice ? minPrice : null}
          onClose={() => setSelectedStock(null)}
        />
      )}
    </div>
  );
}
