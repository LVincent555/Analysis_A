/**
 * 日期格式化工具函数
 */

/**
 * 格式化日期字符串，从YYYYMMDD转换为YYYY年MM月DD日
 * @param {string} dateStr - 日期字符串
 * @returns {string} - 格式化后的日期
 */
export const formatDate = (dateStr) => {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  const year = dateStr.slice(0, 4);
  const month = dateStr.slice(4, 6);
  const day = dateStr.slice(6, 8);
  return `${year}年${month}月${day}日`;
};

/**
 * 格式化日期为简短格式 MM/DD
 * @param {string} dateStr - 日期字符串
 * @returns {string} - 格式化后的日期
 */
export const formatShortDate = (dateStr) => {
  if (!dateStr || dateStr.length !== 8) return dateStr;
  const month = dateStr.slice(4, 6);
  const day = dateStr.slice(6, 8);
  return `${month}/${day}`;
};
