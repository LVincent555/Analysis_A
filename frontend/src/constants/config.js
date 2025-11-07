/**
 * 应用配置常量
 */

// API配置
// 生产环境：直接访问服务器后端
// 注意：如果需要本地开发，请临时改为 '' 并配置package.json的proxy
// API配置 - 生产环境：直接访问服务器后端
export const API_BASE_URL = 'http://60.205.251.109:8000';

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
