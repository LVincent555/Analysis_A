import React from 'react';
import {
  BarChart2,
  Search,
  TrendingUp,
  TrendingDown,
  Shield,
  Upload,
  UserCog,
  Monitor,
  FileText,
  Lock,
  Settings,
  Database
} from 'lucide-react';

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
} from '../components/modules';
import SectorQueryModule from '../components/modules/SectorQueryModule';
import StockRankingModule from '../components/modules/StockRankingModule';
import AdminPanel from '../pages/AdminPanel';
import UserLoginHistory from '../pages/UserLoginHistory';
import UserManagement from '../pages/UserManagement';
import SessionManagement from '../pages/SessionManagement';
import OperationLogs from '../pages/OperationLogs';
import SystemConfig from '../pages/SystemConfig';
import UserSecuritySettings from '../pages/UserSecuritySettings';
import RoleManagement from '../pages/RoleManagement';
import ExtBoardSync from '../pages/ExtBoardSync';
import ExtBoardHeat from '../pages/ExtBoardHeat';
import BoardAnalysisPage from '../pages/BoardAnalysisPage';

export const DEFAULT_MODULE_ID = 'hot-spots';

export const QUERY_MODULE_IDS = ['stock-query', 'industry-query', 'sector-query', 'stock-ranking'];
export const INDUSTRY_MODULE_IDS = ['industry-trend', 'industry-weighted', 'sector-trend', 'ext-board-heat'];
export const ADMIN_MODULE_IDS = [
  'admin',
  'ext-board-sync',
  'user-management',
  'role-management',
  'session-management',
  'operation-logs',
  'user-security-settings',
  'system-config'
];

function BoardHeatRoute({ appState }) {
  const [analysisBoard, setAnalysisBoard] = React.useState(null);

  if (analysisBoard) {
    return (
      <BoardAnalysisPage
        board={analysisBoard}
        selectedDate={appState.selectedDate}
        onBack={() => setAnalysisBoard(null)}
      />
    );
  }

  return (
    <ExtBoardHeat
      selectedDate={appState.selectedDate}
      onNavigateToAnalysis={(board) => setAnalysisBoard(board)}
    />
  );
}

