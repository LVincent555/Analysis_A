/**
 * Electron 主进程
 * A股分析系统桌面客户端
 */
const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const database = require('./database');

// 判断是否开发模式
const isDev = !app.isPackaged;

let mainWindow = null;
let autoUpdater = null;

// 尝试加载自动更新模块
try {
  autoUpdater = require('electron-updater').autoUpdater;
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;
} catch (e) {
  console.warn('electron-updater 未安装，自动更新功能不可用');
}

/**
 * 创建主窗口
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 768,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../public/icon.ico'),
    title: 'A股分析系统',
    show: false, // 先隐藏，加载完成后显示
    backgroundColor: '#0f172a' // 深色背景，避免白屏闪烁
  });

  // 加载页面
  if (isDev) {
    // 开发模式：加载本地开发服务器
    mainWindow.loadURL('http://localhost:3000');
    // 打开开发者工具
    mainWindow.webContents.openDevTools();
  } else {
    // 生产模式：加载打包后的文件
    mainWindow.loadFile(path.join(__dirname, '../build/index.html'));
  }

  // 页面加载完成后显示窗口
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // 窗口关闭事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 拦截新窗口打开，使用默认浏览器
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // 启动后检查更新（非开发模式）
  if (!isDev) {
    setTimeout(() => {
      checkForUpdates();
    }, 3000);
  }
}

/**
 * 检查更新
 */
function checkForUpdates() {
  if (!autoUpdater) {
    console.log('自动更新模块未加载');
    return;
  }
  
  console.log('检查更新...');
  autoUpdater.checkForUpdates().catch(err => {
    console.error('检查更新失败:', err);
  });
}

/**
 * 设置自动更新事件监听
 */
function setupAutoUpdater() {
  if (!autoUpdater) return;
  
  autoUpdater.on('checking-for-update', () => {
    console.log('正在检查更新...');
    sendToRenderer('update:checking');
  });
  
  autoUpdater.on('update-available', (info) => {
    console.log('发现新版本:', info.version);
    sendToRenderer('update:available', {
      version: info.version,
      releaseDate: info.releaseDate,
      releaseNotes: info.releaseNotes
    });
  });
  
  autoUpdater.on('update-not-available', () => {
    console.log('当前已是最新版本');
    sendToRenderer('update:not-available');
  });
  
  autoUpdater.on('download-progress', (progress) => {
    console.log(`下载进度: ${progress.percent.toFixed(1)}%`);
    sendToRenderer('update:progress', {
      percent: progress.percent,
      bytesPerSecond: progress.bytesPerSecond,
      transferred: progress.transferred,
      total: progress.total
    });
  });
  
  autoUpdater.on('update-downloaded', (info) => {
    console.log('更新下载完成:', info.version);
    sendToRenderer('update:downloaded', info.version);
  });
  
  autoUpdater.on('error', (err) => {
    console.error('更新错误:', err);
    sendToRenderer('update:error', err.message);
  });
}

/**
 * 发送消息到渲染进程
 */
function sendToRenderer(channel, data) {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send(channel, data);
  }
}

// 应用就绪
app.whenReady().then(async () => {
  // 初始化数据库（异步）
  const userDataPath = app.getPath('userData');
  await database.initDatabase(userDataPath);
  
  // 设置自动更新
  setupAutoUpdater();
  
  // 创建窗口
  createWindow();

  // macOS: 点击dock图标时重新创建窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
  
  // 定期清理过期缓存
  setInterval(() => {
    const cleared = database.clearExpiredCache();
    if (cleared > 0) {
      console.log(`清理了 ${cleared} 条过期缓存`);
    }
  }, 10 * 60 * 1000); // 每10分钟清理一次
});

// 所有窗口关闭时退出（Windows/Linux）
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// ==================== IPC 处理器 ====================

// 获取应用版本
ipcMain.handle('app:version', () => {
  return app.getVersion();
});

// 获取应用路径
ipcMain.handle('app:path', (event, name) => {
  return app.getPath(name);
});

// 检查是否开发模式
ipcMain.handle('app:isDev', () => {
  return isDev;
});

// 重启应用
ipcMain.handle('app:restart', () => {
  app.relaunch();
  app.exit(0);
});

// 退出应用
ipcMain.handle('app:quit', () => {
  app.quit();
});

// 最小化窗口
ipcMain.handle('window:minimize', () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});

// 最大化/还原窗口
ipcMain.handle('window:maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

// 关闭窗口
ipcMain.handle('window:close', () => {
  if (mainWindow) {
    mainWindow.close();
  }
});

// ==================== 数据库 IPC 处理器 ====================

// 查询缓存
ipcMain.handle('db:getCache', (event, endpoint, params) => {
  return database.getCache(endpoint, params);
});

// 设置缓存
ipcMain.handle('db:setCache', (event, endpoint, params, response, ttlMinutes) => {
  return database.setCache(endpoint, params, response, ttlMinutes);
});

// 获取缓存统计
ipcMain.handle('db:getCacheStats', () => {
  return database.getCacheStats();
});

// 清空缓存
ipcMain.handle('db:clearCache', () => {
  return database.clearAllCache();
});

// 保存股票信息
ipcMain.handle('db:saveStockInfo', (event, stocks) => {
  return database.saveStockInfo(stocks);
});

// 获取股票信息
ipcMain.handle('db:getStockInfo', (event, stockCode) => {
  return database.getStockInfo(stockCode);
});

// 搜索股票
ipcMain.handle('db:searchStocks', (event, keyword, limit) => {
  return database.searchStocks(keyword, limit);
});

// 获取同步状态
ipcMain.handle('db:getSyncStatus', (event, key) => {
  return database.getSyncStatus(key);
});

// 设置同步状态
ipcMain.handle('db:setSyncStatus', (event, key, value) => {
  return database.setSyncStatus(key, value);
});

// 检查数据库是否可用
ipcMain.handle('db:isAvailable', () => {
  return database.isAvailable();
});

// ==================== 更新 IPC 处理器 ====================

// 检查更新
ipcMain.handle('update:check', () => {
  if (autoUpdater) {
    return autoUpdater.checkForUpdates();
  }
  return Promise.resolve(null);
});

// 下载更新
ipcMain.handle('update:download', () => {
  if (autoUpdater) {
    return autoUpdater.downloadUpdate();
  }
  return Promise.resolve(null);
});

// 安装更新并重启
ipcMain.handle('update:install', () => {
  if (autoUpdater) {
    autoUpdater.quitAndInstall();
  }
});

// 应用退出时关闭数据库
app.on('before-quit', () => {
  database.closeDatabase();
});

console.log('Electron 主进程已启动');
