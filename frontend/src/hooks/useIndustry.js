/**
 * 行业数据Hook
 */
import { useState, useEffect } from 'react';
import { getTop1000IndustryStats, getIndustryTrend } from '../services';

export const useTop1000Industry = (shouldLoad) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!shouldLoad || data) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getTop1000IndustryStats();
        setData(result);
      } catch (err) {
        setError(err.response?.data?.detail || '获取数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [shouldLoad, data]);

  return { data, loading, error };
};

export const useIndustryTrend = (shouldLoad) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!shouldLoad || data) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getIndustryTrend();
        setData(result);
      } catch (err) {
        setError(err.response?.data?.detail || '获取数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [shouldLoad, data]);

  return { data, loading, error };
};
