import React, { useMemo, useState } from 'react';
import { ResponsiveContainer, Treemap, Tooltip } from 'recharts';

const MarketTreemap = ({ data, loading, onBoardClick }) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Normalize data to array (keep hooks unconditional)
  const list = useMemo(() => {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.items)) return data.items;
    return [];
  }, [data]);

  // Transform data for Treemap
  const treeData = useMemo(() => {
    return [
      {
        name: 'Market',
        children: list.map((item) => ({
          ...item,
          size: Number(item.value) || 0, // for recharts calculation
        }))
      }
    ];
  }, [list]);

  if (loading) return <div className="h-80 bg-gray-100 rounded animate-pulse" />;

  if (!list || list.length === 0) {
    return <div className="h-80 flex items-center justify-center text-gray-400 border rounded bg-white">暂无热力图数据</div>;
  }

  const getColor = (heatPct) => {
    if (heatPct >= 0.95) return '#dc2626'; // red-600
    if (heatPct >= 0.85) return '#ea580c'; // orange-600
    if (heatPct >= 0.70) return '#eab308'; // yellow-500
    if (heatPct >= 0.50) return '#65a30d'; // lime-600
    if (heatPct >= 0.30) return '#059669'; // emerald-600
    return '#4b5563'; // gray-600
  };

  const CustomizedContent = (props) => {
    const { depth, x, y, width, height, name, heat_pct } = props;
    
    // Check if payload is available (recharts behavior varies)
    const pct = heat_pct !== undefined ? heat_pct : (props.payload ? props.payload.heat_pct : 0);
    const boardName = name || (props.payload ? props.payload.name : '');

    return (
      <g onClick={() => onBoardClick && onBoardClick(props)}>
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          style={{
            fill: getColor(pct),
            stroke: '#fff',
            strokeWidth: 2 / (depth + 1e-10),
            strokeOpacity: 1 / (depth + 1e-10),
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
        />
        {width > 36 && height > 24 && (
          <text
            x={x + width / 2}
            y={y + height / 2}
            textAnchor="middle"
            fill="#fff"
            fontSize={Math.min(width / 4, height / 2, 14)}
            fontWeight="bold"
            dominantBaseline="central"
            style={{ pointerEvents: 'none' }}
          >
            {boardName}
          </text>
        )}
      </g>
    );
  };

  const chart = (
    <div style={{ width: '100%', height: 'calc(100% - 2rem)' }}>
      <ResponsiveContainer width="100%" height="100%">
        <Treemap
          data={treeData}
          dataKey="size"
          ratio={4 / 3}
          stroke="#fff"
          fill="#8884d8"
          content={<CustomizedContent />}
          animationDuration={500}
        >
          <Tooltip 
             content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-3 border shadow-lg rounded text-sm z-50">
                      <p className="font-bold text-gray-900 mb-1">{data.name}</p>
                      <p className="text-gray-600">类型: {data.type === 'industry' ? '行业' : '概念'}</p>
                      <p className="text-gray-600">热度: <span className="font-medium text-orange-600">{(data.heat_pct * 100).toFixed(1)}%</span></p>
                      <p className="text-gray-600">强度: {data.value.toLocaleString()}</p>
                    </div>
                  );
                }
                return null;
             }}
          />
        </Treemap>
      </ResponsiveContainer>
    </div>
  );

  return (
    <>
      <div className="bg-white p-4 rounded-lg border shadow-sm h-96">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">全市场资金热力图</h3>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-500">面积=资金强度(C1) 颜色=热度(Heat)</span>
            <button
              type="button"
              onClick={() => setIsFullscreen(true)}
              className="text-xs px-2 py-1 rounded border bg-white hover:bg-gray-50"
            >
              放大
            </button>
          </div>
        </div>
        {chart}
      </div>

      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={() => setIsFullscreen(false)}>
          <div className="bg-white w-full h-full max-w-[1200px] max-h-[900px] rounded-lg border shadow-xl p-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">全市场资金热力图（放大）</h3>
              <button
                type="button"
                onClick={() => setIsFullscreen(false)}
                className="text-sm px-3 py-1.5 rounded bg-gray-900 text-white hover:bg-gray-800"
              >
                关闭
              </button>
            </div>
            <div style={{ width: '100%', height: 'calc(100% - 3rem)' }}>
              <ResponsiveContainer width="100%" height="100%">
                <Treemap
                  data={treeData}
                  dataKey="size"
                  ratio={4 / 3}
                  stroke="#fff"
                  fill="#8884d8"
                  content={<CustomizedContent />}
                  animationDuration={500}
                >
                  <Tooltip 
                     content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white p-3 border shadow-lg rounded text-sm z-50">
                              <p className="font-bold text-gray-900 mb-1">{data.name}</p>
                              <p className="text-gray-600">类型: {data.type === 'industry' ? '行业' : '概念'}</p>
                              <p className="text-gray-600">热度: <span className="font-medium text-orange-600">{(data.heat_pct * 100).toFixed(1)}%</span></p>
                              <p className="text-gray-600">强度: {data.value.toLocaleString()}</p>
                            </div>
                          );
                        }
                        return null;
                     }}
                  />
                </Treemap>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default MarketTreemap;
