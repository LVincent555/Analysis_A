import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Calendar, Settings, Menu, Activity, Minus } from 'lucide-react';
import axios from 'axios';
import { formatDate } from '../../utils';
import { API_BASE_URL } from '../../constants';

const Header = ({ 
  openConfig, 
  availableDates, 
  selectedDate, 
  setSelectedDate,
  onMenuClick 
}) => {
  // 市场波动率数据
  const [volatilityData, setVolatilityData] = useState(null);
  
  // 获取市场波动率数据
  useEffect(() => {
    const fetchVolatility = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/market/volatility-summary?days=3`);
        setVolatilityData(response.data);
      } catch (err) {
        console.error('获取市场波动率失败:', err);
      }
    };
    
    fetchVolatility();
    // 每5分钟刷新一次
    const interval = setInterval(fetchVolatility, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);
  
  // 渲染趋势图标
  const renderTrendIcon = (trend) => {
    if (trend === 'up') {
      return <TrendingUp className="h-3 w-3 text-red-500" />;
    } else if (trend === 'down') {
      return <TrendingDown className="h-3 w-3 text-green-500" />;
    }
    return <Minus className="h-3 w-3 text-gray-400" />;
  };
  
  return (
    <header className="bg-white shadow-md z-10 relative sticky top-0">
      <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          {/* Logo区域 */}
          <div className="flex items-center space-x-3">
            {/* 移动端汉堡菜单 */}
            <button 
              onClick={onMenuClick}
              className="lg:hidden p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Menu className="h-6 w-6" />
            </button>

            <div className="bg-indigo-100 p-2 rounded-lg hidden sm:block">
              <TrendingUp className="h-6 w-6 text-indigo-600" />
            </div>
            {/* 桌面端显示标题 */}
            <div className="hidden sm:block">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight truncate">
                潘哥的底裤
              </h1>
              <p className="text-xs text-gray-500">
                一个兴趣使然的股票分析系统
              </p>
            </div>
            
            {/* 移动端显示三天波动率趋势 */}
            {volatilityData && volatilityData.days && volatilityData.days.length >= 3 && (
              <div className="sm:hidden flex items-center gap-1 bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 rounded-lg px-2 py-1">
                <Activity className="h-3.5 w-3.5 text-orange-500 flex-shrink-0" />
                <div className="flex items-center gap-0.5 text-[9px]">
                  <span className="text-orange-600 font-medium">{volatilityData.days[2].avg_volatility.toFixed(2)}%</span>
                  <span className="text-gray-400">→</span>
                  <span className="text-orange-600 font-medium">{volatilityData.days[1].avg_volatility.toFixed(2)}%</span>
                  <span className="text-gray-400">→</span>
                  <span className="text-orange-700 font-bold">{volatilityData.days[0].avg_volatility.toFixed(2)}%</span>
                  {renderTrendIcon(volatilityData.trend)}
                </div>
              </div>
            )}
          </div>

          {/* 右侧操作区 */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* 市场波动率指标 - 桌面端 */}
            {volatilityData && volatilityData.days && volatilityData.days.length >= 3 && (
              <div className="hidden md:flex items-center gap-2 bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-200 rounded-lg px-3 py-2">
                <Activity className="h-4 w-4 text-orange-500 flex-shrink-0" />
                <div className="flex flex-col">
                  <div className="flex items-center gap-1">
                    <span className="text-xs text-orange-600 font-medium">市场波动率</span>
                    {renderTrendIcon(volatilityData.trend)}
                  </div>
                  <div className="flex items-center gap-1 text-[10px]">
                    <span className="text-orange-400">前天</span>
                    <span className="font-medium text-orange-600">{volatilityData.days[2].avg_volatility.toFixed(2)}%</span>
                    <span className="text-gray-400">→</span>
                    <span className="text-orange-400">昨天</span>
                    <span className="font-medium text-orange-600">{volatilityData.days[1].avg_volatility.toFixed(2)}%</span>
                    <span className="text-gray-400">→</span>
                    <span className="text-orange-400">今天</span>
                    <span className="font-bold text-orange-700">{volatilityData.days[0].avg_volatility.toFixed(2)}%</span>
                  </div>
                </div>
              </div>
            )}
            
            {/* 信号配置按钮 */}
            <button
              onClick={openConfig}
              className="hidden sm:flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-all shadow-md hover:shadow-lg active:scale-95"
            >
              <Settings className="h-4 w-4" />
              <span className="font-medium text-sm">信号配置</span>
            </button>
            
            {/* 移动端仅显示图标 */}
            <button
              onClick={openConfig}
              className="sm:hidden p-2 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200"
            >
              <Settings className="h-5 w-5" />
            </button>
            
            {/* 日期选择器 */}
            {availableDates && selectedDate && (
              <div className="flex items-center space-x-2 bg-gray-50 rounded-lg px-3 py-2 border border-gray-200">
                <Calendar className="h-4 w-4 text-indigo-500" />
                <div className="relative">
                  <select
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="appearance-none bg-transparent text-sm font-semibold text-gray-900 focus:outline-none cursor-pointer pr-6"
                    style={{ minWidth: '100px' }}
                  >
                    {availableDates.dates.map((date) => (
                      <option key={date} value={date}>
                        {formatDate(date)}
                      </option>
                    ))}
                  </select>
                  {/* 自定义下拉箭头 */}
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center text-gray-500">
                    <svg className="h-3 w-3 fill-current" viewBox="0 0 20 20">
                      <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                    </svg>
                  </div>
                </div>
                
                {selectedDate === availableDates.latest_date && (
                  <span className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-100 text-green-800">
                    最新
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
