/**
 * 应用配置常量
 */

// 服务器配置
const SERVERS = {
  LOCAL: 'http://localhost:8000',      // 本地开发服务器
  REMOTE: 'http://60.205.251.109:8000' // 远程生产服务器
};

// 判断是否使用远程服务器
// 1. 生产环境打包后默认使用远程服务器
// 2. 开发环境默认使用本地服务器
// 3. 可通过 localStorage 手动切换
const getServerUrl = () => {
  // 检查 localStorage 是否有手动设置
  const savedServer = typeof localStorage !== 'undefined' 
    ? localStorage.getItem('API_SERVER') 
    : null;
  
  if (savedServer === 'LOCAL') return SERVERS.LOCAL;
  if (savedServer === 'REMOTE') return SERVERS.REMOTE;
  
  // 默认逻辑：开发环境用本地，生产环境用远程
  if (process.env.NODE_ENV === 'development') {
    return SERVERS.LOCAL;
  }
  return SERVERS.REMOTE;
};

// API基础地址
export const API_BASE_URL = getServerUrl();

// 导出服务器配置，方便切换
export { SERVERS };

// 切换服务器的工具函数
export const switchServer = (serverType) => {
  if (serverType === 'LOCAL' || serverType === 'REMOTE') {
    localStorage.setItem('API_SERVER', serverType);
    window.location.reload(); // 刷新页面应用新配置
  }
};

// 获取当前服务器类型
export const getCurrentServer = () => {
  const savedServer = localStorage.getItem('API_SERVER');
  if (savedServer) return savedServer;
  return process.env.NODE_ENV === 'development' ? 'LOCAL' : 'REMOTE';
};

// 分析周期选项
export const PERIODS = [2, 3, 5, 7, 14];

// 分页配置
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
export const DEFAULT_PAGE_SIZE = 20;

// 行业趋势显示数量选项
export const TREND_TOP_N_OPTIONS = [5, 10, 15, 20];
export const DEFAULT_TREND_TOP_N = 10;

// 图表类型
export const CHART_TYPES = {
  LINE: 'line',
  AREA: 'area'
};
