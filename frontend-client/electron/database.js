/**
 * SQLite 本地数据库模块
 * 使用 sql.js（纯JavaScript SQLite实现）
 */
const path = require('path');
const fs = require('fs');

let db = null;
let dbPath = null;
let initPromise = null;

/**
 * 初始化数据库
 * @param {string} userDataPath - 用户数据目录
 */
async function initDatabase(userDataPath) {
  if (initPromise) return initPromise;
  
  initPromise = (async () => {
    try {
      const initSqlJs = require('sql.js');
      const SQL = await initSqlJs();
      
      dbPath = path.join(userDataPath, 'cache.db');
      
      // 确保目录存在
      const dbDir = path.dirname(dbPath);
      if (!fs.existsSync(dbDir)) {
        fs.mkdirSync(dbDir, { recursive: true });
      }
      
      // 如果数据库文件存在，加载它
      if (fs.existsSync(dbPath)) {
        const buffer = fs.readFileSync(dbPath);
        db = new SQL.Database(buffer);
      } else {
        db = new SQL.Database();
      }
      
      // 创建表
      db.run(`
    -- API响应缓存表
    CREATE TABLE IF NOT EXISTS api_cache (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      cache_key TEXT UNIQUE NOT NULL,
      endpoint TEXT NOT NULL,
      params TEXT,
      response TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL,
      size_bytes INTEGER DEFAULT 0
    );
    
    -- 股票基础信息缓存
    CREATE TABLE IF NOT EXISTS stock_info (
      stock_code TEXT PRIMARY KEY,
      stock_name TEXT,
      industry TEXT,
      board_type INTEGER,
      updated_at INTEGER
    );
    
    -- 行业列表缓存
    CREATE TABLE IF NOT EXISTS industry_list (
      industry_name TEXT PRIMARY KEY,
      stock_count INTEGER,
      updated_at INTEGER
    );
    
    -- 同步状态表
    CREATE TABLE IF NOT EXISTS sync_status (
      key TEXT PRIMARY KEY,
      value TEXT,
      updated_at INTEGER
    );
    
    -- 设备信息（持久化本机指纹）
    CREATE TABLE IF NOT EXISTS device_info (
      key TEXT PRIMARY KEY,
      value TEXT
    );

    -- 创建索引
    CREATE INDEX IF NOT EXISTS idx_cache_key ON api_cache(cache_key);
    CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache(expires_at);
    CREATE INDEX IF NOT EXISTS idx_cache_endpoint ON api_cache(endpoint);
  `);

      // 保存数据库
      saveDatabase();
      
      console.log('SQLite 数据库初始化成功:', dbPath);
      return true;
    } catch (e) {
      console.warn('sql.js 初始化失败，离线缓存功能不可用:', e.message);
      return false;
    }
  })();
  
  return initPromise;
}

/**
 * 保存数据库到文件
 */
function saveDatabase() {
  if (!db || !dbPath) return;
  try {
    const data = db.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(dbPath, buffer);
  } catch (e) {
    console.error('保存数据库失败:', e);
  }
}

/**
 * 生成缓存键
 */
function generateCacheKey(endpoint, params) {
  const sortedParams = params ? JSON.stringify(params, Object.keys(params).sort()) : '';
  return `${endpoint}:${sortedParams}`;
}

/**
 * 获取缓存
 * @param {string} endpoint - API端点
 * @param {object} params - 请求参数
 * @returns {object|null} 缓存的响应数据
 */
function getCache(endpoint, params) {
  if (!db) return null;
  
  const cacheKey = generateCacheKey(endpoint, params);
  const now = Date.now();
  
  try {
    const stmt = db.prepare(`
      SELECT response FROM api_cache 
      WHERE cache_key = ? AND expires_at > ?
    `);
    stmt.bind([cacheKey, now]);
    
    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return JSON.parse(row.response);
    }
    stmt.free();
  } catch (e) {
    console.error('获取缓存失败:', e);
  }
  return null;
}

/**
 * 设置缓存
 * @param {string} endpoint - API端点
 * @param {object} params - 请求参数
 * @param {object} response - 响应数据
 * @param {number} ttlMinutes - 缓存有效期（分钟），默认30分钟
 */
function setCache(endpoint, params, response, ttlMinutes = 30) {
  if (!db) return false;
  
  const cacheKey = generateCacheKey(endpoint, params);
  const now = Date.now();
  const expiresAt = now + ttlMinutes * 60 * 1000;
  const responseStr = JSON.stringify(response);
  
  try {
    db.run(`
      INSERT OR REPLACE INTO api_cache 
      (cache_key, endpoint, params, response, created_at, expires_at, size_bytes)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `, [cacheKey, endpoint, JSON.stringify(params), responseStr, now, expiresAt, responseStr.length]);
    
    saveDatabase();
    return true;
  } catch (e) {
    console.error('设置缓存失败:', e);
    return false;
  }
}

/**
 * 清除过期缓存
 */
function clearExpiredCache() {
  if (!db) return 0;
  
  try {
    const now = Date.now();
    db.run('DELETE FROM api_cache WHERE expires_at < ?', [now]);
    const changes = db.getRowsModified();
    if (changes > 0) saveDatabase();
    return changes;
  } catch (e) {
    console.error('清除过期缓存失败:', e);
    return 0;
  }
}

