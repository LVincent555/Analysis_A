import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  RefreshCw,
  Plus,
  Edit2,
  Trash2,
  AlertCircle,
  X,
  CheckCircle,
  Users,
  Lock,
  Eye,
  Save
} from 'lucide-react';
import secureApi from '../services/secureApi';

/**
 * 角色管理页面
 * 提供角色CRUD、权限配置等功能
 */
const RoleManagement = () => {
  // 角色列表状态
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  // 权限定义
  const [allPermissions, setAllPermissions] = useState({});
  
  // 弹窗状态
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);

  // 加载权限定义
  useEffect(() => {
    const loadPermissions = async () => {
      try {
        const response = await secureApi.request({
          path: '/api/admin/roles/permissions',
          method: 'GET'
        });
        setAllPermissions(response.permissions || {});
      } catch (err) {
        console.error('加载权限定义失败:', err);
      }
    };
    loadPermissions();
  }, []);

  // 加载角色列表
  const loadRoles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await secureApi.request({
        path: '/api/admin/roles?include_inactive=true',
        method: 'GET'
      });
      
      setRoles(response.roles || []);
    } catch (err) {
      setError(err.message || '加载角色列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    loadRoles();
  }, [loadRoles]);

  // 查看角色详情
  const handleViewDetail = async (roleId) => {
    try {
      const response = await secureApi.request({
        path: `/api/admin/roles/${roleId}`,
        method: 'GET'
      });
      setSelectedRole(response);
      setShowDetailModal(true);
    } catch (err) {
      setError(err.message || '获取角色详情失败');
    }
  };

  // 编辑角色
  const handleEdit = (role) => {
    setSelectedRole(role);
    setShowEditModal(true);
  };

  // 删除角色
  const handleDelete = async (role) => {
    if (role.is_system) {
      setError('系统预设角色不可删除');
      return;
    }
    
    if (!window.confirm(`确定要删除角色 "${role.display_name}" 吗？`)) {
      return;
    }
    
    try {
      await secureApi.request({
        path: `/api/admin/roles/${role.id}`,
        method: 'DELETE'
      });
      setSuccess('角色删除成功');
      loadRoles();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  // 创建角色成功
  const handleCreateSuccess = () => {
    setShowCreateModal(false);
    setSuccess('角色创建成功');
    loadRoles();
    setTimeout(() => setSuccess(null), 3000);
  };

  // 编辑角色成功
  const handleEditSuccess = () => {
    setShowEditModal(false);
    setSelectedRole(null);
    setSuccess('角色更新成功');
    loadRoles();
    setTimeout(() => setSuccess(null), 3000);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Shield className="w-8 h-8 text-indigo-400" />
              角色管理
            </h1>
            <p className="text-gray-400 mt-1">管理系统角色和权限配置</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadRoles}
              disabled={loading}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg flex items-center gap-2 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-2 transition-colors"
            >
              <Plus className="w-4 h-4" />
              新建角色
            </button>
          </div>
        </div>

        {/* 提示信息 */}
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

        {/* 角色卡片列表 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {loading ? (
            <div className="col-span-2 p-12 text-center text-gray-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
              加载中...
            </div>
          ) : roles.length === 0 ? (
            <div className="col-span-2 p-12 text-center text-gray-400">
              暂无角色数据
            </div>
          ) : (
            roles.map((role) => (
              <RoleCard
                key={role.id}
                role={role}
                onView={() => handleViewDetail(role.id)}
                onEdit={() => handleEdit(role)}
                onDelete={() => handleDelete(role)}
              />
            ))
          )}
        </div>
      </div>

      {/* 创建角色弹窗 */}
      {showCreateModal && (
        <RoleFormModal
          title="新建角色"
          allPermissions={allPermissions}
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleCreateSuccess}
        />
      )}

      {/* 编辑角色弹窗 */}
      {showEditModal && selectedRole && (
        <RoleFormModal
          title="编辑角色"
          role={selectedRole}
          allPermissions={allPermissions}
          onClose={() => { setShowEditModal(false); setSelectedRole(null); }}
          onSuccess={handleEditSuccess}
        />
      )}

      {/* 角色详情弹窗 */}
      {showDetailModal && selectedRole && (
        <RoleDetailModal
          role={selectedRole}
          allPermissions={allPermissions}
          onClose={() => { setShowDetailModal(false); setSelectedRole(null); }}
        />
      )}
    </div>
  );
};

