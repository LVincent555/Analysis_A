/**
 * 应用配置常量
 */

// API配置
// 优先使用环境变量
// Linux服务器: 使用服务器IP (60.205.251.109:8000)
// Windows本地: 使用localhost (localhost:8000)
const getApiBaseUrl = () => {
  // 1. 优先使用环境变量
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  
  // 2. 根据访问域名判断
  const hostname = window.location.hostname;
  
  // 如果是IP访问（服务器）或者不是localhost，使用完整URL
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    return `${window.location.protocol}//${hostname}:8000`;
  }
  
  // 3. 本地开发使用localhost
  return 'http://localhost:8000';
};

export const API_BASE_URL = getApiBaseUrl();

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
