import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  RefreshCw,
  Search,
  Download,
  AlertCircle,
  X,
  ChevronLeft,
  ChevronRight,
  Eye,
  Filter,
  Calendar,
  CheckCircle,
  XCircle,
  LogIn,
  UserPlus,
  Shield,
  Settings,
  Monitor,
  TrendingUp
} from 'lucide-react';
import secureApi from '../services/secureApi';

/**
 * 操作日志页面
 * 提供日志查询、统计、导出等功能
 */
const OperationLogs = () => {
  // 日志列表状态
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 统计信息
  const [statistics, setStatistics] = useState(null);
  
  // 筛选状态
  const [logType, setLogType] = useState('');
  const [action, setAction] = useState('');
  const [logStatus, setLogStatus] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [search, setSearch] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  
  // 日志类型和动作列表
  const [logTypes, setLogTypes] = useState({});
  const [logActions, setLogActions] = useState({});
  
  // 弹窗状态
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  // 加载日志类型
  useEffect(() => {
    const loadTypes = async () => {
      try {
        const response = await secureApi.request({
          path: '/api/admin/logs/types',
          method: 'GET'
        });
        setLogTypes(response.types || {});
        setLogActions(response.actions || {});
      } catch (err) {
        console.error('加载日志类型失败:', err);
      }
    };
    loadTypes();
  }, []);

  // 加载日志列表
  const loadLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      
      if (logType) params.append('log_type', logType);
      if (action) params.append('action', action);
      if (logStatus) params.append('log_status', logStatus);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (search) params.append('search', search);
      
      const response = await secureApi.request({
        path: `/api/admin/logs?${params.toString()}`,
        method: 'GET'
      });
      
      setLogs(response.items || []);
      setTotal(response.total || 0);
    } catch (err) {
      setError(err.message || '加载日志列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, logType, action, logStatus, startDate, endDate, search]);

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    try {
      const response = await secureApi.request({
        path: '/api/admin/logs/statistics?days=7',
        method: 'GET'
      });
      setStatistics(response);
    } catch (err) {
      console.error('加载统计信息失败:', err);
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    loadLogs();
    loadStatistics();
  }, [loadLogs, loadStatistics]);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // 获取日志详情
  const loadLogDetail = async (logId) => {
    try {
      const response = await secureApi.request({
        path: `/api/admin/logs/${logId}`,
        method: 'GET'
      });
      setSelectedLog(response);
      setShowDetailModal(true);
    } catch (err) {
      setError(err.message || '获取日志详情失败');
    }
  };

  // 导出日志
  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (logType) params.append('log_type', logType);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      params.append('limit', '1000');
      
      // 直接打开下载链接
      const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      window.open(`${baseUrl}/api/admin/logs/export/csv?${params.toString()}`, '_blank');
    } catch (err) {
      setError(err.message || '导出失败');
    }
  };

  // 日志类型图标
  const getTypeIcon = (type) => {
    const icons = {
      LOGIN: <LogIn className="w-4 h-4" />,
      USER: <UserPlus className="w-4 h-4" />,
      SESSION: <Monitor className="w-4 h-4" />,
      SECURITY: <Shield className="w-4 h-4" />,
      SYSTEM: <Settings className="w-4 h-4" />
    };
    return icons[type] || <FileText className="w-4 h-4" />;
  };

  // 日志类型颜色
  const getTypeColor = (type) => {
    const colors = {
      LOGIN: 'bg-blue-500/20 text-blue-400 ring-blue-500/30',
      USER: 'bg-green-500/20 text-green-400 ring-green-500/30',
      SESSION: 'bg-purple-500/20 text-purple-400 ring-purple-500/30',
      SECURITY: 'bg-red-500/20 text-red-400 ring-red-500/30',
      SYSTEM: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30'
    };
    return colors[type] || 'bg-gray-500/20 text-gray-400 ring-gray-500/30';
  };

  // 分页信息
  const totalPages = Math.ceil(total / pageSize);

  // 重置筛选
  const resetFilters = () => {
    setLogType('');
    setAction('');
    setLogStatus('');
    setStartDate('');
    setEndDate('');
    setSearch('');
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <FileText className="w-8 h-8 text-blue-400" />
              操作日志
            </h1>
            <p className="text-gray-400 mt-1">查看系统操作记录和安全事件</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg flex items-center gap-2 transition-colors"
            >
              <Download className="w-4 h-4" />
              导出
            </button>
            <button
              onClick={() => { loadLogs(); loadStatistics(); }}
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
              icon={<FileText className="w-6 h-6 text-blue-400" />}
              label="7天总日志"
              value={statistics.total}
              color="blue"
            />
            <StatCard
              icon={<CheckCircle className="w-6 h-6 text-green-400" />}
              label="成功操作"
              value={statistics.status_distribution?.success || 0}
              color="green"
            />
            <StatCard
              icon={<XCircle className="w-6 h-6 text-red-400" />}
              label="登录失败"
              value={statistics.login_failed_count}
              color="red"
            />
            <StatCard
              icon={<Shield className="w-6 h-6 text-yellow-400" />}
              label="安全事件"
              value={statistics.security_event_count}
              color="yellow"
            />
          </div>
        )}

        {/* 趋势图 */}
        {statistics?.daily_trend && statistics.daily_trend.length > 0 && (
          <div className="bg-gray-800 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              7天趋势
            </h3>
            <div className="flex items-end gap-1 h-20">
              {statistics.daily_trend.map((day, i) => {
                const maxCount = Math.max(...statistics.daily_trend.map(d => d.count));
                const height = maxCount > 0 ? (day.count / maxCount) * 100 : 0;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full bg-blue-500/50 rounded-t transition-all"
                      style={{ height: `${height}%`, minHeight: day.count > 0 ? '4px' : '0' }}
                    />
                    <span className="text-xs text-gray-500">
                      {day.date ? new Date(day.date).getDate() : ''}
                    </span>
                  </div>
                );
              })}
            </div>
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
                placeholder="搜索操作者、目标、IP..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            
            {/* 日志类型 */}
            <select
              value={logType}
              onChange={(e) => { setLogType(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">全部类型</option>
              {Object.entries(logTypes).map(([key, label]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
            
            {/* 状态筛选 */}
            <select
              value={logStatus}
              onChange={(e) => { setLogStatus(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">全部状态</option>
              <option value="success">成功</option>
              <option value="failed">失败</option>
            </select>
            
            {/* 更多筛选 */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                showFilters ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
              }`}
            >
              <Filter className="w-4 h-4" />
              更多
            </button>
            
            {/* 重置 */}
            {(logType || action || logStatus || startDate || endDate || search) && (
              <button
                onClick={resetFilters}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                重置
              </button>
            )}
          </div>
          
          {/* 展开的筛选项 */}
          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-700 flex flex-wrap items-center gap-4">
              {/* 日期范围 */}
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-gray-400" />
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
                  className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                />
                <span className="text-gray-400">至</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
                  className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                />
              </div>
              
              {/* 操作动作 */}
              <select
                value={action}
                onChange={(e) => { setAction(e.target.value); setPage(1); }}
                className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              >
                <option value="">全部操作</option>
                {Object.entries(logActions).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* 日志表格 */}
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">时间</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">类型</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">操作</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">操作者</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">目标</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">状态</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan="7" className="px-4 py-12 text-center text-gray-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    加载中...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-4 py-12 text-center text-gray-400">
                    暂无日志数据
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {log.created_at ? new Date(log.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ring-1 ${getTypeColor(log.log_type)}`}>
                        {getTypeIcon(log.log_type)}
                        {log.log_type_label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {log.action_label}
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">{log.operator_name}</div>
                      {log.ip_address && (
                        <div className="text-xs text-gray-500">{log.ip_address}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {log.target_name || '-'}
                    </td>
                    <td className="px-4 py-3">
                      {log.status === 'success' ? (
                        <span className="inline-flex items-center gap-1 text-green-400 text-sm">
                          <CheckCircle className="w-4 h-4" />
                          成功
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-red-400 text-sm">
                          <XCircle className="w-4 h-4" />
                          失败
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end">
                        <button
                          onClick={() => loadLogDetail(log.id)}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="查看详情"
                        >
                          <Eye className="w-4 h-4 text-gray-400" />
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
                        page === pageNum ? 'bg-blue-600' : 'hover:bg-gray-700'
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

      {/* 日志详情弹窗 */}
      {showDetailModal && selectedLog && (
        <LogDetailModal
          log={selectedLog}
          onClose={() => { setShowDetailModal(false); setSelectedLog(null); }}
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
    red: 'bg-red-500/10',
    yellow: 'bg-yellow-500/10'
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
 * 日志详情弹窗
 */
const LogDetailModal = ({ log, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">日志详情</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-4 space-y-4">
          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <InfoItem label="日志类型" value={log.log_type_label} />
            <InfoItem label="操作动作" value={log.action_label} />
            <InfoItem label="操作者" value={log.operator_name} />
            <InfoItem label="目标" value={log.target_name || '-'} />
            <InfoItem label="IP地址" value={log.ip_address || '-'} />
            <InfoItem label="状态" value={log.status === 'success' ? '成功' : '失败'} />
            <InfoItem 
              label="时间" 
              value={log.created_at ? new Date(log.created_at).toLocaleString() : '-'} 
              className="col-span-2"
            />
          </div>
          
          {/* User Agent */}
          {log.user_agent && (
            <div className="bg-gray-700/50 rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-300 mb-2">User Agent</h4>
              <p className="text-xs text-gray-400 break-all">{log.user_agent}</p>
            </div>
          )}
          
          {/* 详细信息 */}
          {log.detail && (
            <div className="bg-gray-700/50 rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-300 mb-2">详细信息</h4>
              <pre className="text-xs text-gray-400 overflow-x-auto">
                {JSON.stringify(log.detail, null, 2)}
              </pre>
            </div>
          )}
          
          {/* 变更对比 */}
          {(log.old_value || log.new_value) && (
            <div className="grid grid-cols-2 gap-4">
              {log.old_value && (
                <div className="bg-red-500/10 rounded-lg p-3">
                  <h4 className="text-sm font-medium text-red-400 mb-2">修改前</h4>
                  <pre className="text-xs text-gray-400 overflow-x-auto">
                    {JSON.stringify(log.old_value, null, 2)}
                  </pre>
                </div>
              )}
              {log.new_value && (
                <div className="bg-green-500/10 rounded-lg p-3">
                  <h4 className="text-sm font-medium text-green-400 mb-2">修改后</h4>
                  <pre className="text-xs text-gray-400 overflow-x-auto">
                    {JSON.stringify(log.new_value, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
          
          {/* 错误信息 */}
          {log.error_message && (
            <div className="bg-red-500/10 rounded-lg p-3">
              <h4 className="text-sm font-medium text-red-400 mb-2">错误信息</h4>
              <p className="text-sm text-red-300">{log.error_message}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * 信息项组件
 */
const InfoItem = ({ label, value, className = '' }) => (
  <div className={className}>
    <span className="text-sm text-gray-400">{label}</span>
    <p className="text-gray-200">{value}</p>
  </div>
);

export default OperationLogs;
