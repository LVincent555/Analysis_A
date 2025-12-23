import React from 'react';
import { Settings, Info } from 'lucide-react';

/**
 * 系统配置占位页
 * 说明：策略类设置已移动到“用户中心 -> 用户登录设置”
 */
const SystemConfig = () => {
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Settings className="w-8 h-8 text-purple-400" />
              系统设置
            </h1>
            <p className="text-gray-400 mt-1">全局系统级配置（规划中）</p>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-8 text-gray-300">
          <div className="flex items-center gap-3 mb-3">
            <Info className="w-5 h-5 text-purple-300" />
            <span className="text-lg font-semibold">模块说明</span>
          </div>
          <ul className="space-y-2 text-sm text-gray-400">
            <li>• 安全策略配置（密码/登录/会话策略）请使用「安全策略」菜单。</li>
            <li>• 本模块将用于：日志保留天数、邮件通知等全局系统配置。</li>
            <li>• 当前暂无可配置项目。</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default SystemConfig;
