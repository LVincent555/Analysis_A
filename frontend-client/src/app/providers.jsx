import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { HashRouter } from 'react-router-dom';
import queryClient from '../shared/api/queryClient';

export default function AppProviders({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        {children}
      </HashRouter>
    </QueryClientProvider>
  );
}
