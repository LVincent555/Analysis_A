import React from 'react';
import { Hammer, Gem, ArrowRight, TrendingUp } from 'lucide-react';

const StockCard = ({ stock, type, onStockClick }) => {
  return (
    <div 
      onClick={() => onStockClick && onStockClick(stock.stock_code)}
      className="bg-white p-3 rounded-lg border hover:shadow-md transition-shadow cursor-pointer flex justify-between items-center group"
    >
      <div>
        <div className="flex items-center gap-2">
          <span className="font-bold text-gray-900">{stock.stock_name}</span>
          <span className="text-xs text-gray-400">{stock.stock_code}</span>
          {stock.signal_level === 'S' && (
            <span className="px-1.5 py-0.5 rounded text-[10px] bg-gradient-to-r from-orange-500 to-pink-500 text-white font-bold">
              S级
            </span>
          )}
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs">
          <span className="text-gray-500">
            {type === 'resonance' ? '双S共振:' : '最强驱动:'}
          </span>
          <span className="font-medium text-indigo-600 bg-indigo-50 px-1 rounded">
             {stock.board_name || '未知板块'}
          </span>
        </div>
        <div className="mt-1 text-xs text-gray-400">
           {stock.reason}
        </div>
      </div>
      
      <div className="text-right">
        <div className="text-lg font-bold text-red-600">
          {stock.final_score?.toFixed(0)}
          <span className="text-xs text-gray-400 font-normal ml-0.5">分</span>
        </div>
        <div className="text-xs text-gray-400">
          排名 #{stock.market_rank}
        </div>
      </div>
    </div>
  );
};

const MiningList = ({ 
  resonanceData, 
  hiddenGemsData, 
  loading, 
  onStockClick 
}) => {
  const resonanceList = Array.isArray(resonanceData) ? resonanceData : Array.isArray(resonanceData?.items) ? resonanceData.items : [];
  const hiddenList = Array.isArray(hiddenGemsData) ? hiddenGemsData : Array.isArray(hiddenGemsData?.items) ? hiddenGemsData.items : [];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Resonance Hunter */}
      <div className="bg-gray-50 rounded-xl p-4 border border-indigo-100">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-indigo-100 rounded-lg text-indigo-600">
            <Hammer className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">双S级共振猎手</h3>
            <p className="text-xs text-gray-500">行业S级 + 概念S级 = 最强共振</p>
          </div>
        </div>
        
        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
          {loading ? (
             [1,2,3].map(i => <div key={i} className="h-20 bg-gray-200 rounded animate-pulse" />)
          ) : resonanceList.length > 0 ? (
            resonanceList.map(stock => (
              <StockCard 
                key={stock.stock_code || stock.id || Math.random()} 
                stock={stock} 
                type="resonance"
                onStockClick={onStockClick}
              />
            ))
          ) : (
            <div className="text-center py-10 text-gray-400 text-sm">暂无共振标的</div>
          )}
        </div>
      </div>

      {/* Hidden Gems */}
      <div className="bg-gray-50 rounded-xl p-4 border border-orange-100">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-orange-100 rounded-lg text-orange-600">
            <Gem className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">隐形冠军挖掘机</h3>
            <p className="text-xs text-gray-500">板块S级 + 高分 + 低排名 = 补涨潜力</p>
          </div>
        </div>
        
        <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
          {loading ? (
             [1,2,3].map(i => <div key={i} className="h-20 bg-gray-200 rounded animate-pulse" />)
          ) : hiddenList.length > 0 ? (
            hiddenList.map(stock => (
              <StockCard 
                key={stock.stock_code || stock.id || Math.random()} 
                stock={stock} 
                type="hidden"
                onStockClick={onStockClick}
              />
            ))
          ) : (
            <div className="text-center py-10 text-gray-400 text-sm">暂无挖掘标的</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MiningList;
