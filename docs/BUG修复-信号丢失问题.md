# BUG修复：新版信号丢失问题

## 🐛 问题描述

**日期**: 2025-11-11

**症状**:
- 老版显示：`TOP800·2次`、`跳变2060`、`涨幅7%` （3个信号，强度37%）
- 新版显示：`热点TOP500`、`跳变2380` （2个信号，强度25%）
- **丢失**: TOP800信号、涨幅信号

## 🔍 根本原因

### 信号模式不一致

**老版使用**: 最新热点TOP信号（frequent模式）
```
格式: TOP800·2次
说明: 基于14天聚合的最新热点数据
```

**新版使用**: 总分TOP信号（instant模式）  ❌ 
```
格式: 热点TOP500
说明: 基于当日综合评分排名
```

### 问题根源

1. **localStorage缓存问题**
   - 用户浏览器localStorage中保存的是旧配置
   - 旧配置: `hotListMode: 'instant'`
   - 新默认值: `hotListMode: 'frequent'` 
   - **localStorage优先级高于默认值！**

2. **信号差异**
   - `instant`模式：只根据当日排名判断，信号较少
   - `frequent`模式：基于14天聚合，信号更丰富

## ✅ 解决方案

### 方案1：用户手动清除（临时）

**步骤**:
1. 打开浏览器开发者工具 (F12)
2. 进入Console标签页
3. 执行以下命令：
```javascript
localStorage.removeItem('stock_analysis_signal_thresholds');
location.reload();
```

### 方案2：添加配置版本检查（推荐）

**实现**:

在 `SignalConfigContext.js` 中添加版本检查：

```javascript
const CONFIG_VERSION = 2; // 配置版本号
const STORAGE_KEY = 'stock_analysis_signal_thresholds';
const VERSION_KEY = 'stock_analysis_config_version';

const loadThresholdsFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    const version = localStorage.getItem(VERSION_KEY);
    
    // 版本不匹配，清除旧配置
    if (version !== String(CONFIG_VERSION)) {
      console.log('配置版本升级，清除旧配置');
      localStorage.removeItem(STORAGE_KEY);
      localStorage.setItem(VERSION_KEY, String(CONFIG_VERSION));
      return {...DEFAULT_THRESHOLDS};
    }
    
    if (saved) {
      const parsed = JSON.parse(saved);
      return {...DEFAULT_THRESHOLDS, ...parsed};
    }
  } catch (error) {
    console.error('加载配置失败:', error);
  }
  return {...DEFAULT_THRESHOLDS};
};
```

### 方案3：强制更新hot_list_mode

```javascript
const loadThresholdsFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      
      // 强制使用新默认值（如果是旧的instant模式）
      if (parsed.hotListMode === 'instant') {
        console.log('检测到旧配置，更新为新模式');
        parsed.hotListMode = 'frequent';
      }
      
      return {...DEFAULT_THRESHOLDS, ...parsed};
    }
  } catch (error) {
    console.error('加载配置失败:', error);
  }
  return {...DEFAULT_THRESHOLDS};
};
```

## 📋 实施计划

### 短期（立即）
- [x] 文档化问题
- [ ] 让用户清除localStorage测试
- [ ] 实现方案2（配置版本检查）
- [ ] 重新编译前端

### 中期（下版本）
- [ ] 添加配置迁移机制
- [ ] 在UI中显示当前配置版本
- [ ] 添加"恢复最新默认值"按钮

## 🎯 验证步骤

1. **清除localStorage**
```javascript
localStorage.clear();
location.reload();
```

2. **检查默认配置**
   - 打开配置面板
   - 确认"热点榜模式"默认为"最新热点TOP信号"
   - 确认信号显示完整

3. **测试信号显示**
   - 查看板块详情
   - 确认显示：TOP100/200/400等格式
   - 确认涨幅、换手率信号正常显示

## 📊 预期效果

### 修复前
```
热点TOP500     ← instant模式（旧）
跳变2380
强度: 25%
```

### 修复后
```
TOP800·2次     ← frequent模式（新）
跳变2060
涨幅7.0%
强度: 37%
```

---

**文档作者**: AI Assistant  
**创建日期**: 2025-11-11  
**状态**: 待实施