// ==================== 子组件 ====================

/**
 * 角色卡片
 */
const RoleCard = ({ role, onView, onEdit, onDelete }) => {
  const permCount = role.permissions?.length || 0;
  
  return (
    <div className={`bg-gray-800 rounded-xl p-4 ${!role.is_active ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            role.is_system ? 'bg-indigo-500/20' : 'bg-gray-700'
          }`}>
            <Shield className={`w-5 h-5 ${role.is_system ? 'text-indigo-400' : 'text-gray-400'}`} />
          </div>
          <div>
            <h3 className="font-semibold flex items-center gap-2">
              {role.display_name}
              {role.is_system && (
                <span className="text-xs px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded">
                  系统
                </span>
              )}
              {!role.is_active && (
                <span className="text-xs px-2 py-0.5 bg-gray-600 text-gray-400 rounded">
                  已禁用
                </span>
              )}
            </h3>
            <p className="text-sm text-gray-500 font-mono">{role.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onView}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors"
            title="查看详情"
          >
            <Eye className="w-4 h-4 text-gray-400" />
          </button>
          <button
            onClick={onEdit}
            className="p-1.5 hover:bg-gray-700 rounded transition-colors"
            title="编辑"
          >
            <Edit2 className="w-4 h-4 text-gray-400" />
          </button>
          {!role.is_system && (
            <button
              onClick={onDelete}
              className="p-1.5 hover:bg-gray-700 rounded transition-colors"
              title="删除"
            >
              <Trash2 className="w-4 h-4 text-red-400" />
            </button>
          )}
        </div>
      </div>
      
      <p className="text-sm text-gray-400 mb-3">{role.description || '暂无描述'}</p>
      
      <div className="flex items-center gap-4 text-sm text-gray-500">
        <span className="flex items-center gap-1">
          <Lock className="w-4 h-4" />
          {permCount === 1 && role.permissions?.[0] === '*' ? '所有权限' : `${permCount} 项权限`}
        </span>
        <span className="flex items-center gap-1">
          <Users className="w-4 h-4" />
          {role.user_count || 0} 用户
        </span>
      </div>
    </div>
  );
};

/**
 * 角色表单弹窗（创建/编辑）
 */
