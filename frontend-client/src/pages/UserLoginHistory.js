/**
 * 用户登录记录页面
 * 显示所有用户的登录历史和活跃会话
 */
import React, { useState, useEffect } from 'react';
import { 
  Users, Monitor, Clock, Shield, RefreshCw, 
  CheckCircle, XCircle, Activity, Calendar,
  User, Smartphone, Laptop, Globe
} from 'lucide-react';
import secureApi from '../services/secureApi';

function UserLoginHistory() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    users: [],
    sessions: [],
    stats: {
      totalUsers: 0,
      activeUsers: 0,
      totalSessions: 0,
      activeSessions: 0
    }
  });
  const [refreshing, setRefreshing] = useState(false);

  // 加载数据
  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await secureApi.request({ 
        path: '/admin/login-history', 
        method: 'GET' 
      });
      
      if (response.success) {
        setData(response.data);
      } else {
        setError(response.error || '加载失败');
      }
    } catch (err) {
      console.error('加载登录记录失败:', err);
      setError(err.message || '加载失败');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // 刷新数据
  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  // 将 UTC 时间转换为北京时间
  const toBeijingTime = (timeStr) => {
    if (!timeStr) return null;
    // 服务器返回的是 UTC 时间，需要转换为北京时间 (UTC+8)
    const date = new Date(timeStr + 'Z'); // 添加 Z 确保解析为 UTC
    return date;
  };

  // 格式化时间（北京时间）
  const formatTime = (timeStr) => {
    const date = toBeijingTime(timeStr);
    if (!date) return '-';
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 格式化完整时间（北京时间）
  const formatFullTime = (timeStr) => {
    const date = toBeijingTime(timeStr);
    if (!date) return '-';
    return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
  };

  // 计算时间差
  const getTimeDiff = (timeStr) => {
    const time = toBeijingTime(timeStr);
    if (!time) return '-';
    const now = new Date();
    const diff = now - time;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    return `${days}天前`;
  };

  // 判断会话是否活跃（1小时内有活动）
  const isSessionActive = (lastActive) => {
    const active = toBeijingTime(lastActive);
    if (!active) return false;
    const now = new Date();
    return (now - active) < 3600000; // 1小时
  };

  // 获取设备图标
  const getDeviceIcon = (deviceName) => {
    if (!deviceName) return <Monitor className="h-4 w-4" />;
    const name = deviceName.toLowerCase();
    if (name.includes('mobile') || name.includes('phone') || name.includes('android') || name.includes('iphone')) {
      return <Smartphone className="h-4 w-4" />;
    }
    if (name.includes('laptop') || name.includes('macbook')) {
      return <Laptop className="h-4 w-4" />;
    }
    return <Monitor className="h-4 w-4" />;
  };

  // 统计卡片组件
  const StatCard = ({ icon: Icon, label, value, subValue, color }) => (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 mb-1">{label}</p>
          <p className={`text-3xl font-bold ${color}`}>{value}</p>
          {subValue && <p className="text-xs text-gray-400 mt-1">{subValue}</p>}
        </div>
        <div className={`p-3 rounded-xl ${color.replace('text-', 'bg-').replace('700', '100').replace('600', '100')}`}>
          <Icon className={`h-6 w-6 ${color}`} />
        </div>
      </div>
    </div>
  );

  if (loading && !refreshing) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin text-amber-500 mx-auto mb-3" />
          <p className="text-gray-500">加载登录记录...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-red-400 mx-auto mb-3" />
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-6 bg-gray-50">
      {/* 头部 */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
            <Users className="h-7 w-7 text-amber-500" />
            用户登录记录
          </h1>
          <p className="text-gray-500 mt-1">查看系统用户登录历史和活跃状态</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard 
          icon={Users} 
          label="总用户数" 
          value={data.stats.totalUsers}
          subValue="已注册用户"
          color="text-blue-600"
        />
        <StatCard 
          icon={Activity} 
          label="活跃用户" 
          value={data.stats.activeUsers}
          subValue="24小时内登录"
          color="text-green-600"
        />
        <StatCard 
          icon={Monitor} 
          label="总会话数" 
          value={data.stats.totalSessions}
          subValue="所有设备"
          color="text-purple-600"
        />
        <StatCard 
          icon={Globe} 
          label="在线会话" 
          value={data.stats.activeSessions}
          subValue="1小时内活跃"
          color="text-amber-600"
        />
      </div>

      {/* 用户列表 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 mb-6">
        <div className="p-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <User className="h-5 w-5 text-gray-600" />
            用户列表
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">角色</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">注册时间</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">最后登录</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">活跃设备</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                        user.role === 'admin' ? 'bg-amber-100' : 'bg-blue-100'
                      }`}>
                        {user.role === 'admin' ? (
                          <Shield className="h-5 w-5 text-amber-600" />
                        ) : (
                          <User className="h-5 w-5 text-blue-600" />
                        )}
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{user.username}</p>
                        <p className="text-xs text-gray-400">ID: {user.id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      user.role === 'admin' 
                        ? 'bg-amber-100 text-amber-700' 
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      {user.role === 'admin' ? '管理员' : '普通用户'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {user.is_active ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-sm">启用</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-500">
                        <XCircle className="h-4 w-4" />
                        <span className="text-sm">禁用</span>
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatTime(user.created_at)}
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm text-gray-600">{formatTime(user.last_login)}</p>
                      <p className="text-xs text-gray-400">{getTimeDiff(user.last_login)}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-blue-50 text-blue-600 rounded-full text-xs font-medium">
                      {user.session_count || 0} 个设备
                    </span>
                  </td>
                </tr>
              ))}
              {data.users.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-gray-400">
                    暂无用户数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 活跃会话列表 */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <Monitor className="h-5 w-5 text-gray-600" />
            活跃会话
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">设备</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">登录时间</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">最后活跃</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">过期时间</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.sessions.map((session) => {
                const active = isSessionActive(session.last_active);
                return (
                  <tr key={session.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          session.role === 'admin' ? 'bg-amber-100' : 'bg-blue-100'
                        }`}>
                          {session.role === 'admin' ? (
                            <Shield className="h-4 w-4 text-amber-600" />
                          ) : (
                            <User className="h-4 w-4 text-blue-600" />
                          )}
                        </div>
                        <span className="font-medium text-gray-800">{session.username}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getDeviceIcon(session.device_name)}
                        <div>
                          <p className="text-sm text-gray-700">{session.device_name || '未知设备'}</p>
                          <p className="text-xs text-gray-400 font-mono">{session.device_id?.slice(0, 16)}...</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm text-gray-600">{formatTime(session.created_at)}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm text-gray-600">{formatTime(session.last_active)}</p>
                        <p className="text-xs text-gray-400">{getTimeDiff(session.last_active)}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {formatTime(session.expires_at)}
                    </td>
                    <td className="px-4 py-3">
                      {active ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                          在线
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">
                          <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
                          离线
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {data.sessions.length === 0 && (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-gray-400">
                    暂无活跃会话
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 底部信息 */}
      <div className="mt-4 text-center text-xs text-gray-400">
        <Clock className="h-3 w-3 inline mr-1" />
        数据更新时间: {new Date().toLocaleString('zh-CN')}
      </div>
    </div>
  );
}

export default UserLoginHistory;
