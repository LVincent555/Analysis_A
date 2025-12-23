import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  RefreshCw, Play, Square, Clock, Database, 
  CheckCircle, XCircle, AlertCircle, ChevronDown, ChevronUp 
} from 'lucide-react';
import apiClient from '../services/api';

/**
 * 外部板块同步管理页面
 */
const ExtBoardSync = () => {
  // 状态
  const [stats, setStats] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [logsExpanded, setLogsExpanded] = useState(true);
  const [error, setError] = useState(null);

  // 热度计算状态
  const [heatStatus, setHeatStatus] = useState(null);
  const [heatRunning, setHeatRunning] = useState(false);
  const [heatLogsExpanded, setHeatLogsExpanded] = useState(true);
  const [heatParams, setHeatParams] = useState({
    date: '',
    calc_all: false,
    force: false,
    allow_fallback: true
  });

  const [syncParams, setSyncParams] = useState({
    provider: 'em',
    date: '',
    board_type: 'all',
    force: true,
    use_proxy: true,
    skip_cons: false,
    skip_map: false,
    delay: '8',
    concurrent: true,
    workers: '10',
    max_ips: '200',
    ip_ttl: '50',
    req_delay_min: '2',
    req_delay_max: '4',
    limit: ''
  });
  
  // 轮询定时器
  const pollIntervalRef = useRef(null);
  const heatPollRef = useRef(null);
  const logsEndRef = useRef(null);
  const heatLogsEndRef = useRef(null);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/admin/ext-boards/stats');
      setStats(response);
    } catch (err) {
      console.error('加载统计数据失败:', err);
    }
  }, []);

  // 加载同步历史
  const loadHistory = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/admin/ext-boards/sync-history');
      setHistory(response.history || []);
    } catch (err) {
      console.error('加载同步历史失败:', err);
    }
  }, []);

  // 加载同步状态
  const loadSyncStatus = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/admin/ext-boards/sync-status');
      setSyncStatus(response);
      setSyncing(response.is_syncing);
      
      // 自动滚动日志
      if (logsEndRef.current) {
        logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
      
      return response.is_syncing;
    } catch (err) {
      console.error('加载同步状态失败:', err);
      return false;
    }
  }, []);

  // 加载热度计算状态
  const loadHeatStatus = useCallback(async () => {
    try {
      const response = await apiClient.get('/api/admin/ext-boards/heat/status');
      setHeatStatus(response);
      setHeatRunning(response.is_running);
      
      if (heatLogsEndRef.current) {
        heatLogsEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
      
      return response.is_running;
    } catch (err) {
      console.error('加载热度计算状态失败:', err);
      return false;
    }
  }, []);

  // 初始加载
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([loadStats(), loadHistory(), loadSyncStatus(), loadHeatStatus()]);
      setLoading(false);
    };
    init();
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (heatPollRef.current) {
        clearInterval(heatPollRef.current);
      }
    };
  }, [loadStats, loadHistory, loadSyncStatus, loadHeatStatus]);

  // 轮询同步状态
  useEffect(() => {
    if (syncing) {
      pollIntervalRef.current = setInterval(async () => {
        const stillSyncing = await loadSyncStatus();
        if (!stillSyncing) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
          // 同步完成后刷新数据
          await Promise.all([loadStats(), loadHistory()]);
        }
      }, 2000);
    }
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [syncing, loadSyncStatus, loadStats, loadHistory]);

  // 轮询热度计算状态
  useEffect(() => {
    if (heatRunning) {
      heatPollRef.current = setInterval(async () => {
        const stillRunning = await loadHeatStatus();
        if (!stillRunning) {
          clearInterval(heatPollRef.current);
          heatPollRef.current = null;
          await loadStats();
        }
      }, 2000);
    }
    
    return () => {
      if (heatPollRef.current) {
        clearInterval(heatPollRef.current);
      }
    };
  }, [heatRunning, loadHeatStatus, loadStats]);

  // 触发同步
  const handleSync = async () => {
    try {
      setError(null);

      const payload = {
        provider: syncParams.provider,
        force: !!syncParams.force,
        use_proxy: !!syncParams.use_proxy,
        date: (syncParams.date || '').trim() ? (syncParams.date || '').trim() : null,
        board_type: syncParams.board_type,
        delay: syncParams.delay !== '' ? Number(syncParams.delay) : undefined,
        concurrent: !!syncParams.concurrent,
        workers: syncParams.workers !== '' ? Number(syncParams.workers) : undefined,
        max_ips: syncParams.max_ips !== '' ? Number(syncParams.max_ips) : undefined,
        ip_ttl: syncParams.ip_ttl !== '' ? Number(syncParams.ip_ttl) : undefined,
        req_delay_min: syncParams.req_delay_min !== '' ? Number(syncParams.req_delay_min) : undefined,
        req_delay_max: syncParams.req_delay_max !== '' ? Number(syncParams.req_delay_max) : undefined,
        limit: syncParams.limit !== '' ? Number(syncParams.limit) : null,
        skip_cons: !!syncParams.skip_cons,
        skip_map: !!syncParams.skip_map
      };

      const response = await apiClient.post('/api/admin/ext-boards/sync', {
        ...payload
      });
      
      if (response.success) {
        setSyncing(true);
        await loadSyncStatus();
      }
    } catch (err) {
      setError(err.message || '启动同步失败');
    }
  };

  // 取消同步
  const handleCancel = async () => {
    try {
      await apiClient.post('/api/admin/ext-boards/sync/cancel');
      await loadSyncStatus();
    } catch (err) {
      setError(err.message || '取消同步失败');
    }
  };

  const handleAutoMap = async () => {
    try {
      setError(null);
      await apiClient.post('/api/admin/ext-boards/mapping/auto');
      setLogsExpanded(true);
      await Promise.all([loadStats(), loadHistory(), loadSyncStatus()]);
    } catch (err) {
      setError(err.message || '编制数据库关系失败');
    }
  };

  // 触发热度计算
  const handleHeatCalc = async () => {
    try {
      setError(null);
      const payload = {
        date: heatParams.date.trim() || null,
        calc_all: !!heatParams.calc_all,
        force: !!heatParams.force,
        allow_fallback: !!heatParams.allow_fallback
      };
      const response = await apiClient.post('/api/admin/ext-boards/heat/calc', payload);
      if (response.success) {
        setHeatRunning(true);
        await loadHeatStatus();
      }
    } catch (err) {
      setError(err.message || '启动热度计算失败');
    }
  };

  // 取消热度计算
  const handleCancelHeat = async () => {
    try {
      await apiClient.post('/api/admin/ext-boards/heat/cancel');
      await loadHeatStatus();
    } catch (err) {
      setError(err.message || '取消热度计算失败');
    }
  };

  // 状态图标
  const StatusIcon = ({ status }) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'partial_success':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* 标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">外部板块同步</h1>
        <button
          onClick={() => Promise.all([loadStats(), loadHistory()])}
          className="p-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">
          {error}
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* 总板块数 */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">总板块数</p>
              <p className="text-2xl font-bold text-white">{stats?.total_boards || 0}</p>
            </div>
            <Database className="w-10 h-10 text-blue-500 opacity-50" />
          </div>
        </div>

        {/* 总成分股 */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">成分股记录</p>
              <p className="text-2xl font-bold text-white">
                {(stats?.total_cons_records || 0).toLocaleString()}
              </p>
            </div>
            <Database className="w-10 h-10 text-green-500 opacity-50" />
          </div>
        </div>

        {/* 映射数量 */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">自动映射</p>
              <p className="text-2xl font-bold text-white">{stats?.mapping_count || 0}</p>
            </div>
            <Database className="w-10 h-10 text-purple-500 opacity-50" />
          </div>
        </div>

        {/* 最近同步 */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">最近同步</p>
              <p className="text-lg font-bold text-white">
                {stats?.last_sync?.date || '无'}
              </p>
              {stats?.last_sync?.status && (
                <div className="flex items-center mt-1">
                  <StatusIcon status={stats.last_sync.status} />
                  <span className="ml-1 text-sm text-gray-400">
                    {stats.last_sync.status === 'success' ? '成功' : '失败'}
                  </span>
                </div>
              )}
            </div>
            <Clock className="w-10 h-10 text-yellow-500 opacity-50" />
          </div>
        </div>
      </div>

      {/* 数据源详情 */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">数据源统计</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {stats?.providers?.map((provider) => (
            <div 
              key={provider.code} 
              className="bg-gray-700/50 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-white">{provider.name}</span>
                <span className="text-sm text-gray-400">{provider.code}</span>
              </div>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">行业板块</span>
                  <span className="text-white">{provider.boards?.industry || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">概念板块</span>
                  <span className="text-white">{provider.boards?.concept || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">成分股记录</span>
                  <span className="text-white">{(provider.cons_count || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">不重复股票</span>
                  <span className="text-white">{(provider.stock_count || 0).toLocaleString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 同步操作 */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">同步操作</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div>
            <div className="text-xs text-gray-400 mb-1">数据源</div>
            <select
              value={syncParams.provider}
              onChange={(e) => setSyncParams((p) => ({ ...p, provider: e.target.value }))}
              disabled={syncing}
              className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
            >
              <option value="em">东财</option>
              <option value="ths">同花顺</option>
              <option value="all">全部</option>
            </select>
          </div>

          <div>
            <div className="text-xs text-gray-400 mb-1">目标日期</div>
            <input
              type="date"
              value={syncParams.date}
              onChange={(e) => setSyncParams((p) => ({ ...p, date: e.target.value }))}
              disabled={syncing}
              className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
            />
          </div>

          <div>
            <div className="text-xs text-gray-400 mb-1">板块类型</div>
            <select
              value={syncParams.board_type}
              onChange={(e) => setSyncParams((p) => ({ ...p, board_type: e.target.value }))}
              disabled={syncing}
              className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
            >
              <option value="all">全部</option>
              <option value="industry">行业</option>
              <option value="concept">概念</option>
            </select>
          </div>

          <div>
            <div className="text-xs text-gray-400 mb-1">请求间隔(秒)</div>
            <input
              type="number"
              step="0.1"
              value={syncParams.delay}
              onChange={(e) => setSyncParams((p) => ({ ...p, delay: e.target.value }))}
              disabled={syncing}
              className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
            />
          </div>

          <div className="md:col-span-2 flex flex-wrap gap-4 items-end">
            <label className="flex items-center gap-2 text-sm text-gray-300 select-none">
              <input
                type="checkbox"
                checked={syncParams.force}
                onChange={(e) => setSyncParams((p) => ({ ...p, force: e.target.checked }))}
                disabled={syncing}
                className="rounded"
              />
              强制同步
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-300 select-none">
              <input
                type="checkbox"
                checked={syncParams.use_proxy}
                onChange={(e) => setSyncParams((p) => ({ ...p, use_proxy: e.target.checked }))}
                disabled={syncing}
                className="rounded"
              />
              使用代理
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-300 select-none">
              <input
                type="checkbox"
                checked={syncParams.skip_cons}
                onChange={(e) => setSyncParams((p) => ({ ...p, skip_cons: e.target.checked }))}
                disabled={syncing}
                className="rounded"
              />
              跳过成分股
            </label>

            <label className="flex items-center gap-2 text-sm text-gray-300 select-none">
              <input
                type="checkbox"
                checked={syncParams.skip_map}
                onChange={(e) => setSyncParams((p) => ({ ...p, skip_map: e.target.checked }))}
                disabled={syncing}
                className="rounded"
              />
              跳过映射
            </label>
          </div>

          <div>
            <div className="text-xs text-gray-400 mb-1">限制板块数(可空)</div>
            <input
              type="number"
              value={syncParams.limit}
              onChange={(e) => setSyncParams((p) => ({ ...p, limit: e.target.value }))}
              disabled={syncing}
              className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
            />
          </div>

          <div className="md:col-span-2 flex flex-wrap gap-4 items-end">
            <label className="flex items-center gap-2 text-sm text-gray-300 select-none">
              <input
                type="checkbox"
                checked={syncParams.concurrent}
                onChange={(e) => setSyncParams((p) => ({ ...p, concurrent: e.target.checked }))}
                disabled={syncing}
                className="rounded"
              />
              并发模式
            </label>
          </div>

          {syncParams.concurrent && (
            <>
              <div>
                <div className="text-xs text-gray-400 mb-1">线程数</div>
                <input
                  type="number"
                  value={syncParams.workers}
                  onChange={(e) => setSyncParams((p) => ({ ...p, workers: e.target.value }))}
                  disabled={syncing}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
                />
              </div>

              <div>
                <div className="text-xs text-gray-400 mb-1">最大IP数</div>
                <input
                  type="number"
                  value={syncParams.max_ips}
                  onChange={(e) => setSyncParams((p) => ({ ...p, max_ips: e.target.value }))}
                  disabled={syncing}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
                />
              </div>

              <div>
                <div className="text-xs text-gray-400 mb-1">IP复用秒数</div>
                <input
                  type="number"
                  step="0.1"
                  value={syncParams.ip_ttl}
                  onChange={(e) => setSyncParams((p) => ({ ...p, ip_ttl: e.target.value }))}
                  disabled={syncing}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
                />
              </div>

              <div>
                <div className="text-xs text-gray-400 mb-1">请求延迟最小(秒)</div>
                <input
                  type="number"
                  step="0.1"
                  value={syncParams.req_delay_min}
                  onChange={(e) => setSyncParams((p) => ({ ...p, req_delay_min: e.target.value }))}
                  disabled={syncing}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
                />
              </div>

              <div>
                <div className="text-xs text-gray-400 mb-1">请求延迟最大(秒)</div>
                <input
                  type="number"
                  step="0.1"
                  value={syncParams.req_delay_max}
                  onChange={(e) => setSyncParams((p) => ({ ...p, req_delay_max: e.target.value }))}
                  disabled={syncing}
                  className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-gray-200 text-sm"
                />
              </div>
            </>
          )}
        </div>
        
        <div className="flex flex-wrap gap-3 mb-4">
          {!syncing ? (
            <>
              <button
                onClick={() => handleSync()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center"
              >
                <Play className="w-4 h-4 mr-2" />
                {syncParams.provider === 'em' ? '同步东财板块' : syncParams.provider === 'ths' ? '同步同花顺板块' : '同步全部板块'}
              </button>

              <button
                onClick={handleAutoMap}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
              >
                编制数据库关系
              </button>
            </>
          ) : (
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center"
            >
              <Square className="w-4 h-4 mr-2" />
              取消同步
            </button>
          )}
        </div>

        {/* 同步日志 */}
        {(syncing || syncStatus?.logs?.length > 0) && (
          <div className="mt-4">
            <button
              onClick={() => setLogsExpanded(!logsExpanded)}
              className="flex items-center text-gray-400 hover:text-white mb-2"
            >
              {logsExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              <span className="ml-1">同步日志</span>
              {syncing && <RefreshCw className="w-4 h-4 ml-2 animate-spin" />}
            </button>
            
            {logsExpanded && (
              <div className="bg-gray-900 rounded-lg p-3 max-h-64 overflow-y-auto font-mono text-sm">
                {syncStatus?.logs?.map((log, index) => (
                  <div 
                    key={index}
                    className={`${
                      log.includes('ERROR') ? 'text-red-400' :
                      log.includes('WARNING') ? 'text-yellow-400' :
                      log.includes('成功') || log.includes('完成') ? 'text-green-400' :
                      'text-gray-300'
                    }`}
                  >
                    {log}
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        )}

        {/* 提示 */}
        {syncParams.use_proxy && (
          <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-yellow-300 text-sm">
            ⚠️ 同步需要使用代理 IP 池，每次同步约消耗 10-20 个 IP（约 ¥0.10-0.20）
          </div>
        )}
      </div>

      {/* 板块热度计算 */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">板块热度计算 (ETL)</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">指定日期</label>
            <input
              type="date"
              value={heatParams.date}
              onChange={(e) => setHeatParams({ ...heatParams, date: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm"
              disabled={heatRunning}
            />
          </div>
          
          <div className="flex items-end gap-4">
            <label className="flex items-center text-sm text-gray-300">
              <input
                type="checkbox"
                checked={heatParams.calc_all}
                onChange={(e) => setHeatParams({ ...heatParams, calc_all: e.target.checked })}
                className="mr-2 rounded"
                disabled={heatRunning}
              />
              计算全部日期
            </label>
          </div>
          
          <div className="flex items-end gap-4">
            <label className="flex items-center text-sm text-gray-300">
              <input
                type="checkbox"
                checked={heatParams.force}
                onChange={(e) => setHeatParams({ ...heatParams, force: e.target.checked })}
                className="mr-2 rounded"
                disabled={heatRunning}
              />
              强制重算
            </label>
          </div>
          
          <div className="flex items-end gap-4">
            <label className="flex items-center text-sm text-gray-300">
              <input
                type="checkbox"
                checked={heatParams.allow_fallback}
                onChange={(e) => setHeatParams({ ...heatParams, allow_fallback: e.target.checked })}
                className="mr-2 rounded"
                disabled={heatRunning}
              />
              允许借用快照
            </label>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-3 mb-4">
          {!heatRunning ? (
            <button
              onClick={handleHeatCalc}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg flex items-center"
            >
              <Play className="w-4 h-4 mr-2" />
              {heatParams.calc_all ? '计算全部热度' : heatParams.date ? `计算 ${heatParams.date} 热度` : '计算最新热度'}
            </button>
          ) : (
            <button
              onClick={handleCancelHeat}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg flex items-center"
            >
              <Square className="w-4 h-4 mr-2" />
              取消计算
            </button>
          )}
        </div>

        {/* 热度计算日志 */}
        {(heatRunning || heatStatus?.logs?.length > 0) && (
          <div className="mt-4">
            <button
              onClick={() => setHeatLogsExpanded(!heatLogsExpanded)}
              className="flex items-center text-gray-400 hover:text-white mb-2"
            >
              {heatLogsExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              <span className="ml-1">热度计算日志</span>
              {heatRunning && <RefreshCw className="w-4 h-4 ml-2 animate-spin" />}
            </button>
            
            {heatLogsExpanded && (
              <div className="bg-gray-900 rounded-lg p-3 max-h-64 overflow-y-auto font-mono text-sm">
                {heatStatus?.logs?.map((log, index) => (
                  <div 
                    key={index}
                    className={`${
                      log.includes('ERROR') || log.includes('❌') ? 'text-red-400' :
                      log.includes('WARNING') || log.includes('⚠️') ? 'text-yellow-400' :
                      log.includes('✅') || log.includes('完成') ? 'text-green-400' :
                      'text-gray-300'
                    }`}
                  >
                    {log}
                  </div>
                ))}
                <div ref={heatLogsEndRef} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* 同步历史 */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">同步历史</h3>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                <th className="pb-3 pr-4">日期</th>
                <th className="pb-3 pr-4">状态</th>
                <th className="pb-3 pr-4">板块数/成分股</th>
                <th className="pb-3 pr-4">耗时</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-gray-500">
                    暂无同步历史
                  </td>
                </tr>
              ) : (
                history.map((item) => (
                  <tr key={item.date} className="border-b border-gray-700/50">
                    <td className="py-3 pr-4 text-white">{item.date}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center">
                        <StatusIcon status={item.status} />
                        <span className={`ml-2 ${
                          item.status === 'success' ? 'text-green-400' :
                          item.status === 'failed' ? 'text-red-400' :
                          'text-yellow-400'
                        }`}>
                          {item.status === 'success' ? '成功' :
                           item.status === 'failed' ? '失败' : '部分成功'}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-gray-300">
                      {item.providers?.em ? (
                        `${item.providers.em.board_count || 0} / ${(item.providers.em.cons_count || 0).toLocaleString()}`
                      ) : '-'}
                    </td>
                    <td className="py-3 pr-4 text-gray-400">
                      {item.duration_seconds ? `${Math.round(item.duration_seconds / 60)} 分钟` : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ExtBoardSync;
