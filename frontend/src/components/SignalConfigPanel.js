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

  if (!showConfig) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center pt-20" style={{ zIndex: 9999 }}>
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-y-auto">
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

        {/* 配置内容 */}
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {/* 热点榜阈值 */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <label className="block text-sm font-semibold text-green-900 mb-2">
                🔥 热点榜阈值
              </label>
              <select
                value={tempThresholds.hotListTop}
                onChange={(e) => setTempThresholds({...tempThresholds, hotListTop: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-green-300 rounded-lg focus:ring-2 focus:ring-green-500"
              >
                <option value={50}>TOP 50</option>
                <option value={100}>TOP 100</option>
                <option value={200}>TOP 200</option>
                <option value={500}>TOP 500</option>
              </select>
              <p className="text-xs text-green-700 mt-2">排名需要进入前X名</p>
            </div>

            {/* 跳变榜阈值 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
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
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
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
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
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
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
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
            <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
              <label className="block text-sm font-semibold text-indigo-900 mb-2">
                ⚡ 波动率上升阈值
              </label>
              <select
                value={tempThresholds.volatilitySurgeMin}
                onChange={(e) => setTempThresholds({...tempThresholds, volatilitySurgeMin: Number(e.target.value)})}
                className="w-full px-3 py-2 border border-indigo-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value={30}>≥30%</option>
                <option value={50}>≥50%</option>
                <option value={100}>≥100%</option>
                <option value={150}>≥150%</option>
              </select>
              <p className="text-xs text-indigo-700 mt-2">波动率百分比变化≥X%</p>
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
              onClick={applyConfig}
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
