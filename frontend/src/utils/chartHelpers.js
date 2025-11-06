/**
 * 图表辅助函数
 */

/**
 * 计算行业总数量
 * @param {Array} trendData - 趋势数据
 * @returns {Object} - 行业总数量映射
 */
export const calculateIndustryTotals = (trendData) => {
  const industryTotals = {};
  
  trendData.forEach(dateData => {
    Object.entries(dateData.industry_counts).forEach(([industry, count]) => {
      industryTotals[industry] = (industryTotals[industry] || 0) + count;
    });
  });
  
  return industryTotals;
};

/**
 * 获取排序后的前N个行业
 * @param {Object} industryTotals - 行业总数量
 * @param {number} topN - 取前N个
 * @returns {Array} - 行业列表
 */
export const getTopNIndustries = (industryTotals, topN) => {
  return Object.entries(industryTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([industry]) => industry);
};
