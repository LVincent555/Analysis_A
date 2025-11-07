/**
 * 稳步上升分析 Hook
 */
import { useState, useEffect } from 'react';
import { analyzeSteadyRise } from '../services';

export function useSteadyRise(period, boardType, minImprovement) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!period || !boardType || !minImprovement) return;
      
      setLoading(true);
      setError(null);
      try {
        const result = await analyzeSteadyRise(period, boardType, minImprovement);
        setData(result);
      } catch (err) {
        setError(err.message || '获取数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period, boardType, minImprovement]);

  return { data, loading, error };
}
