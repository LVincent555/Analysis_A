/**
 * 本地缓存服务
 * 在 Electron 环境中使用 SQLite 缓存，浏览器环境中使用 localStorage
 */

// 检查是否在 Electron 环境中
const isElectron = () => {
  return window.electronAPI && window.electronAPI.isElectron;
};

// 缓存 TTL 配置（分钟）
const CACHE_TTL = {
  // 静态数据，缓存时间长
  'stock_info': 60 * 24,      // 股票基础信息：24小时
  'industry_list': 60 * 24,   // 行业列表：24小时
  'dates': 60 * 4,            // 可用日期：4小时
  
  // 动态数据，缓存时间短
  'hotspots': 30,             // 热点数据：30分钟
  'industry_stats': 30,       // 行业统计：30分钟
  'stock_history': 60,        // 股票历史：1小时
  'rank_jump': 30,            // 排名跳变：30分钟
  'steady_rise': 30,          // 稳步上升：30分钟
  'needle_under_20': 30,      // 单针下二十：30分钟
  
  // 默认
  'default': 15               // 默认：15分钟
};

/**
 * 获取缓存 TTL
 */
function getCacheTTL(endpoint) {
  for (const [key, ttl] of Object.entries(CACHE_TTL)) {
    if (endpoint.includes(key)) {
      return ttl;
    }
  }
  return CACHE_TTL.default;
}

/**
 * 从缓存获取数据
 * @param {string} endpoint - API端点
 * @param {object} params - 请求参数
 * @returns {Promise<object|null>} 缓存数据或null
 */
async function getFromCache(endpoint, params = {}) {
  try {
    if (isElectron()) {
      // Electron 环境：使用 SQLite
      return await window.electronAPI.getCache(endpoint, params);
    } else {
      // 浏览器环境：使用 localStorage
      const cacheKey = `cache:${endpoint}:${JSON.stringify(params)}`;
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        const { data, expiresAt } = JSON.parse(cached);
        if (Date.now() < expiresAt) {
          return data;
        }
        // 过期则删除
        localStorage.removeItem(cacheKey);
      }
    }
  } catch (e) {
    console.warn('获取缓存失败:', e);
  }
  return null;
}

/**
 * 保存数据到缓存
 * @param {string} endpoint - API端点
 * @param {object} params - 请求参数
 * @param {object} data - 响应数据
 */
async function saveToCache(endpoint, params = {}, data) {
  try {
    const ttl = getCacheTTL(endpoint);
    
    if (isElectron()) {
      // Electron 环境：使用 SQLite
      await window.electronAPI.setCache(endpoint, params, data, ttl);
    } else {
      // 浏览器环境：使用 localStorage
      const cacheKey = `cache:${endpoint}:${JSON.stringify(params)}`;
      const cacheData = {
        data,
        expiresAt: Date.now() + ttl * 60 * 1000
      };
      localStorage.setItem(cacheKey, JSON.stringify(cacheData));
    }
  } catch (e) {
    console.warn('保存缓存失败:', e);
  }
}

/**
 * 清空所有缓存
 */
async function clearAllCache() {
  try {
    if (isElectron()) {
      await window.electronAPI.clearCache();
    } else {
      // 清除所有 cache: 开头的 localStorage
      const keys = Object.keys(localStorage).filter(k => k.startsWith('cache:'));
      keys.forEach(k => localStorage.removeItem(k));
    }
    return true;
  } catch (e) {
    console.warn('清空缓存失败:', e);
    return false;
  }
}

/**
 * 获取缓存统计
 */
async function getCacheStats() {
  try {
    if (isElectron()) {
      return await window.electronAPI.getCacheStats();
    } else {
      const keys = Object.keys(localStorage).filter(k => k.startsWith('cache:'));
      let totalSize = 0;
      keys.forEach(k => {
        totalSize += localStorage.getItem(k)?.length || 0;
      });
      return {
        total_items: keys.length,
        total_size: totalSize,
        oldest: null,
        newest: null
      };
    }
  } catch (e) {
    console.warn('获取缓存统计失败:', e);
    return null;
  }
}

/**
 * 检查是否在线
 */
function isOnline() {
  return navigator.onLine;
}

/**
 * 带缓存的 API 请求包装器
 * @param {Function} apiFn - API 请求函数
 * @param {string} endpoint - API端点
 * @param {object} params - 请求参数
 * @param {object} options - 选项
 */
async function withCache(apiFn, endpoint, params = {}, options = {}) {
  const { 
    forceRefresh = false,     // 强制刷新
    cacheOnly = false,        // 仅使用缓存（离线模式）
    ttl = null                // 自定义TTL
  } = options;
  
  // 尝试从缓存获取
  if (!forceRefresh) {
    const cached = await getFromCache(endpoint, params);
    if (cached) {
      console.log(`✓ 命中本地缓存: ${endpoint}`);
      return cached;
    }
  }
  
  // 如果仅使用缓存且无缓存，返回null
  if (cacheOnly) {
    console.warn(`离线模式，无缓存数据: ${endpoint}`);
    return null;
  }
  
  // 检查网络连接
  if (!isOnline()) {
    console.warn(`离线状态，无法请求: ${endpoint}`);
    return null;
  }
  
  // 发起请求
  try {
    const data = await apiFn();
    
    // 保存到缓存
    if (data) {
      if (ttl) {
        // 自定义TTL
        if (isElectron()) {
          await window.electronAPI.setCache(endpoint, params, data, ttl);
        } else {
          const cacheKey = `cache:${endpoint}:${JSON.stringify(params)}`;
          localStorage.setItem(cacheKey, JSON.stringify({
            data,
            expiresAt: Date.now() + ttl * 60 * 1000
          }));
        }
      } else {
        await saveToCache(endpoint, params, data);
      }
    }
    
    return data;
  } catch (e) {
    // 请求失败，尝试使用过期缓存
    const cached = await getFromCache(endpoint, params);
    if (cached) {
      console.warn(`请求失败，使用过期缓存: ${endpoint}`);
      return cached;
    }
    throw e;
  }
}

export {
  getFromCache,
  saveToCache,
  clearAllCache,
  getCacheStats,
  isOnline,
  withCache,
  isElectron
};

export default {
  getFromCache,
  saveToCache,
  clearAllCache,
  getCacheStats,
  isOnline,
  withCache,
  isElectron
};
