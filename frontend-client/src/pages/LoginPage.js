/**
 * 登录页面
 */
import React, { useState, useEffect } from 'react';
import { Lock, User, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';
import authService from '../services/authService';
import secureApi from '../services/secureApi';
import { API_BASE_URL, SERVERS, switchServer, getCurrentServer } from '../constants/config';

const LoginPage = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [appVersion, setAppVersion] = useState('0.4.0');
  const [isElectron, setIsElectron] = useState(false);
  const [serverStatus, setServerStatus] = useState('checking'); // checking, online, offline

  // 检测服务器状态
  const checkServerStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/`, { 
        method: 'GET',
        timeout: 5000 
      });
      setServerStatus(response.ok ? 'online' : 'offline');
    } catch (e) {
      setServerStatus('offline');
    }
  };

  // 获取应用版本和检测Electron环境
  useEffect(() => {
    // 检测是否Electron环境
    const electronAPI = window.electronAPI;
    if (electronAPI && electronAPI.isElectron === true) {
      setIsElectron(true);
      
      // 异步获取版本
      if (typeof electronAPI.getVersion === 'function') {
        electronAPI.getVersion()
          .then(version => setAppVersion(version || '0.4.0'))
          .catch(e => console.log('获取版本失败:', e));
      }
    }
    
    // 检测服务器状态
    checkServerStatus();
    
    // 定期检测服务器状态（每30秒）
    const interval = setInterval(checkServerStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!username.trim() || !password.trim()) {
      setError('请输入用户名和密码');
      return;
    }

    setLoading(true);

    try {
      const result = await authService.login(username, password);
      
      if (result.success) {
        // 初始化加密器
        const sessionKey = authService.getSessionKey();
        if (sessionKey) {
          secureApi.initCrypto(sessionKey);
        }
        
        // 通知父组件登录成功
        onLoginSuccess(result.user);
      } else {
        setError(result.message || '登录失败');
      }
    } catch (err) {
      setError(err.message || '网络错误，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo区域 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl mb-4 shadow-lg shadow-blue-500/30">
            <span className="text-4xl">📊</span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">A股分析系统</h1>
          <p className="text-slate-400">专业的股票数据分析平台</p>
        </div>

        {/* 登录表单 */}
        <div className="bg-slate-800/50 backdrop-blur-xl rounded-2xl p-8 shadow-2xl border border-slate-700/50">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 用户名 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                用户名
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="请输入用户名"
                  autoComplete="username"
                  disabled={loading}
                />
              </div>
            </div>

            {/* 密码 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                密码
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-slate-700/50 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="请输入密码"
                  autoComplete="current-password"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300 transition"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* 登录按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 disabled:from-blue-600/50 disabled:to-blue-700/50 text-white font-medium rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  登录中...
                </>
              ) : (
                '登 录'
              )}
            </button>
          </form>

          {/* 分隔线 */}
          <div className="mt-6 pt-6 border-t border-slate-700/50">
            <div className="flex items-center justify-between text-sm text-slate-500">
              <span>版本 {appVersion}</span>
              <span className="flex items-center gap-2">
                {isElectron && (
                  <span className="text-slate-400">桌面客户端</span>
                )}
                <span className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${
                    serverStatus === 'online' ? 'bg-green-500' : 
                    serverStatus === 'offline' ? 'bg-red-500' : 
                    'bg-yellow-500 animate-pulse'
                  }`}></span>
                  <span className={
                    serverStatus === 'online' ? 'text-green-400' : 
                    serverStatus === 'offline' ? 'text-red-400' : 
                    'text-yellow-400'
                  }>
                    {serverStatus === 'online' ? '服务器在线' : 
                     serverStatus === 'offline' ? '服务器离线' : 
                     '检测中...'}
                  </span>
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* 服务器切换 */}
        <div className="mt-4 flex items-center justify-center gap-2">
          <span className="text-slate-500 text-xs">服务器:</span>
          <button
            onClick={() => switchServer('LOCAL')}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              getCurrentServer() === 'LOCAL'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
          >
            本地
          </button>
          <button
            onClick={() => switchServer('REMOTE')}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              getCurrentServer() === 'REMOTE'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
          >
            远程
          </button>
        </div>

        {/* 底部提示 */}
        <p className="mt-4 text-center text-slate-500 text-sm">
          首次使用请联系管理员获取账号
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
