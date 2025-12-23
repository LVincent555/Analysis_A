import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  UserPlus,
  Search,
  RefreshCw,
  Edit2,
  Trash2,
  Lock,
  Unlock,
  Key,
  MoreVertical,
  CheckCircle,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  X,
  Eye,
  EyeOff,
  Monitor
} from 'lucide-react';
import secureApi from '../services/secureApi';

/**
 * 用户管理页面
 * 提供用户CRUD、状态管理、密码重置等功能
 */
const UserManagement = () => {
  // 用户列表状态
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 筛选状态
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  
  // 弹窗状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showResetPwdModal, setShowResetPwdModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // 批量操作
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showBatchMenu, setShowBatchMenu] = useState(false);

  // 加载用户列表
  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: 'created_at',
        sort_order: 'desc'
      });
      
      if (search) params.append('search', search);
      if (roleFilter) params.append('role', roleFilter);
      if (statusFilter) params.append('status', statusFilter);
      
      const response = await secureApi.request({
        path: `/api/admin/users?${params.toString()}`,
        method: 'GET'
      });
      
      setUsers(response.items || []);
      setTotal(response.total || 0);
    } catch (err) {
      setError(err.message || '加载用户列表失败');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, roleFilter, statusFilter]);

  // 初始化加载
  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // 搜索防抖
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      loadUsers();
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // 获取用户详情
  const loadUserDetail = async (userId) => {
    try {
      const response = await secureApi.request({
        path: `/api/admin/users/${userId}`,
        method: 'GET'
      });
      setSelectedUser(response);
      setShowDetailModal(true);
    } catch (err) {
      setError(err.message || '获取用户详情失败');
    }
  };

  // 创建用户
  const handleCreateUser = async (userData) => {
    try {
      await secureApi.request({
        path: '/api/admin/users',
        method: 'POST',
        body: userData
      });
      setShowCreateModal(false);
      loadUsers();
    } catch (err) {
      throw new Error(err.message || '创建用户失败');
    }
  };

  // 更新用户
  const handleUpdateUser = async (userId, userData) => {
    try {
      await secureApi.request({
        path: `/api/admin/users/${userId}`,
        method: 'PUT',
        body: userData
      });
      setShowEditModal(false);
      setSelectedUser(null);
      loadUsers();
    } catch (err) {
      throw new Error(err.message || '更新用户失败');
    }
  };

  // 切换用户状态
  const handleToggleStatus = async (user) => {
    const action = user.is_active ? '禁用' : '启用';
    if (!window.confirm(`确定要${action}用户 ${user.username} 吗？`)) return;
    
    try {
      await secureApi.request({
        path: `/api/admin/users/${user.id}/toggle-status`,
        method: 'POST',
        body: { is_active: !user.is_active }
      });
      loadUsers();
    } catch (err) {
      setError(err.message || `${action}用户失败`);
    }
  };

  // 解锁用户
  const handleUnlock = async (user) => {
    try {
      await secureApi.request({
        path: `/api/admin/users/${user.id}/unlock`,
        method: 'POST'
      });
      loadUsers();
    } catch (err) {
      setError(err.message || '解锁用户失败');
    }
  };

  // 重置密码
  const handleResetPassword = async (userId, newPassword, forceLogout) => {
    try {
      await secureApi.request({
        path: `/api/admin/users/${userId}/reset-password`,
        method: 'POST',
        body: { new_password: newPassword, force_logout: forceLogout }
      });
      setShowResetPwdModal(false);
      setSelectedUser(null);
    } catch (err) {
      throw new Error(err.message || '重置密码失败');
    }
  };

  // 删除用户
  const handleDeleteUser = async (user) => {
    if (!window.confirm(`确定要删除用户 ${user.username} 吗？\n此操作将禁用该用户并撤销所有会话。`)) return;
    
    try {
      await secureApi.request({
        path: `/api/admin/users/${user.id}?hard=false`,
        method: 'DELETE'
      });
      loadUsers();
    } catch (err) {
      setError(err.message || '删除用户失败');
    }
  };

  // 批量操作
  const handleBatchAction = async (action) => {
    if (selectedIds.size === 0) return;
    
    const actionText = { enable: '启用', disable: '禁用', delete: '删除' };
    if (!window.confirm(`确定要${actionText[action]} ${selectedIds.size} 个用户吗？`)) return;
    
    try {
      await secureApi.request({
        path: '/api/admin/users/batch',
        method: 'POST',
        body: { action, user_ids: Array.from(selectedIds) }
      });
      setSelectedIds(new Set());
      setShowBatchMenu(false);
      loadUsers();
    } catch (err) {
      setError(err.message || '批量操作失败');
    }
  };

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedIds.size === users.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(users.map(u => u.id)));
    }
  };

  // 切换单个选择
  const toggleSelect = (id) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  // 状态徽章
  const StatusBadge = ({ status }) => {
    const styles = {
      active: 'bg-green-500/20 text-green-400 ring-green-500/30',
      inactive: 'bg-gray-500/20 text-gray-400 ring-gray-500/30',
      locked: 'bg-red-500/20 text-red-400 ring-red-500/30',
      expired: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30',
      deleted: 'bg-gray-700 text-gray-500 ring-gray-600'
    };
    const labels = {
      active: '正常',
      inactive: '禁用',
      locked: '锁定',
      expired: '过期',
      deleted: '已删除'
    };
    return (
      <span className={`px-2 py-0.5 text-xs rounded-full ring-1 ${styles[status] || styles.inactive}`}>
        {labels[status] || status}
      </span>
    );
  };

  // 角色徽章
  const RoleBadge = ({ role }) => {
    const isAdmin = role === 'admin';
    return (
      <span className={`px-2 py-0.5 text-xs rounded-full ${
        isAdmin ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'
      }`}>
        {isAdmin ? '管理员' : '普通用户'}
      </span>
    );
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
              <Users className="w-8 h-8 text-blue-400" />
              用户管理
            </h1>
            <p className="text-gray-400 mt-1">管理系统用户账户</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center gap-2 transition-colors"
          >
            <UserPlus className="w-5 h-5" />
            创建用户
          </button>
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

        {/* 筛选栏 */}
        <div className="bg-gray-800 rounded-xl p-4 mb-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* 搜索框 */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="搜索用户名、邮箱、昵称..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            
            {/* 角色筛选 */}
            <select
              value={roleFilter}
              onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">全部角色</option>
              <option value="admin">管理员</option>
              <option value="user">普通用户</option>
            </select>
            
            {/* 状态筛选 */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="">全部状态</option>
              <option value="active">正常</option>
              <option value="inactive">禁用</option>
              <option value="locked">锁定</option>
              <option value="expired">过期</option>
            </select>
            
            {/* 刷新按钮 */}
            <button
              onClick={loadUsers}
              disabled={loading}
              className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            
            {/* 批量操作 */}
            {selectedIds.size > 0 && (
              <div className="relative">
                <button
                  onClick={() => setShowBatchMenu(!showBatchMenu)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2"
                >
                  已选 {selectedIds.size} 项
                  <MoreVertical className="w-4 h-4" />
                </button>
                {showBatchMenu && (
                  <div className="absolute right-0 top-full mt-1 w-32 bg-gray-700 rounded-lg shadow-lg overflow-hidden z-10">
                    <button
                      onClick={() => handleBatchAction('enable')}
                      className="w-full px-4 py-2 text-left hover:bg-gray-600 text-green-400"
                    >
                      批量启用
                    </button>
                    <button
                      onClick={() => handleBatchAction('disable')}
                      className="w-full px-4 py-2 text-left hover:bg-gray-600 text-yellow-400"
                    >
                      批量禁用
                    </button>
                    <button
                      onClick={() => handleBatchAction('delete')}
                      className="w-full px-4 py-2 text-left hover:bg-gray-600 text-red-400"
                    >
                      批量删除
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 用户表格 */}
        <div className="bg-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedIds.size === users.length && users.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded bg-gray-600 border-gray-500"
                  />
                </th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">用户</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">角色</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">状态</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">会话</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">注册时间</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">最后登录</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan="8" className="px-4 py-12 text-center text-gray-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    加载中...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-4 py-12 text-center text-gray-400">
                    暂无用户数据
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(user.id)}
                        onChange={() => toggleSelect(user.id)}
                        className="rounded bg-gray-600 border-gray-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm font-bold">
                          {user.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-medium">{user.username}</div>
                          {user.nickname && user.nickname !== user.username && (
                            <div className="text-xs text-gray-400">{user.nickname}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <RoleBadge role={user.role} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={user.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {user.active_sessions || 0}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {user.last_login ? new Date(user.last_login).toLocaleString() : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => loadUserDetail(user.id)}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="查看详情"
                        >
                          <Eye className="w-4 h-4 text-gray-400" />
                        </button>
                        <button
                          onClick={() => { setSelectedUser(user); setShowEditModal(true); }}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="编辑"
                        >
                          <Edit2 className="w-4 h-4 text-blue-400" />
                        </button>
                        <button
                          onClick={() => { setSelectedUser(user); setShowResetPwdModal(true); }}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="重置密码"
                        >
                          <Key className="w-4 h-4 text-yellow-400" />
                        </button>
                        {user.status === 'locked' ? (
                          <button
                            onClick={() => handleUnlock(user)}
                            className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                            title="解锁"
                          >
                            <Unlock className="w-4 h-4 text-green-400" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleToggleStatus(user)}
                            className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                            title={user.is_active ? '禁用' : '启用'}
                          >
                            {user.is_active ? (
                              <Lock className="w-4 h-4 text-orange-400" />
                            ) : (
                              <CheckCircle className="w-4 h-4 text-green-400" />
                            )}
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteUser(user)}
                          className="p-1.5 hover:bg-gray-600 rounded transition-colors"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4 text-red-400" />
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

      {/* 创建用户弹窗 */}
      {showCreateModal && (
        <UserFormModal
          title="创建用户"
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateUser}
        />
      )}

      {/* 编辑用户弹窗 */}
      {showEditModal && selectedUser && (
        <UserFormModal
          title="编辑用户"
          user={selectedUser}
          onClose={() => { setShowEditModal(false); setSelectedUser(null); }}
          onSubmit={(data) => handleUpdateUser(selectedUser.id, data)}
        />
      )}

      {/* 用户详情弹窗 */}
      {showDetailModal && selectedUser && (
        <UserDetailModal
          user={selectedUser}
          onClose={() => { setShowDetailModal(false); setSelectedUser(null); }}
        />
      )}

      {/* 重置密码弹窗 */}
      {showResetPwdModal && selectedUser && (
        <ResetPasswordModal
          user={selectedUser}
          onClose={() => { setShowResetPwdModal(false); setSelectedUser(null); }}
          onSubmit={(pwd, logout) => handleResetPassword(selectedUser.id, pwd, logout)}
        />
      )}
    </div>
  );
};

// ==================== 子组件 ====================

/**
 * 用户表单弹窗（创建/编辑）
 */
const UserFormModal = ({ title, user, onClose, onSubmit }) => {
  const [formData, setFormData] = useState({
    username: user?.username || '',
    password: '',
    email: user?.email || '',
    phone: user?.phone || '',
    nickname: user?.nickname || '',
    role: user?.role || 'user',
    allowed_devices: user?.allowed_devices || 3,
    offline_enabled: user?.offline_enabled ?? true,
    offline_days: user?.offline_days || 7,
    remark: user?.remark || ''
  });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const isEdit = !!user;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    // 验证
    if (!isEdit && !formData.username) {
      setError('请输入用户名');
      return;
    }
    if (!isEdit && !formData.password) {
      setError('请输入密码');
      return;
    }
    if (!isEdit && formData.password.length < 6) {
      setError('密码长度至少6位');
      return;
    }
    
    try {
      setLoading(true);
      const submitData = { ...formData };
      
      // 编辑模式不提交用户名和密码
      if (isEdit) {
        delete submitData.username;
        delete submitData.password;
      }
      
      await onSubmit(submitData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}
          
          {/* 用户名 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">用户名 *</label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
              disabled={isEdit}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 disabled:opacity-50"
              placeholder="请输入用户名"
            />
          </div>
          
          {/* 密码（仅创建时） */}
          {!isEdit && (
            <div>
              <label className="block text-sm text-gray-400 mb-1">密码 *</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.password}
                  onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
                  className="w-full px-3 py-2 pr-10 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                  placeholder="请输入密码（至少6位）"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          )}
          
          {/* 昵称 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">昵称</label>
            <input
              type="text"
              value={formData.nickname}
              onChange={(e) => setFormData(prev => ({ ...prev, nickname: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              placeholder="显示名称"
            />
          </div>
          
          {/* 邮箱和手机 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">邮箱</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="user@example.com"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">手机</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData(prev => ({ ...prev, phone: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="13800138000"
              />
            </div>
          </div>
          
          {/* 角色 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">角色</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
            >
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
            </select>
          </div>
          
          {/* 设备和离线配置 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">允许设备数</label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.allowed_devices}
                onChange={(e) => setFormData(prev => ({ ...prev, allowed_devices: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">离线天数</label>
              <input
                type="number"
                min="1"
                max="30"
                value={formData.offline_days}
                onChange={(e) => setFormData(prev => ({ ...prev, offline_days: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
          
          {/* 离线功能开关 */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="offline_enabled"
              checked={formData.offline_enabled}
              onChange={(e) => setFormData(prev => ({ ...prev, offline_enabled: e.target.checked }))}
              className="rounded bg-gray-600 border-gray-500"
            />
            <label htmlFor="offline_enabled" className="text-sm text-gray-300">允许离线使用</label>
          </div>
          
          {/* 备注 */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">备注</label>
            <textarea
              value={formData.remark}
              onChange={(e) => setFormData(prev => ({ ...prev, remark: e.target.value }))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 resize-none"
              rows="2"
              placeholder="备注信息"
            />
          </div>
          
          {/* 按钮 */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? '提交中...' : (isEdit ? '保存' : '创建')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

/**
 * 用户详情弹窗
 */
const UserDetailModal = ({ user, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">用户详情</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-4">
          {/* 基本信息 */}
          <div className="flex items-start gap-4 mb-6">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl font-bold">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div>
              <h3 className="text-xl font-semibold">{user.username}</h3>
              {user.nickname && <p className="text-gray-400">{user.nickname}</p>}
              <div className="flex items-center gap-2 mt-2">
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  user.role === 'admin' ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {user.role === 'admin' ? '管理员' : '普通用户'}
                </span>
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  user.status === 'active' ? 'bg-green-500/20 text-green-400' :
                  user.status === 'locked' ? 'bg-red-500/20 text-red-400' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {user.status === 'active' ? '正常' : user.status === 'locked' ? '锁定' : '禁用'}
                </span>
              </div>
            </div>
          </div>
          
          {/* 详细信息 */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <InfoItem label="邮箱" value={user.email || '-'} />
            <InfoItem label="手机" value={user.phone || '-'} />
            <InfoItem label="允许设备数" value={user.allowed_devices} />
            <InfoItem label="离线天数" value={user.offline_days} />
            <InfoItem label="离线功能" value={user.offline_enabled ? '已启用' : '已禁用'} />
            <InfoItem label="登录失败次数" value={user.failed_attempts || 0} />
            <InfoItem label="注册时间" value={user.created_at ? new Date(user.created_at).toLocaleString() : '-'} />
            <InfoItem label="最后登录" value={user.last_login ? new Date(user.last_login).toLocaleString() : '-'} />
          </div>
          
          {/* 备注 */}
          {user.remark && (
            <div className="mb-6">
              <h4 className="text-sm text-gray-400 mb-2">备注</h4>
              <p className="text-gray-300 bg-gray-700/50 p-3 rounded-lg">{user.remark}</p>
            </div>
          )}
          
          {/* 活跃会话 */}
          {user.sessions && user.sessions.length > 0 && (
            <div>
              <h4 className="text-sm text-gray-400 mb-2 flex items-center gap-2">
                <Monitor className="w-4 h-4" />
                活跃会话 ({user.sessions.length})
              </h4>
              <div className="space-y-2">
                {user.sessions.map((session, idx) => (
                  <div key={idx} className="bg-gray-700/50 p-3 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Monitor className="w-4 h-4 text-blue-400" />
                        <span>{session.device_name || session.device_id}</span>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        session.current_status === 'online' ? 'bg-green-500/20 text-green-400' :
                        session.current_status === 'idle' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {session.current_status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {session.ip_address && <span className="mr-3">IP: {session.ip_address}</span>}
                      {session.platform && <span className="mr-3">{session.platform}</span>}
                      {session.last_active && (
                        <span>最后活跃: {new Date(session.last_active).toLocaleString()}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
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
const InfoItem = ({ label, value }) => (
  <div>
    <span className="text-sm text-gray-400">{label}</span>
    <p className="text-gray-200">{value}</p>
  </div>
);

/**
 * 重置密码弹窗
 */
const ResetPasswordModal = ({ user, onClose, onSubmit }) => {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [forceLogout, setForceLogout] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    
    if (!password) {
      setError('请输入新密码');
      return;
    }
    if (password.length < 6) {
      setError('密码长度至少6位');
      return;
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    
    try {
      setLoading(true);
      await onSubmit(password, forceLogout);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">重置密码</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div className="text-center text-gray-400 mb-4">
            为用户 <span className="text-white font-medium">{user.username}</span> 重置密码
          </div>
          
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}
          
          <div>
            <label className="block text-sm text-gray-400 mb-1">新密码</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 pr-10 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
                placeholder="请输入新密码（至少6位）"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm text-gray-400 mb-1">确认密码</label>
            <input
              type={showPassword ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500"
              placeholder="请再次输入新密码"
            />
          </div>
          
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="force_logout"
              checked={forceLogout}
              onChange={(e) => setForceLogout(e.target.checked)}
              className="rounded bg-gray-600 border-gray-500"
            />
            <label htmlFor="force_logout" className="text-sm text-gray-300">
              强制登出所有设备
            </label>
          </div>
          
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {loading ? '重置中...' : '重置密码'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserManagement;
