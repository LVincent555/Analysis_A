import React from 'react';
import { Activity } from 'lucide-react';

const MarketSignalBar = ({ data, loading }) => {
  if (loading) return <div className="h-24 bg-gray-100 rounded animate-pulse" />;
  if (!data) return null;

  const { distribution, total, sentiment } = data;
  const s_pct = total > 0 ? (distribution.S / total) * 100 : 0;
  const a_pct = total > 0 ? (distribution.A / total) * 100 : 0;
  const b_pct = total > 0 ? (distribution.B / total) * 100 : 0;
  // none is the rest

  let sentimentColor = 'text-gray-600';
  if (s_pct >= 5) sentimentColor = 'text-red-600';
  else if (s_pct >= 2) sentimentColor = 'text-orange-600';
  else if (s_pct <= 1) sentimentColor = 'text-blue-600';

  return (
    <div className="bg-white p-4 rounded-lg border shadow-sm mb-6">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-bold flex items-center gap-2">
          <Activity className="w-5 h-5 text-indigo-600" />
          市场信号体检
        </h3>
        <div className={`text-sm font-bold ${sentimentColor}`}>
          {sentiment}
        </div>
      </div>
      
      {/* Bar */}
      <div className="h-4 flex rounded-full overflow-hidden bg-gray-100 relative">
        <div style={{ width: `${s_pct}%` }} className="bg-gradient-to-r from-orange-500 to-red-500 transition-all duration-500" title={`S级: ${distribution.S}`} />
        <div style={{ width: `${a_pct}%` }} className="bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-500" title={`A级: ${distribution.A}`} />
        <div style={{ width: `${b_pct}%` }} className="bg-gray-400 transition-all duration-500" title={`B级: ${distribution.B}`} />
      </div>
      
      {/* Legend */}
      <div className="flex gap-4 mt-2 text-xs text-gray-500 justify-end">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-gradient-to-r from-orange-500 to-red-500" />
          S级 ({distribution.S})
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-500 to-pink-500" />
          A级 ({distribution.A})
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-gray-400" />
          B级 ({distribution.B})
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-gray-200 border" />
          Total: {total}
        </div>
      </div>
    </div>
  );
};

export default MarketSignalBar;
