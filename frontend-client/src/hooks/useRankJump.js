/**
 * 排名跳变分析 Hook
 */
import { useState, useEffect } from 'react';
import { analyzeRankJump } from '../services';

export function useRankJump(period, threshold, boardType) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!period || !threshold || !boardType) return;
      
      setLoading(true);
      setError(null);
      try {
        const result = await analyzeRankJump(period, threshold, boardType);
        setData(result);
      } catch (err) {
        setError(err.message || '获取数据失败');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period, threshold, boardType]);

  return { data, loading, error };
}
