/**
 * 主应用组件 - 模块化重构版
 * 整合所有功能模块，提供统一的导航和布局
 */
import React from 'react';
import { useAppState } from './hooks/useAppState';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import Drawer from './components/layout/Drawer';

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
import IndustryDetailPage from './pages/IndustryDetailPage';
import { SignalConfigProvider, useSignalConfig } from './contexts/SignalConfigContext';
import SignalConfigPanel from './components/SignalConfigPanel';

// 将内容区域提取为组件，避免Props Drilling过深
const ContentArea = ({ appState, openConfig }) => {
  const { 
    activeModule, selectedDate, 
    hotSpotsState, queryState, rankJumpState, steadyRiseState, industryTrendState,
    navigateToDetail
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

function AppContent() {
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
      />

      {/* 移动端抽屉导航 */}
      <Drawer 
        isOpen={appState.isDrawerOpen} 
        onClose={() => appState.setIsDrawerOpen(false)}
      >
        <div className="p-4">
          <Sidebar {...appState} />
        </div>
      </Drawer>

      {/* 主内容区 */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* 左侧导航 (桌面端显示，移动端隐藏) */}
          <div className="hidden lg:block">
            <Sidebar {...appState} />
          </div>

          {/* 右侧功能区 */}
          <ContentArea appState={appState} openConfig={openConfig} />
        </div>
      </main>
    </div>
  );
}

function App() {
  return (
    <SignalConfigProvider>
      <AppContent />
    </SignalConfigProvider>
  );
}

export default App;
