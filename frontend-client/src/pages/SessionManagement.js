import React, { useState, useEffect, useCallback } from 'react';
import {
  Monitor,
  RefreshCw,
  Search,
  LogOut,
  AlertCircle,
  X,
  ChevronLeft,
  ChevronRight,
  Eye,
  Users,
  Activity,
  Wifi,
  WifiOff,
  Clock,
  Smartphone,
  Laptop,
  Globe
} from 'lucide-react';
import secureApi from '../services/secureApi';

/**
 * 会话管理页面
 * 提供会话监控、强制下线等功能
 */
const SessionManagement = () => {
  // 会话列表状态
  const [sessions, setSessions] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 统计信息
  const [statistics, setStatistics] = useState(null);
  
  // 筛选状态
  const [username, setUsername] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [includeExpired, setIncludeExpired] = useState(false);
  
  // 弹窗状态
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedSession, setSelectedSession] = useState(null);
  
  // 自动刷新
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 加载会话列表
  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        include_expired: includeExpired.toString(),
        include_revoked: 'false'
      });
      
      if (username) params.append('username', username);
      if (statusFilter) params.append('session_status', statusFilter);
      
      const response = await secureApi.request({
        path: `/api/admin/sessions?${params.toString()}`,
        method: 'GET'
      });
      
      setSessions(response.items || []);
      setTotal(response.total || 0);
    } catch (err) {
      setError(err.message || '加载会话列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, username, statusFilter, includeExpired]);

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    try {
      const response = await secureApi.request({
        path: '/api/admin/sessions/statistics',
        method: 'GET'
      });
      setStatistics(response);
    } catch (err) {
      console.error('加载统计信息失败:', err);
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    loadSessions();
    loadStatistics();
  }, [loadSessions, loadStatistics]);

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      loadSessions();
      loadStatistics();
    }, 30000); // 30秒刷新一次
    
    return () => clearInterval(interval);
  }, [autoRefresh, loadSessions, loadStatistics]);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [username]);

  // 获取会话详情
  const loadSessionDetail = async (sessionId) => {
    try {
      const response = await secureApi.request({
        path: `/api/admin/sessions/${sessionId}`,
        method: 'GET'
      });
      setSelectedSession(response);
      setShowDetailModal(true);
    } catch (err) {
      setError(err.message || '获取会话详情失败');
    }
  };

  // 撤销会话
  const handleRevokeSession = async (session) => {
    if (!window.confirm(`确定要强制下线 ${session.username}@${session.device_name || session.device_id} 吗？`)) {
      return;
    }
    
    try {
      await secureApi.request({
        path: `/api/admin/sessions/${session.id}/revoke`,
        method: 'POST',
        body: {}
      });
      loadSessions();
      loadStatistics();
    } catch (err) {
      setError(err.message || '强制下线失败');
    }
  };

  // 撤销用户所有会话
  const handleRevokeUserSessions = async (userId, username) => {
    if (!window.confirm(`确定要强制下线 ${username} 的所有设备吗？`)) {
      return;
    }
    
    try {
      await secureApi.request({
        path: `/api/admin/sessions/user/${userId}/revoke-all`,
        method: 'POST',
        body: { exclude_current: false }
      });
      loadSessions();
      loadStatistics();
    } catch (err) {
      setError(err.message || '强制下线失败');
    }
  };

  // 状态徽章
  const StatusBadge = ({ status, color, label }) => {
    const colorStyles = {
      green: 'bg-green-500/20 text-green-400 ring-green-500/30',
      yellow: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30',
      red: 'bg-red-500/20 text-red-400 ring-red-500/30',
      gray: 'bg-gray-500/20 text-gray-400 ring-gray-500/30',
      black: 'bg-gray-700 text-gray-500 ring-gray-600'
    };
    
    const icons = {
      active: <Wifi className="w-3 h-3" />,
      idle: <Clock className="w-3 h-3" />,
      locked: <Monitor className="w-3 h-3" />,
      lost: <WifiOff className="w-3 h-3" />,
      offline: <WifiOff className="w-3 h-3" />
    };
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ring-1 ${colorStyles[color] || colorStyles.gray}`}>
        {icons[status]}
        {label}
      </span>
    );
  };

  // 平台图标
  const PlatformIcon = ({ platform }) => {
    if (platform === 'win32') return <Laptop className="w-4 h-4 text-blue-400" />;
    if (platform === 'darwin') return <Laptop className="w-4 h-4 text-gray-400" />;
    if (platform === 'linux') return <Monitor className="w-4 h-4 text-orange-400" />;
    return <Smartphone className="w-4 h-4 text-gray-400" />;
  };

  // 分页信息
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Activity className="w-8 h-8 text-green-400" />
              会话管理
            </h1>
            <p className="text-gray-400 mt-1">监控在线会话，管理用户连接</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded bg-gray-600 border-gray-500"
              />
              自动刷新
            </label>
            <button
              onClick={() => { loadSessions(); loadStatistics(); }}
              disabled={loading}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-4 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* 统计卡片 */}
        {statistics && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard
              icon={<Users className="w-6 h-6 text-blue-400" />}
              label="在线用户"
              value={statistics.online_users}
              color="blue"
            />
            <StatCard
              icon={<Monitor className="w-6 h-6 text-green-400" />}
              label="活跃会话"
              value={statistics.status_distribution?.active || 0}
              color="green"
            />
            <StatCard
              icon={<Clock className="w-6 h-6 text-yellow-400" />}
              label="空闲会话"
              value={(statistics.status_distribution?.idle || 0) + (statistics.status_distribution?.locked || 0)}
              color="yellow"
            />
            <StatCard
              icon={<WifiOff className="w-6 h-6 text-gray-400" />}
              label="离线会话"
              value={(statistics.status_distribution?.offline || 0) + (statistics.status_distribution?.lost || 0)}
              color="gray"
            />
          </div>
        )}

        {/* 筛选栏 */}
        <div className="bg-gray-800 rounded-xl p-4 mb-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* 搜索框 */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索用户名..."
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            
            {/* 状态筛选 */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">全部状态</option>
              <option value="active">活跃</option>
              <option value="idle">空闲</option>
              <option value="locked">锁屏</option>
              <option value="lost">失联</option>
              <option value="offline">离线</option>
            </select>
            
            {/* 包含过期 */}
            <label className="flex items-center gap-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={includeExpired}
                onChange={(e) => { setIncludeExpired(e.target.checked); setPage(1); }}
                className="rounded bg-gray-600 border-gray-500"
              />
              包含过期
            </label>
          </div>
        </div>

        {/* 会话表格 */}
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">用户</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">设备</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">状态</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">IP地址</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">最后活跃</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan="6" className="px-4 py-12 text-center text-gray-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    加载中...
                  </td>
                </tr>
              ) : sessions.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-4 py-12 text-center text-gray-400">
                    暂无会话数据
                  </td>
                </tr>
              ) : (
                sessions.map((session) => (
                  <tr key={session.id} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-green-500 to-blue-600 flex items-center justify-center text-sm font-bold">
                          {session.username?.charAt(0).toUpperCase() || '?'}
                        </div>
                        <div>
                          <div className="font-medium">{session.username}</div>
                          {session.nickname && session.nickname !== session.username && (
                            <div className="text-xs text-gray-400">{session.nickname}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <PlatformIcon platform={session.platform} />
                        <div>
                          <div className="text-sm">{session.device_name || session.device_id}</div>
                          {session.app_version && (
                            <div className="text-xs text-gray-500">v{session.app_version}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge
                        status={session.status}
                        color={session.status_color}
                        label={session.status_label}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 text-sm text-gray-400">
                        <Globe className="w-4 h-4" />
                        {session.ip_address || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {session.last_active ? formatRelativeTime(session.last_active) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => loadSessionDetail(session.id)}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="查看详情"
                        >
                          <Eye className="w-4 h-4 text-gray-400" />
                        </button>
                        <button
                          onClick={() => handleRevokeSession(session)}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="强制下线"
                        >
                          <LogOut className="w-4 h-4 text-red-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          
          {/* 分页 */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-400">
                共 {total} 条，第 {page}/{totalPages} 页
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                {[...Array(Math.min(5, totalPages))].map((_, i) => {
                  const pageNum = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                  if (pageNum > totalPages) return null;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className={`w-8 h-8 rounded ${
                        page === pageNum ? 'bg-green-600' : 'hover:bg-gray-700'
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 hover:bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 会话详情弹窗 */}
      {showDetailModal && selectedSession && (
        <SessionDetailModal
          session={selectedSession}
          onClose={() => { setShowDetailModal(false); setSelectedSession(null); }}
          onRevoke={() => {
            handleRevokeSession(selectedSession);
            setShowDetailModal(false);
            setSelectedSession(null);
          }}
          onRevokeAll={() => {
            handleRevokeUserSessions(selectedSession.user_id, selectedSession.username);
            setShowDetailModal(false);
            setSelectedSession(null);
          }}
        />
      )}
    </div>
  );
};

