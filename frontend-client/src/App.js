/**
 * 主应用组件 - 桌面客户端版
 * 整合所有功能模块，提供统一的导航和布局
 * v0.4.0: 添加登录认证
 */
import React, { useState, useEffect } from 'react';
import { useAppState } from './hooks/useAppState';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import Drawer from './components/layout/Drawer';
import LoginPage from './pages/LoginPage';
import authService from './services/authService';
import secureApi from './services/secureApi';
import './services/api'; // 初始化axios拦截器

// 模块导入
import {
  HotSpotsModule,
  StockQueryModule,
  IndustryQueryModule,
  IndustryTrendModule,
  IndustryWeightedModule,
  SectorTrendModule,
  RankJumpModule,
  SteadyRiseModule,
  NeedleUnder20Module
} from './components/modules';
import SectorQueryModule from './components/modules/SectorQueryModule';
import StockRankingModule from './components/modules/StockRankingModule';
import IndustryDetailPage from './pages/IndustryDetailPage';
import AdminPanel from './pages/AdminPanel';
import UserLoginHistory from './pages/UserLoginHistory';
import { SignalConfigProvider, useSignalConfig } from './contexts/SignalConfigContext';
import SignalConfigPanel from './components/SignalConfigPanel';
import UpdateManager from './components/common/UpdateManager';
import SessionExpiredDialog from './components/common/SessionExpiredDialog';

// 将内容区域提取为组件，避免Props Drilling过深
const ContentArea = ({ appState, openConfig }) => {
  const { 
    activeModule, selectedDate, 
    hotSpotsState, queryState, sectorQueryState, rankJumpState, steadyRiseState, industryTrendState,
    navigateToDetail, refreshDates
  } = appState;

  // 渲染内容模块
  const renderContent = () => {
    switch (activeModule) {
      case 'hot-spots':
        return (
          <HotSpotsModule 
            selectedDate={selectedDate}
            boardType={hotSpotsState.boardType}
            selectedPeriod={hotSpotsState.selectedPeriod}
            topN={hotSpotsState.topN}
            refreshTrigger={hotSpotsState.refreshTrigger}
          />
        );
      
      case 'stock-query':
        return (
          <StockQueryModule 
            stockCode={queryState.stockCode}
            setStockCode={queryState.setStockCode}
            onSearch={queryState.handleStockQuery}
            queryTrigger={queryState.queryTrigger}
            onLoading={queryState.setStockLoading}
            onError={queryState.setStockError}
            selectedDate={selectedDate}
          />
        );

      case 'sector-query':
        return <SectorQueryModule selectedDate={selectedDate} />;

      case 'stock-ranking':
        return <StockRankingModule selectedDate={selectedDate} />;

      case 'industry-query':
        return (
          <IndustryQueryModule 
            onNavigate={navigateToDetail}
          />
        );

      case 'industry-trend':
        return (
          <IndustryTrendModule 
            selectedDate={selectedDate}
            topNLimit={industryTrendState.topNLimit}
            onNavigate={navigateToDetail}
          />
        );

      case 'industry-weighted':
        return (
          <IndustryWeightedModule 
            selectedDate={selectedDate}
            onNavigate={navigateToDetail}
          />
        );

      case 'sector-trend':
        return <SectorTrendModule selectedDate={selectedDate} />;

      case 'rank-jump':
        return (
          <RankJumpModule 
            selectedDate={selectedDate}
            jumpBoardType={rankJumpState.boardType}
            jumpThreshold={rankJumpState.threshold}
          />
        );

      case 'steady-rise':
        return (
          <SteadyRiseModule 
            selectedDate={selectedDate}
            riseBoardType={steadyRiseState.boardType}
            risePeriod={steadyRiseState.period}
            minRankImprovement={steadyRiseState.minImprovement}
          />
        );
        
      case 'needle-under-20':
        return (
          <NeedleUnder20Module selectedDate={selectedDate} />
        );

      case 'admin':
        return <AdminPanel onImportComplete={refreshDates} />;

      case 'user-login-history':
        return <UserLoginHistory />;

      default:
        return (
          <HotSpotsModule 
            selectedDate={selectedDate}
            boardType={hotSpotsState.boardType}
            period={hotSpotsState.selectedPeriod}
            topN={hotSpotsState.topN}
            loading={hotSpotsState.loading}
          />
        );
    }
  };

  return (
    <div className="flex-1 min-w-0">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[600px]">
        {renderContent()}
      </div>
      <SignalConfigPanel />
    </div>
  );
};

function AppContent({ user, onLogout }) {
  // 全局状态 Hook
  const appState = useAppState();
  const { openConfig } = useSignalConfig();

  // 详情页模式
  if (appState.showDetailPage && appState.selectedIndustry) {
    return (
      <IndustryDetailPage 
        industryName={appState.selectedIndustry} 
        selectedDate={appState.selectedDate} 
        onBack={appState.backToMain} 
      />
    );
  }
  
  return (
    <div className="min-h-screen bg-slate-50">
      {/* 顶部导航 */}
      <Header 
        openConfig={openConfig}
        availableDates={appState.availableDates}
        selectedDate={appState.selectedDate}
        setSelectedDate={appState.setSelectedDate}
        onMenuClick={() => appState.setIsDrawerOpen(true)}
        user={user}
        onLogout={onLogout}
      />

      {/* 移动端抽屉导航 */}
      <Drawer 
        isOpen={appState.isDrawerOpen} 
        onClose={() => appState.setIsDrawerOpen(false)}
      >
        <div className="p-4">
          <Sidebar {...appState} user={user} />
        </div>
      </Drawer>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* 左侧导航 (桌面端显示，移动端隐藏) */}
          <div className="hidden lg:block">
            <Sidebar {...appState} user={user} />
          </div>

          {/* 右侧功能区 */}
          <ContentArea appState={appState} openConfig={openConfig} />
        </div>
      </main>
    </div>
  );
}

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSessionExpired, setShowSessionExpired] = useState(false);

  // 检查登录状态
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

  // 监听会话过期事件
  useEffect(() => {
    const handleSessionExpired = () => {
      setShowSessionExpired(true);
    };
    
    window.addEventListener('session-expired', handleSessionExpired);
    return () => {
      window.removeEventListener('session-expired', handleSessionExpired);
    };
  }, []);

  // 登录成功处理
  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setIsLoggedIn(true);
  };

  // 登出处理
  const handleLogout = async () => {
    await authService.logout();
    secureApi.reset();
    setUser(null);
    setIsLoggedIn(false);
  };

  // 会话过期确认处理
  const handleSessionExpiredConfirm = async () => {
    setShowSessionExpired(false);
    await authService.logout();
    secureApi.reset();
    setUser(null);
    setIsLoggedIn(false);
  };

  // 加载中
  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">加载中...</div>
      </div>
    );
  }

  // 未登录显示登录页
  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  // 已登录显示主应用
  return (
    <SignalConfigProvider>
      <AppContent user={user} onLogout={handleLogout} />
      <UpdateManager />
      <SessionExpiredDialog 
        isOpen={showSessionExpired} 
        onConfirm={handleSessionExpiredConfirm} 
      />
    </SignalConfigProvider>
  );
}

export default App;
