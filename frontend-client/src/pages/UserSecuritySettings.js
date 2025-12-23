import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  RefreshCw,
  Save,
  AlertCircle,
  X,
  Key,
  LogIn,
  Monitor,
  RotateCcw,
  CheckCircle,
  Info
} from 'lucide-react';
import secureApi from '../services/secureApi';

const SECURITY_KEYS = ['password', 'login', 'session'];

/**
 * 安全策略配置 (v2.2.1)
 * 集中管理密码策略、登录策略、会话策略
 */
const UserSecuritySettings = () => {
  const [configs, setConfigs] = useState({});
  const [categories, setCategories] = useState({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [changes, setChanges] = useState({});
  const [activeCategory, setActiveCategory] = useState('password');

  const loadConfigs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await secureApi.request({
        path: '/api/admin/config/by-category',
        method: 'GET'
      });

      // 仅保留安全相关分类
      const filteredCategories = Object.fromEntries(
        Object.entries(response.categories || {}).filter(([k]) => SECURITY_KEYS.includes(k))
      );
      const filteredConfigs = {};
      SECURITY_KEYS.forEach((key) => {
        if (response.configs && response.configs[key]) {
          filteredConfigs[key] = response.configs[key];
        }
      });

      setCategories(filteredCategories);
      setConfigs(filteredConfigs);
      setChanges({});
      if (!filteredCategories[activeCategory]) {
        const firstKey = Object.keys(filteredCategories)[0] || 'password';
        setActiveCategory(firstKey);
      }
    } catch (err) {
      setError(err.message || '加载配置失败');
    } finally {
      setLoading(false);
    }
  }, [activeCategory]);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleChange = (key, value, type) => {
    let parsedValue = value;
    if (type === 'int') {
      parsedValue = parseInt(value, 10) || 0;
    } else if (type === 'bool') {
      parsedValue = value === true || value === 'true';
    }
    setChanges((prev) => ({ ...prev, [key]: parsedValue }));
  };

  const handleSave = async () => {
    if (Object.keys(changes).length === 0) {
      setError('没有需要保存的更改');
      return;
    }
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      await secureApi.request({
        path: '/api/admin/config',
        method: 'PUT',
        body: { updates: changes }
      });
      setSuccess('配置已保存');
      setChanges({});
      loadConfigs();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || '保存配置失败');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async (key) => {
    if (!window.confirm(`确定要将 ${key} 重置为默认值吗？`)) return;
    try {
      await secureApi.request({
        path: `/api/admin/config/${key}/reset`,
        method: 'POST',
        body: {}
      });
      setSuccess('配置已重置');
      loadConfigs();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || '重置失败');
    }
  };

  const getCurrentValue = (config) => {
    if (config.key in changes) return changes[config.key];
    return config.value;
  };

  const getCategoryIcon = (category) => {
    const icons = {
      password: <Key className="w-5 h-5" />,
      login: <LogIn className="w-5 h-5" />,
      session: <Monitor className="w-5 h-5" />
    };
    return icons[category] || <Shield className="w-5 h-5" />;
  };

  const currentConfigs = configs[activeCategory] || [];
  const hasChanges = Object.keys(changes).length > 0;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Shield className="w-8 h-8 text-amber-400" />
              安全策略
            </h1>
            <p className="text-gray-400 mt-1">集中管理密码策略、登录策略、会话策略</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadConfigs}
              disabled={loading}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${hasChanges ? 'bg-amber-500 hover:bg-amber-600' : 'bg-gray-700 opacity-50 cursor-not-allowed'
                }`}
            >
              <Save className={`w-4 h-4 ${saving ? 'animate-pulse' : ''}`} />
              保存 {hasChanges && `(${Object.keys(changes).length})`}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {success && (
          <div className="mb-4 p-4 bg-green-500/20 border border-green-500/50 rounded-lg flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-green-300">{success}</span>
          </div>
        )}

        <div className="flex gap-2 mb-6">
          {Object.entries(categories).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveCategory(key)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${activeCategory === key ? 'bg-amber-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
            >
              {getCategoryIcon(key)}
              {label}
            </button>
          ))}
        </div>

        <div className="bg-gray-800 rounded-xl overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-gray-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : currentConfigs.length === 0 ? (
            <div className="p-12 text-center text-gray-400">暂无配置项</div>
          ) : (
            <div className="divide-y divide-gray-700">
              {currentConfigs.map((config) => (
                <ConfigItem
                  key={config.key}
                  config={config}
                  value={getCurrentValue(config)}
                  isChanged={config.key in changes}
                  onChange={(value) => handleChange(config.key, value, config.type)}
                  onReset={() => handleReset(config.key)}
                />
              ))}
            </div>
          )}
        </div>

        <div className="mt-6 p-4 bg-gray-800/50 rounded-xl">
          <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2 mb-2">
            <Info className="w-4 h-4" />
            配置说明
          </h3>
          <ul className="text-sm text-gray-400 space-y-1">
            <li>• 密码策略：控制密码复杂度、长度、过期等安全项。</li>
            <li>• 登录策略：控制登录失败锁定、验证码等安全措施。</li>
            <li>• 会话策略：控制 Token 有效期、最大设备数、会话状态策略。</li>
            <li>• 修改配置后点击“保存”生效，部分配置可能需用户重新登录。</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

const ConfigItem = ({ config, value, isChanged, onChange, onReset }) => {
  const renderInput = () => {
    if (config.type === 'bool') {
      return (
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={value === true}
            onChange={(e) => onChange(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
          <span className="ml-3 text-sm text-gray-400">{value ? '启用' : '禁用'}</span>
        </label>
      );
    }

    if (config.type === 'int') {
      return (
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-32 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-amber-500 text-right"
        />
      );
    }

    return (
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-64 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-amber-500"
      />
    );
  };

  return (
    <div className={`p-4 flex items-center justify-between ${isChanged ? 'bg-amber-500/10' : ''}`}>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{config.description}</span>
          {isChanged && (
            <span className="text-xs px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded">
              已修改
            </span>
          )}
        </div>
        <div className="text-xs text-gray-500 mt-1 font-mono">{config.key}</div>
      </div>
      <div className="flex items-center gap-3">
        {renderInput()}
        <button
          onClick={onReset}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors"
          title="重置为默认值"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default UserSecuritySettings;
