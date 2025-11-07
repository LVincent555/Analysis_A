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
 * @returns {Promise} - 分析结果
 */
export const analyzePeriod = async (period, boardType = 'main') => {
  return await apiClient.get(`/api/analyze/${period}?board_type=${boardType}`);
};

/**
 * 排名跳变分析
 * @param {number} period - 周期天数
 * @param {number} threshold - 跳变阈值
 * @param {string} boardType - 板块类型
 * @returns {Promise} - 分析结果
 */
export const analyzeRankJump = async (period, threshold, boardType = 'main') => {
  return await apiClient.get(`/api/rank-jump?jump_threshold=${threshold}&board_type=${boardType}`);
};

/**
 * 稳步上升分析
 * @param {number} period - 周期天数
 * @param {string} boardType - 板块类型
 * @param {number} minImprovement - 最小排名提升
 * @returns {Promise} - 分析结果
 */
export const analyzeSteadyRise = async (period, boardType = 'main', minImprovement = 100) => {
  return await apiClient.get(`/api/steady-rise?period=${period}&board_type=${boardType}&min_rank_improvement=${minImprovement}`);
};
