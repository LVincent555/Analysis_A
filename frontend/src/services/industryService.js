/**
 * 行业分析相关API服务
 */
import apiClient from './api';

/**
 * 获取前1000名行业统计
 * @param {number} limit - 限制数量（1000/2000/3000/5000）
 * @param {string} date - 指定日期 (YYYYMMDD 格式)，不传则使用最新日期
 * @returns {Promise} - 行业统计数据
 */
export const getTop1000IndustryStats = async (limit = 1000, date = null) => {
  let url = `/api/industry/top1000?limit=${limit}`;
  if (date) {
    url += `&date=${date}`;
  }
  return await apiClient.get(url);
};

/**
 * 获取行业趋势数据
 * @param {string} date - 指定日期 (YYYYMMDD 格式)，不传则使用最新日期
 * @returns {Promise} - 行业趋势数据
 */
export const getIndustryTrend = async (date = null) => {
  let url = '/api/industry/trend';
  if (date) {
    url += `?date=${date}`;
  }
  return await apiClient.get(url);
};
