/**
 * 全局信号阈值配置面板
 * 独立组件，便于扩展和维护
 */
import React from 'react';
import { X, RotateCcw } from 'lucide-react';
import { useSignalConfig } from '../contexts/SignalConfigContext';

export default function SignalConfigPanel() {
  const {
    showConfig,
    tempThresholds,
    setTempThresholds,
    applyConfig,
    closeConfig,
    resetToDefault
  } = useSignalConfig();

  // 应用配置
  const handleApply = () => {
    applyConfig();
  };

  if (!showConfig) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center pt-12" style={{ zIndex: 9999 }}>
      <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full mx-4 max-h-[85vh] overflow-y-auto">
        {/* 标题栏 */}
        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold">🎯 信号阈值配置</h2>
            <p className="text-sm text-purple-100 mt-1">调整信号识别的敏感度，全局生效</p>
          </div>
          <button
            onClick={closeConfig}
            className="text-white hover:bg-white hover:bg-opacity-20 rounded-full p-2 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 持久化提示 */}
        <div className="mx-6 mt-6 mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="text-blue-600 text-lg">💾</div>
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900">配置自动保存</p>
              <p className="text-xs text-blue-700 mt-1">
                您的配置会自动保存到浏览器本地存储，刷新页面后仍然保留。每个用户的配置独立，互不影响。
              </p>
            </div>
          </div>
        </div>

        {/* 配置内容 */}
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-6">
            {/* 热点榜模式选择 */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-green-900 mb-2">
                🔥 热点榜信号模式
              </label>
              <select
                value={
                  tempThresholds.hotListMode === 'instant' ? 'instant' :
                  tempThresholds.hotListVersion === 'v1' ? 'frequent_v1' : 'frequent_v2'
                }
                onChange={(e) => {
                  const val = e.target.value;
                  if (val === 'instant') {
                    setTempThresholds({...tempThresholds, hotListMode: 'instant', hotListVersion: 'v2'});
                  } else if (val === 'frequent_v1') {
                    setTempThresholds({...tempThresholds, hotListMode: 'frequent', hotListVersion: 'v1'});
                  } else {
                    setTempThresholds({...tempThresholds, hotListMode: 'frequent', hotListVersion: 'v2'});
                  }
                }}
                className="w-full px-3 py-2 border border-green-300 rounded-lg focus:ring-2 focus:ring-green-500 mb-3"
              >
                <option value="instant">总分TOP信号</option>
                <option value="frequent_v1">最新热点TOP信号（原版）</option>
                <option value="frequent_v2">最新热点TOP信号（新版）</option>
              </select>
              
              {/* 模式说明 */}
              {tempThresholds.hotListMode === 'instant' ? (
                // 模式1：总分TOP信号
                <div className="space-y-2">
                  <p className="text-xs text-green-800 font-medium">
                    📊 总分TOP信号
                  </p>
                  <div className="text-xs text-green-700 space-y-1">
                    <div>• 基于综合评分排名的即时判断</div>
                    <div>• 信号格式：热点榜TOP100、热点榜TOP500</div>
                    <div>• 快速筛选当日综合得分龙头股票</div>
                    <div>• 排名越靠前，信号权重越高</div>
                  </div>
                  <p className="text-xs text-green-600 mt-2 pt-2 border-t border-green-200">
                    💡 权重25%（固定），阈值可调节（TOP100/200/500）
                  </p>
                </div>
              ) : tempThresholds.hotListVersion === 'v1' ? (
                // 模式2：最新热点TOP信号（原版）
                <div className="space-y-2">
                  <p className="text-xs text-green-800 font-medium">
                    🔥 最新热点TOP信号（原版）
                  </p>
                  <div className="text-xs text-green-700 space-y-1">
                    <div>• 基于14天聚合数据，与线上服务器版本一致</div>
                    <div>• 信号格式：TOP100·5次（区间·出现次数）</div>
                    <div>• 区间范围：TOP100/200/400/600/800/1000/2000/3000</div>
                    <div>• <strong className="text-red-700">特点：TOP100权重最高(50%)，多信号优先排序</strong></div>
                  </div>
                  <p className="text-xs text-green-600 mt-2 pt-2 border-t border-green-200">
                    💡 档位倍数：TOP100(2.0×50%)、TOP200(1.5×37.5%)、TOP400(1.2×30%)、TOP600(1.0×25%)、TOP800(0.8×20%)、TOP1000(0.5×12.5%)、TOP2000(0.3×7.5%)、TOP3000(0.2×5%)
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    💡 次数加权：12次×1.2、10次×1.1、8次×1.05
                  </p>
                  <p className="text-xs text-red-600 mt-1">
                    💡 排序：优先按信号数量，其次信号强度
                  </p>
                </div>
              ) : (
                // 模式3：最新热点TOP信号（新版）
                <div className="space-y-2">
                  <p className="text-xs text-green-800 font-medium">
                    🔥 最新热点TOP信号（新版）⭐推荐
                  </p>
                  <div className="text-xs text-green-700 space-y-1">
                    <div>• 基于14天聚合数据，优化后的权重分配</div>
                    <div>• 信号格式：TOP100·5次（区间·出现次数）</div>
                    <div>• 区间范围：TOP100/200/400/600/800/1000/2000/3000</div>
                    <div>• <strong className="text-blue-700">特点：降低TOP100权重(37.5%)，强度优先排序</strong></div>
                  </div>
                  <p className="text-xs text-green-600 mt-2 pt-2 border-t border-green-200">
                    💡 档位倍数：TOP100(1.5×37.5%)、TOP200(1.3×32.5%)、TOP400(1.2×30%)、TOP600(1.0×25%)、TOP800(0.9×22.5%)、TOP1000(0.8×20%)、TOP2000(0.6×15%)、TOP3000(0.5×12.5%)
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    💡 次数加权：12次×1.2、10次×1.1、8次×1.05
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    💡 排序：优先按信号强度，其次信号数量
                  </p>
                </div>
              )}
            </div>

            {/* 跳变榜阈值 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-blue-900 mb-2">
                📈 跳变榜阈值
              </label>
              <select
                value={tempThresholds.rankJumpMin}
                onChange={(e) => setTempThresholds({...tempThresholds, rankJumpMin: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value={1000}>≥1000名</option>
                <option value={1500}>≥1500名</option>
                <option value={2000}>≥2000名</option>
                <option value={2500}>≥2500名</option>
                <option value={3000}>≥3000名</option>
                <option value={3500}>≥3500名</option>
              </select>
              <p className="text-xs text-blue-700 mt-2">相比前一天排名提升≥X名</p>
            </div>

            {/* 稳步上升天数 */}
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-purple-900 mb-2">
                📊 稳步上升天数
              </label>
              <select
                value={tempThresholds.steadyRiseDays}
                onChange={(e) => setTempThresholds({...tempThresholds, steadyRiseDays: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-purple-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              >
                <option value={2}>≥2天</option>
                <option value={3}>≥3天</option>
                <option value={5}>≥5天</option>
                <option value={7}>≥7天</option>
                <option value={10}>≥10天</option>
                <option value={14}>≥14天</option>
              </select>
              <p className="text-xs text-purple-700 mt-2">连续X天排名上升</p>
            </div>

            {/* 涨幅榜阈值 */}
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-orange-900 mb-2">
                💰 涨幅榜阈值
              </label>
              <select
                value={tempThresholds.priceSurgeMin}
                onChange={(e) => setTempThresholds({...tempThresholds, priceSurgeMin: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-orange-300 rounded-lg focus:ring-2 focus:ring-orange-500"
              >
                <option value={3}>≥3%</option>
                <option value={5}>≥5%</option>
                <option value={7}>≥7%</option>
                <option value={10}>≥10%</option>
              </select>
              <p className="text-xs text-orange-700 mt-2">当日涨跌幅≥X%</p>
            </div>

            {/* 成交量阈值 */}
            <div className="bg-red-50 border border-red-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-red-900 mb-2">
                📦 成交量阈值
              </label>
              <select
                value={tempThresholds.volumeSurgeMin}
                onChange={(e) => setTempThresholds({...tempThresholds, volumeSurgeMin: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-red-300 rounded-lg focus:ring-2 focus:ring-red-500"
              >
                <option value={5}>≥5%</option>
                <option value={10}>≥10%</option>
                <option value={15}>≥15%</option>
                <option value={20}>≥20%</option>
              </select>
              <p className="text-xs text-red-700 mt-2">当日换手率≥X%</p>
            </div>

            {/* 波动率上升阈值 */}
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-indigo-900 mb-2">
                ⚡ 波动率上升阈值
              </label>
              <select
                value={tempThresholds.volatilitySurgeMin}
                onChange={(e) => setTempThresholds({...tempThresholds, volatilitySurgeMin: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value={10}>≥10%</option>
                <option value={30}>≥30%</option>
                <option value={50}>≥50%</option>
                <option value={100}>≥100%</option>
                <option value={150}>≥150%</option>
              </select>
              <p className="text-xs text-indigo-700 mt-2">波动率百分比变化≥X%</p>
            </div>

            {/* 板块数据源 */}
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-5">
              <label className="block text-sm font-semibold text-teal-900 mb-2">
                📊 板块数据源
              </label>
              <select
                value={tempThresholds.boardDataSource || 'dc'}
                onChange={(e) => setTempThresholds({...tempThresholds, boardDataSource: e.target.value})}
                className="w-full px-3 py-2 border border-teal-300 rounded-lg focus:ring-2 focus:ring-teal-500"
              >
                <option value="dc">DC原版（87行业，一对一）</option>
                <option value="eastmoney">东财板块（527，多对多）🆕</option>
              </select>
              <p className="text-xs text-teal-700 mt-2">
                {tempThresholds.boardDataSource === 'eastmoney' 
                  ? '多对多关系：个股可属于多个板块，热度分摊计算' 
                  : '一对一关系：个股对应单一行业板块'}
              </p>
              {tempThresholds.boardDataSource === 'eastmoney' && (
                <div className="mt-2 p-2 bg-teal-100 rounded text-xs text-teal-800">
                  <strong>🆕 新版特性：</strong>
                  <ul className="mt-1 space-y-0.5">
                    <li>• 527个板块（86行业+441概念）</li>
                    <li>• 多对多热度守恒分摊</li>
                    <li>• 攻守分离信号（行业防守/概念进攻）</li>
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* 说明 */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-900 mb-2">💡 配置说明</h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• 配置修改后需要点击"应用配置"按钮才会生效</li>
              <li>• 配置全局生效，影响所有页面的信号计算</li>
              <li>• 阈值越小越敏感，触发的信号越多；阈值越大越严格，只显示强信号</li>
              <li>• 可以点击"恢复默认"按钮重置为推荐配置</li>
            </ul>
          </div>

          {/* 按钮组 */}
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={resetToDefault}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
              恢复默认
            </button>
            <button
              onClick={closeConfig}
              className="px-6 py-2 bg-gray-300 hover:bg-gray-400 text-gray-700 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleApply}
              className="px-6 py-2 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg transition-colors font-medium"
            >
              ✓ 应用配置
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