/**
 * 清空所有缓存
 */
function clearAllCache() {
  if (!db) return false;
  
  try {
    db.run('DELETE FROM api_cache');
    db.run('DELETE FROM stock_info');
    db.run('DELETE FROM industry_list');
    saveDatabase();
    return true;
  } catch (e) {
    console.error('清空缓存失败:', e);
    return false;
  }
}

/**
 * 获取缓存统计
 */
function getCacheStats() {
  if (!db) return null;
  
  try {
    const statsStmt = db.prepare(`
      SELECT 
        COUNT(*) as total_items,
        COALESCE(SUM(size_bytes), 0) as total_size,
        MIN(created_at) as oldest,
        MAX(created_at) as newest
      FROM api_cache
    `);
    statsStmt.step();
    const stats = statsStmt.getAsObject();
    statsStmt.free();
    
    const byEndpoint = [];
    const endpointStmt = db.prepare(`
      SELECT endpoint, COUNT(*) as count
      FROM api_cache
      GROUP BY endpoint
    `);
    while (endpointStmt.step()) {
      byEndpoint.push(endpointStmt.getAsObject());
    }
    endpointStmt.free();
    
    return { ...stats, byEndpoint };
  } catch (e) {
    console.error('获取缓存统计失败:', e);
    return null;
  }
}

/**
 * 获取设备信息
 */
function getDeviceInfo(key) {
  if (!db) return null;
  try {
    const stmt = db.prepare('SELECT value FROM device_info WHERE key = ?');
    stmt.bind([key]);
    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return row.value;
    }
    stmt.free();
  } catch (e) {
    console.error('获取设备信息失败:', e);
  }
  return null;
}

/**
 * 保存设备信息
 */
function setDeviceInfo(key, value) {
  if (!db) return false;
  try {
    db.run(
      'INSERT OR REPLACE INTO device_info (key, value) VALUES (?, ?)',
      [key, value]
    );
    saveDatabase();
    return true;
  } catch (e) {
    console.error('保存设备信息失败:', e);
    return false;
  }
}

/**
 * 保存股票信息
 */
function saveStockInfo(stocks) {
  if (!db || !stocks || !stocks.length) return false;
  
  try {
    const now = Date.now();
    for (const stock of stocks) {
      db.run(`
        INSERT OR REPLACE INTO stock_info 
        (stock_code, stock_name, industry, board_type, updated_at)
        VALUES (?, ?, ?, ?, ?)
      `, [stock.stock_code, stock.stock_name, stock.industry, stock.board_type, now]);
    }
    saveDatabase();
    return true;
  } catch (e) {
    console.error('保存股票信息失败:', e);
    return false;
  }
}

/**
 * 获取股票信息
 */
function getStockInfo(stockCode) {
  if (!db) return null;
  
  try {
    const stmt = db.prepare('SELECT * FROM stock_info WHERE stock_code = ?');
    stmt.bind([stockCode]);
    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return row;
    }
    stmt.free();
  } catch (e) {
    console.error('获取股票信息失败:', e);
  }
  return null;
}

/**
 * 搜索股票
 */
function searchStocks(keyword, limit = 20) {
  if (!db) return [];
  
  try {
    const pattern = `%${keyword}%`;
    const stmt = db.prepare(`
      SELECT * FROM stock_info 
      WHERE stock_code LIKE ? OR stock_name LIKE ?
      LIMIT ?
    `);
    stmt.bind([pattern, pattern, limit]);
    
    const results = [];
    while (stmt.step()) {
      results.push(stmt.getAsObject());
    }
    stmt.free();
    return results;
  } catch (e) {
    console.error('搜索股票失败:', e);
    return [];
  }
}

/**
 * 获取同步状态
 */
function getSyncStatus(key) {
  if (!db) return null;
  
  try {
    const stmt = db.prepare('SELECT value FROM sync_status WHERE key = ?');
    stmt.bind([key]);
    if (stmt.step()) {
      const row = stmt.getAsObject();
      stmt.free();
      return JSON.parse(row.value);
    }
    stmt.free();
  } catch (e) {
    console.error('获取同步状态失败:', e);
  }
  return null;
}

/**
 * 设置同步状态
 */
function setSyncStatus(key, value) {
  if (!db) return false;
  
  try {
    db.run(`
      INSERT OR REPLACE INTO sync_status (key, value, updated_at)
      VALUES (?, ?, ?)
    `, [key, JSON.stringify(value), Date.now()]);
    saveDatabase();
    return true;
  } catch (e) {
    console.error('设置同步状态失败:', e);
    return false;
  }
}

/**
 * 关闭数据库
 */
function closeDatabase() {
  if (db) {
    saveDatabase();
    db.close();
    db = null;
  }
}

/**
 * 检查数据库是否可用
 */
function isAvailable() {
  return db !== null;
}

module.exports = {
  initDatabase,
  getCache,
  setCache,
  clearExpiredCache,
  clearAllCache,
  getCacheStats,
  getDeviceInfo,
  setDeviceInfo,
  saveStockInfo,
  getStockInfo,
  searchStocks,
  getSyncStatus,
  setSyncStatus,
  closeDatabase,
  isAvailable
};
