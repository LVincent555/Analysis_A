/**
 * 板块趋势分析模块
 * 整合原板块分析功能，新增趋势图和排名变化统计
 */
import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, TrendingDown, Minus, BarChart3, Activity, ChevronDown, ChevronUp, Search } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../../constants/config';
import { COLORS } from '../../constants/colors';
import { formatDate } from '../../utils';

export default function SectorTrendModule({ selectedDate }) {
  // 状态
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 数据
  const [trendData, setTrendData] = useState(null);
  const [rankChanges, setRankChanges] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [sectorHistoryData, setSectorHistoryData] = useState({});
  
  // 控制参数
  const [topN, setTopN] = useState(30); // 固定获取前30个板块数据
  const [days, setDays] = useState(7);
  const [sortBy, setSortBy] = useState('current_rank');
  
  // 图表控制
  const [chartType, setChartType] = useState('line'); // 'line', 'area', 'bar'
  const [chartTopN, setChartTopN] = useState(10); // 图表显示前N个（独立控制）
  const [hiddenSectors, setHiddenSectors] = useState([]); // 隐藏的板块
  const [expandedSector, setExpandedSector] = useState(null); // 展开的板块详情
  
  // 分页和搜索控制
  const [pageSize, setPageSize] = useState(50); // 每页显示数量
  const [currentPage, setCurrentPage] = useState(1); // 当前页码
  const [searchQuery, setSearchQuery] = useState(''); // 搜索关键词
  
  // 获取趋势数据
  const fetchTrendData = async () => {
    try {
      const params = new URLSearchParams();
      params.append('limit', topN);
      params.append('days', days);
      if (selectedDate) params.append('date', selectedDate);
      
      const url = `${API_BASE_URL}/api/sectors/trend?${params}`;
      const response = await axios.get(url);
      setTrendData(response.data);
    } catch (err) {
      console.error('获取趋势数据失败:', err);
      throw err;
    }
  };
  
  // 获取排名变化
  const fetchRankChanges = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedDate) params.append('date', selectedDate);
      params.append('compare_days', 1);
      
      const url = `${API_BASE_URL}/api/sectors/rank-changes?${params}`;
      const response = await axios.get(url);
      setRankChanges(response.data);
    } catch (err) {
      console.error('获取排名变化失败:', err);
      throw err;
    }
  };
  
  // 获取单个板块的历史数据
  const fetchSectorHistory = async (sectorName) => {
    try {
      const params = new URLSearchParams();
      params.append('days', 30); // 获取30天历史数据
      if (selectedDate) params.append('date', selectedDate);
      
      const url = `${API_BASE_URL}/api/sectors/${encodeURIComponent(sectorName)}?${params}`;
      const response = await axios.get(url);
      setSectorHistoryData(prev => ({
        ...prev,
        [sectorName]: response.data
      }));
      setExpandedSector(sectorName);
    } catch (err) {
      console.error('获取板块历史数据失败:', err);
      alert(`获取${sectorName}历史数据失败: ${err.response?.data?.detail || err.message}`);
    }
  };
  
  // 切换图例显示/隐藏
  const toggleSectorVisibility = (sectorName) => {
    setHiddenSectors(prev => {
      if (prev.includes(sectorName)) {
        return prev.filter(s => s !== sectorName);
      } else {
        return [...prev, sectorName];
      }
    });
  };
  
  // 加载数据
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([
        fetchTrendData(),
        fetchRankChanges()
      ]);
    } catch (err) {
      setError(err.response?.data?.detail || '获取数据失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 监听参数变化
  useEffect(() => {
    loadData();
    // 重新加载数据时清空隐藏列表
    setHiddenSectors([]);
  }, [selectedDate, topN, days]);
  
  // 监听图表显示数量变化，清空隐藏列表
  useEffect(() => {
    setHiddenSectors([]);
  }, [chartTopN]);
  
  // 准备图表数据（只显示前chartTopN个）
  const chartData = trendData ? trendData.dates.map((date, index) => {
    const point = { date: formatDate(date) };
    trendData.sectors.slice(0, chartTopN).forEach(sector => {
      point[sector.name] = sector.ranks[index];
    });
    return point;
  }) : [];
  
  // 可见的板块列表（用于图表渲染）
  const visibleSectors = trendData ? trendData.sectors.slice(0, chartTopN).filter(
    sector => !hiddenSectors.includes(sector.name)
  ) : [];
  
  // 排序后的板块列表
  const sortedSectors = rankChanges ? [...rankChanges.sectors].sort((a, b) => {
    if (sortBy === 'current_rank') return a.current_rank - b.current_rank;
    if (sortBy === 'rank_change') return (b.rank_change || 0) - (a.rank_change || 0);
    if (sortBy === 'total_score') return (b.total_score || 0) - (a.total_score || 0);
    if (sortBy === 'price_change') return (b.price_change || 0) - (a.price_change || 0);
    return 0;
  }) : [];
  
  // 搜索过滤（保持原始排名）
  const filteredSectors = sortedSectors.filter(sector => 
    sector.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  // 分页计算
  const totalPages = Math.ceil(filteredSectors.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedSectors = filteredSectors.slice(startIndex, endIndex);
  
  // 重置页码当搜索或分页大小改变时
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, pageSize]);
  
  // 渲染排名变化图标
  const renderRankChange = (change, isNew) => {
    if (isNew) {
      return <span className="text-blue-600 font-bold">🆕 新上榜</span>;
    }
    if (!change) {
      return <span className="text-gray-500 flex items-center"><Minus className="h-4 w-4 mr-1" />持平</span>;
    }
    if (change > 0) {
      return <span className="text-red-600 flex items-center"><TrendingUp className="h-4 w-4 mr-1" />↑ {change}</span>;
    }
    return <span className="text-green-600 flex items-center"><TrendingDown className="h-4 w-4 mr-1" />↓ {Math.abs(change)}</span>;
  };
  
  return (
    <>
      {/* 控制面板 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center space-x-2 mb-4">
          <BarChart3 className="h-5 w-5 text-indigo-600" />
          <h3 className="text-lg font-bold text-gray-900">板块趋势分析</h3>
          <span className="text-sm text-gray-500">直接查询板块排名数据</span>
        </div>
        
        <div className="flex items-center space-x-4 flex-wrap">
          {/* 显示天数 */}
          <div>
            <label className="text-xs text-gray-600 mr-2">时间范围:</label>
            {[7, 14, 30].map(d => (
              <button
                key={d}
                onClick={() => {
                  console.log('点击时间范围按钮:', d, '当前days:', days);
                  setDays(d);
                }}
                className={`px-3 py-1 rounded text-sm mr-2 transition-colors ${
                  days === d
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {d}天
              </button>
            ))}
            <span className="text-xs text-gray-500 ml-2">(当前: {days}天)</span>
          </div>
          
          {/* 刷新按钮 */}
          <button
            onClick={loadData}
            disabled={loading}
            className="px-4 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
          >
            {loading ? '加载中...' : '刷新数据'}
          </button>
        </div>
      </div>
      
      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">错误: {error}</p>
        </div>
      )}
      
      {/* 排名变化概览 */}
      {rankChanges && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-indigo-600" />
              <h4 className="text-lg font-bold text-gray-900">排名变化概览</h4>
              <span className="text-sm text-gray-600">
                ({formatDate(rankChanges.compare_date)} vs {formatDate(rankChanges.date)})
              </span>
            </div>
            <div className="text-xs text-indigo-600 bg-white px-3 py-1 rounded-full">
              📊 昨日 vs 今日板块排名变化统计
            </div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg p-4 text-center hover:shadow-md transition-shadow cursor-help" title="今天新进入排名，昨天不在榜单的板块">
              <div className="text-2xl font-bold text-blue-600">{rankChanges.statistics.new_entries}</div>
              <div className="text-sm text-gray-600 font-medium">🆕 新上榜</div>
              <div className="text-xs text-gray-400 mt-1">昨天不在榜</div>
            </div>
            <div className="bg-white rounded-lg p-4 text-center hover:shadow-md transition-shadow cursor-help" title="今天排名比昨天更靠前的板块（热度上升）">
              <div className="text-2xl font-bold text-red-600">{rankChanges.statistics.rank_up}</div>
              <div className="text-sm text-gray-600 font-medium">↑ 排名上升</div>
              <div className="text-xs text-gray-400 mt-1">热度提高</div>
            </div>
            <div className="bg-white rounded-lg p-4 text-center hover:shadow-md transition-shadow cursor-help" title="今天排名比昨天更靠后的板块（热度下降）">
              <div className="text-2xl font-bold text-green-600">{rankChanges.statistics.rank_down}</div>
              <div className="text-sm text-gray-600 font-medium">↓ 排名下降</div>
              <div className="text-xs text-gray-400 mt-1">热度降低</div>
            </div>
            <div className="bg-white rounded-lg p-4 text-center hover:shadow-md transition-shadow cursor-help" title="排名完全一样的板块">
              <div className="text-2xl font-bold text-gray-600">{rankChanges.statistics.rank_same}</div>
              <div className="text-sm text-gray-600 font-medium">➖ 排名不变</div>
              <div className="text-xs text-gray-400 mt-1">保持稳定</div>
            </div>
          </div>
        </div>
      )}
      
      {/* 趋势变化图 */}
      {trendData && chartData.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="text-lg font-bold text-gray-900">
                板块排名趋势（前{chartTopN}个板块，最近{days}天）
              </h4>
              <div className="text-xs text-gray-600 mt-1">
                💡 提示：Y轴数值越小排名越高，点击图例可显示/隐藏板块
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* 图表类型选择 */}
              <div>
                <label className="text-xs text-gray-600 mr-2">图表类型:</label>
                <select
                  value={chartType}
                  onChange={(e) => setChartType(e.target.value)}
                  className="px-3 py-1 border border-gray-300 rounded text-sm"
                >
                  <option value="line">折线图</option>
                  <option value="area">面积图</option>
                  <option value="bar">柱状图</option>
                </select>
              </div>
              
              {/* 显示数量选择 */}
              <div>
                <label className="text-xs text-gray-600 mr-2">显示数量:</label>
                <select
                  value={chartTopN}
                  onChange={(e) => {
                    const newValue = Number(e.target.value);
                    console.log('切换图表显示数量:', newValue, '当前chartTopN:', chartTopN);
                    setChartTopN(newValue);
                  }}
                  className="px-3 py-1 border border-gray-300 rounded text-sm font-medium"
                >
                  <option value="5">前5个</option>
                  <option value="10">前10个</option>
                  <option value="15">前15个</option>
                  <option value="20">前20个</option>
                  <option value="30">前30个</option>
                </select>
              </div>
            </div>
          </div>
          
          {/* 自定义可交互图例 */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <div className="text-xs text-gray-600 mb-2">
              💡 点击图例可显示/隐藏板块 | 
              当前显示: {visibleSectors.length}/{chartTopN}个板块
            </div>
            <div className="flex flex-wrap gap-2">
              {trendData.sectors.slice(0, chartTopN).map((sector, index) => {
                const isHidden = hiddenSectors.includes(sector.name);
                return (
                  <button
                    key={sector.name}
                    onClick={() => {
                      toggleSectorVisibility(sector.name);
                      console.log('切换板块显示:', sector.name, '隐藏状态:', !isHidden);
                    }}
                    className={`px-3 py-1 rounded text-sm font-medium transition-all cursor-pointer hover:shadow-md ${
                      isHidden
                        ? 'bg-gray-200 text-gray-400 line-through opacity-50'
                        : 'bg-white text-gray-700 border-2 shadow-sm'
                    }`}
                    style={{
                      borderColor: isHidden ? '#d1d5db' : COLORS[index % COLORS.length],
                      color: isHidden ? '#9ca3af' : COLORS[index % COLORS.length]
                    }}
                    title={isHidden ? `点击显示 ${sector.name}` : `点击隐藏 ${sector.name}`}
                  >
                    {isHidden && '👁️‍🗨️ '}
                    {sector.name}
                    {!isHidden && ' ✓'}
                  </button>
                );
              })}
            </div>
          </div>
          
          <ResponsiveContainer width="100%" height={400}>
            {chartType === 'line' && (
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  reversed
                  label={{ value: '排名', angle: -90, position: 'insideLeft' }}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                {visibleSectors.map((sector, index) => (
                  <Line
                    key={sector.name}
                    type="monotone"
                    dataKey={sector.name}
                    stroke={COLORS[trendData.sectors.findIndex(s => s.name === sector.name) % COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            )}
            
            {chartType === 'area' && (
              <AreaChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  reversed
                  label={{ value: '排名', angle: -90, position: 'insideLeft' }}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                {visibleSectors.map((sector, index) => (
                  <Area
                    key={sector.name}
                    type="monotone"
                    dataKey={sector.name}
                    stroke={COLORS[trendData.sectors.findIndex(s => s.name === sector.name) % COLORS.length]}
                    fill={COLORS[trendData.sectors.findIndex(s => s.name === sector.name) % COLORS.length]}
                    fillOpacity={0.3}
                    strokeWidth={2}
                  />
                ))}
              </AreaChart>
            )}
            
            {chartType === 'bar' && (
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis 
                  reversed
                  label={{ value: '排名', angle: -90, position: 'insideLeft' }}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                {visibleSectors.map((sector, index) => (
                  <Bar
                    key={sector.name}
                    dataKey={sector.name}
                    fill={COLORS[trendData.sectors.findIndex(s => s.name === sector.name) % COLORS.length]}
                  />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
      
      {/* 板块详细列表 */}
      {rankChanges && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-bold text-gray-900">
              板块详细列表（共{rankChanges.sectors.length}个板块）
            </h4>
            
            {/* 搜索框和分页控制 */}
            <div className="flex items-center space-x-4">
              {/* 搜索框 */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索板块名称..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  style={{ width: '200px' }}
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                )}
              </div>
              
              {/* 每页显示数量 */}
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-600">每页:</label>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value={20}>20条</option>
                  <option value={30}>30条</option>
                  <option value={50}>50条</option>
                  <option value={100}>100条</option>
                  <option value={rankChanges.sectors.length}>全部</option>
                </select>
              </div>
            </div>
          </div>
          
          {/* 排序按钮和搜索结果提示 */}
          <div className="flex items-center justify-between mb-4">
            {/* 排序按钮 */}
            <div className="flex space-x-2">
              <button
                onClick={() => setSortBy('current_rank')}
                className={`px-3 py-1 rounded text-sm ${
                  sortBy === 'current_rank'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                按排名
              </button>
              <button
                onClick={() => setSortBy('rank_change')}
                className={`px-3 py-1 rounded text-sm ${
                  sortBy === 'rank_change'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                按变化
              </button>
              <button
                onClick={() => setSortBy('price_change')}
                className={`px-3 py-1 rounded text-sm ${
                  sortBy === 'price_change'
                    ? 'bg-indigo-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                按涨跌幅
              </button>
            </div>
            
            {/* 搜索结果提示 */}
            {searchQuery && (
              <div className="text-sm text-gray-600">
                找到 <span className="font-bold text-indigo-600">{filteredSectors.length}</span> 个匹配结果
                {filteredSectors.length > 0 && (
                  <span className="ml-2 text-gray-500">
                    （显示第 {startIndex + 1}-{Math.min(endIndex, filteredSectors.length)} 个）
                  </span>
                )}
              </div>
            )}
          </div>
          
          {/* 表格 */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b-2 border-gray-200">
                  <th className="py-3 px-4 text-left font-semibold text-gray-700">排名</th>
                  <th className="py-3 px-4 text-left font-semibold text-gray-700">板块名称</th>
                  <th className="py-3 px-4 text-right font-semibold text-gray-700">总分</th>
                  <th className="py-3 px-4 text-right font-semibold text-gray-700">涨跌幅</th>
                  <th className="py-3 px-4 text-right font-semibold text-gray-700">放量天数</th>
                  <th className="py-3 px-4 text-center font-semibold text-gray-700">排名变化</th>
                  <th className="py-3 px-4 text-center font-semibold text-gray-700">操作</th>
                </tr>
              </thead>
              <tbody>
                {paginatedSectors.map((sector, index) => (
                  <React.Fragment key={index}>
                    <tr 
                      className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                    >
                      <td className="py-3 px-4 font-medium text-gray-900">
                        {sector.current_rank}
                      </td>
                      <td className="py-3 px-4 font-medium text-indigo-600">
                        {sector.name}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-700">
                        {sector.total_score ? sector.total_score.toFixed(2) : '-'}
                      </td>
                      <td className={`py-3 px-4 text-right font-medium ${
                        sector.price_change > 0 ? 'text-red-600' : 
                        sector.price_change < 0 ? 'text-green-600' : 
                        'text-gray-700'
                      }`}>
                        {sector.price_change !== null ? `${sector.price_change > 0 ? '+' : ''}${sector.price_change.toFixed(2)}%` : '-'}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-700">
                        {sector.volume_days !== null ? sector.volume_days.toFixed(0) : '-'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {renderRankChange(sector.rank_change, sector.is_new)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => {
                            if (expandedSector === sector.name) {
                              setExpandedSector(null);
                            } else {
                              fetchSectorHistory(sector.name);
                            }
                          }}
                          className="px-3 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors inline-flex items-center"
                        >
                          {expandedSector === sector.name ? (
                            <>
                              <ChevronUp className="h-3 w-3 mr-1" />
                              收起
                            </>
                          ) : (
                            <>
                              <ChevronDown className="h-3 w-3 mr-1" />
                              详情
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                    
                    {/* 展开的板块详情 */}
                    {expandedSector === sector.name && sectorHistoryData[sector.name] && (
                      <tr>
                        <td colSpan="7" className="bg-gray-50 p-6">
                          <div className="bg-white rounded-lg p-4 shadow-inner">
                            <h5 className="text-md font-bold text-gray-900 mb-4">
                              {sector.name} - 历史数据（最近30天）
                            </h5>
                            
                            {/* 历史数据图表 */}
                            <ResponsiveContainer width="100%" height={300}>
                              <LineChart data={sectorHistoryData[sector.name].history}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis 
                                  dataKey="date"
                                  tick={{ fontSize: 11 }}
                                  angle={-45}
                                  textAnchor="end"
                                  height={60}
                                />
                                <YAxis 
                                  yAxisId="left"
                                  label={{ value: '排名', angle: -90, position: 'insideLeft' }}
                                  reversed
                                  tick={{ fontSize: 11 }}
                                />
                                <YAxis 
                                  yAxisId="right"
                                  orientation="right"
                                  label={{ value: '总分', angle: 90, position: 'insideRight' }}
                                  tick={{ fontSize: 11 }}
                                />
                                <Tooltip />
                                <Legend />
                                <Line
                                  yAxisId="left"
                                  type="monotone"
                                  dataKey="rank"
                                  stroke="#8884d8"
                                  strokeWidth={2}
                                  name="排名"
                                  dot={{ r: 3 }}
                                />
                                <Line
                                  yAxisId="right"
                                  type="monotone"
                                  dataKey="total_score"
                                  stroke="#82ca9d"
                                  strokeWidth={2}
                                  name="总分"
                                  dot={{ r: 3 }}
                                />
                              </LineChart>
                            </ResponsiveContainer>
                            
                            {/* 历史数据表格 */}
                            <div className="mt-4 max-h-64 overflow-y-auto">
                              <table className="w-full text-xs">
                                <thead className="sticky top-0 bg-gray-100">
                                  <tr>
                                    <th className="py-2 px-3 text-left">日期</th>
                                    <th className="py-2 px-3 text-center">排名</th>
                                    <th className="py-2 px-3 text-right">总分</th>
                                    <th className="py-2 px-3 text-right">涨跌幅</th>
                                    <th className="py-2 px-3 text-right">放量天数</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {sectorHistoryData[sector.name].history.map((day, idx) => (
                                    <tr key={idx} className="border-b border-gray-100">
                                      <td className="py-2 px-3">{day.date}</td>
                                      <td className="py-2 px-3 text-center font-medium">{day.rank}</td>
                                      <td className="py-2 px-3 text-right">{day.total_score?.toFixed(2) || '-'}</td>
                                      <td className={`py-2 px-3 text-right ${
                                        day.price_change > 0 ? 'text-red-600' :
                                        day.price_change < 0 ? 'text-green-600' :
                                        'text-gray-700'
                                      }`}>
                                        {day.price_change !== null ? `${day.price_change > 0 ? '+' : ''}${day.price_change.toFixed(2)}%` : '-'}
                                      </td>
                                      <td className="py-2 px-3 text-right">{day.volume_days?.toFixed(0) || '-'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* 分页控制 */}
          {filteredSectors.length > 0 && totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-gray-600">
                显示第 <span className="font-medium">{startIndex + 1}</span> - 
                <span className="font-medium">{Math.min(endIndex, filteredSectors.length)}</span> 条，
                共 <span className="font-medium">{filteredSectors.length}</span> 条
              </div>
              
              <div className="flex items-center space-x-2">
                {/* 上一页 */}
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  上一页
                </button>
                
                {/* 页码 */}
                <div className="flex items-center space-x-1">
                  {/* 第一页 */}
                  {currentPage > 3 && (
                    <>
                      <button
                        onClick={() => setCurrentPage(1)}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        1
                      </button>
                      {currentPage > 4 && <span className="px-2 text-gray-500">...</span>}
                    </>
                  )}
                  
                  {/* 当前页附近的页码 */}
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(page => Math.abs(page - currentPage) <= 2)
                    .map(page => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`px-3 py-2 border rounded-lg text-sm font-medium transition-colors ${
                          page === currentPage
                            ? 'bg-indigo-600 text-white border-indigo-600'
                            : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {page}
                      </button>
                    ))
                  }
                  
                  {/* 最后一页 */}
                  {currentPage < totalPages - 2 && (
                    <>
                      {currentPage < totalPages - 3 && <span className="px-2 text-gray-500">...</span>}
                      <button
                        onClick={() => setCurrentPage(totalPages)}
                        className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        {totalPages}
                      </button>
                    </>
                  )}
                </div>
                
                {/* 下一页 */}
                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  下一页
                </button>
                
                {/* 跳转到指定页 */}
                <div className="flex items-center space-x-2 ml-4">
                  <span className="text-sm text-gray-600">跳转到</span>
                  <input
                    type="number"
                    min="1"
                    max={totalPages}
                    value={currentPage}
                    onChange={(e) => {
                      const page = parseInt(e.target.value);
                      if (page >= 1 && page <= totalPages) {
                        setCurrentPage(page);
                      }
                    }}
                    className="w-16 px-2 py-1 border border-gray-300 rounded text-sm text-center focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <span className="text-sm text-gray-600">页</span>
                </div>
              </div>
            </div>
          )}
          
          {/* 无搜索结果提示 */}
          {searchQuery && filteredSectors.length === 0 && (
            <div className="mt-6 text-center py-12">
              <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">未找到匹配的板块</p>
              <p className="text-gray-400 text-sm mt-2">请尝试其他关键词</p>
            </div>
          )}
        </div>
      )}
      
      {/* 加载状态 */}
      {loading && !trendData && (
        <div className="bg-white rounded-lg shadow-md p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      )}
    </>
  );
}
