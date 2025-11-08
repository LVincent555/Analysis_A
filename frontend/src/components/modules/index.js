/**
 * 模块组件统一导出
 */
export { default as HotSpotsModule } from './HotSpotsModule';
export { default as StockQueryModule } from './StockQueryModule';
export { default as IndustryTrendModule } from './IndustryTrendModule';  // 已废弃，保留以防兼容性
export { default as IndustryWeightedModule } from './IndustryWeightedModule';
export { default as SectorTrendModule } from './SectorTrendModule';  // 新增：板块趋势分析
export { default as RankJumpModule } from './RankJumpModule';
export { default as SteadyRiseModule } from './SteadyRiseModule';
export { default as SectorModule } from './SectorModule';  // 已整合到SectorTrendModule，保留以防兼容性
