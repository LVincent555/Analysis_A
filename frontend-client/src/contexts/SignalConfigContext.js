/**
 * 全局信号阈值配置Context
 * 用于在整个应用中共享和同步信号配置
 * 支持localStorage持久化，刷新后配置保留
 */
import React, { createContext, useState, useContext, useEffect } from 'react';

// localStorage key
const STORAGE_KEY = 'stock_analysis_signal_thresholds';

// 默认阈值配置
const DEFAULT_THRESHOLDS = {
  hotListMode: 'frequent',  // 热点榜模式：instant=总分TOP信号，frequent=最新热点TOP信号（默认）
  hotListVersion: 'v2',  // 热点榜版本：v1=原版（2.0倍数），v2=新版（1.5倍数，默认）
  hotListTop: 100,
  rankJumpMin: 1000,  // 跳变榜阈值改为1000
  steadyRiseDays: 3,
  priceSurgeMin: 5.0,
  volumeSurgeMin: 10.0,
  volatilitySurgeMin: 10.0,  // 波动率上升阈值默认改为10%
  // 板块数据源配置（多对多系统）
  boardDataSource: 'dc',  // dc=DC原版(87行业,一对一), eastmoney=东财板块(527,多对多)
};

/**
 * 从localStorage加载配置
 */
const loadThresholdsFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // 合并默认值，确保新增配置项有默认值
      return {...DEFAULT_THRESHOLDS, ...parsed};
    }
  } catch (error) {
    console.error('加载配置失败:', error);
  }
  return {...DEFAULT_THRESHOLDS};
};

/**
 * 保存配置到localStorage
 */
const saveThresholdsToStorage = (thresholds) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(thresholds));
  } catch (error) {
    console.error('保存配置失败:', error);
  }
};

// 创建Context
const SignalConfigContext = createContext();

// Provider组件
export function SignalConfigProvider({ children }) {
  // 从localStorage初始化配置
  const [signalThresholds, setSignalThresholdsRaw] = useState(() => loadThresholdsFromStorage());
  const [showConfig, setShowConfig] = useState(false);
  const [tempThresholds, setTempThresholds] = useState({...signalThresholds});
  
  // 包装setter，同时保存到localStorage
  const setSignalThresholds = (newThresholds) => {
    setSignalThresholdsRaw(newThresholds);
    saveThresholdsToStorage(newThresholds);
  };

  // 监听配置变化，自动保存（备用机制）
  useEffect(() => {
    saveThresholdsToStorage(signalThresholds);
  }, [signalThresholds]);

  // 打开配置面板
  const openConfig = () => {
    setTempThresholds({...signalThresholds});
    setShowConfig(true);
  };

  // 关闭配置面板
  const closeConfig = () => {
    setShowConfig(false);
  };

  // 应用配置
  const applyConfig = () => {
    const newThresholds = {...tempThresholds};
    setSignalThresholds(newThresholds);
    setShowConfig(false);
  };

  // 重置为默认值
  const resetToDefault = () => {
    setTempThresholds({...DEFAULT_THRESHOLDS});
  };

  // 清除保存的配置（恢复默认）
  const clearSavedConfig = () => {
    try {
      localStorage.removeItem(STORAGE_KEY);
      const defaultConfig = {...DEFAULT_THRESHOLDS};
      setSignalThresholdsRaw(defaultConfig);
      setTempThresholds(defaultConfig);
    } catch (error) {
      console.error('清除配置失败:', error);
    }
  };

  const value = {
    // 状态
    signalThresholds,
    showConfig,
    tempThresholds,
    
    // 方法
    setTempThresholds,
    openConfig,
    closeConfig,
    applyConfig,
    resetToDefault,
    clearSavedConfig  // 新增：清除保存的配置
  };

  return (
    <SignalConfigContext.Provider value={value}>
      {children}
    </SignalConfigContext.Provider>
  );
}

// 自定义Hook
export function useSignalConfig() {
  const context = useContext(SignalConfigContext);
  if (!context) {
    throw new Error('useSignalConfig must be used within SignalConfigProvider');
  }
  return context;
}
