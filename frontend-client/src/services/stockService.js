/**
 * 股票查询相关API服务
 */
import apiClient from './api';

/**
 * 查询个股历史数据
 * @param {string} stockCode - 股票代码
 * @param {string} date - 指定日期 (YYYYMMDD 格式)，不传则使用最新日期
 * @returns {Promise} - 股票历史数据
 */
export const queryStock = async (stockCode, date = null) => {
  let url = `/api/stock/${stockCode}`;
  if (date) {
    url += `?date=${date}`;
  }
  return await apiClient.get(url);
};
