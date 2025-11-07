/**
 * 应用配置常量
 */

// API配置
// 生产环境：通过Nginx代理访问后端（使用相对路径）
// 本地开发：直接访问后端 'http://localhost:8000'
export const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000'  // 本地开发环境
  : '';  // 生产环境通过Nginx代理

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
