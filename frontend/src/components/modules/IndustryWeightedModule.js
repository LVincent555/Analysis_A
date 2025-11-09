/**
 * 行业热度分析模块 - 加权版本
 * 始终使用全部数据，通过k值和指标调节视角
 */
import React, { useState } from 'react';
import { BarChart3, TrendingUp, Calculator } from 'lucide-react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { API_BASE_URL } from '../../constants/config';
import { COLORS } from '../../constants/colors';
import { formatDate } from '../../utils';
import IndustryDetailDialog from '../dialogs/IndustryDetailDialog';

// k值的吸附点（黄金分割相关）
const K_SNAP_POINTS = [0.382, 0.618, 1.0, 1.618];
const K_MIN = 0.3;
const K_MAX = 1.8;

export default function IndustryWeightedModule({ selectedDate, onNavigate }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  
  // 用户控制的参数
  const [kValue, setKValue] = useState(1.0);  // 默认改为1.0（标准倒数）
  const [metric, setMetric] = useState('B1');
  
  // 对话框状态
  const [showDialog, setShowDialog] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState(null);
  
  // 打开板块详情对话框
  const handleIndustryClick = (industryName) => {
    setSelectedIndustry(industryName);
    setShowDialog(true);
  };
  
  // 跳转到完整分析页面
  const handleViewDetails = (industryName) => {
    if (onNavigate) {
      onNavigate(industryName);
    }
  };
  
  // k值滑块的吸附逻辑（增强吸附力）
  const handleKChange = (e) => {
    const value = parseFloat(e.target.value);
    
    // 查找最近的吸附点
    const closest = K_SNAP_POINTS.reduce((prev, curr) => 
      Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev
    );
    
    // 增强吸附范围到0.08，让吸附更明显
    if (Math.abs(value - closest) < 0.08) {
      setKValue(closest);
    } else {
      setKValue(value);
    }
  };
  
  // 开始计算
  const handleCalculate = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      params.append('k', kValue.toString());
      params.append('metric', metric);
      if (selectedDate) {
        params.append('date', selectedDate);
      }
      
      const url = `${API_BASE_URL}/api/industry/weighted?${params}`;
      const response = await axios.get(url);
      setData(response.data);
    } catch (err) {
      console.error('获取加权行业数据失败:', err);
      setError(err.response?.data?.detail || '获取数据失败');
    } finally {
      setLoading(false);
    }
  };
  
  // 获取当前指标的显示值
  const getMetricValue = (stat) => {
    switch (metric) {
      case 'B1': return stat.total_heat_rank.toFixed(2);
      case 'B2': return stat.avg_heat_rank.toFixed(4);
      case 'C1': return stat.total_score.toFixed(0);
      case 'C2': return stat.avg_score.toFixed(2);
      default: return '0';
    }
  };
  
  // 获取当前指标的名称
  const getMetricName = () => {
    switch (metric) {
      case 'B1': return '总热度';
      case 'B2': return '平均热度';
      case 'C1': return '总分数';
      case 'C2': return '平均分数';
      default: return '未知';
    }
  };
  
  return (
    <>
      {/* 控制面板 */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <div className="flex items-center space-x-2 mb-4">
          <TrendingUp className="h-5 w-5 text-indigo-600" />
          <h3 className="text-lg font-bold text-gray-900">行业热度分析（加权版本）</h3>
          <span className="text-sm text-gray-500">始终使用全部数据</span>
        </div>
        
        {/* 排序指标选择 */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-3">
            排序指标（选择你想要的排序维度）：
          </label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { 
                value: 'B1', 
                label: 'B1: 总热度', 
                desc: '看哪个行业精英多',
                detail: '排名加权累加，适合找当前最火的行业（追热点）'
              },
              { 
                value: 'B2', 
                label: 'B2: 平均热度', 
                desc: '看哪个行业最精锐',
                detail: '总热度/股票数，适合找小而精的行业（挖潜力）'
              },
              { 
                value: 'C1', 
                label: 'C1: 总分数', 
                desc: '看哪个行业总能量大',
                detail: '分数直接累加，适合看行业整体趋势和规模'
              },
              { 
                value: 'C2', 
                label: 'C2: 平均分数', 
                desc: '看哪个行业平均质量高',
                detail: '总分/股票数，适合选股时评估行业质量'
              }
            ].map(item => (
              <button
                key={item.value}
                onClick={() => setMetric(item.value)}
                className={`px-4 py-3 rounded-lg text-left transition-all ${
                  metric === item.value
                    ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white shadow-lg'
                    : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                <div className="font-bold text-sm mb-1">{item.label}</div>
                <div className={`text-xs mb-1 ${metric === item.value ? 'text-white/90' : 'text-gray-600'}`}>
                  {item.desc}
                </div>
                <div className={`text-xs ${metric === item.value ? 'text-white/75' : 'text-gray-500'}`}>
                  {item.detail}
                </div>
              </button>
            ))}
          </div>
        </div>
        
        {/* k值滑块（仅B方案显示） */}
        {(metric === 'B1' || metric === 'B2') && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              k值调节（聚焦程度）：
              <span className="ml-2 text-indigo-600 font-bold text-lg">{kValue.toFixed(3)}</span>
            </label>
            <div className="relative px-2">
              {/* 进度条背景 */}
              <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden mb-1">
                {/* 已选择的进度 */}
                <div 
                  className="absolute h-full bg-gradient-to-r from-indigo-400 to-indigo-600 transition-all duration-200"
                  style={{ width: `${((kValue - K_MIN) / (K_MAX - K_MIN)) * 100}%` }}
                />
                {/* 滑块 */}
                <input
                  type="range"
                  min={K_MIN}
                  max={K_MAX}
                  step="0.001"
                  value={kValue}
                  onChange={handleKChange}
                  className="absolute inset-0 w-full opacity-0 cursor-pointer"
                />
              </div>
              
              {/* 吸附点标记 - 精确定位 */}
              <div className="relative h-8 mt-1">
                {K_SNAP_POINTS.map(point => {
                  const position = ((point - K_MIN) / (K_MAX - K_MIN)) * 100;
                  const isActive = Math.abs(kValue - point) < 0.001;
                  return (
                    <div
                      key={point}
                      className="absolute transform -translate-x-1/2"
                      style={{ left: `${position}%` }}
                    >
                      {/* 刻度线 */}
                      <div className={`w-0.5 h-4 mx-auto mb-1 transition-all ${
                        isActive ? 'bg-indigo-600 h-5' : 'bg-gray-400'
                      }`} />
                      {/* 数值 */}
                      <div className={`text-xs whitespace-nowrap transition-all ${
                        isActive ? 'text-indigo-600 font-bold text-sm' : 'text-gray-500'
                      }`}>
                        {point}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="mt-3 p-3 bg-blue-50 rounded-lg">
              <div className="text-xs text-blue-800">
                <div className="font-semibold mb-1">💡 k值含义：</div>
                <div className="space-y-1 ml-3">
                  <div><strong>0.382</strong> - 广角镜头：看全局，第5000名也有分量</div>
                  <div><strong>0.618</strong> - 黄金分割：平衡模式，推荐日常使用</div>
                  <div><strong>1.0</strong> - 标准倒数：传统分析方法</div>
                  <div><strong>1.618</strong> - 长焦镜头：只看龙头，聚焦前100名</div>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* 开始计算按钮 */}
        <div className="space-y-2">
          <button
            onClick={handleCalculate}
            disabled={loading}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-4 rounded-lg font-bold text-lg hover:from-indigo-700 hover:to-purple-700 transition-all disabled:opacity-50 flex items-center justify-center space-x-2 shadow-lg"
          >
            <Calculator className={`h-6 w-6 ${loading ? 'animate-spin' : ''}`} />
            <span>{loading ? '正在计算全部数据...' : '🚀 开始计算'}</span>
          </button>
          <div className="text-xs text-center text-gray-500">
            点击后将遍历全部股票数据并计算4个维度指标（约需2-5秒）
          </div>
        </div>
      </div>
      
      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800 font-medium">错误: {error}</p>
        </div>
      )}
      
      {/* 数据展示 */}
      {!loading && data && data.stats && (
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-green-600" />
              <h3 className="text-lg font-bold text-gray-900">
                行业热度排名（{getMetricName()}）
              </h3>
              <span className="text-sm text-gray-500">(前30个行业)</span>
              <span className="text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded">
                💡 点击柱状图查看板块详情
              </span>
            </div>
            <div className="text-sm text-gray-600">
              共 {data.total_stocks} 只股票，{data.stats.length} 个行业 · {formatDate(data.date)}
              {(metric === 'B1' || metric === 'B2') && (
                <span className="ml-2 text-indigo-600 font-medium">k={data.k_value.toFixed(3)}</span>
              )}
            </div>
          </div>
          
          {/* 条形图 */}
          <ResponsiveContainer width="100%" height={800}>
            <BarChart data={data.stats.slice(0, 30)} layout="vertical" margin={{ left: 120, right: 50 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" label={{ value: getMetricName(), position: 'bottom' }} />
              <YAxis 
                type="category" 
                dataKey="industry" 
                width={110}
                tick={{ fontSize: 11 }}
                interval={0}
              />
              <Tooltip 
                formatter={(value) => [parseFloat(value).toFixed(2), getMetricName()]}
              />
              <Bar 
                dataKey={(stat) => parseFloat(getMetricValue(stat))}
                fill="#10b981" 
                label={{ position: 'right', fontSize: 11, fill: '#666', formatter: (val) => parseFloat(val).toFixed(2) }}
                onClick={(data) => {
                  if (data && data.industry) {
                    handleIndustryClick(data.industry);
                  }
                }}
                cursor="pointer"
              >
                {data.stats.slice(0, 30).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          
          {/* 详细数据表格 */}
          <div className="mt-6 overflow-x-auto">
            <h4 className="text-sm font-semibold text-gray-700 mb-3">详细数据（所有指标）</h4>
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">排名</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">行业</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">数量</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">B1:总热度</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">B2:平均热度</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">C1:总分</th>
                  <th className="px-4 py-2 text-right font-medium text-gray-500">C2:平均分</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.stats.slice(0, 50).map((stat, index) => (
                  <tr key={index} className={metric === 'B1' || metric === 'B2' || metric === 'C1' || metric === 'C2' ? (index < 10 ? 'bg-indigo-50' : '') : ''}>
                    <td className="px-4 py-2 text-gray-900">{index + 1}</td>
                    <td className="px-4 py-2 font-medium text-gray-900">{stat.industry}</td>
                    <td className="px-4 py-2 text-right text-gray-600">{stat.count}</td>
                    <td className="px-4 py-2 text-right font-medium text-blue-600">{stat.total_heat_rank.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right text-blue-600">{stat.avg_heat_rank.toFixed(4)}</td>
                    <td className="px-4 py-2 text-right font-medium text-green-600">{stat.total_score.toFixed(0)}</td>
                    <td className="px-4 py-2 text-right text-green-600">{stat.avg_score.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      {/* 初始提示 */}
      {!loading && !data && !error && (
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="text-center mb-8">
            <BarChart3 className="mx-auto h-20 w-20 text-indigo-500 mb-4" />
            <h3 className="text-2xl font-bold text-gray-900 mb-2">行业热度分析（加权版本）</h3>
            <p className="text-gray-600 text-lg">请选择排序指标和k值，然后点击"开始计算"</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-lg border border-indigo-200">
              <h4 className="font-bold text-indigo-900 mb-3 flex items-center">
                <span className="text-2xl mr-2">🎯</span>
                为什么需要加权？
              </h4>
              <p className="text-sm text-indigo-800 leading-relaxed">
                原版"前1000/2000名"是硬切分：第2000名权重=1，第2001名权重=0。
                这会造成数据失真。<br/><br/>
                加权版使用<strong>平滑衰减</strong>：所有股票都有权重，越靠前权重越高，
                避免了硬切分的问题。
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-6 rounded-lg border border-green-200">
              <h4 className="font-bold text-green-900 mb-3 flex items-center">
                <span className="text-2xl mr-2">📊</span>
                四个维度有什么用？
              </h4>
              <div className="text-sm text-green-800 space-y-2">
                <div><strong>B1/B2</strong>: 基于排名加权，看当前最火的行业</div>
                <div><strong>C1/C2</strong>: 基于分数加权，看真实质量</div>
                <div><strong>总/平均</strong>: 看规模 vs 看密度</div>
                <div className="pt-2 text-xs text-green-700">
                  四个维度结合，可以全方位评估行业热度
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
            <div className="flex">
              <div className="flex-shrink-0">
                <span className="text-2xl">💡</span>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-bold text-yellow-900 mb-1">使用建议</h4>
                <p className="text-sm text-yellow-800">
                  1️⃣ 追热点选<strong>B1总热度</strong>；2️⃣ 挖潜力选<strong>B2平均热度</strong>；
                  3️⃣ 看趋势选<strong>C1总分数</strong>；4️⃣ 选股选<strong>C2平均分数</strong>
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* 板块详情对话框 */}
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
