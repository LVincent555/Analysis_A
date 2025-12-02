"""
索引管理器 - 管理 stock_code/date 与 idx 的双向映射

核心功能：
1. stock_code ↔ stock_idx 双向映射
2. date ↔ date_idx 双向映射
3. (stock_idx, date_idx) → row_idx 复合索引
4. date_idx → (start_row, end_row) 日期分组索引
"""

import numpy as np
from datetime import date
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IndexManager:
    """
    高性能索引管理器
    
    ⚠️ 字符串处理策略：
       - Numpy数组中绝对禁止存储字符串
       - 只存 stock_idx (int32)，通过本类反查 stock_code
    """
    
    def __init__(self):
        # === 股票索引 ===
        self.stock_code_to_idx: Dict[str, int] = {}
        self.idx_to_stock_code: List[str] = []
        
        # === 日期索引 ===
        self.date_to_idx: Dict[date, int] = {}
        self.idx_to_date: List[date] = []
        
        # === 复合索引 (stock_idx, date_idx) → row_idx ===
        # 用于 O(1) 查询单条数据
        self.composite_idx: Dict[Tuple[int, int], int] = {}
        
        # === 日期分组索引 date_idx → (start_row, end_row) ===
        # 用于快速获取某日期的所有数据
        self.date_range_idx: Dict[int, Tuple[int, int]] = {}
        
        # === 股票分组索引 stock_idx → List[row_idx] ===
        # 用于获取某股票的所有历史数据
        self.stock_rows_idx: Dict[int, List[int]] = {}
        
        # 状态
        self._initialized = False
    
    # ========== 构建索引 ==========
    
    def build_stock_index(self, stock_codes: List[str]) -> None:
        """
        构建股票代码索引
        
        Args:
            stock_codes: 唯一的股票代码列表
        """
        self.stock_code_to_idx.clear()
        self.idx_to_stock_code = list(stock_codes)
        
        for idx, code in enumerate(stock_codes):
            self.stock_code_to_idx[code] = idx
        
        logger.debug(f"构建股票索引: {len(stock_codes)} 只股票")
    
    def build_date_index(self, dates: List[date]) -> None:
        """
        构建日期索引
        
        Args:
            dates: 唯一的日期列表 (应按降序排列，最新日期在前)
        """
        self.date_to_idx.clear()
        self.idx_to_date = list(dates)
        
        for idx, d in enumerate(dates):
            self.date_to_idx[d] = idx
        
        logger.debug(f"构建日期索引: {len(dates)} 天")
    
    def build_composite_index(
        self, 
        stock_indices: np.ndarray, 
        date_indices: np.ndarray
    ) -> None:
        """
        构建复合索引 (stock_idx, date_idx) → row_idx
        
        Args:
            stock_indices: 数组中所有记录的 stock_idx
            date_indices: 数组中所有记录的 date_idx
        """
        self.composite_idx.clear()
        self.date_range_idx.clear()
        self.stock_rows_idx.clear()
        
        n_records = len(stock_indices)
        
        # 临时变量用于构建日期范围索引
        current_date_idx = -1
        range_start = 0
        
        for row_idx in range(n_records):
            stock_idx = int(stock_indices[row_idx])
            date_idx = int(date_indices[row_idx])
            
            # 复合索引
            self.composite_idx[(stock_idx, date_idx)] = row_idx
            
            # 股票分组索引
            if stock_idx not in self.stock_rows_idx:
                self.stock_rows_idx[stock_idx] = []
            self.stock_rows_idx[stock_idx].append(row_idx)
            
            # 日期范围索引 (假设数据按日期分组排列)
            if date_idx != current_date_idx:
                if current_date_idx >= 0:
                    self.date_range_idx[current_date_idx] = (range_start, row_idx)
                current_date_idx = date_idx
                range_start = row_idx
        
        # 最后一个日期的范围
        if current_date_idx >= 0:
            self.date_range_idx[current_date_idx] = (range_start, n_records)
        
        self._initialized = True
        logger.debug(f"构建复合索引: {n_records} 条记录, {len(self.date_range_idx)} 个日期分组")
    
    # ========== 查询接口 ==========
    
    def get_stock_idx(self, stock_code: str) -> Optional[int]:
        """获取股票代码对应的索引"""
        return self.stock_code_to_idx.get(stock_code)
    
    def get_stock_code(self, stock_idx: int) -> Optional[str]:
        """获取索引对应的股票代码"""
        if 0 <= stock_idx < len(self.idx_to_stock_code):
            return self.idx_to_stock_code[stock_idx]
        return None
    
    def get_date_idx(self, target_date: date) -> Optional[int]:
        """获取日期对应的索引"""
        return self.date_to_idx.get(target_date)
    
    def get_date(self, date_idx: int) -> Optional[date]:
        """获取索引对应的日期"""
        if 0 <= date_idx < len(self.idx_to_date):
            return self.idx_to_date[date_idx]
        return None
    
    def get_row_idx(self, stock_idx: int, date_idx: int) -> Optional[int]:
        """
        获取 (stock_idx, date_idx) 对应的行号
        
        Returns:
            行号，不存在则返回 None
        """
        return self.composite_idx.get((stock_idx, date_idx))
    
    def get_row_idx_by_code_date(self, stock_code: str, target_date: date) -> Optional[int]:
        """
        获取 (stock_code, date) 对应的行号
        
        便捷方法，内部转换为索引查询
        """
        stock_idx = self.get_stock_idx(stock_code)
        date_idx = self.get_date_idx(target_date)
        
        if stock_idx is None or date_idx is None:
            return None
        
        return self.get_row_idx(stock_idx, date_idx)
    
    def get_rows_by_date(self, date_idx: int) -> Optional[Tuple[int, int]]:
        """
        获取某日期的所有数据行范围
        
        Returns:
            (start_row, end_row) 左闭右开区间
        """
        return self.date_range_idx.get(date_idx)
    
    def get_rows_by_stock(self, stock_idx: int) -> List[int]:
        """
        获取某股票的所有历史数据行号
        
        Returns:
            行号列表
        """
        return self.stock_rows_idx.get(stock_idx, [])
    
    # ========== 日期查询 ==========
    
    def get_all_dates(self) -> List[date]:
        """获取所有日期 (按原始顺序，通常是降序)"""
        return self.idx_to_date.copy()
    
    def get_latest_date(self) -> Optional[date]:
        """获取最新日期"""
        if self.idx_to_date:
            return self.idx_to_date[0]
        return None
    
    def get_dates_range(self, n: int) -> List[date]:
        """获取最近N天日期"""
        return self.idx_to_date[:n]
    
    def has_date(self, target_date: date) -> bool:
        """检查日期是否存在"""
        return target_date in self.date_to_idx
    
    # ========== 股票查询 ==========
    
    def get_all_stock_codes(self) -> List[str]:
        """获取所有股票代码"""
        return self.idx_to_stock_code.copy()
    
    def has_stock(self, stock_code: str) -> bool:
        """检查股票是否存在"""
        return stock_code in self.stock_code_to_idx
    
    # ========== 状态查询 ==========
    
    def is_initialized(self) -> bool:
        """检查索引是否已初始化"""
        return self._initialized
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            'n_stocks': len(self.idx_to_stock_code),
            'n_dates': len(self.idx_to_date),
            'n_composite_entries': len(self.composite_idx),
            'n_date_groups': len(self.date_range_idx),
            'initialized': self._initialized,
        }
    
    def clear(self) -> None:
        """清空所有索引"""
        self.stock_code_to_idx.clear()
        self.idx_to_stock_code.clear()
        self.date_to_idx.clear()
        self.idx_to_date.clear()
        self.composite_idx.clear()
        self.date_range_idx.clear()
        self.stock_rows_idx.clear()
        self._initialized = False
        logger.debug("索引已清空")
