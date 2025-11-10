/**
 * 高亮文本组件
 * 用于搜索结果中高亮显示匹配的文本
 */
import React from 'react';

export default function HighlightText({ text, highlight }) {
  // 如果没有高亮词，直接返回文本
  if (!highlight || !highlight.trim()) {
    return <>{text}</>;
  }

  // 转义特殊字符
  const escapeRegex = (str) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  
  try {
    // 使用正则表达式分割文本
    const escapedHighlight = escapeRegex(highlight);
    const parts = String(text || '').split(new RegExp(`(${escapedHighlight})`, 'gi'));
    
    return (
      <>
        {parts.map((part, index) => {
          // 比较时忽略大小写
          const isMatch = part.toLowerCase() === highlight.toLowerCase();
          
          return isMatch ? (
            <mark 
              key={index} 
              className="bg-yellow-200 text-yellow-900 font-semibold px-0.5 rounded"
            >
              {part}
            </mark>
          ) : (
            <span key={index}>{part}</span>
          );
        })}
      </>
    );
  } catch (error) {
    // 如果正则表达式有误，返回原文本
    return <>{text}</>;
  }
}