export const modules = [
  {
    id: 'hot-spots',
    path: '/',
    aliases: ['/hot-spots'],
    label: '最新热点',
    icon: BarChart2,
    group: 'analysis',
    colorClass: 'indigo',
    render: ({ appState }) => (
      <HotSpotsModule
        selectedDate={appState.selectedDate}
        boardType={appState.hotSpotsState.boardType}
        selectedPeriod={appState.hotSpotsState.selectedPeriod}
        topN={appState.hotSpotsState.topN}
        refreshTrigger={appState.hotSpotsState.refreshTrigger}
      />
    )
  },
  {
    id: 'stock-query',
    path: '/query/stock',
    label: '股票查询',
    icon: Search,
    group: 'query',
    render: ({ appState }) => (
      <StockQueryModule
        stockCode={appState.queryState.stockCode}
        setStockCode={appState.queryState.setStockCode}
        onSearch={appState.queryState.handleStockQuery}
        queryTrigger={appState.queryState.queryTrigger}
        onLoading={appState.queryState.setStockLoading}
        onError={appState.queryState.setStockError}
        selectedDate={appState.selectedDate}
      />
    )
  },
  {
    id: 'industry-query',
    path: '/query/industry',
    label: '板块查询',
    icon: Search,
    group: 'query',
    render: ({ appState }) => (
      <IndustryQueryModule onNavigate={appState.navigateToDetail} />
    )
  },
  {
    id: 'sector-query',
    path: '/query/sector-data',
    label: '当日DC数据',
    icon: FileText,
    group: 'query',
    render: ({ appState }) => <SectorQueryModule selectedDate={appState.selectedDate} />
  },
  {
    id: 'stock-ranking',
    path: '/query/stock-ranking',
    label: '当日股票排名',
    icon: TrendingUp,
    group: 'query',
    render: ({ appState }) => <StockRankingModule selectedDate={appState.selectedDate} />
  },
  {
    id: 'industry-trend',
    path: '/industry/trend',
    label: '行业趋势分析',
    icon: TrendingUp,
    group: 'industry',
    render: ({ appState }) => (
      <IndustryTrendModule
        selectedDate={appState.selectedDate}
        topNLimit={appState.industryTrendState.topNLimit}
        onNavigate={appState.navigateToDetail}
      />
    )
  },
  {
    id: 'industry-weighted',
    path: '/industry/weighted',
    label: '股票板块-权值热度',
    icon: TrendingUp,
    group: 'industry',
    render: ({ appState }) => (
      <IndustryWeightedModule
        selectedDate={appState.selectedDate}
        onNavigate={appState.navigateToDetail}
      />
    )
  },
  {
    id: 'sector-trend',
    path: '/industry/sector-trend',
    label: 'dc板块数据分析',
    icon: TrendingUp,
    group: 'industry',
    render: ({ appState }) => <SectorTrendModule selectedDate={appState.selectedDate} />
  },
  {
    id: 'ext-board-heat',
    path: '/board-heat',
    label: '东财板块热度榜',
    icon: TrendingUp,
    group: 'industry',
    render: ({ appState }) => <BoardHeatRoute appState={appState} />
  },
  {
    id: 'rank-jump',
    path: '/analysis/rank-jump',
    label: '排名跳变',
    icon: TrendingUp,
    group: 'strategy',
    render: ({ appState }) => (
      <RankJumpModule
        selectedDate={appState.selectedDate}
        jumpBoardType={appState.rankJumpState.boardType}
        jumpThreshold={appState.rankJumpState.threshold}
      />
    )
  },
  {
    id: 'steady-rise',
    path: '/analysis/steady-rise',
    label: '稳步上升',
    icon: TrendingDown,
    group: 'strategy',
    render: ({ appState }) => (
      <SteadyRiseModule
        selectedDate={appState.selectedDate}
        riseBoardType={appState.steadyRiseState.boardType}
        risePeriod={appState.steadyRiseState.period}
        minRankImprovement={appState.steadyRiseState.minImprovement}
      />
    )
  },
  {
    id: 'needle-under-20',
    path: '/analysis/needle-under-20',
    label: '单针下二十策略',
    icon: TrendingDown,
    group: 'strategy',
    render: ({ appState }) => <NeedleUnder20Module selectedDate={appState.selectedDate} />
  },
  {
    id: 'admin',
    path: '/admin/data',
    label: '数据管理',
    icon: Upload,
    group: 'admin',
    adminOnly: true,
    render: ({ appState }) => <AdminPanel onImportComplete={appState.refreshDates} />
  },
  {
    id: 'ext-board-sync',
    path: '/admin/ext-board-sync',
    label: '外部板块同步',
    icon: Database,
    group: 'admin',
    adminOnly: true,
    render: () => <ExtBoardSync />
  },
  {
    id: 'user-management',
    path: '/admin/users',
    label: '用户管理',
    icon: UserCog,
    group: 'admin',
    adminOnly: true,
    render: () => <UserManagement />
  },
  {
    id: 'role-management',
    path: '/admin/roles',
    label: '角色管理',
    icon: Shield,
    group: 'admin',
    adminOnly: true,
    render: () => <RoleManagement />
  },
  {
    id: 'session-management',
    path: '/admin/sessions',
    label: '会话管理',
    icon: Monitor,
    group: 'admin',
    adminOnly: true,
    render: () => <SessionManagement />
  },
  {
    id: 'operation-logs',
    path: '/admin/logs',
    label: '操作日志',
    icon: FileText,
    group: 'admin',
    adminOnly: true,
    render: () => <OperationLogs />
  },
  {
    id: 'user-security-settings',
    path: '/admin/security',
    label: '安全策略',
    icon: Lock,
    group: 'admin',
    adminOnly: true,
    render: () => <UserSecuritySettings />
  },
  {
    id: 'system-config',
    path: '/admin/config',
    label: '系统设置',
    icon: Settings,
    group: 'admin',
    adminOnly: true,
    render: () => <SystemConfig />
  },
  {
    id: 'user-login-history',
    path: '/admin/login-history',
    label: '登录历史',
    icon: FileText,
    group: 'admin',
    adminOnly: true,
    hidden: true,
    render: () => <UserLoginHistory />
  }
];

export const moduleById = new Map(modules.map((module) => [module.id, module]));

export function getModuleById(id) {
  return moduleById.get(id) || moduleById.get(DEFAULT_MODULE_ID);
}

export function getModulePath(id) {
  return getModuleById(id)?.path || '/';
}

export function getModuleByPathname(pathname) {
  return modules.find((module) => {
    const paths = [module.path, ...(module.aliases || [])];
    return paths.includes(pathname);
  }) || getModuleById(DEFAULT_MODULE_ID);
}

export function isModuleInGroup(moduleId, groupIds) {
  return groupIds.includes(moduleId);
}
