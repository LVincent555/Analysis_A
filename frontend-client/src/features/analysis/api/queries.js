import { useQuery } from '@tanstack/react-query';
import secureClient from '../../../shared/api/secureClient';

export const analysisQueryKeys = {
  all: ['analysis'],
  dates: () => [...analysisQueryKeys.all, 'dates'],
  periodAnalysis: (params) => [...analysisQueryKeys.all, 'periodAnalysis', params]
};

export async function fetchAvailableDates() {
  return secureClient.get('/api/dates');
}

export function useAvailableDatesQuery(options = {}) {
  return useQuery({
    queryKey: analysisQueryKeys.dates(),
    queryFn: fetchAvailableDates,
    ...options
  });
}

export async function fetchPeriodAnalysis({ period, boardType = 'main', topN = 100, date = null }) {
  const params = new URLSearchParams({
    board_type: boardType,
    top_n: String(topN)
  });

  if (date) {
    params.set('date', date);
  }

  return secureClient.get(`/api/analyze/${period}?${params.toString()}`);
}

export function usePeriodAnalysisQuery({
  period,
  boardType,
  topN,
  date,
  refreshTrigger = 0
}, options = {}) {
  const enabled = Boolean(period && boardType && topN && date);
  const params = { period, boardType, topN, date, refreshTrigger };

  return useQuery({
    queryKey: analysisQueryKeys.periodAnalysis(params),
    queryFn: () => fetchPeriodAnalysis({ period, boardType, topN, date }),
    enabled,
    ...options
  });
}
