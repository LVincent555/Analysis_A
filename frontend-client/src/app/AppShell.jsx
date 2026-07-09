import React, { useCallback, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAppState } from '../hooks/useAppState';
import Header from '../components/layout/Header';
import Sidebar from '../components/layout/Sidebar';
import Drawer from '../components/layout/Drawer';
import IndustryDetailPage from '../pages/IndustryDetailPage';
import SignalConfigPanel from '../components/SignalConfigPanel';
import { useSignalConfig } from '../contexts/SignalConfigContext';
import AppRoutes from './router';
import {
  DEFAULT_MODULE_ID,
  getModuleById,
  getModuleByPathname
} from './moduleRegistry';

function ContentArea({ appState }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden min-h-[600px]">
        <AppRoutes appState={appState} />
      </div>
      <SignalConfigPanel />
    </div>
  );
}

export default function AppShell({ user, onLogout }) {
  const appState = useAppState();
  const { openConfig } = useSignalConfig();
  const location = useLocation();
  const navigate = useNavigate();
  const activeModule = getModuleByPathname(location.pathname)?.id || DEFAULT_MODULE_ID;

  const setActiveModule = useCallback((moduleId) => {
    const target = getModuleById(moduleId);
    navigate(target.path);
  }, [navigate]);

  const routedAppState = useMemo(() => ({
    ...appState,
    activeModule,
    setActiveModule
  }), [activeModule, appState, setActiveModule]);

  if (routedAppState.showDetailPage && routedAppState.selectedIndustry) {
    return (
      <IndustryDetailPage
        industryName={routedAppState.selectedIndustry}
        selectedDate={routedAppState.selectedDate}
        onBack={routedAppState.backToMain}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header
        openConfig={openConfig}
        availableDates={routedAppState.availableDates}
        selectedDate={routedAppState.selectedDate}
        setSelectedDate={routedAppState.setSelectedDate}
        onMenuClick={() => routedAppState.setIsDrawerOpen(true)}
        user={user}
        onLogout={onLogout}
      />

      <Drawer
        isOpen={routedAppState.isDrawerOpen}
        onClose={() => routedAppState.setIsDrawerOpen(false)}
      >
        <div className="p-4">
          <Sidebar {...routedAppState} user={user} />
        </div>
      </Drawer>

      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="hidden lg:block">
            <Sidebar {...routedAppState} user={user} />
          </div>

          <ContentArea appState={routedAppState} />
        </div>
      </main>
    </div>
  );
}
