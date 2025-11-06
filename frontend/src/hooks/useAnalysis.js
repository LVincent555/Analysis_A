/**
 * 分析数据Hook
 */
import { useState, useEffect } from 'react';
import { analyzePeriod, getAvailableDates } from '../services';

export const useAnalysis = (period) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!period) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await analyzePeriod(period);
        setData(result);
      } catch (err) {
        setError(err.response?.data?.detail || '获取数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period]);

  return { data, loading, error };
};

export const useAvailableDates = () => {
  const [dates, setDates] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDates = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getAvailableDates();
        setDates(result);
      } catch (err) {
        setError(err.response?.data?.detail || '获取日期失败');
      } finally {
        setLoading(false);
      }
    };

    fetchDates();
  }, []);

  return { dates, loading, error };
};
