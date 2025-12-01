/**
 * Electron 预加载脚本
 * 安全地暴露API给渲染进程
 */
const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // ==================== 应用信息 ====================
  
  /** 获取应用版本 */
  getVersion: () => ipcRenderer.invoke('app:version'),
  
  /** 获取应用路径 */
  getPath: (name) => ipcRenderer.invoke('app:path', name),
  
  /** 是否开发模式 */
  isDev: () => ipcRenderer.invoke('app:isDev'),
  
  /** 重启应用 */
  restart: () => ipcRenderer.invoke('app:restart'),
  
  /** 退出应用 */
  quit: () => ipcRenderer.invoke('app:quit'),
  
  // ==================== 窗口控制 ====================
  
  /** 最小化窗口 */
  minimize: () => ipcRenderer.invoke('window:minimize'),
  
  /** 最大化/还原窗口 */
  maximize: () => ipcRenderer.invoke('window:maximize'),
  
  /** 关闭窗口 */
  close: () => ipcRenderer.invoke('window:close'),
  
  // ==================== 网络状态 ====================
  
  /** 是否在线 */
  isOnline: () => navigator.onLine,
  
  /** 监听网络状态变化 */
  onOnlineStatusChange: (callback) => {
    window.addEventListener('online', () => callback(true));
    window.addEventListener('offline', () => callback(false));
  },
  
  // ==================== 更新相关 ====================
  
  /** 检查更新 */
  checkForUpdates: () => ipcRenderer.invoke('update:check'),
  
  /** 下载更新 */
  downloadUpdate: () => ipcRenderer.invoke('update:download'),
  
  /** 安装更新 */
  installUpdate: () => ipcRenderer.invoke('update:install'),
  
  /** 监听更新事件 */
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update:available', (_, data) => callback(data));
  },
  
  onUpdateProgress: (callback) => {
    ipcRenderer.on('update:progress', (_, data) => callback(data));
  },
  
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update:downloaded', (_, version) => callback(version));
  },
  
  onUpdateNotAvailable: (callback) => {
    ipcRenderer.on('update:not-available', () => callback());
  },
  
  onUpdateChecking: (callback) => {
    ipcRenderer.on('update:checking', () => callback());
  },
  
  onUpdateError: (callback) => {
    ipcRenderer.on('update:error', (_, error) => callback(error));
  },
  
  // ==================== 本地缓存 ====================
  
  /** 获取API缓存 */
  getCache: (endpoint, params) => 
    ipcRenderer.invoke('db:getCache', endpoint, params),
  
  /** 设置API缓存 */
  setCache: (endpoint, params, response, ttlMinutes) => 
    ipcRenderer.invoke('db:setCache', endpoint, params, response, ttlMinutes),
  
  /** 获取缓存统计 */
  getCacheStats: () => 
    ipcRenderer.invoke('db:getCacheStats'),
  
  /** 清空缓存 */
  clearCache: () => 
    ipcRenderer.invoke('db:clearCache'),
  
  /** 保存股票信息 */
  saveStockInfo: (stocks) => 
    ipcRenderer.invoke('db:saveStockInfo', stocks),
  
  /** 获取股票信息 */
  getStockInfo: (stockCode) => 
    ipcRenderer.invoke('db:getStockInfo', stockCode),
  
  /** 搜索股票 */
  searchStocks: (keyword, limit) => 
    ipcRenderer.invoke('db:searchStocks', keyword, limit),
  
  /** 获取同步状态 */
  getSyncStatus: (key) => 
    ipcRenderer.invoke('db:getSyncStatus', key),
  
  /** 设置同步状态 */
  setSyncStatus: (key, value) => 
    ipcRenderer.invoke('db:setSyncStatus', key, value),
  
  /** 检查数据库是否可用 */
  isDBAvailable: () => 
    ipcRenderer.invoke('db:isAvailable'),
  
  // ==================== 平台信息 ====================
  
  /** 平台类型 */
  platform: process.platform,
  
  /** 是否Electron环境 */
  isElectron: true
});

console.log('Electron preload 脚本已加载');
