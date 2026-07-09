import React from 'react';
import {
  ChevronUp, ChevronDown, RefreshCw, Activity
} from 'lucide-react';
import {
  adminNavigationSections,
  industryNavigationItems,
  navigationGroups,
  queryNavigationItems,
  strategyNavigationItems
} from '../../app/navigationConfig';

/**
 * 侧边栏导航组件
 * 包含所有的模块切换和筛选逻辑
 */
const Sidebar = ({
  activeModule,
  setActiveModule,
  expandedMenu,
  toggleMenu,

  // 各模块状态
  hotSpotsState,
  queryState,
  rankJumpState,
  steadyRiseState,
  industryTrendState,

  // 用户信息
  user
}) => {
  // 判断是否是管理员
  const isAdmin = user?.role === 'admin';

  // 辅助函数：渲染菜单项
  const MenuItem = ({ id, icon: Icon, label, children, colorClass = "indigo", activeIds = [], containerOnly = false }) => {
    const isActive = activeModule === id || activeIds.includes(activeModule);
    const isExpanded = expandedMenu === id;

    // 颜色映射
    const colors = {
      indigo: { bg: 'bg-indigo-50', text: 'text-indigo-700', hover: 'hover:bg-indigo-50', border: 'border-indigo-200' },
      purple: { bg: 'bg-purple-50', text: 'text-purple-700', hover: 'hover:bg-purple-50', border: 'border-purple-200' },
      green: { bg: 'bg-green-50', text: 'text-green-700', hover: 'hover:bg-green-50', border: 'border-green-200' },
      orange: { bg: 'bg-orange-50', text: 'text-orange-700', hover: 'hover:bg-orange-50', border: 'border-orange-200' },
      blue: { bg: 'bg-blue-50', text: 'text-blue-700', hover: 'hover:bg-blue-50', border: 'border-blue-200' },
    };

    const currentColors = colors[colorClass] || colors.indigo;

    return (
      <div className="mb-2">
        <button
          onClick={() => {
            if (!containerOnly) {
              setActiveModule(id);
            } else if (children) {
              toggleMenu(id);
              return;
            }

            // 同时也展开/折叠菜单
            if (children) {
              toggleMenu(id);
            }

            // 特殊处理：如果是最新热点，点击主菜单也触发刷新
            if (id === 'hot-spots') {
              if (hotSpotsState.handleRefresh) hotSpotsState.handleRefresh();
            }
          }}
          className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${isActive ? `${currentColors.bg} ${currentColors.text}` : 'text-gray-700 hover:bg-gray-50'
            }`}
        >
          <div className="flex items-center space-x-2">
            <Icon className="h-5 w-5" />
            <span>{label}</span>
          </div>
          {children && (
            isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
          )}
        </button>

        {/* 子菜单内容 */}
        {isExpanded && children && (
          <div className={`mt-2 ml-4 space-y-3 border-l-2 ${currentColors.border} pl-3 animate-fadeIn`}>
            {children}
          </div>
        )}
      </div>
    );
  };

  // 辅助组件：筛选按钮
  const FilterButton = ({ active, onClick, label, colorClass = "indigo", subLabel }) => {
    const colors = {
      indigo: 'bg-indigo-100 text-indigo-700',
      purple: 'bg-purple-100 text-purple-700',
      green: 'bg-green-100 text-green-700',
      orange: 'bg-orange-100 text-orange-700',
      blue: 'bg-blue-100 text-blue-700',
      cyan: 'bg-cyan-100 text-cyan-700'
    };

    return (
      <button
        onClick={onClick}
        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${active ? colors[colorClass] : 'text-gray-600 hover:bg-gray-50'
          }`}
      >
        {label} {subLabel && <span className="text-xs opacity-75">{subLabel}</span>}
      </button>
    );
  };

  const ModuleButton = ({ item, colorClass = "purple", context = {}, showIcon = false }) => {
    const active = activeModule === item.id;
    const activeColors = {
      indigo: 'bg-indigo-100 text-indigo-700',
      purple: 'bg-purple-100 text-purple-700',
      green: 'bg-green-100 text-green-700',
      orange: 'bg-orange-100 text-orange-700',
      blue: 'bg-blue-100 text-blue-700',
      cyan: 'bg-cyan-100 text-cyan-700',
      amber: 'bg-amber-100 text-amber-700',
      rose: 'bg-rose-50 text-rose-700 border border-rose-200'
    };
    const Icon = item.icon;
    const selectedClass = item.activeClassName || activeColors[item.colorClass || colorClass] || activeColors.purple;
    const idleClass = colorClass === 'amber' ? 'text-gray-600 hover:bg-amber-50' : 'text-gray-600 hover:bg-gray-50';

    return (
      <button
        onClick={() => {
          item.onBeforeNavigate?.({ ...context, setActiveModule });
          setActiveModule(item.id);
        }}
        className={`w-full text-left py-2 px-3 rounded text-sm font-medium transition-colors ${showIcon ? 'flex items-center space-x-2' : ''} ${active ? selectedClass : idleClass}`}
      >
        {showIcon && Icon && <Icon className="h-4 w-4" />}
        <span>
          {item.prefix ? `${item.prefix} ` : ''}{item.label}
        </span>
        {item.suffix && <span className="text-xs text-gray-400 ml-1">{item.suffix}</span>}
        {item.badge && <span className="ml-2 text-xs bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded">{item.badge}</span>}
      </button>
    );
  };

  const AdminIcon = navigationGroups.admin.icon;

  return (
    <aside className="w-full lg:w-72 flex-shrink-0">
      <div className="bg-white rounded-lg shadow-md overflow-hidden sticky top-4">
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-4 text-white">
          <h3 className="text-lg font-bold flex items-center space-x-2">
            <Activity className="h-5 w-5" />
            <span>功能导航</span>
          </h3>
        </div>

        <nav className="p-2 max-h-[calc(100vh-160px)] overflow-y-auto custom-scrollbar">
          {/* 1. 最新热点 */}
          <MenuItem {...navigationGroups.hotSpots}>
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">板块类型</div>
            <FilterButton
              active={hotSpotsState.boardType === 'main'}
              onClick={() => hotSpotsState.setBoardType('main')}
              label="主板" subLabel="(排除双创)"
            />
            <FilterButton
              active={hotSpotsState.boardType === 'all'}
              onClick={() => hotSpotsState.setBoardType('all')}
              label="全部" subLabel="(含双创)"
            />
            <FilterButton
              active={hotSpotsState.boardType === 'bjs'}
              onClick={() => hotSpotsState.setBoardType('bjs')}
              label="北交所" subLabel="(920开头)"
            />

            <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">分析周期</div>
            <div className="grid grid-cols-2 gap-2">
              {[2, 3, 5, 7, 14].map(p => (
                <button
                  key={p}
                  onClick={() => hotSpotsState.setSelectedPeriod(p)}
                  className={`py-2 px-2 rounded text-sm font-medium transition-colors ${hotSpotsState.selectedPeriod === p ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                >
                  {p}天
                </button>
              ))}
            </div>

            <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">分析股票数</div>
            <div className="grid grid-cols-2 gap-2">
              {[100, 200, 400, 600, 800, 1000, 2000, 3000].map(n => (
                <button
                  key={n}
                  onClick={() => hotSpotsState.setTopN(n)}
                  className={`py-2 px-2 rounded text-sm font-medium transition-colors ${hotSpotsState.topN === n ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                >
                  前{n}个
                </button>
              ))}
            </div>

            <button
              onClick={hotSpotsState.handleRefresh}
              disabled={hotSpotsState.loading}
              className="mt-4 w-full flex items-center justify-center space-x-2 bg-green-600 hover:bg-green-700 text-white py-2 px-3 rounded text-sm font-medium transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${hotSpotsState.loading ? 'animate-spin' : ''}`} />
              <span>{hotSpotsState.loading ? '分析中...' : '刷新数据'}</span>
            </button>
          </MenuItem>

          {/* 2. 查询系统 */}
          <MenuItem {...navigationGroups.query}>
            {queryNavigationItems.map((item) => (
              <ModuleButton
                key={item.id}
                item={item}
                colorClass="purple"
                context={{ queryState }}
              />
            ))}
          </MenuItem>

          {/* 3. 行业趋势 */}
          <MenuItem {...navigationGroups.industry}>
            {industryNavigationItems.map((item) => (
              <React.Fragment key={item.id}>
                <ModuleButton item={item} colorClass="green" />
                {item.id === 'industry-trend' && activeModule === 'industry-trend' && (
                  <div className="mt-2 ml-2 space-y-2">
                    <div className="text-xs font-semibold text-gray-500 uppercase mb-2">数据范围</div>
                    <div className="grid grid-cols-3 gap-2">
                      {[1000, 2000, 3000].map(limit => (
                        <button
                          key={limit}
                          onClick={() => industryTrendState.setTopNLimit(limit)}
                          className={`py-2 px-2 rounded text-sm font-medium transition-colors ${industryTrendState.topNLimit === limit ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                        >
                          前{limit}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </React.Fragment>
            ))}
          </MenuItem>

          {/* 4. 排名跳变 */}
          <MenuItem {...navigationGroups.rankJump}>
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">板块类型</div>
            <FilterButton active={rankJumpState.boardType === 'main'} onClick={() => rankJumpState.setBoardType('main')} label="主板" colorClass="orange" />
            <FilterButton active={rankJumpState.boardType === 'all'} onClick={() => rankJumpState.setBoardType('all')} label="全部" colorClass="orange" />
            <FilterButton active={rankJumpState.boardType === 'bjs'} onClick={() => rankJumpState.setBoardType('bjs')} label="北交所" colorClass="orange" />

            <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">跳变阈值</div>
            <div className="space-y-2">
              {[1000, 1500, 2000, 2500, 3000].map(t => (
                <FilterButton
                  key={t}
                  active={rankJumpState.threshold === t}
                  onClick={() => rankJumpState.setThreshold(t)}
                  label={`向前跳变 ≥${t}名`} colorClass="orange"
                />
              ))}
            </div>
          </MenuItem>

          {/* 5. 稳步上升 */}
          <MenuItem {...navigationGroups.steadyRise}>
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">板块类型</div>
            <FilterButton active={steadyRiseState.boardType === 'main'} onClick={() => steadyRiseState.setBoardType('main')} label="主板" colorClass="blue" />
            <FilterButton active={steadyRiseState.boardType === 'all'} onClick={() => steadyRiseState.setBoardType('all')} label="全部" colorClass="blue" />
            <FilterButton active={steadyRiseState.boardType === 'bjs'} onClick={() => steadyRiseState.setBoardType('bjs')} label="北交所" colorClass="blue" />

            <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">分析周期</div>
            <div className="grid grid-cols-2 gap-2">
              {[2, 3, 5, 7, 14].map(p => (
                <button key={p} onClick={() => steadyRiseState.setPeriod(p)}
                  className={`py-2 px-2 rounded text-sm font-medium transition-colors ${steadyRiseState.period === p ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}>
                  {p}天
                </button>
              ))}
            </div>

            <div className="text-xs font-semibold text-gray-500 uppercase mb-2 mt-4">最小提升幅度</div>
            <div className="space-y-2">
              {[100, 500, 1000, 2000].map(t => (
                <FilterButton
                  key={t}
                  active={steadyRiseState.minImprovement === t}
                  onClick={() => steadyRiseState.setMinImprovement(t)}
                  label={`提升 ≥${t}名`} colorClass="blue"
                />
              ))}
            </div>
          </MenuItem>

          {/* 6. 策略：单针下二十 */}
          {strategyNavigationItems.map((item) => {
            const Icon = item.icon;
            return (
              <div className="mb-2" key={item.id}>
                <button
                  onClick={() => setActiveModule(item.id)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${activeModule === item.id
                    ? 'bg-rose-50 text-rose-700 border border-rose-200'
                    : 'text-gray-700 hover:bg-gray-50'
                    }`}
                >
                  <div className="flex items-center space-x-2">
                    <Icon className="h-5 w-5 text-rose-500" />
                    <span>{item.label}</span>
                  </div>
                </button>
              </div>
            );
          })}

          {/* 7. 系统管理 - 仅 admin 可见 */}
          {isAdmin && (
            <>
              <div className="my-4 border-t border-gray-200"></div>
              <div className="mb-2">
                {/* 系统管理主菜单 */}
                <button
                  onClick={() => toggleMenu(navigationGroups.admin.id)}
                  className={`w-full flex items-center justify-between p-3 rounded-lg font-medium transition-all ${navigationGroups.admin.activeIds.includes(activeModule)
                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                    : 'text-gray-700 hover:bg-gray-50'
                    }`}
                >
                  <div className="flex items-center space-x-2">
                    <AdminIcon className="h-5 w-5 text-amber-500" />
                    <span>{navigationGroups.admin.label}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs bg-amber-100 text-amber-600 px-2 py-0.5 rounded-full">
                      管理员
                    </span>
                    {expandedMenu === navigationGroups.admin.id ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </button>

                {/* 子菜单 */}
                {expandedMenu === navigationGroups.admin.id && (
                  <div className="mt-2 ml-4 space-y-3 border-l-2 border-amber-200 pl-3">
                    {adminNavigationSections.map((section, index) => (
                      <div key={section.title || `admin-section-${index}`} className={section.title ? 'space-y-1' : 'space-y-3'}>
                        {section.title && (
                          <div className="text-xs text-amber-600 font-semibold mt-2">
                            {section.title}
                          </div>
                        )}
                        {section.items.map((item) => (
                          <ModuleButton
                            key={item.id}
                            item={item}
                            colorClass="amber"
                            showIcon
                          />
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

        </nav>
      </div>
    </aside>
  );
};

export default Sidebar;
