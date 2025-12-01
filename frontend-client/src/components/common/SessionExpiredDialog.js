/**
 * 会话过期提示对话框
 */
import React from 'react';
import { AlertCircle, LogIn } from 'lucide-react';

function SessionExpiredDialog({ isOpen, onConfirm }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      
      {/* 对话框 */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-sm w-full mx-4 overflow-hidden">
        {/* 顶部装饰 */}
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 h-2" />
        
        <div className="p-6">
          {/* 图标 */}
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-amber-600" />
            </div>
          </div>
          
          {/* 标题 */}
          <h3 className="text-xl font-bold text-center text-slate-800 mb-2">
            会话已过期
          </h3>
          
          {/* 描述 */}
          <p className="text-center text-slate-600 mb-6">
            您的登录会话已过期，请重新登录以继续使用
          </p>
          
          {/* 按钮 */}
          <button
            onClick={onConfirm}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-medium rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all shadow-lg"
          >
            <LogIn className="w-5 h-5" />
            重新登录
          </button>
        </div>
      </div>
    </div>
  );
}

export default SessionExpiredDialog;
