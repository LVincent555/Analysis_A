import React, { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { API_BASE_URL } from '../../constants/config';

// 样式定义
const styles = {
  container: {
    backgroundColor: 'white',
    borderRadius: '0.5rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    padding: '1.5rem'
  },
  header: {
    marginBottom: '1.5rem',
    borderBottom: '2px solid #e5e7eb',
    paddingBottom: '1rem'
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: '0.5rem'
  },
  controls: {
    display: 'flex',
    gap: '1rem',
    marginBottom: '1.5rem',
    flexWrap: 'wrap',
    alignItems: 'center'
  },
  select: {
    padding: '0.5rem',
    borderRadius: '0.375rem',
    border: '1px solid #d1d5db',
    fontSize: '0.875rem'
  },
  button: {
    padding: '0.5rem 1rem',
    borderRadius: '0.375rem',
    border: 'none',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: '500',
    transition: 'all 0.2s'
  },
  tableContainer: {
    overflowX: 'auto',
    marginTop: '1rem'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.875rem'
  },
  th: {
    padding: '0.75rem',
    textAlign: 'left',
    backgroundColor: '#f9fafb',
    borderBottom: '2px solid #e5e7eb',
    fontWeight: '600',
    color: '#374151'
  },
  td: {
    padding: '0.75rem',
    borderBottom: '1px solid #e5e7eb'
  },
  positive: {
    color: '#ef4444'
  },
  negative: {
    color: '#10b981'
  },
  chartBox: {
    marginBottom: '2rem',
    padding: '1rem',
    backgroundColor: '#f9fafb',
    borderRadius: '0.5rem'
  }
};

const SectorModule = ({ selectedDate, onDateChange }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // 状态
  const [sectorRanking, setSectorRanking] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [sectorDetail, setSectorDetail] = useState(null);
  const [topN, setTopN] = useState(30);
  const [historyDays, setHistoryDays] = useState(30);

  // 获取板块排名
  const fetchSectorRanking = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedDate) params.append('date', selectedDate);
      params.append('limit', topN.toString());

      const response = await fetch(`/api/sectors/ranking?${params}`);
      if (!response.ok) throw new Error('获取板块排名失败');
      
      const data = await response.json();
      setSectorRanking(data);
    } catch (err) {
      setError(err.message);
      console.error('获取板块排名失败:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, topN]);

  // 获取板块详情
  const fetchSectorDetail = useCallback(async (sectorName) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('days', historyDays.toString());
      if (selectedDate) params.append('date', selectedDate);

      const response = await fetch(
        `/api/sectors/${encodeURIComponent(sectorName)}?${params}`
      );
      if (!response.ok) throw new Error('获取板块详情失败');
      
      const data = await response.json();
      setSectorDetail(data);
    } catch (err) {
      setError(err.message);
      console.error('获取板块详情失败:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, historyDays]);

  // 初始加载
  useEffect(() => {
    fetchSectorRanking();
  }, [fetchSectorRanking]);

  // 选择板块查看详情
  const handleSelectSector = (sectorName) => {
    setSelectedSector(sectorName);
    fetchSectorDetail(sectorName);
  };

  // 渲染板块排名表格
  const renderRankingTable = () => {
    if (!sectorRanking || !sectorRanking.sectors) return null;

    return (
      <div style={styles.tableContainer}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>排名</th>
              <th style={styles.th}>板块名称</th>
              <th style={styles.th}>综合评分</th>
              <th style={styles.th}>涨跌幅(%)</th>
              <th style={styles.th}>换手率(%)</th>
              <th style={styles.th}>成交量</th>
              <th style={styles.th}>波动率</th>
              <th style={styles.th}>操作</th>
            </tr>
          </thead>
          <tbody>
            {sectorRanking.sectors.map((sector, index) => (
              <tr 
                key={index}
                style={selectedSector === sector.name ? {backgroundColor: '#f0f9ff'} : {}}
              >
                <td style={styles.td}>{sector.rank}</td>
                <td style={{...styles.td, fontWeight: '500'}}>{sector.name}</td>
                <td style={styles.td}>{sector.total_score?.toFixed(2) || '-'}</td>
                <td style={{...styles.td, ...(sector.price_change > 0 ? styles.positive : styles.negative)}}>
                  {sector.price_change?.toFixed(2) || '-'}
                </td>
                <td style={styles.td}>{sector.turnover_rate?.toFixed(2) || '-'}</td>
                <td style={styles.td}>{sector.volume ? (sector.volume / 100000000).toFixed(2) + '亿' : '-'}</td>
                <td style={styles.td}>{sector.volatility?.toFixed(4) || '-'}</td>
                <td style={styles.td}>
                  <button 
                    onClick={() => handleSelectSector(sector.name)}
                    style={{...styles.button, backgroundColor: '#3b82f6', color: 'white'}}
                  >
                    查看详情
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // 渲染板块详情
  const renderSectorDetail = () => {
    if (!sectorDetail) return null;

    // 排名趋势图数据
    const rankTrendData = sectorDetail.history.map(item => ({
      date: item.date,
      rank: item.rank
    }));

    // 涨跌幅趋势图数据
    const priceChangeData = sectorDetail.history.map(item => ({
      date: item.date,
      price_change: item.price_change
    }));

    return (
      <div style={{...styles.container, marginTop: '1.5rem'}}>
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem'}}>
          <h3 style={styles.title}>{sectorDetail.name} - 详细信息</h3>
          <button onClick={() => setSelectedSector(null)} style={{...styles.button, backgroundColor: '#6b7280', color: 'white'}}>
            关闭
          </button>
        </div>

        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem'}}>
          {/* 排名趋势图 */}
          <div style={styles.chartBox}>
            <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>排名趋势（排名越小越靠前）</h4>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={rankTrendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis reversed label={{ value: '排名', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="rank" 
                  stroke="#8884d8" 
                  name="排名"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 涨跌幅趋势图 */}
          <div style={styles.chartBox}>
            <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>涨跌幅趋势</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={priceChangeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis label={{ value: '涨跌幅(%)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Bar 
                  dataKey="price_change" 
                  fill="#82ca9d" 
                  name="涨跌幅(%)"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 数据表格 */}
        <div style={{marginTop: '2rem'}}>
          <h4 style={{fontSize: '1rem', fontWeight: '600', marginBottom: '1rem'}}>历史数据</h4>
          <div style={styles.tableContainer}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>日期</th>
                  <th style={styles.th}>排名</th>
                  <th style={styles.th}>综合评分</th>
                  <th style={styles.th}>涨跌幅(%)</th>
                  <th style={styles.th}>换手率(%)</th>
                  <th style={styles.th}>成交量</th>
                  <th style={styles.th}>收盘价</th>
                </tr>
              </thead>
              <tbody>
                {sectorDetail.history.slice().reverse().map((item, index) => (
                  <tr key={index}>
                    <td style={styles.td}>{item.date}</td>
                    <td style={styles.td}>{item.rank}</td>
                    <td style={styles.td}>{item.total_score?.toFixed(2) || '-'}</td>
                    <td style={{...styles.td, ...(item.price_change > 0 ? styles.positive : styles.negative)}}>
                      {item.price_change?.toFixed(2) || '-'}
                    </td>
                    <td style={styles.td}>{item.turnover_rate?.toFixed(2) || '-'}</td>
                    <td style={styles.td}>{item.volume ? (item.volume / 100000000).toFixed(2) + '亿' : '-'}</td>
                    <td style={styles.td}>{item.close_price?.toFixed(2) || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>📊 板块分析</h2>
        <div style={{fontSize: '0.875rem', color: '#6b7280'}}>
          {sectorRanking && (
            <span>
              数据日期: {sectorRanking.date} | 总板块数: {sectorRanking.total_count}
            </span>
          )}
        </div>
      </div>

      {/* 控制面板 */}
      <div style={styles.controls}>
        <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
          <label style={{fontSize: '0.875rem', fontWeight: '500'}}>显示前N名板块：</label>
          <select 
            value={topN} 
            onChange={(e) => setTopN(Number(e.target.value))}
            style={styles.select}
          >
            <option value={10}>前10名</option>
            <option value={20}>前20名</option>
            <option value={30}>前30名</option>
            <option value={50}>前50名</option>
            <option value={100}>前100名</option>
          </select>
        </div>

        <div style={{display: 'flex', alignItems: 'center', gap: '0.5rem'}}>
          <label style={{fontSize: '0.875rem', fontWeight: '500'}}>历史天数：</label>
          <select 
            value={historyDays} 
            onChange={(e) => setHistoryDays(Number(e.target.value))}
            style={styles.select}
          >
            <option value={7}>7天</option>
            <option value={15}>15天</option>
            <option value={30}>30天</option>
            <option value={60}>60天</option>
            <option value={90}>90天</option>
          </select>
        </div>

        <button onClick={fetchSectorRanking} style={{...styles.button, backgroundColor: '#10b981', color: 'white'}}>
          🔄 刷新数据
        </button>
      </div>

      {/* 加载和错误状态 */}
      {loading && <div style={{padding: '2rem', textAlign: 'center', color: '#6b7280'}}>加载中...</div>}
      {error && <div style={{padding: '1rem', backgroundColor: '#fee2e2', color: '#dc2626', borderRadius: '0.375rem', marginBottom: '1rem'}}>错误: {error}</div>}

      {/* 板块排名表格 */}
      {!selectedSector && (
        <div style={{marginTop: '1.5rem'}}>
          <h3 style={{fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem'}}>板块排名（前{topN}名）</h3>
          {renderRankingTable()}
        </div>
      )}

      {/* 板块详情 */}
      {selectedSector && renderSectorDetail()}
    </div>
  );
};

export default SectorModule;

