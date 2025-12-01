/**
 * 当日股票排名数据模块 - 显示当日所有股票原始排名数据（带分页）
 */
import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, TrendingUp, ChevronLeft, ChevronRight } from 'lucide-react';
import apiClient from '../../services/api';
import { formatDate } from '../../utils';

export default function StockRankingModule({ selectedDate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [sortField, setSortField] = useState('rank');
  const [sortOrder, setSortOrder] = useState('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/api/stocks/raw-data', {
        params: { date: selectedDate, limit: 5000 }
      });
      setData(response);
      setCurrentPage(1);
    } catch (err) {
      const errorMessage = err.message || '获取数据失败';
      console.error('加载股票数据失败:', errorMessage);
      setError(errorMessage);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDate) loadData();
  }, [selectedDate]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchKeyword]);

  const getFilteredData = () => {
    if (!data?.data) return [];
    let filtered = data.data;
    if (searchKeyword) {
      const keyword = searchKeyword.toLowerCase();
      filtered = filtered.filter(s => 
        s.name?.toLowerCase().includes(keyword) || 
        s.code?.toLowerCase().includes(keyword) ||
        s.industry?.toLowerCase().includes(keyword)
      );
    }
    filtered = [...filtered].sort((a, b) => {
      let aVal = a[sortField], bVal = b[sortField];
      if (sortField === 'name' || sortField === 'code' || sortField === 'industry') {
        aVal = aVal || '';
        bVal = bVal || '';
        return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
    return filtered;
  };

  const toggleSort = (field) => {
    if (sortField === field) setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortOrder(field === 'rank' ? 'asc' : 'desc'); }
  };

  const filteredData = getFilteredData();
  const totalPages = Math.ceil(filteredData.length / pageSize);
  const paginatedData = filteredData.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  
  const columns = [
    { key: 'rank', label: '排名' },
    { key: 'code', label: '代码' },
    { key: 'name', label: '名称' },
    { key: 'industry', label: '行业' },
    { key: 'total_score', label: '总分' },
    { key: 'price_change', label: '涨跌幅' },
    { key: 'close_price', label: '收盘价' },
    { key: 'turnover_rate', label: '换手率' },
    { key: 'volume_days', label: '放量天数' },
    { key: 'volatility', label: '波动率' },
    { key: 'market_cap', label: '市值(亿)' },
  ];

  return (
    <div className="max-w-7xl mx-auto p-4 md:p-6">
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 mb-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <TrendingUp className="h-6 w-6 text-green-500" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">当日股票排名数据</h2>
              <p className="text-gray-500 text-sm">{data ? `${formatDate(data.date)} 共 ${data.total_count} 只股票` : '加载中...'}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input 
                type="text" 
                value={searchKeyword} 
                onChange={(e) => setSearchKeyword(e.target.value)} 
                placeholder="搜索代码/名称/行业..." 
                className="pl-9 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 text-sm w-48" 
              />
            </div>
            <button 
              onClick={loadData} 
              disabled={loading} 
              className="px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2 disabled:opacity-50 text-sm"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
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
          <RefreshCw className="h-8 w-8 text-green-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">加载数据中...</p>
        </div>
      )}

      {!loading && filteredData.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto max-h-[550px]">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  {columns.map(col => (
                    <th 
                      key={col.key} 
                      onClick={() => toggleSort(col.key)} 
                      className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    >
                      {col.label}
                      {sortField === col.key && (sortOrder === 'asc' ? ' ↑' : ' ↓')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {paginatedData.map((item, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className={`text-sm font-bold ${item.rank <= 10 ? 'text-red-600' : item.rank <= 50 ? 'text-orange-600' : item.rank <= 100 ? 'text-blue-600' : 'text-gray-600'}`}>
                        {item.rank}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm font-mono text-gray-700">{item.code}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{item.name}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-600">{item.industry || '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.total_score?.toFixed(2) || '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <span className={`text-sm font-medium ${item.price_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {item.price_change >= 0 ? '+' : ''}{item.price_change?.toFixed(2) || '0.00'}%
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.close_price?.toFixed(2) || '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.turnover_rate?.toFixed(2) || '-'}%</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.volume_days?.toFixed(1) || '-'}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.volatility?.toFixed(2) || '-'}%</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">{item.market_cap?.toFixed(2) || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 flex items-center justify-between flex-wrap gap-3">
            <div className="text-sm text-gray-500">
              共 {filteredData.length} 条数据，显示第 {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, filteredData.length)} 条
              {searchKeyword && ` (搜索: "${searchKeyword}")`}
            </div>
            <div className="flex items-center gap-2">
              <select 
                value={pageSize} 
                onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                className="px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value={50}>50条/页</option>
                <option value={100}>100条/页</option>
                <option value={200}>200条/页</option>
                <option value={500}>500条/页</option>
              </select>
              <button 
                onClick={() => setCurrentPage(1)} 
                disabled={currentPage === 1}
                className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 hover:bg-gray-100"
              >
                首页
              </button>
              <button 
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))} 
                disabled={currentPage === 1}
                className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 hover:bg-gray-100"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-gray-600">
                {currentPage} / {totalPages}
              </span>
              <button 
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} 
                disabled={currentPage === totalPages}
                className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 hover:bg-gray-100"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button 
                onClick={() => setCurrentPage(totalPages)} 
                disabled={currentPage === totalPages}
                className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 hover:bg-gray-100"
              >
                末页
              </button>
            </div>
          </div>
        </div>
      )}

      {!loading && !error && filteredData.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <TrendingUp className="h-12 w-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">
            {searchKeyword ? `没有找到包含 "${searchKeyword}" 的股票` : '暂无数据'}
          </p>
        </div>
      )}
    </div>
  );
}
