/**
 * 分析相关API服务
 */
import apiClient from './api';

/**
 * 获取可用日期列表
 * @returns {Promise} - 可用日期数据
 */
export const getAvailableDates = async () => {
  return await apiClient.get('/api/dates');
};

/**
 * 获取指定周期的分析结果
 * @param {number} period - 周期天数
 * @returns {Promise} - 分析结果
 */
export const analyzePeriod = async (period) => {
  return await apiClient.get(`/api/analyze/${period}`);
};
