/**
 * 日期格式化工具函数
 */

/**
 * 格式化日期为中文格式
 * @param {string} dateStr - 格式为 'YYYYMMDD' 的日期字符串
 * @returns {string} - 格式化后的日期，如 '2025年01月06日'
 */
export const formatDate = (dateStr) => {
  if (!dateStr) return '';
  return `${dateStr.slice(0, 4)}年${dateStr.slice(4, 6)}月${dateStr.slice(6, 8)}日`;
};

/**
 * 格式化日期为短格式
 * @param {string} dateStr - 格式为 'YYYYMMDD' 的日期字符串
 * @returns {string} - 格式化后的日期，如 '01/06'
 */
export const formatShortDate = (dateStr) => {
  if (!dateStr) return '';
  const month = dateStr.slice(4, 6);
  const day = dateStr.slice(6, 8);
  return `${month}/${day}`;
};
