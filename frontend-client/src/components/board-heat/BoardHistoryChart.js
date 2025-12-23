import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Area
} from 'recharts';

const BoardHistoryChart = ({ data, loading }) => {
  if (loading) {
    return <div className="h-80 bg-gray-100 rounded animate-pulse" />;
  }

  if (!data || data.length === 0) {
    return (
      <div className="h-80 flex items-center justify-center text-gray-400 border rounded bg-white">
        暂无历史数据
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-lg border shadow-sm">
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-900">板块热度趋势 (30天)</h3>
        <p className="text-xs text-gray-500">
          <span className="inline-block w-3 h-3 bg-orange-500 mr-1 rounded-sm"></span>热度(%)
          <span className="mx-2">|</span>
          <span className="inline-block w-3 h-3 bg-blue-300 mr-1 rounded-sm"></span>资金总量
        </p>
      </div>

      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorFunds" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#93c5fd" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#93c5fd" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
            <XAxis 
              dataKey="trade_date" 
              tick={{ fontSize: 10, fill: '#6b7280' }} 
              tickFormatter={(val) => val.slice(5)} // Show MM-DD
            />
            <YAxis 
              yAxisId="left" 
              orientation="left" 
              stroke="#f97316" 
              tick={{ fontSize: 10, fill: '#f97316' }}
              domain={[0, 1]}
              tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
            />
            <YAxis 
              yAxisId="right" 
              orientation="right" 
              stroke="#60a5fa" 
              tick={{ fontSize: 10, fill: '#60a5fa' }}
            />
            <Tooltip 
              contentStyle={{ borderRadius: '0.5rem', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              labelStyle={{ color: '#374151', fontWeight: 'bold', marginBottom: '0.25rem' }}
              formatter={(value, name) => {
                if (name === '热度') return [`${(value * 100).toFixed(1)}%`, name];
                if (name === '资金') return [value.toFixed(1), name];
                return [value, name];
              }}
            />
            <Legend verticalAlign="top" height={36}/>
            
            <Bar 
              yAxisId="right" 
              dataKey="funds" 
              name="资金" 
              fill="url(#colorFunds)" 
              barSize={20} 
              radius={[4, 4, 0, 0]} 
            />
            <Line 
              yAxisId="left" 
              type="monotone" 
              dataKey="heat_pct" 
              name="热度" 
              stroke="#f97316" 
              strokeWidth={3} 
              dot={false} 
              activeDot={{ r: 6 }} 
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default BoardHistoryChart;
