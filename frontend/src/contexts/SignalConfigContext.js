/**
 * 全局信号阈值配置Context
 * 用于在整个应用中共享和同步信号配置
 */
import React, { createContext, useState, useContext } from 'react';

// 默认阈值配置
const DEFAULT_THRESHOLDS = {
  hotListTop: 100,
  rankJumpMin: 1000,  // 跳变榜阈值改为1000
  steadyRiseDays: 3,
  priceSurgeMin: 5.0,
  volumeSurgeMin: 10.0,
  volatilitySurgeMin: 30.0
};

// 创建Context
const SignalConfigContext = createContext();

// Provider组件
export function SignalConfigProvider({ children }) {
  const [signalThresholds, setSignalThresholdsRaw] = useState(DEFAULT_THRESHOLDS);
  const [showConfig, setShowConfig] = useState(false);
  const [tempThresholds, setTempThresholds] = useState({...DEFAULT_THRESHOLDS});
  
  // 包装setter
  const setSignalThresholds = (newThresholds) => {
    setSignalThresholdsRaw(newThresholds);
  };

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
    setSignalThresholds({...tempThresholds});
    setShowConfig(false);
  };

  // 重置为默认值
  const resetToDefault = () => {
    setTempThresholds({...DEFAULT_THRESHOLDS});
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
    resetToDefault
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
