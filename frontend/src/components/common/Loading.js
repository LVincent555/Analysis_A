/**
 * 加载中组件
 */
import React from 'react';
import { RefreshCw } from 'lucide-react';

const Loading = ({ message = '正在加载数据...' }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-12 text-center">
      <RefreshCw className="mx-auto h-12 w-12 text-indigo-600 animate-spin mb-4" />
      <p className="text-gray-600 text-lg">{message}</p>
    </div>
  );
};

export default Loading;
