"""
股票每日数据存储 - 基于 Numpy 结构化数组

⚠️ 关键技术规范：
   - 价格/金额/总分 → np.float64 (避免0.01误差导致排名错误)
   - 其他指标 → np.float32 (节省空间)
   - 整数空值 → 填充默认值 (rank=-1, volume=0)
   - 禁止存储字符串 → 只存 stock_idx
"""

import numpy as np
from datetime import date
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging

from .index_manager import IndexManager

logger = logging.getLogger(__name__)


# === 统一 dtype 定义 (合并 core + extended) ===
DAILY_DTYPE = np.dtype([
    # === 索引字段 ===
    ('stock_idx', np.int32),       # 4B - 股票索引 (非字符串!)
    ('date_idx', np.int32),        # 4B - 日期索引
    
    # === 核心字段 (float64 高精度) ===
    ('rank', np.int32),            # 4B - 排名 (空值填-1)
    ('total_score', np.float64),   # 8B - 总分
    ('price_change', np.float64),  # 8B - 涨跌幅
    ('close_price', np.float64),   # 8B - 收盘价
    ('open_price', np.float64),    # 8B - 开盘价
    ('high_price', np.float64),    # 8B - 最高价
    ('low_price', np.float64),     # 8B - 最低价
    ('market_cap', np.float64),    # 8B - 总市值(亿)
    
    # === 交易数据 ===
    ('volume', np.int64),          # 8B - 成交量 (空值填0)
    ('turnover_rate', np.float32), # 4B - 换手率
    ('volatility', np.float32),    # 4B - 波动率
    ('volume_days', np.float32),   # 4B - 量比(天)
    ('avg_volume_ratio_50', np.float32),  # 4B - 50日均量比
    
    # === 技术指标 (float32 足够) ===
    ('macd_signal', np.float32),   # 4B
    ('dif', np.float32),           # 4B
    ('dem', np.float32),           # 4B
    ('histgram', np.float32),      # 4B - MACD柱
    ('rsi', np.float32),           # 4B
    ('slowk', np.float32),         # 4B - KDJ
    ('adx', np.float32),           # 4B
    ('plus_di', np.float32),       # 4B
    ('beta', np.float32),          # 4B
    ('correlation', np.float32),   # 4B
    ('long_term', np.float32),     # 4B
    ('short_term', np.int16),      # 2B
    ('overbought', np.int16),      # 2B
    ('oversold', np.int16),        # 2B
    
    # === BOLL ===
    ('lower_band', np.float32),    # 4B
    ('middle_band', np.float32),   # 4B
    ('upper_band', np.float32),    # 4B
])


def _safe_int(value: Any, default: int = -1) -> int:
    """安全转换为int，空值返回默认值"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为float，空值返回默认值"""
    if value is None:
        return default
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default


