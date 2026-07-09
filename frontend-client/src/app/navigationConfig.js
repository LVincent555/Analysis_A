import {
  BarChart2,
  Search,
  TrendingDown,
  TrendingUp,
  Shield
} from 'lucide-react';
import {
  ADMIN_MODULE_IDS,
  INDUSTRY_MODULE_IDS,
  QUERY_MODULE_IDS,
  getModuleById
} from './moduleRegistry';

const moduleItem = (id, options = {}) => {
  const module = getModuleById(id);
  return {
    id,
    label: module.label,
    icon: module.icon,
    ...options
  };
};

export const navigationGroups = {
  hotSpots: {
    id: 'hot-spots',
    label: getModuleById('hot-spots').label,
    icon: BarChart2,
    colorClass: 'indigo'
  },
  query: {
    id: 'query-system',
    label: '查询系统',
    icon: Search,
    colorClass: 'purple',
    activeIds: QUERY_MODULE_IDS,
    containerOnly: true
  },
  industry: {
    id: 'industry-trend',
    label: getModuleById('industry-trend').label,
    icon: TrendingUp,
    colorClass: 'green',
    activeIds: INDUSTRY_MODULE_IDS
  },
  rankJump: {
    id: 'rank-jump',
    label: getModuleById('rank-jump').label,
    icon: TrendingUp,
    colorClass: 'orange'
  },
  steadyRise: {
    id: 'steady-rise',
    label: getModuleById('steady-rise').label,
    icon: TrendingDown,
    colorClass: 'blue'
  },
  admin: {
    id: 'system-admin',
    label: '系统管理',
    icon: Shield,
    colorClass: 'amber',
    activeIds: ADMIN_MODULE_IDS,
    containerOnly: true
  }
};

export const queryNavigationItems = [
  moduleItem('stock-query', {
    prefix: '🔍',
    onBeforeNavigate: ({ queryState }) => queryState.setQuerySubModule('stock')
  }),
  moduleItem('industry-query', {
    prefix: '📊',
    onBeforeNavigate: ({ queryState }) => queryState.setQuerySubModule('industry')
  }),
  moduleItem('sector-query', { prefix: '📋' }),
  moduleItem('stock-ranking', { prefix: '📈' })
];

export const industryNavigationItems = [
  moduleItem('industry-trend', {
    prefix: '📊',
    label: '股票板块-直接数量统计',
    colorClass: 'green'
  }),
  moduleItem('industry-weighted', {
    prefix: '🔥',
    colorClass: 'indigo',
    activeClassName: 'bg-gradient-to-r from-green-100 to-indigo-100 text-indigo-700 border-l-4 border-indigo-500'
  }),
  moduleItem('sector-trend', {
    prefix: '📈',
    colorClass: 'cyan',
    activeClassName: 'bg-gradient-to-r from-blue-100 to-cyan-100 text-cyan-700 border-l-4 border-cyan-500'
  }),
  moduleItem('ext-board-heat', {
    prefix: '🔥',
    badge: 'NEW',
    colorClass: 'orange',
    activeClassName: 'bg-gradient-to-r from-orange-100 to-red-100 text-orange-700 border-l-4 border-orange-500'
  })
];

export const strategyNavigationItems = [
  moduleItem('needle-under-20', {
    colorClass: 'rose'
  })
];

export const adminNavigationSections = [
  {
    items: [
      moduleItem('admin'),
      moduleItem('ext-board-sync')
    ]
  },
  {
    title: '用户中心',
    items: [
      moduleItem('user-management'),
      moduleItem('role-management'),
      moduleItem('session-management'),
      moduleItem('operation-logs', { suffix: '(含登录记录)' })
    ]
  },
  {
    title: '系统配置',
    items: [
      moduleItem('user-security-settings'),
      moduleItem('system-config')
    ]
  }
];
