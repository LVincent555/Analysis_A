/**
 * 主应用组件 - 桌面客户端版
 * v0.7.0: 应用壳层、路由和模块注册迁移到 src/app
 */
import React, { useEffect, useState } from 'react';
import LoginPage from './pages/LoginPage';
import authService from './services/authService';
import secureApi from './services/secureApi';
import './services/api';
import { SignalConfigProvider } from './contexts/SignalConfigContext';
import SessionExpiredDialog from './components/common/SessionExpiredDialog';
import AppShell from './app/AppShell';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSessionExpired, setShowSessionExpired] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      if (authService.isLoggedIn()) {
        const sessionKey = authService.getSessionKey();
        if (sessionKey) {
          secureApi.initCrypto(sessionKey);
        }
        setUser(authService.getUser());
        setIsLoggedIn(true);
      }
      setLoading(false);
    };
    checkAuth();
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => {
      setShowSessionExpired(true);
    };

    window.addEventListener('session-expired', handleSessionExpired);
    return () => {
      window.removeEventListener('session-expired', handleSessionExpired);
    };
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setIsLoggedIn(true);
  };

  const handleLogout = async () => {
    await authService.logout();
    secureApi.reset();
    setUser(null);
    setIsLoggedIn(false);
  };

  const handleSessionExpiredConfirm = async () => {
    setShowSessionExpired(false);
    await authService.logout();
    secureApi.reset();
    setUser(null);
    setIsLoggedIn(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <SignalConfigProvider>
      <AppShell user={user} onLogout={handleLogout} />
      <SessionExpiredDialog
        isOpen={showSessionExpired}
        onConfirm={handleSessionExpiredConfirm}
      />
    </SignalConfigProvider>
  );
}

export default App;