class DailyDataStore:
    """
    股票每日数据存储
    
    使用 Numpy 结构化数组存储，内存效率高，查询快速
    """
    
    def __init__(self):
        self.data_array: Optional[np.ndarray] = None
        self._n_records = 0
    
    def build_from_tuples(
        self,
        rows: List[tuple],
        index_mgr: IndexManager,
        field_mapping: Dict[str, int]
    ) -> None:
        """
        从数据库查询结果 (Tuples) 构建数组
        
        Args:
            rows: 数据库查询结果，List[tuple]
            index_mgr: 索引管理器 (必须已构建好 stock/date 索引)
            field_mapping: 字段名 → tuple索引 的映射
        
        Example:
            field_mapping = {
                'stock_code': 0,
                'date': 1,
                'rank': 2,
                'total_score': 3,
                ...
            }
        """
        n_records = len(rows)
        if n_records == 0:
            self.data_array = np.zeros(0, dtype=DAILY_DTYPE)
            self._n_records = 0
            return
        
        # 创建数组
        self.data_array = np.zeros(n_records, dtype=DAILY_DTYPE)
        
        # 字段索引
        f = field_mapping
        
        for i, row in enumerate(rows):
            # 获取索引
            stock_code = row[f['stock_code']]
            row_date = row[f['date']]
            
            stock_idx = index_mgr.get_stock_idx(stock_code)
            date_idx = index_mgr.get_date_idx(row_date)
            
            if stock_idx is None or date_idx is None:
                continue
            
            # 填充数据
            self.data_array[i]['stock_idx'] = stock_idx
            self.data_array[i]['date_idx'] = date_idx
            
            # 核心字段
            self.data_array[i]['rank'] = _safe_int(row[f.get('rank', -1)], -1)
            self.data_array[i]['total_score'] = _safe_float(row[f.get('total_score', -1)])
            self.data_array[i]['price_change'] = _safe_float(row[f.get('price_change', -1)])
            self.data_array[i]['close_price'] = _safe_float(row[f.get('close_price', -1)])
            self.data_array[i]['open_price'] = _safe_float(row[f.get('open_price', -1)])
            self.data_array[i]['high_price'] = _safe_float(row[f.get('high_price', -1)])
            self.data_array[i]['low_price'] = _safe_float(row[f.get('low_price', -1)])
            self.data_array[i]['market_cap'] = _safe_float(row[f.get('market_cap', -1)])
            
            # 交易数据
            self.data_array[i]['volume'] = _safe_int(row[f.get('volume', -1)], 0)
            self.data_array[i]['turnover_rate'] = _safe_float(row[f.get('turnover_rate', -1)])
            self.data_array[i]['volatility'] = _safe_float(row[f.get('volatility', -1)])
            self.data_array[i]['volume_days'] = _safe_float(row[f.get('volume_days', -1)])
            self.data_array[i]['avg_volume_ratio_50'] = _safe_float(row[f.get('avg_volume_ratio_50', -1)])
            
            # 技术指标 (按需填充)
            if 'macd_signal' in f:
                self.data_array[i]['macd_signal'] = _safe_float(row[f['macd_signal']])
            if 'dif' in f:
                self.data_array[i]['dif'] = _safe_float(row[f['dif']])
            if 'dem' in f:
                self.data_array[i]['dem'] = _safe_float(row[f['dem']])
            if 'histgram' in f:
                self.data_array[i]['histgram'] = _safe_float(row[f['histgram']])
            if 'rsi' in f:
                self.data_array[i]['rsi'] = _safe_float(row[f['rsi']])
            if 'slowk' in f:
                self.data_array[i]['slowk'] = _safe_float(row[f['slowk']])
            if 'adx' in f:
                self.data_array[i]['adx'] = _safe_float(row[f['adx']])
            if 'plus_di' in f:
                self.data_array[i]['plus_di'] = _safe_float(row[f['plus_di']])
            if 'beta' in f:
                self.data_array[i]['beta'] = _safe_float(row[f['beta']])
            if 'correlation' in f:
                self.data_array[i]['correlation'] = _safe_float(row[f['correlation']])
            if 'long_term' in f:
                self.data_array[i]['long_term'] = _safe_float(row[f['long_term']])
            if 'short_term' in f:
                self.data_array[i]['short_term'] = _safe_int(row[f['short_term']], 0)
            if 'overbought' in f:
                self.data_array[i]['overbought'] = _safe_int(row[f['overbought']], 0)
            if 'oversold' in f:
                self.data_array[i]['oversold'] = _safe_int(row[f['oversold']], 0)
            if 'lower_band' in f:
                self.data_array[i]['lower_band'] = _safe_float(row[f['lower_band']])
            if 'middle_band' in f:
                self.data_array[i]['middle_band'] = _safe_float(row[f['middle_band']])
            if 'upper_band' in f:
                self.data_array[i]['upper_band'] = _safe_float(row[f['upper_band']])
        
        self._n_records = n_records
        logger.info(f"✅ DailyDataStore 构建完成: {n_records} 条记录")
    
    # ========== 查询接口 ==========
    
    def get_row(self, row_idx: int) -> Optional[np.void]:
        """获取指定行的数据"""
        if self.data_array is None or row_idx < 0 or row_idx >= self._n_records:
            return None
        return self.data_array[row_idx]
    
    def get_rows_slice(self, start: int, end: int) -> np.ndarray:
        """获取指定范围的数据 [start, end)"""
        if self.data_array is None:
            return np.zeros(0, dtype=DAILY_DTYPE)
        return self.data_array[start:end]
    
    def get_rows_by_indices(self, indices: List[int]) -> np.ndarray:
        """获取指定行号列表的数据"""
        if self.data_array is None or not indices:
            return np.zeros(0, dtype=DAILY_DTYPE)
        return self.data_array[indices]
    
    def get_top_n_by_rank(self, start: int, end: int, n: int) -> np.ndarray:
        """
        从指定范围获取排名前N的数据
        
        Args:
            start: 起始行号
            end: 结束行号
            n: 返回数量
        """
        if self.data_array is None:
            return np.zeros(0, dtype=DAILY_DTYPE)
        
        slice_data = self.data_array[start:end]
        
        # 按 rank 升序排序 (rank越小越靠前)
        sorted_indices = np.argsort(slice_data['rank'])
        
        return slice_data[sorted_indices[:n]]
    
    # ========== 转换方法 ==========
    
    def row_to_dict(self, row: np.void, index_mgr: IndexManager) -> Dict:
        """
        将单行数据转换为字典
        
        Args:
            row: Numpy行数据
            index_mgr: 索引管理器，用于反查 stock_code 和 date
        """
        stock_code = index_mgr.get_stock_code(int(row['stock_idx']))
        row_date = index_mgr.get_date(int(row['date_idx']))
        
        return {
            'stock_code': stock_code,
            'date': row_date.strftime('%Y%m%d') if row_date else None,
            'rank': int(row['rank']) if row['rank'] >= 0 else None,
            'total_score': float(row['total_score']),
            'price_change': float(row['price_change']),
            'close_price': float(row['close_price']),
            'open_price': float(row['open_price']),
            'high_price': float(row['high_price']),
            'low_price': float(row['low_price']),
            'market_cap': float(row['market_cap']),
            'volume': int(row['volume']),
            'turnover_rate': float(row['turnover_rate']),
            'volatility': float(row['volatility']),
            'volume_days': float(row['volume_days']),
            'avg_volume_ratio_50': float(row['avg_volume_ratio_50']),
            # 技术指标
            'macd_signal': float(row['macd_signal']),
            'dif': float(row['dif']),
            'dem': float(row['dem']),
            'rsi': float(row['rsi']),
            'slowk': float(row['slowk']),
            'adx': float(row['adx']),
            'beta': float(row['beta']),
            'correlation': float(row['correlation']),
            'lower_band': float(row['lower_band']),
            'middle_band': float(row['middle_band']),
            'upper_band': float(row['upper_band']),
        }
    
    def rows_to_dicts(self, rows: np.ndarray, index_mgr: IndexManager) -> List[Dict]:
        """将多行数据转换为字典列表"""
        return [self.row_to_dict(row, index_mgr) for row in rows]
    
    # ========== 状态查询 ==========
    
    def get_memory_usage(self) -> Dict:
        """获取内存使用统计"""
        if self.data_array is None:
            return {'n_records': 0, 'bytes': 0, 'mb': 0.0}
        
        nbytes = self.data_array.nbytes
        return {
            'n_records': self._n_records,
            'bytes': nbytes,
            'mb': nbytes / (1024 * 1024),
            'bytes_per_record': nbytes / self._n_records if self._n_records > 0 else 0,
        }
    
    def clear(self) -> None:
        """清空数据"""
        self.data_array = None
        self._n_records = 0
        logger.debug("DailyDataStore 已清空")
