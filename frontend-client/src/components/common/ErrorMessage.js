/**
 * 错误提示组件
 */
import React from 'react';

const ErrorMessage = ({ message }) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <p className="text-red-800 font-medium">错误: {message}</p>
    </div>
  );
};

export default ErrorMessage;
