/**
 * 板块信号标签组件
 * 显示格式：[S级｜锂电池]
 * 
 * 样式说明：
 * - S级：橙→粉渐变，白字（最强信号）
 * - A级：蓝紫→粉渐变，白字
 * - B级：灰色半透明，浅色字
 * - NONE：不渲染
 */
import React from 'react';

const LEVEL_STYLES = {
  S: {
    background: 'linear-gradient(135deg, #f97316 0%, #ec4899 100%)',
    textColor: 'white',
    borderColor: 'transparent',
    shadowColor: 'rgba(249, 115, 22, 0.4)',
  },
  A: {
    background: 'linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)',
    textColor: 'white',
    borderColor: 'transparent',
    shadowColor: 'rgba(139, 92, 246, 0.4)',
  },
  B: {
    background: 'rgba(156, 163, 175, 0.2)',
    textColor: '#6b7280',
    borderColor: '#d1d5db',
    shadowColor: 'transparent',
  },
};

export default function BoardSignalBadge({
  level = 'NONE',
  label = '',
  type = 'concept',
  heatPct,
  onClick,
  size = 'md',
  showHeat = false,
}) {
  // NONE 级别不渲染
  if (level === 'NONE' || !label) {
    return null;
  }

  const style = LEVEL_STYLES[level] || LEVEL_STYLES.B;
  
  // 尺寸配置
  const sizeClasses = {
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  const baseClasses = `
    inline-flex items-center gap-1 rounded-full font-medium
    transition-all duration-200 cursor-pointer
    ${sizeClasses[size] || sizeClasses.md}
  `;

  const inlineStyle = {
    background: style.background,
    color: style.textColor,
    border: style.borderColor !== 'transparent' ? `1px solid ${style.borderColor}` : 'none',
    boxShadow: style.shadowColor !== 'transparent' ? `0 2px 8px ${style.shadowColor}` : 'none',
  };

  // 类型图标
  const typeIcon = type === 'industry' ? '🏭' : '💡';

  return (
    <span
      className={baseClasses}
      style={inlineStyle}
      onClick={onClick}
      title={`${level}级板块信号｜${label}${heatPct ? ` (热度: ${(heatPct * 100).toFixed(1)}%)` : ''}`}
    >
      <span className="font-bold">{level}级</span>
      <span className="opacity-60">｜</span>
      <span>{typeIcon} {label}</span>
      {showHeat && heatPct !== undefined && (
        <span className="ml-1 opacity-75 text-xs">
          {(heatPct * 100).toFixed(0)}%
        </span>
      )}
    </span>
  );
}

/**
 * 简化版标签（只显示板块名）
 */
export function BoardBadge({
  boardName,
  boardType = 'concept',
  heatPct,
  onClick,
  size = 'sm',
}) {
  const isHot = heatPct && heatPct >= 0.8;
  const isWarm = heatPct && heatPct >= 0.5;

  const bgColor = isHot 
    ? 'bg-gradient-to-r from-orange-100 to-pink-100 border-orange-200' 
    : isWarm 
      ? 'bg-blue-50 border-blue-200'
      : 'bg-gray-50 border-gray-200';

  const textColor = isHot 
    ? 'text-orange-700' 
    : isWarm 
      ? 'text-blue-700'
      : 'text-gray-600';

  const sizeClasses = {
    xs: 'text-xs px-1 py-0.5',
    sm: 'text-xs px-1.5 py-0.5',
    md: 'text-sm px-2 py-1',
  };

  const typeIcon = boardType === 'industry' ? '🏭' : '💡';

  return (
    <span
      className={`
        inline-flex items-center gap-0.5 rounded border
        ${bgColor} ${textColor} ${sizeClasses[size] || sizeClasses.sm}
        ${onClick ? 'cursor-pointer hover:opacity-80' : ''}
      `}
      onClick={onClick}
      title={boardName + (heatPct ? ` (热度: ${(heatPct * 100).toFixed(1)}%)` : '')}
    >
      <span className="opacity-60">{typeIcon}</span>
      <span>{boardName}</span>
      {heatPct !== undefined && (
        <span className={`ml-0.5 ${isHot ? 'text-orange-600' : 'opacity-60'}`}>
          {(heatPct * 100).toFixed(0)}%
        </span>
      )}
    </span>
  );
}

/**
 * 板块信号列表组件（用于展示个股的所有关联板块）
 */
export function BoardSignalList({
  boards = [],
  maxShow = 3,
  onBoardClick,
}) {
  if (!boards || boards.length === 0) {
    return <span className="text-gray-400 text-xs">暂无板块</span>;
  }

  const displayBoards = boards.slice(0, maxShow);
  const remainCount = boards.length - maxShow;

  return (
    <div className="flex flex-wrap gap-1 items-center">
      {displayBoards.map((board, idx) => (
        <BoardBadge
          key={board.board_id || idx}
          boardName={board.board_name}
          boardType={board.board_type}
          heatPct={board.heat_pct}
          onClick={onBoardClick ? () => onBoardClick(board) : undefined}
          size="xs"
        />
      ))}
      {remainCount > 0 && (
        <span className="text-xs text-gray-400">
          +{remainCount}
        </span>
      )}
    </div>
  );
}
