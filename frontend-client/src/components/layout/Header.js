import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Calendar, Settings, Menu, Activity, Minus, User, LogOut, RefreshCw, Download } from 'lucide-react';
import apiClient from '../../services/api';
import { formatDate } from '../../utils';
import { API_BASE_URL } from '../../constants';
import authService from '../../services/authService';

// 检查是否在 Electron 环境
const isElectron = window.electronAPI?.isElectron;

const Header = ({ 
  openConfig, 
  availableDates, 
  selectedDate, 
  setSelectedDate,
  onMenuClick,
  user,
  onLogout
}) => {
  // 市场波动率数据
  const [volatilityData, setVolatilityData] = useState(null);
  
  // 更新状态
  const [updateStatus, setUpdateStatus] = useState('idle'); // idle, checking, available, downloading, downloaded
  const [updateInfo, setUpdateInfo] = useState(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  
  // 监听更新事件
  useEffect(() => {
    if (!isElectron) return;
    
    window.electronAPI.onUpdateAvailable?.((info) => {
      console.log('🎉 发现新版本:', info);
      setUpdateStatus('available');
      setUpdateInfo(info);
    });
    
    window.electronAPI.onUpdateNotAvailable?.(() => {
      console.log('✅ 当前已是最新版本');
      setUpdateStatus('idle');
      alert('当前已是最新版本');
    });
    
    window.electronAPI.onUpdateProgress?.((progress) => {
      console.log('📥 下载进度:', progress.percent?.toFixed(1) + '%');
      setDownloadProgress(progress.percent || 0);
    });
    
    window.electronAPI.onUpdateDownloaded?.((version) => {
      console.log('📦 更新下载完成:', version);
      setUpdateStatus('downloaded');
      setDownloadProgress(100);
    });
    
    window.electronAPI.onUpdateError?.((err) => {
      console.error('❌ 更新错误:', err);
      setUpdateStatus('idle');
      setDownloadProgress(0);
      alert('更新失败: ' + err);
    });
  }, []);
  
  // 检查更新
  const handleCheckUpdate = async () => {
    if (!isElectron) {
      alert('更新功能仅在桌面客户端可用');
      return;
    }
    
    console.log('🔄 手动检查更新...');
    setUpdateStatus('checking');
    
    // 15秒超时
    const timeoutId = setTimeout(() => {
      console.log('⏰ 更新检查超时');
      setUpdateStatus('idle');
      alert('检查更新超时，请稍后重试');
    }, 15000);
    
    try {
      const token = authService.getToken();
      console.log('Token:', token ? '已获取' : '未获取');
      const result = await window.electronAPI.checkForUpdates(token);
      console.log('📥 检查更新返回:', result);
      clearTimeout(timeoutId);
      
      // 如果返回结果但没有触发事件，手动处理
      if (result && result.updateInfo) {
        console.log('🎉 发现新版本:', result.updateInfo.version);
        setUpdateStatus('available');
        setUpdateInfo(result.updateInfo);
      }
    } catch (e) {
      clearTimeout(timeoutId);
      console.error('检查更新失败:', e);
      setUpdateStatus('idle');
      alert('检查更新失败: ' + e.message);
    }
  };
  
  // 下载更新
  const handleDownloadUpdate = async () => {
    if (!isElectron) return;
    setUpdateStatus('downloading');
    try {
      await window.electronAPI.downloadUpdate();
    } catch (e) {
      console.error('下载更新失败:', e);
      setUpdateStatus('available');
    }
  };
  
  // 安装更新
  const handleInstallUpdate = () => {
    if (!isElectron) return;
    window.electronAPI.installUpdate();
  };
  
  // 获取市场波动率数据
  useEffect(() => {
    const fetchVolatility = async () => {
      try {
        const response = await apiClient.get(`/api/market/volatility-summary?days=3`);
        setVolatilityData(response);
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

          {/* 用户信息区域 */}
          {user && (
            <div className="flex items-center gap-2 ml-4">
              {/* 更新状态按钮 */}
              <div className="flex items-center">
                {/* 检查更新 */}
                {updateStatus === 'idle' && (
                  <button
                    onClick={handleCheckUpdate}
                    className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all duration-200"
                    title="检查更新"
                  >
                    <RefreshCw className="w-4 h-4" />
                    <span className="hidden lg:inline">检查更新</span>
                  </button>
                )}
                
                {/* 检查中 */}
                {updateStatus === 'checking' && (
                  <div className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-500 bg-slate-100 rounded-xl">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span className="hidden lg:inline">检查中...</span>
                  </div>
                )}
                
                {/* 发现新版本 */}
                {updateStatus === 'available' && (
                  <button
                    onClick={handleDownloadUpdate}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600 rounded-xl shadow-lg shadow-green-500/25 transition-all duration-200"
                    title={`发现新版本 ${updateInfo?.version || ''}`}
                  >
                    <Download className="w-4 h-4" />
                    <span>更新 {updateInfo?.version || ''}</span>
                  </button>
                )}
                
                {/* 下载中 */}
                {updateStatus === 'downloading' && (
                  <div className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gradient-to-r from-blue-500 to-indigo-500 text-white rounded-xl shadow-lg">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>下载中 {downloadProgress.toFixed(0)}%</span>
                    <div className="w-16 h-1.5 bg-blue-300/50 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-white rounded-full transition-all duration-300"
                        style={{ width: `${downloadProgress}%` }}
                      />
                    </div>
                  </div>
                )}
                
                {/* 下载完成 */}
                {updateStatus === 'downloaded' && (
                  <button
                    onClick={handleInstallUpdate}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-gradient-to-r from-emerald-500 to-teal-500 text-white hover:from-emerald-600 hover:to-teal-600 rounded-xl shadow-lg shadow-emerald-500/25 transition-all duration-200"
                  >
                    <Download className="w-4 h-4" />
                    <span>立即安装</span>
                  </button>
                )}
              </div>

              {/* 分隔线 */}
              <div className="h-8 w-px bg-slate-200 mx-1"></div>

              {/* 用户信息卡片 */}
              <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 rounded-xl transition-colors">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-md">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <div className="hidden md:block">
                    <p className="text-sm font-semibold text-slate-700 leading-tight">
                      {user.username}
                    </p>
                    <p className="text-[10px] text-slate-400 leading-tight">
                      {user.role === 'admin' ? '管理员' : '用户'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={onLogout}
                  className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all duration-200"
                  title="退出登录"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;


