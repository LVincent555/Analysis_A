/**
 * 侧边栏导航组件
 */
import React from 'react';
import { BarChart3, Search, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';

const Sidebar = ({ activeModule, setActiveModule, expandedMenu, setExpandedMenu }) => {
  const menuItems = [
    {
      id: 'hot-spots',
      label: '最新热点',
      icon: BarChart3,
      description: '分析重复出现的股票'
    },
    {
      id: 'stock-query',
      label: '股票查询',
      icon: Search,
      description: '查询个股历史数据'
    },
    {
      id: 'industry-trend',
      label: '行业趋势分析',
      icon: TrendingUp,
      description: '行业分布与趋势'
    }
  ];

  const handleMenuClick = (id) => {
    if (expandedMenu === id) {
      setExpandedMenu(null);
    } else {
      setExpandedMenu(id);
      setActiveModule(id);
    }
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo区域 */}
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-indigo-600">股票分析</h1>
        <p className="text-sm text-gray-500 mt-1">A股数据分析系统</p>
      </div>

      {/* 菜单区域 */}
      <nav className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeModule === item.id;
          const isExpanded = expandedMenu === item.id;

          return (
            <div key={item.id}>
              <button
                onClick={() => handleMenuClick(item.id)}
                className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-600'
                    : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className="h-5 w-5" />
                  <div className="text-left">
                    <div className="font-medium">{item.label}</div>
                    <div className="text-xs text-gray-500">{item.description}</div>
                  </div>
                </div>
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </button>
            </div>
          );
        })}
      </nav>

      {/* 底部信息 */}
      <div className="p-4 border-t border-gray-200 text-xs text-gray-500">
        <p>版本: v0.2.0</p>
        <p className="mt-1">模块化重构版本</p>
      </div>
    </div>
  );
};

export default Sidebar;