// ==================== 子组件 ====================

/**
 * 统计卡片
 */
const StatCard = ({ icon, label, value, color }) => {
  const bgColors = {
    blue: 'bg-blue-500/10',
    green: 'bg-green-500/10',
    yellow: 'bg-yellow-500/10',
    gray: 'bg-gray-500/10'
  };
  
  return (
    <div className={`${bgColors[color]} rounded-xl p-4`}>
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-sm text-gray-400">{label}</div>
        </div>
      </div>
    </div>
  );
};

/**
 * 会话详情弹窗
 */
const SessionDetailModal = ({ session, onClose, onRevoke, onRevokeAll }) => {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">会话详情</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-4 space-y-4">
          {/* 用户信息 */}
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-green-500 to-blue-600 flex items-center justify-center text-xl font-bold">
              {session.username?.charAt(0).toUpperCase() || '?'}
            </div>
            <div>
              <h3 className="text-lg font-semibold">{session.username}</h3>
              {session.nickname && <p className="text-gray-400">{session.nickname}</p>}
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                session.user_role === 'admin' ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'
              }`}>
                {session.user_role === 'admin' ? '管理员' : '普通用户'}
              </span>
            </div>
          </div>
          
          {/* 设备信息 */}
          <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
            <h4 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Monitor className="w-4 h-4" />
              设备信息
            </h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <InfoItem label="设备名称" value={session.device_name || session.device_id} />
              <InfoItem label="平台" value={session.platform || '-'} />
              <InfoItem label="版本" value={session.app_version ? `v${session.app_version}` : '-'} />
              <InfoItem label="IP地址" value={session.ip_address || '-'} />
            </div>
            {session.user_agent && (
              <div className="text-xs text-gray-500 break-all">
                {session.user_agent}
              </div>
            )}
          </div>
          
          {/* 状态信息 */}
          <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
            <h4 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              状态信息
            </h4>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-400">当前状态</span>
                <div className="mt-1">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ring-1 ${
                    session.status === 'active' ? 'bg-green-500/20 text-green-400 ring-green-500/30' :
                    session.status === 'idle' ? 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30' :
                    session.status === 'lost' ? 'bg-red-500/20 text-red-400 ring-red-500/30' :
                    'bg-gray-500/20 text-gray-400 ring-gray-500/30'
                  }`}>
                    {session.status_label}
                  </span>
                </div>
              </div>
              <InfoItem label="创建时间" value={session.created_at ? new Date(session.created_at).toLocaleString() : '-'} />
              <InfoItem label="最后活跃" value={session.last_active ? new Date(session.last_active).toLocaleString() : '-'} />
              <InfoItem label="过期时间" value={session.expires_at ? new Date(session.expires_at).toLocaleString() : '-'} />
            </div>
          </div>
          
          {/* 操作按钮 */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={onRevoke}
              className="flex-1 py-2 bg-red-600 hover:bg-red-700 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              强制下线此设备
            </button>
            <button
              onClick={onRevokeAll}
              className="flex-1 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <Users className="w-4 h-4" />
              下线所有设备
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * 信息项组件
 */
const InfoItem = ({ label, value }) => (
  <div>
    <span className="text-gray-400">{label}</span>
    <p className="text-gray-200">{value}</p>
  </div>
);

/**
 * 格式化相对时间
 */
function formatRelativeTime(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) return '刚刚';
  if (diffMin < 60) return `${diffMin}分钟前`;
  if (diffHour < 24) return `${diffHour}小时前`;
  if (diffDay < 7) return `${diffDay}天前`;
  return date.toLocaleDateString();
}

export default SessionManagement;
