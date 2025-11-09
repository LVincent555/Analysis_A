/**
 * 板块查询模块
 * 提供板块搜索和跳转到详情页面的功能
 */
import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, ArrowRight } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from '../../constants/config';

export default function IndustryQueryModule({ onNavigate }) {
  const [industryName, setIndustryName] = useState('');
  const [industries, setIndustries] = useState([]);
  const [filteredIndustries, setFilteredIndustries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 加载所有行业列表
  useEffect(() => {
    const fetchIndustries = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/industry/top1000?limit=1000`);
        if (response.data && response.data.stats) {
          const industryList = response.data.stats.map(stat => stat.industry);
          setIndustries(industryList);
        }
      } catch (err) {
        console.error('加载行业列表失败:', err);
      }
    };
    fetchIndustries();
  }, []);

  // 筛选行业列表
  useEffect(() => {
    if (industryName.trim()) {
      const filtered = industries.filter(ind => 
        ind.includes(industryName.trim())
      );
      setFilteredIndustries(filtered);
    } else {
      setFilteredIndustries([]);
    }
  }, [industryName, industries]);

  // 查询板块
  const handleQuery = async (selectedIndustry) => {
    const targetIndustry = selectedIndustry || industryName.trim();
    
    if (!targetIndustry) {
      setError('请输入板块名称');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      // 验证板块是否存在
      const response = await axios.get(
        `${API_BASE_URL}/api/industry/${encodeURIComponent(targetIndustry)}/detail`
      );
      
      if (response.status === 200) {
        // 跳转到详情页面
        if (onNavigate) {
          onNavigate(targetIndustry);
        }
      }
    } catch (err) {
      if (err.response?.status === 404) {
        setError(`未找到板块 "${targetIndustry}"，请检查名称是否正确`);
      } else {
        setError(err.response?.data?.detail || '查询失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Search className="h-6 w-6 text-purple-600" />
          <h3 className="text-xl font-bold text-gray-900">板块查询</h3>
        </div>
        <p className="text-gray-600">
          输入板块名称查看详细分析、成分股信息、历史趋势和板块对比
        </p>
      </div>

      {/* 搜索框 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          请输入板块名称：
        </label>
        <div className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={industryName}
              onChange={(e) => setIndustryName(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
              placeholder="例如：化学制品、通信设备、医疗器械..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
            {filteredIndustries.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {filteredIndustries.slice(0, 10).map((ind, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setIndustryName(ind);
                      setFilteredIndustries([]);
                      handleQuery(ind);
                    }}
                    className="w-full text-left px-4 py-2 hover:bg-purple-50 transition-colors border-b border-gray-100 last:border-b-0"
                  >
                    <span className="text-gray-900">{ind}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => handleQuery()}
            disabled={loading || !industryName.trim()}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <Search className={`h-5 w-5 ${loading ? 'animate-pulse' : ''}`} />
            <span>{loading ? '查询中...' : '查询'}</span>
          </button>
        </div>
        {error && (
          <p className="mt-3 text-sm text-red-600 bg-red-50 px-4 py-2 rounded">{error}</p>
        )}
      </div>

      {/* 热门板块快捷入口 */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center">
          <TrendingUp className="h-4 w-4 mr-2 text-purple-600" />
          热门板块快速查询
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {industries.slice(0, 12).map((ind, index) => (
            <button
              key={index}
              onClick={() => handleQuery(ind)}
              className="px-4 py-3 bg-gradient-to-r from-purple-50 to-indigo-50 hover:from-purple-100 hover:to-indigo-100 border border-purple-200 rounded-lg text-sm font-medium text-gray-700 transition-all flex items-center justify-between group"
            >
              <span>{ind}</span>
              <ArrowRight className="h-4 w-4 text-purple-600 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          ))}
        </div>
      </div>

      {/* 使用说明 */}
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-6 border border-indigo-200">
        <h4 className="text-sm font-bold text-indigo-900 mb-3">💡 使用说明</h4>
        <div className="space-y-2 text-sm text-indigo-800">
          <p>• <strong>输入搜索</strong>：在搜索框中输入板块名称，支持模糊匹配</p>
          <p>• <strong>快捷选择</strong>：点击下方热门板块快速查询</p>
          <p>• <strong>查看详情</strong>：查询后将跳转到板块详情页面，包含：</p>
          <div className="ml-6 space-y-1">
            <p>- 板块概览（排名、TOP100数量、信号强度等）</p>
            <p>- 成分股分析（完整列表、排序、筛选、分页）</p>
            <p>- 历史趋势（4维指标趋势、成分股数量趋势）</p>
            <p>- 板块对比（与其他板块的多维度对比）</p>
          </div>
        </div>
      </div>
    </div>
  );
}
