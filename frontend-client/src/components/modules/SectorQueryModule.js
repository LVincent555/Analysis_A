import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Database } from 'lucide-react';
import apiClient from '../../services/api';
import { formatDate } from '../../utils';

function SectorQueryModule({ selectedDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [sortField, setSortField] = useState('rank');
  const [sortOrder, setSortOrder] = useState('asc');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/sectors/raw-data', {
        params: { date: selectedDate, limit: 600 }
      });
      setData(response);
    } catch (err) {
      setError(err.message || 'Failed to load data');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDate) loadData();
  }, [selectedDate]);

  const getFilteredData = () => {
    if (!data?.data) return [];
    let filtered = data.data;
    if (searchKeyword) {
      filtered = filtered.filter(s => s.name?.toLowerCase().includes(searchKeyword.toLowerCase()));
    }
    return [...filtered].sort((a, b) => {
      let aVal = a[sortField], bVal = b[sortField];
      if (sortField === 'name') return sortOrder === 'asc' ? (aVal||'').localeCompare(bVal||'') : (bVal||'').localeCompare(aVal||'');
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
  };

  const toggleSort = (field) => {
    if (sortField === field) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortOrder(field === 'rank' ? 'asc' : 'desc'); }
  };

  const filteredData = getFilteredData();

  return (
    <div className="max-w-6xl mx-auto p-4 md:p-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <Database className="h-6 w-6 text-purple-500" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">当日DC数据</h2>
              <p className="text-gray-500 text-sm">
                {data ? formatDate(data.date) + ' 共 ' + data.total_count + ' 个板块' : '加载中...'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input 
                type="text" 
                value={searchKeyword} 
                onChange={(e) => setSearchKeyword(e.target.value)} 
                placeholder="搜索板块..."
                className="pl-9 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm w-40" 
              />
            </div>
            <button 
              onClick={loadData} 
              disabled={loading} 
              className="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50 text-sm"
            >
              <RefreshCw className={'h-4 w-4 ' + (loading ? 'animate-spin' : '')} />
              刷新
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4 text-center">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {loading && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <RefreshCw className="h-8 w-8 text-purple-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">加载数据中...</p>
        </div>
      )}

      {!loading && filteredData.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto max-h-[600px]">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th onClick={() => toggleSort('rank')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">排名{sortField === 'rank' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('name')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">板块名称{sortField === 'name' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('close_price')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">收盘价{sortField === 'close_price' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('price_change')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">涨跌幅{sortField === 'price_change' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('turnover_rate')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">换手率{sortField === 'turnover_rate' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('volatility')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">波动率{sortField === 'volatility' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('volume_days')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">放量天数{sortField === 'volume_days' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                  <th onClick={() => toggleSort('avg_volume_ratio_50')} className="px-3 py-2 text-left text-xs font-medium text-gray-500 cursor-pointer hover:bg-gray-100">平均量比{sortField === 'avg_volume_ratio_50' ? (sortOrder === 'asc' ? ' ^' : ' v') : ''}</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredData.map((item, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className={'text-sm font-bold ' + (item.rank <= 10 ? 'text-red-600' : item.rank <= 50 ? 'text-orange-600' : item.rank <= 100 ? 'text-blue-600' : 'text-gray-600')}>
                        {item.rank}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{item.name}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.close_price ? item.close_price.toFixed(2) : '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className={'text-sm font-medium ' + (item.price_change >= 0 ? 'text-red-600' : 'text-green-600')}>
                        {item.price_change >= 0 ? '+' : ''}{item.price_change ? item.price_change.toFixed(2) : '0.00'}%
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.turnover_rate ? item.turnover_rate.toFixed(2) : '-'}%</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.volatility ? item.volatility.toFixed(2) : '-'}%</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.volume_days ? item.volume_days.toFixed(1) : '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.avg_volume_ratio_50 ? item.avg_volume_ratio_50.toFixed(2) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
            显示 {filteredData.length} 条数据{searchKeyword ? ' (搜索: "' + searchKeyword + '")' : ''}
          </div>
        </div>
      )}

      {!loading && !error && filteredData.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <Database className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">{searchKeyword ? '没有找到包含 "' + searchKeyword + '" 的板块' : '暂无数据'}</p>
        </div>
      )}
    </div>
  );
}

export default SectorQueryModule;
