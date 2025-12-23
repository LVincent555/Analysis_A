/**
 * 更新管理组件
 * 显示更新状态和控制更新
 * 登录后自动检查更新（带认证Token）
 */
import React, { useState, useEffect } from 'react';
import { Download, RefreshCw, CheckCircle, AlertCircle, X } from 'lucide-react';
import authService from '../../services/authService';

// 检查是否在 Electron 环境
const isElectron = window.electronAPI?.isElectron;

function UpdateManager() {
  const [updateStatus, setUpdateStatus] = useState('idle'); // idle, checking, available, downloading, downloaded, error
  const [updateInfo, setUpdateInfo] = useState(null);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [error, setError] = useState(null);
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    if (!isElectron) return;

    // 监听更新事件
    window.electronAPI.onUpdateAvailable?.((info) => {
      console.log('发现新版本:', info);
      setUpdateStatus('available');
      setUpdateInfo(info);
      setShowBanner(true);
    });

    window.electronAPI.onUpdateProgress?.((progress) => {
      setUpdateStatus('downloading');
      setDownloadProgress(progress.percent);
    });

    window.electronAPI.onUpdateDownloaded?.((version) => {
      setUpdateStatus('downloaded');
      setShowBanner(true);
    });

    window.electronAPI.onUpdateNotAvailable?.(() => {
      // 自动检查时不打印日志（避免重复）
      setUpdateStatus('idle');
    });

    window.electronAPI.onUpdateError?.((err) => {
      console.error('更新检查错误:', err);
      setUpdateStatus('error');
      setError(err);
    });

    // 登录后自动检查更新（带Token）
    const checkUpdateWithAuth = async () => {
      if (authService.isLoggedIn()) {
        const token = authService.getToken();
        console.log('登录后检查更新...');
        try {
          await window.electronAPI.checkForUpdates(token);
        } catch (e) {
          console.error('检查更新失败:', e);
        }
      }
    };

    // 延迟3秒后检查（确保登录完成）
    const timer = setTimeout(checkUpdateWithAuth, 3000);
    
    return () => clearTimeout(timer);
  }, []);

  // 检查更新（带Token）
  const handleCheckUpdate = async () => {
    if (!isElectron) {
      console.log('❌ 非Electron环境，跳过更新检查');
      return;
    }
    
    console.log('🔄 开始检查更新...');
    setUpdateStatus('checking');
    setError(null);
    
    try {
      const token = authService.getToken();
      console.log('📤 发送更新检查请求，Token:', token ? '已获取' : '未获取');
      const result = await window.electronAPI.checkForUpdates(token);
      console.log('📥 更新检查结果:', result);
      // 如果没有更新，5秒后恢复idle状态
      setTimeout(() => {
        if (updateStatus === 'checking') {
          console.log('⏰ 检查超时，恢复idle状态');
          setUpdateStatus('idle');
        }
      }, 5000);
    } catch (e) {
      console.error('❌ 更新检查失败:', e);
      setUpdateStatus('error');
      setError(e.message);
    }
  };

  // 下载更新
  const handleDownload = async () => {
    if (!isElectron) return;
    
    setUpdateStatus('downloading');
    setDownloadProgress(0);
    
    try {
      await window.electronAPI.downloadUpdate();
    } catch (e) {
      setUpdateStatus('error');
      setError(e.message);
    }
  };

  // 安装更新
  const handleInstall = () => {
    if (!isElectron) return;
    window.electronAPI.installUpdate();
  };

  // 关闭提示
  const handleClose = () => {
    setShowBanner(false);
  };

  // 非 Electron 环境不显示
  if (!isElectron) return null;

  // 不显示横幅时返回 null
  if (!showBanner) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* 有更新可用 */}
      {updateStatus === 'available' && (
        <div className="bg-indigo-600 text-white p-4 rounded-lg shadow-lg max-w-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Download className="w-5 h-5" />
              <span className="font-medium">发现新版本</span>
            </div>
            <button onClick={handleClose} className="text-white/80 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="mt-2 text-sm text-indigo-100">
            版本 {updateInfo?.version} 可用
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleDownload}
              className="px-3 py-1.5 bg-white text-indigo-600 rounded text-sm font-medium hover:bg-indigo-50"
            >
              立即下载
            </button>
            <button
              onClick={handleClose}
              className="px-3 py-1.5 bg-indigo-500 text-white rounded text-sm hover:bg-indigo-400"
            >
              稍后提醒
            </button>
          </div>
        </div>
      )}

      {/* 下载中 */}
      {updateStatus === 'downloading' && (
        <div className="bg-slate-800 text-white p-4 rounded-lg shadow-lg max-w-sm">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <span className="font-medium">正在下载更新</span>
          </div>
          <div className="mt-3">
            <div className="h-2 bg-slate-600 rounded-full overflow-hidden">
              <div 
                className="h-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${downloadProgress}%` }}
              />
            </div>
            <p className="mt-1 text-sm text-slate-400">
              {downloadProgress.toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      {/* 下载完成 */}
      {updateStatus === 'downloaded' && (
        <div className="bg-green-600 text-white p-4 rounded-lg shadow-lg max-w-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">更新已就绪</span>
            </div>
            <button onClick={handleClose} className="text-white/80 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="mt-2 text-sm text-green-100">
            重启应用以完成更新
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleInstall}
              className="px-3 py-1.5 bg-white text-green-600 rounded text-sm font-medium hover:bg-green-50"
            >
              立即重启
            </button>
            <button
              onClick={handleClose}
              className="px-3 py-1.5 bg-green-500 text-white rounded text-sm hover:bg-green-400"
            >
              稍后
            </button>
          </div>
        </div>
      )}

      {/* 错误 */}
      {updateStatus === 'error' && (
        <div className="bg-red-600 text-white p-4 rounded-lg shadow-lg max-w-sm">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">更新失败</span>
            </div>
            <button onClick={handleClose} className="text-white/80 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="mt-2 text-sm text-red-100">
            {error || '检查更新时出错'}
          </p>
          <button
            onClick={handleCheckUpdate}
            className="mt-3 px-3 py-1.5 bg-white text-red-600 rounded text-sm font-medium hover:bg-red-50"
          >
            重试
          </button>
        </div>
      )}

      {/* 更新按钮已移至 Header.js */}
    </div>
  );
}

export default UpdateManager;
