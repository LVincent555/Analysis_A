import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../constants/config';

/**
 * 全局应用状态管理 Hook
 * 负责管理所有的筛选条件、选中状态和数据获取触发器
 */
export const useAppState = () => {
  // ==================== 核心状态 ====================
  const [activeModule, setActiveModule] = useState('hot-spots');
  const [expandedMenu, setExpandedMenu] = useState('hot-spots');
  
  // 日期相关
  const [availableDates, setAvailableDates] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);

  // 详情页状态 (Phase 6)
  const [showDetailPage, setShowDetailPage] = useState(false);
  const [selectedIndustry, setSelectedIndustry] = useState(null);

  // 移动端 Drawer 状态
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // ==================== 模块筛选状态 ====================
  
  // 1. 最新热点模块
  const [boardType, setBoardType] = useState('main');
  const [selectedPeriod, setSelectedPeriod] = useState(2);
  const [topN, setTopN] = useState(100);
  const [loading, setLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0); // 添加刷新触发器

  // 2. 查询系统模块
  const [querySubModule, setQuerySubModule] = useState('stock');
  const [stockCode, setStockCode] = useState('');
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState(null);
  const [queryTrigger, setQueryTrigger] = useState(0);

  // 3. 排名跳变模块
  const [jumpBoardType, setJumpBoardType] = useState('main');
  const [jumpThreshold, setJumpThreshold] = useState(2000);

  // 4. 稳步上升模块
  const [riseBoardType, setRiseBoardType] = useState('main');
  const [risePeriod, setRisePeriod] = useState(3);
  const [minRankImprovement, setMinRankImprovement] = useState(100);

  // 5. 行业趋势模块
  const [topNLimit, setTopNLimit] = useState(1000);

  // ==================== 核心逻辑 ====================

  // 初始化获取日期
  useEffect(() => {
    const fetchAvailableDates = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/dates`);
        setAvailableDates(response.data);
        if (response.data && response.data.latest_date) {
          setSelectedDate(response.data.latest_date);
        }
      } catch (err) {
        console.error('获取日期失败:', err);
      }
    };
    fetchAvailableDates();
  }, []);

  // 切换菜单展开状态
  const toggleMenu = (menuName) => {
    setExpandedMenu(expandedMenu === menuName ? null : menuName);
  };

  // 触发股票查询
  const handleStockQuery = useCallback(() => {
    if (!stockCode.trim()) {
      setStockError('请输入股票代码');
      return;
    }
    setStockError(null);
    setQueryTrigger(prev => prev + 1);
  }, [stockCode]);

  // 刷新数据
  const handleRefresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);

  // 导航逻辑
  const navigateToDetail = (industryName) => {
    setSelectedIndustry(industryName);
    setShowDetailPage(true);
    setIsDrawerOpen(false); // 移动端跳转时关闭抽屉
  };

  const backToMain = () => {
    setShowDetailPage(false);
    setSelectedIndustry(null);
  };

  // 选中模块时自动关闭抽屉（用于移动端）
  const handleModuleChange = (moduleId) => {
    setActiveModule(moduleId);
    // 移除自动关闭逻辑，允许用户在侧边栏进行多次操作
    // setIsDrawerOpen(false);
  };

  // 返回整合后的状态和方法
  return {
    // 核心状态
    activeModule, setActiveModule: handleModuleChange, // 使用包装后的方法
    expandedMenu, toggleMenu,
    availableDates, 
    selectedDate, setSelectedDate,
    showDetailPage, selectedIndustry,
    navigateToDetail, backToMain,
    isDrawerOpen, setIsDrawerOpen, // 暴露 Drawer 状态

    // 热点模块
    hotSpotsState: {
      boardType, setBoardType,
      selectedPeriod, setSelectedPeriod,
      topN, setTopN,
      loading, handleRefresh,
      refreshTrigger // 暴露 refreshTrigger
    },

    // 查询模块
    queryState: {
      querySubModule, setQuerySubModule,
      stockCode, setStockCode,
      stockLoading, setStockLoading,
      stockError, setStockError,
      queryTrigger,
      handleStockQuery
    },

    // 排名跳变
    rankJumpState: {
      boardType: jumpBoardType, setBoardType: setJumpBoardType,
      threshold: jumpThreshold, setThreshold: setJumpThreshold
    },

    // 稳步上升
    steadyRiseState: {
      boardType: riseBoardType, setBoardType: setRiseBoardType,
      period: risePeriod, setPeriod: setRisePeriod,
      minImprovement: minRankImprovement, setMinImprovement: setMinRankImprovement
    },

    // 行业趋势
    industryTrendState: {
      topNLimit, setTopNLimit
    }
  };
};
