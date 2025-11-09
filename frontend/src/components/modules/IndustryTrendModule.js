/**
 * 行业趋势分析模块 - 完整版
 */
import React, { useState, useEffect } from 'react';
import { RefreshCw, BarChart3, TrendingUp as TrendingUpIcon } from 'lucide-react';
import axios from 'axios';
import { 
  LineChart, Line, AreaChart, Area, BarChart, Bar, 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Legend as RechartsLegend, Cell 
} from 'recharts';
import { API_BASE_URL, COLORS } from '../../constants';
import { formatDate } from '../../utils';
import IndustryDetailDialog from '../dialogs/IndustryDetailDialog';

export default function IndustryTrendModule({ topNLimit, selectedDate, onNavigate }) {
  const [industryTrend, setIndustryTrend] = useState(null);
  const [topNIndustry, setTopNIndustry] = useState(null);
  const [trendLoading, setTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState(null);
  const [trendChartType, setTrendChartType] = useState('line');
  const [trendTopN, setTrendTopN] = useState(10);
  const [hiddenIndustries, setHiddenIndustries] = useState([]);
  const [highlightedIndustry, setHighlightedIndustry] = useState(null);
  
  // Phase 5: 对话框状态
  const [showDialog, setShowDialog] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState(null);
  
  // 打开板块详情对话框
  const handleIndustryClick = (industryName) => {
    setSelectedIndustry(industryName);
    setShowDialog(true);
  };
  
  // 跳转到完整分析页面（Phase 6）
  const handleViewDetails = (industryName) => {
    if (onNavigate) {
      onNavigate(industryName);
    }
  };

  // 获取前N名行业数据
  useEffect(() => {
    const fetchTopNIndustry = async () => {
      try {
        // 尝试使用带limit参数的API，如果不支持则使用默认的top1000
        let url = `${API_BASE_URL}/api/industry/top1000?limit=${topNLimit}`;
        if (selectedDate) {
          url += `&date=${selectedDate}`;
        }
        const response = await axios.get(url);
        setTopNIndustry(response.data);
      } catch (err) {
        console.error('获取前N名行业数据失败:', err);
        // 如果API不支持limit参数，尝试使用默认API
        try {
          let fallbackUrl = `${API_BASE_URL}/api/industry/top1000?limit=1000`;
          if (selectedDate) {
            fallbackUrl += `&date=${selectedDate}`;
          }
          const fallbackResponse = await axios.get(fallbackUrl);
          setTopNIndustry(fallbackResponse.data);
        } catch (fallbackErr) {
          console.error('获取行业数据失败:', fallbackErr);
        }
      }
    };
    fetchTopNIndustry();
  }, [topNLimit, selectedDate]);

  // 获取行业趋势数据
  useEffect(() => {
    const fetchIndustryTrend = async () => {
      setTrendLoading(true);
      setTrendError(null);
      try {
        // 构建URL参数
        const params = new URLSearchParams();
        params.append('top_n', topNLimit.toString());
        if (selectedDate) {
          params.append('date', selectedDate);
        }
        
        const url = `${API_BASE_URL}/api/industry/trend?${params}`;
        const response = await axios.get(url);
        setIndustryTrend(response.data);
      } catch (err) {
        console.error('获取行业趋势数据失败:', err);
        setTrendError(err.response?.data?.detail || '获取行业趋势数据失败');
      } finally {
        setTrendLoading(false);
      }
    };

    fetchIndustryTrend();
  }, [selectedDate, topNLimit]); // 添加topNLimit依赖

  // 当切换图表类型或显示数量时，重置隐藏状态
  useEffect(() => {
    setHiddenIndustries([]);
    setHighlightedIndustry(null);
  }, [trendChartType, trendTopN]);

  return (
    <>
      {trendError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">错误: {trendError}</p>
        </div>
      )}

      {trendLoading && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center mb-6">
          <RefreshCw className="mx-auto h-12 w-12 text-green-600 animate-spin mb-4" />
          <p className="text-gray-600 text-lg">正在加载行业数据...</p>
        </div>
      )}

      {!trendLoading && topNIndustry && topNIndustry.stats && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-green-600" />
              <h3 className="text-lg font-bold text-gray-900">今日前{topNLimit}名行业分布</h3>
              <span className="text-sm text-gray-500">(前30个行业)</span>
              <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                💡 点击柱状图查看板块详情
              </span>
            </div>
            <div className="text-sm text-gray-600">
              共 {topNIndustry.total_stocks} 只股票，{topNIndustry.stats.length} 个行业 · {formatDate(topNIndustry.date)}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={800}>
            <BarChart data={topNIndustry.stats.slice(0, 30)} layout="vertical" margin={{ left: 120, right: 50 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" label={{ value: '股票数量', position: 'bottom' }} />
              <YAxis 
                type="category" 
                dataKey="industry" 
                width={110}
                tick={{ fontSize: 11 }}
                interval={0}
              />
              <Tooltip 
                formatter={(value, name, props) => [`${value}个 (${props.payload.percentage}%)`, '股票数量']} 
              />
              <Bar 
                dataKey="count" 
                fill="#10b981" 
                label={{ position: 'right', fontSize: 11, fill: '#666' }}
                onClick={(data) => {
                  if (data && data.industry) {
                    handleIndustryClick(data.industry);
                  }
                }}
                cursor="pointer"
              >
                {topNIndustry.stats.slice(0, 30).map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {!trendLoading && industryTrend && industryTrend.data && (() => {
        // 动态计算每个行业的总数量，按总数量排序，取前N个
        const industryTotals = {};
        industryTrend.data.forEach(dateData => {
          Object.entries(dateData.industry_counts).forEach(([industry, count]) => {
            industryTotals[industry] = (industryTotals[industry] || 0) + count;
          });
        });
        const topNIndustries = Object.entries(industryTotals)
          .sort((a, b) => b[1] - a[1])
          .slice(0, trendTopN)
          .map(([industry]) => industry);

        // 图例点击事件处理
        const handleLegendClick = (industry) => {
          setHiddenIndustries(prev => 
            prev.includes(industry) 
              ? prev.filter(ind => ind !== industry)
              : [...prev, industry]
          );
        };

        // 自定义图例渲染
        const renderLegend = (props) => {
          const { payload } = props;
          return (
            <div className="pt-4">
              <div className="flex flex-wrap justify-center gap-3" style={{ fontSize: '11px' }}>
                {payload.map((entry, index) => {
                  const isHidden = hiddenIndustries.includes(entry.value);
                  const isHighlighted = highlightedIndustry === entry.value;
                  
                  return (
                    <div
                      key={`legend-${index}`}
                      className="flex items-center select-none transition-all duration-200 px-2 py-1 rounded"
                      style={{ 
                        opacity: isHidden ? 0.4 : 1,
                        fontWeight: isHighlighted ? 'bold' : 'normal',
                        backgroundColor: isHighlighted ? '#f0f9ff' : 'transparent',
                        cursor: 'pointer',
                        border: isHighlighted ? '1px solid #0ea5e9' : '1px solid transparent'
                      }}
                      onClick={(e) => {
                        // 双击打开详情对话框
                        if (e.detail === 2) {
                          handleIndustryClick(entry.value);
                        } else {
                          // 单击切换显示/隐藏
                          handleLegendClick(entry.value);
                        }
                      }}
                      onMouseEnter={() => setHighlightedIndustry(entry.value)}
                      onMouseLeave={() => setHighlightedIndustry(null)}
                      title="单击切换显示/隐藏，双击查看详情"
                    >
                      <div
                        className="w-3 h-3 mr-1.5 rounded-sm flex-shrink-0"
                        style={{ 
                          backgroundColor: entry.color,
                          opacity: isHidden ? 0.3 : 1
                        }}
                      />
                      <span style={{ 
                        textDecoration: isHidden ? 'line-through' : 'none',
                        color: isHidden ? '#999' : '#333'
                      }}>
                        {entry.value}
                      </span>
                    </div>
                  );
                })}
              </div>
              {hiddenIndustries.length > 0 && (
                <div className="text-center mt-2">
                  <button
                    onClick={() => setHiddenIndustries([])}
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    显示全部 ({hiddenIndustries.length}个已隐藏)
                  </button>
                </div>
              )}
            </div>
          );
        };

        // 自定义Tooltip
        const CustomTooltip = ({ active, payload, label }) => {
          if (active && payload && payload.length) {
            const sortedPayload = [...payload].sort((a, b) => b.value - a.value);
            const total = sortedPayload.reduce((sum, entry) => sum + entry.value, 0);
            
            return (
              <div className="bg-white p-3 border border-gray-300 rounded shadow-lg" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                <p className="font-bold mb-2 text-gray-800">{formatDate(label)}</p>
                <p className="text-sm text-gray-600 mb-2">总计: {total}只</p>
                <div className="space-y-1">
                  {sortedPayload.map((entry, index) => (
                    <div key={index} className="flex items-center justify-between text-xs">
                      <div className="flex items-center">
                        <div 
                          className="w-3 h-3 rounded-sm mr-2" 
                          style={{ backgroundColor: entry.color }}
                        />
                        <span className="text-gray-700">{entry.name}</span>
                      </div>
                      <span className="font-semibold ml-4 text-gray-900">
                        {entry.value}只 ({((entry.value / total) * 100).toFixed(1)}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          }
          return null;
        };

        return (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <TrendingUpIcon className="h-5 w-5 text-green-600" />
                <h3 className="text-lg font-bold text-gray-900">行业趋势变化（前{topNLimit}名）</h3>
                <span className="text-sm text-gray-500">(前{trendTopN}个行业)</span>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">图表类型：</span>
                  <select
                    value={trendChartType}
                    onChange={(e) => setTrendChartType(e.target.value)}
                    className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="line">折线图</option>
                    <option value="area">堆叠面积图</option>
                  </select>
                </div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">显示数量：</span>
                  <select
                    value={trendTopN}
                    onChange={(e) => setTrendTopN(Number(e.target.value))}
                    className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value={5}>前5个</option>
                    <option value={10}>前10个</option>
                    <option value={15}>前15个</option>
                    <option value={20}>前20个</option>
                  </select>
                </div>
                <span className="text-sm text-gray-500">
                  (共 {industryTrend.industries.length} 个行业)
                </span>
              </div>
            </div>
            <p className="text-sm text-gray-600 mb-2">
              {trendChartType === 'line' 
                ? '展示主要行业在不同日期的股票数量变化趋势' 
                : '堆叠展示各行业数量变化，更直观地看出占比和总量'}
            </p>
            <p className="text-xs text-gray-500 mb-4">
              💡 提示：点击图例可切换显示/隐藏行业，鼠标悬停查看详细数据
            </p>
            <ResponsiveContainer width="100%" height={500}>
              {trendChartType === 'line' ? (
                <LineChart 
                  data={industryTrend.data} 
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  onMouseLeave={() => setHighlightedIndustry(null)}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                  />
                  <YAxis label={{ value: '股票数量', angle: -90, position: 'insideLeft' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <RechartsLegend content={renderLegend} />
                  {topNIndustries.map((industry, index) => {
                    const isHidden = hiddenIndustries.includes(industry);
                    const isHighlighted = highlightedIndustry === industry;
                    const isDimmed = highlightedIndustry && !isHighlighted;
                    
                    return (
                      <Line
                        key={industry}
                        type="monotone"
                        dataKey={(data) => data.industry_counts[industry] || 0}
                        name={industry}
                        stroke={COLORS[index % COLORS.length]}
                        strokeWidth={isHighlighted ? 4 : 2.5}
                        strokeOpacity={isHidden ? 0 : (isDimmed ? 0.2 : 1)}
                        dot={{ r: isHighlighted ? 5 : 4 }}
                        activeDot={{ r: 7 }}
                        hide={isHidden}
                      />
                    );
                  })}
                </LineChart>
              ) : (
                <AreaChart 
                  data={industryTrend.data} 
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  onMouseLeave={() => setHighlightedIndustry(null)}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tickFormatter={(value) => `${value.slice(4,6)}/${value.slice(6,8)}`}
                  />
                  <YAxis label={{ value: '股票数量', angle: -90, position: 'insideLeft' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <RechartsLegend content={renderLegend} />
                  {topNIndustries.map((industry, index) => {
                    const isHidden = hiddenIndustries.includes(industry);
                    const isHighlighted = highlightedIndustry === industry;
                    const isDimmed = highlightedIndustry && !isHighlighted;
                    
                    return (
                      <Area
                        key={industry}
                        type="monotone"
                        dataKey={(data) => data.industry_counts[industry] || 0}
                        name={industry}
                        stackId="1"
                        stroke={COLORS[index % COLORS.length]}
                        fill={COLORS[index % COLORS.length]}
                        fillOpacity={isHidden ? 0 : (isDimmed ? 0.15 : (isHighlighted ? 0.8 : 0.6))}
                        strokeOpacity={isHidden ? 0 : (isDimmed ? 0.2 : 1)}
                        strokeWidth={isHighlighted ? 2.5 : 1}
                        hide={isHidden}
                      />
                    );
                  })}
                </AreaChart>
              )}
            </ResponsiveContainer>
          </div>
        );
      })()}
      
      {/* Phase 5: 板块详情对话框 */}
      {showDialog && selectedIndustry && (
        <IndustryDetailDialog
          industryName={selectedIndustry}
          onClose={() => {
            setShowDialog(false);
            setSelectedIndustry(null);
          }}
          onViewDetails={handleViewDetails}
        />
      )}
    </>
  );
}
