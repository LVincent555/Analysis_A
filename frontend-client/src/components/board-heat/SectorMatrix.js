import React from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend
} from 'recharts';

const SectorMatrix = ({ data, loading, onBoardClick }) => {
  if (loading) return <div className="h-96 bg-gray-100 rounded animate-pulse" />;

  const list = Array.isArray(data) ? data : Array.isArray(data?.items) ? data.items : [];
  if (!list || list.length === 0) return <div className="h-96 flex items-center justify-center text-gray-400 border rounded bg-white">暂无罗盘数据</div>;

  // Split data by type for different colors in Legend
  const industryData = list.filter(d => d.type === 'industry');
  const conceptData = list.filter(d => d.type === 'concept');

  // Custom Tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-white p-3 border shadow-lg rounded text-sm z-50">
          <p className="font-bold text-gray-900 mb-1">{d.name}</p>
          <p className="text-gray-600">类型: {d.type === 'industry' ? '行业' : '概念'}</p>
          <div className="my-1 border-t border-gray-100" />
          <p className="text-gray-600">头部密度(X): <span className="font-medium text-blue-600">{d.x.toFixed(1)}</span></p>
          <p className="text-gray-600">板块质量(Y): <span className="font-medium text-purple-600">{d.y.toFixed(1)}</span></p>
          <p className="text-gray-600">热度(Size): <span className="font-medium text-orange-600">{(d.size * 100).toFixed(0)}%</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white p-4 rounded-lg border shadow-sm h-[500px]">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-bold">板块风格罗盘</h3>
          <p className="text-xs text-gray-500">X轴=头部密度(B2) Y轴=质量评分(C2) | 右上角为"高密高质量"强势区</p>
        </div>
      </div>
      
      <div style={{ width: '100%', height: 'calc(100% - 3rem)' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis 
              type="number" 
              dataKey="x" 
              name="头部密度" 
              label={{ value: '头部密度 (B2)', position: 'bottom', offset: 0, fontSize: 12 }} 
              domain={['auto', 'auto']}
              tick={{ fontSize: 10 }}
            />
            <YAxis 
              type="number" 
              dataKey="y" 
              name="质量评分" 
              label={{ value: '质量评分 (C2)', angle: -90, position: 'left', offset: 0, fontSize: 12 }}
              domain={['auto', 'auto']}
              tick={{ fontSize: 10 }}
            />
            <ZAxis type="number" dataKey="size" range={[50, 400]} name="热度" />
            
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            <Legend verticalAlign="top" height={36} />
            
            {/* Quadrant Lines (approximate midpoints, can be dynamic) */}
            <ReferenceLine x={50} stroke="#e5e7eb" strokeDasharray="3 3" />
            <ReferenceLine y={50} stroke="#e5e7eb" strokeDasharray="3 3" />

            <Scatter 
              name="行业板块" 
              data={industryData} 
              fill="#3b82f6" 
              shape="circle"
              onClick={(node) => onBoardClick && onBoardClick(node)}
              className="cursor-pointer opacity-80 hover:opacity-100 transition-opacity"
            />
            <Scatter 
              name="概念板块" 
              data={conceptData} 
              fill="#a855f7" 
              shape="triangle"
              onClick={(node) => onBoardClick && onBoardClick(node)}
              className="cursor-pointer opacity-80 hover:opacity-100 transition-opacity"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default SectorMatrix;
