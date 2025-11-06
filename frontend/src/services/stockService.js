/**
 * 股票查询相关API服务
 */
import apiClient from './api';

/**
 * 查询个股历史数据
 * @param {string} stockCode - 股票代码
 * @returns {Promise} - 股票历史数据
 */
export const queryStock = async (stockCode) => {
  return await apiClient.get(`/api/stock/${stockCode}`);
};
