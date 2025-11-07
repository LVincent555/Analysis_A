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
 * @param {string} boardType - 板块类型
 * @param {number} topN - 前 N 个股票
 * @param {string} date - 指定日期 (YYYYMMDD 格式)，不传则使用最新日期
 * @returns {Promise} - 分析结果
 */
export const analyzePeriod = async (period, boardType = 'main', topN = 100, date = null) => {
  let url = `/api/analyze/${period}?board_type=${boardType}&top_n=${topN}`;
  if (date) {
    url += `&date=${date}`;
  }
  return await apiClient.get(url);
};

/**
 * 排名跳变分析
 * @param {number} threshold - 跳变阈值
 * @param {string} boardType - 板块类型
 * @param {string} date - 指定日期 (YYYYMMDD 格式)，不传则使用最新日期
 * @returns {Promise} - 分析结果
 */
export const analyzeRankJump = async (threshold, boardType = 'main', date = null) => {
  let url = `/api/rank-jump?jump_threshold=${threshold}&board_type=${boardType}`;
  if (date) {
    url += `&date=${date}`;
  }
  return await apiClient.get(url);
};

/**
 * 稳步上升分析
 * @param {number} period - 周期天数
 * @param {string} boardType - 板块类型
 * @param {number} minImprovement - 最小排名提升
 * @param {string} date - 指定日期 (YYYYMMDD 格式)，不传则使用最新日期
 * @returns {Promise} - 分析结果
 */
export const analyzeSteadyRise = async (period, boardType = 'main', minImprovement = 100, date = null) => {
  let url = `/api/steady-rise?period=${period}&board_type=${boardType}&min_rank_improvement=${minImprovement}`;
  if (date) {
    url += `&date=${date}`;
  }
  return await apiClient.get(url);
};
