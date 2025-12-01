import React, { useState, useEffect, useCallback } from 'react';
import { 
  Upload, 
  FileSpreadsheet, 
  Play, 
  Trash2, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  Clock,
  AlertCircle,
  FolderOpen,
  Calendar
} from 'lucide-react';
import secureApi from '../services/secureApi';

/**
 * 管理员面板 - 文件上传和数据导入
 * 仅 admin 用户可见
 */
const AdminPanel = () => {
  // 状态
  const [files, setFiles] = useState([]);
  const [uploadQueue, setUploadQueue] = useState([]);
  const [importStatus, setImportStatus] = useState(null);
  const [importedDates, setImportedDates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // 加载数据文件列表
  const loadFiles = useCallback(async () => {
    try {
      const response = await secureApi.request({
        path: '/admin/data-files',
        method: 'GET'
      });
      setFiles(response.files || []);
    } catch (err) {
      console.error('加载文件列表失败:', err);
    }
  }, []);

  // 加载导入状态
  const loadImportStatus = useCallback(async () => {
    try {
      const response = await secureApi.request({
        path: '/admin/import-status',
        method: 'GET'
      });
      setImportStatus(response);
    } catch (err) {
      console.error('加载导入状态失败:', err);
    }
  }, []);

  // 加载已导入日期
  const loadImportedDates = useCallback(async () => {
    try {
      const response = await secureApi.request({
        path: '/admin/dates',
        method: 'GET'
      });
      setImportedDates(response.dates || []);
    } catch (err) {
      console.error('加载日期列表失败:', err);
    }
  }, []);

  // 初始化加载
  useEffect(() => {
    loadFiles();
    loadImportStatus();
    loadImportedDates();
    
    // 如果正在导入，定时刷新状态
    const interval = setInterval(() => {
      if (importStatus?.is_importing) {
        loadImportStatus();
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [loadFiles, loadImportStatus, loadImportedDates, importStatus?.is_importing]);

  // 文件转 Base64
  const fileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        // 移除 data:xxx;base64, 前缀
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
    });
  };

  // 上传文件
  const uploadFile = async (file) => {
    try {
      // 更新上传队列状态
      setUploadQueue(prev => prev.map(f => 
        f.name === file.name ? { ...f, status: 'uploading' } : f
      ));

      // 转换为 Base64
      const base64Content = await fileToBase64(file);

      // 通过加密通道上传
      await secureApi.request({
        path: '/admin/upload',
        method: 'POST',
        body: {
          filename: file.name,
          content: base64Content
        }
      });

      // 更新状态为成功
      setUploadQueue(prev => prev.map(f => 
        f.name === file.name ? { ...f, status: 'success' } : f
      ));

      // 刷新文件列表
      await loadFiles();
      
    } catch (err) {
      console.error('上传失败:', err);
      setUploadQueue(prev => prev.map(f => 
        f.name === file.name ? { ...f, status: 'error', error: err.message } : f
      ));
    }
  };

  // 处理文件选择
  const handleFileSelect = async (selectedFiles) => {
    const fileArray = Array.from(selectedFiles);
    
    // 过滤非 Excel 文件
    const excelFiles = fileArray.filter(f => 
      f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls')
    );
    
    if (excelFiles.length !== fileArray.length) {
      setError('只支持 Excel 文件 (.xlsx, .xls)');
      setTimeout(() => setError(null), 3000);
    }
    
    if (excelFiles.length === 0) return;

    // 添加到上传队列
    const newQueue = excelFiles.map(f => ({
      name: f.name,
      size: f.size,
      status: 'pending',
      file: f
    }));
    
    setUploadQueue(prev => [...prev, ...newQueue]);

    // 依次上传
    for (const item of newQueue) {
      await uploadFile(item.file);
    }
  };

  // 拖拽处理
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  // 触发导入
  const handleImport = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await secureApi.request({
        path: '/admin/import',
        method: 'POST',
        body: {}
      });
      
      // 刷新状态
      await loadImportStatus();
      await loadImportedDates();
      
      if (!response.success) {
        setError(response.message);
      }
      
    } catch (err) {
      setError(err.message || '导入失败');
    } finally {
      setLoading(false);
    }
  };

  // 删除文件
  const handleDeleteFile = async (filename) => {
    if (!window.confirm(`确定要删除 ${filename} 吗？`)) return;
    
    try {
      await secureApi.request({
        path: `/admin/data-files/${encodeURIComponent(filename)}`,
        method: 'DELETE'
      });
      await loadFiles();
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  // 清除已完成的上传队列
  const clearCompletedUploads = () => {
    setUploadQueue(prev => prev.filter(f => f.status === 'uploading' || f.status === 'pending'));
  };

  // 格式化文件大小
  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-6xl mx-auto">
        {/* 标题 */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <FolderOpen className="w-8 h-8 text-blue-400" />
            数据管理
          </h1>
          <p className="text-gray-400 mt-2">上传 Excel 数据文件并导入到数据库</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
            <button 
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-300"
            >
              ✕
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左侧：上传区域 */}
          <div className="space-y-6">
            {/* 拖拽上传区 */}
            <div 
              className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                isDragging 
                  ? 'border-blue-400 bg-blue-400/10' 
                  : 'border-gray-600 hover:border-gray-500'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <Upload className={`w-12 h-12 mx-auto mb-4 ${isDragging ? 'text-blue-400' : 'text-gray-500'}`} />
              <p className="text-lg mb-2">拖拽 Excel 文件到此处</p>
              <p className="text-gray-500 text-sm mb-4">或</p>
              <label className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer transition-colors">
                选择文件
                <input 
                  type="file" 
                  multiple 
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files)}
                />
              </label>
              <p className="text-gray-500 text-xs mt-4">
                支持格式：股票数据 (*_data_sma_feature_color.xlsx) 或 板块数据 (*_allbk_sma_feature_color.xlsx)
              </p>
              <p className="text-gray-500 text-xs">单文件最大 10MB</p>
            </div>

            {/* 上传队列 */}
            {uploadQueue.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">上传队列</h3>
                  <button 
                    onClick={clearCompletedUploads}
                    className="text-sm text-gray-400 hover:text-white"
                  >
                    清除已完成
                  </button>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {uploadQueue.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-2 bg-gray-700/50 rounded">
                      <FileSpreadsheet className="w-5 h-5 text-green-400" />
                      <span className="flex-1 truncate text-sm">{item.name}</span>
                      <span className="text-xs text-gray-400">{formatSize(item.size)}</span>
                      {item.status === 'pending' && <Clock className="w-4 h-4 text-gray-400" />}
                      {item.status === 'uploading' && <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />}
                      {item.status === 'success' && <CheckCircle className="w-4 h-4 text-green-400" />}
                      {item.status === 'error' && <XCircle className="w-4 h-4 text-red-400" />}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 导入按钮 */}
            <button
              onClick={handleImport}
              disabled={loading || importStatus?.is_importing}
              className={`w-full py-4 rounded-xl font-semibold flex items-center justify-center gap-3 transition-colors ${
                loading || importStatus?.is_importing
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {importStatus?.is_importing ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  导入中... {importStatus.progress}%
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  开始导入数据
                </>
              )}
            </button>

            {/* 导入进度 */}
            {importStatus?.is_importing && (
              <div className="bg-gray-800 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-2">
                  <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
                  <span className="text-sm">正在处理: {importStatus.current_file}</span>
                </div>
                <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 transition-all"
                    style={{ width: `${importStatus.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* 导入日志 */}
            {importStatus?.logs?.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-4">
                <h3 className="font-semibold flex items-center gap-2 mb-3">
                  <Clock className="w-5 h-5 text-cyan-400" />
                  导入日志
                </h3>
                <div className="space-y-1 max-h-64 overflow-y-auto font-mono text-xs">
                  {importStatus.logs.map((log, idx) => (
                    <div 
                      key={idx} 
                      className={`flex gap-2 p-1 rounded ${
                        log.level === 'error' ? 'bg-red-500/10 text-red-300' : 
                        log.level === 'warning' ? 'bg-yellow-500/10 text-yellow-300' : 
                        'text-gray-300'
                      }`}
                    >
                      <span className="text-gray-500 flex-shrink-0">{log.time}</span>
                      <span>{log.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 右侧：文件列表和历史 */}
          <div className="space-y-6">
            {/* 服务器文件列表 */}
            <div className="bg-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <FolderOpen className="w-5 h-5 text-yellow-400" />
                  服务器文件
                </h3>
                <button 
                  onClick={loadFiles}
                  className="p-1 hover:bg-gray-700 rounded"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              
              {files.length === 0 ? (
                <p className="text-gray-500 text-center py-8">暂无文件</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {files.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-gray-700/50 rounded-lg">
                      <FileSpreadsheet className="w-5 h-5 text-green-400" />
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-sm">{file.name}</p>
                        <p className="text-xs text-gray-400">
                          {formatSize(file.size)} · {file.modified}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteFile(file.name)}
                        className="p-1 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 已导入日期 */}
            <div className="bg-gray-800 rounded-xl p-4">
              <h3 className="font-semibold flex items-center gap-2 mb-4">
                <Calendar className="w-5 h-5 text-purple-400" />
                已导入日期 (最近30天)
              </h3>
              
              {importedDates.length === 0 ? (
                <p className="text-gray-500 text-center py-4">暂无数据</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {importedDates.map((date, idx) => (
                    <span 
                      key={idx}
                      className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm"
                    >
                      {date}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* 导入历史 */}
            {importStatus?.history?.length > 0 && (
              <div className="bg-gray-800 rounded-xl p-4">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5 text-blue-400" />
                  导入历史
                </h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {importStatus.history.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-2 bg-gray-700/50 rounded">
                      {item.result?.success ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-400" />
                      )}
                      <span className="text-xs text-gray-400">{item.time}</span>
                      <span className="text-sm flex-1">{item.result?.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