const RoleFormModal = ({ title, role, allPermissions, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: role?.name || '',
    display_name: role?.display_name || '',
    description: role?.description || '',
    permissions: role?.permissions || [],
    is_active: role?.is_active ?? true
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const isEdit = !!role;
  const isSystem = role?.is_system;

  // 权限分组
  const permissionGroups = {
    analysis: { label: '分析功能', items: [] },
    query: { label: '查询功能', items: [] },
    data: { label: '数据管理', items: [] },
    user: { label: '用户管理', items: [] },
    session: { label: '会话管理', items: [] },
    log: { label: '日志管理', items: [] },
    config: { label: '系统配置', items: [] },
    role: { label: '角色管理', items: [] },
    other: { label: '其他', items: [] }
  };

  Object.entries(allPermissions).forEach(([key, label]) => {
    if (key === '*') return;
    const group = key.split(':')[0];
    if (permissionGroups[group]) {
      permissionGroups[group].items.push({ key, label });
    } else {
      permissionGroups.other.items.push({ key, label });
    }
  });

  const handlePermissionChange = (perm, checked) => {
    if (checked) {
      setFormData(prev => ({
        ...prev,
        permissions: [...prev.permissions, perm]
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        permissions: prev.permissions.filter(p => p !== perm)
      }));
    }
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.display_name) {
      setError('请填写角色代码和显示名称');
      return;
    }

    try {
      setSaving(true);
      setError(null);

      if (isEdit) {
        await secureApi.request({
          path: `/api/admin/roles/${role.id}`,
          method: 'PUT',
          body: {
            display_name: formData.display_name,
            description: formData.description,
            permissions: isSystem ? undefined : formData.permissions,
            is_active: formData.is_active
          }
        });
      } else {
        await secureApi.request({
          path: '/api/admin/roles',
          method: 'POST',
          body: formData
        });
      }

      onSuccess();
    } catch (err) {
      setError(err.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          {/* 基本信息 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">角色代码 *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                disabled={isEdit}
                placeholder="如: editor"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-indigo-500 disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">显示名称 *</label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData(prev => ({ ...prev, display_name: e.target.value }))}
                placeholder="如: 编辑员"
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">描述</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="角色描述..."
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-indigo-500"
            />
          </div>

          {isEdit && (
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                className="rounded bg-gray-600 border-gray-500"
              />
              <label htmlFor="is_active" className="text-sm text-gray-400">启用此角色</label>
            </div>
          )}

          {/* 权限配置 */}
          {!isSystem && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">权限配置</label>
              <div className="bg-gray-700/50 rounded-lg p-4 max-h-64 overflow-y-auto space-y-4">
                {Object.entries(permissionGroups).map(([groupKey, group]) => {
                  if (group.items.length === 0) return null;
                  return (
                    <div key={groupKey}>
                      <h4 className="text-sm font-medium text-gray-300 mb-2">{group.label}</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {group.items.map(({ key, label }) => (
                          <label key={key} className="flex items-center gap-2 text-sm text-gray-400">
                            <input
                              type="checkbox"
                              checked={formData.permissions.includes(key)}
                              onChange={(e) => handlePermissionChange(key, e.target.checked)}
                              className="rounded bg-gray-600 border-gray-500"
                            />
                            {label}
                          </label>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {isSystem && (
            <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-300 text-sm">
              系统预设角色的权限不可修改
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 p-4 border-t border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-2 transition-colors"
          >
            <Save className={`w-4 h-4 ${saving ? 'animate-pulse' : ''}`} />
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
};

/**
 * 角色详情弹窗
 */
const RoleDetailModal = ({ role, allPermissions, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold">角色详情</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          {/* 基本信息 */}
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              role.is_system ? 'bg-indigo-500/20' : 'bg-gray-700'
            }`}>
              <Shield className={`w-6 h-6 ${role.is_system ? 'text-indigo-400' : 'text-gray-400'}`} />
            </div>
            <div>
              <h3 className="text-lg font-semibold">{role.display_name}</h3>
              <p className="text-sm text-gray-500 font-mono">{role.name}</p>
            </div>
          </div>

          <p className="text-gray-400">{role.description || '暂无描述'}</p>

          {/* 权限列表 */}
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-2">权限列表</h4>
            <div className="bg-gray-700/50 rounded-lg p-3">
              {role.permissions?.length === 1 && role.permissions[0] === '*' ? (
                <span className="text-indigo-400">所有权限</span>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {role.permissions?.map((perm) => (
                    <span key={perm} className="px-2 py-1 bg-gray-600 rounded text-sm">
                      {allPermissions[perm] || perm}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 用户列表 */}
          {role.users && role.users.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">
                拥有此角色的用户 ({role.users.length})
              </h4>
              <div className="bg-gray-700/50 rounded-lg p-3 space-y-2">
                {role.users.map((user) => (
                  <div key={user.id} className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-bold">
                      {user.username?.charAt(0).toUpperCase()}
                    </div>
                    <span>{user.nickname || user.username}</span>
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

export default RoleManagement;
