/**
 * 行业分析相关API服务
 */
import apiClient from './api';

/**
 * 获取前1000名行业统计
 * @returns {Promise} - 行业统计数据
 */
export const getTop1000IndustryStats = async () => {
  return await apiClient.get('/api/industry/top1000');
};

/**
 * 获取行业趋势数据
 * @returns {Promise} - 行业趋势数据
 */
export const getIndustryTrend = async () => {
  return await apiClient.get('/api/industry/trend');
};
