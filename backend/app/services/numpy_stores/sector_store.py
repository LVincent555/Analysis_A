"""
板块每日数据存储 - 基于 Numpy 结构化数组

与 DailyDataStore 类似，但针对板块数据
"""

import numpy as np
from datetime import date
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging

from .index_manager import IndexManager

logger = logging.getLogger(__name__)


# === 板块 dtype 定义 ===
SECTOR_DTYPE = np.dtype([
    # === 索引字段 ===
    ('sector_idx', np.int32),      # 4B - 板块索引
    ('date_idx', np.int32),        # 4B - 日期索引
    
    # === 核心字段 (float64 高精度) ===
    ('rank', np.int32),            # 4B - 排名
    ('total_score', np.float64),   # 8B - 总分
    ('price_change', np.float64),  # 8B - 涨跌幅
    ('close_price', np.float64),   # 8B - 收盘价
    ('open_price', np.float64),    # 8B - 开盘价
    ('high_price', np.float64),    # 8B - 最高价
    ('low_price', np.float64),     # 8B - 最低价
    
    # === 交易数据 ===
    ('volume', np.int64),          # 8B - 成交量
    ('turnover_rate', np.float32), # 4B - 换手率
    ('volatility', np.float32),    # 4B - 波动率
    ('volume_days', np.float32),   # 4B - 量比(天)
    ('avg_volume_ratio_50', np.float32),  # 4B - 50日均量比
    
    # === 技术指标 ===
    ('beta', np.float32),          # 4B
    ('correlation', np.float32),   # 4B
    ('rsi', np.float32),           # 4B
    ('adx', np.float32),           # 4B
    ('slowk', np.float32),         # 4B
    ('dif', np.float32),           # 4B
    ('dem', np.float32),           # 4B
    ('macd_signal', np.float32),   # 4B
    ('long_term', np.float32),     # 4B
    ('short_term', np.int16),      # 2B
    ('overbought', np.int16),      # 2B
    ('oversold', np.int16),        # 2B
])


def _safe_int(value: Any, default: int = -1) -> int:
    """安全转换为int"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为float"""
    if value is None:
        return default
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return default


class SectorIndexManager:
    """
    板块专用索引管理器
    
    与 IndexManager 类似，但管理 sector_id ↔ sector_idx 的映射
    """
    
    def __init__(self):
        # sector_id (数据库ID) ↔ sector_idx (数组索引)
        self.sector_id_to_idx: Dict[int, int] = {}
        self.idx_to_sector_id: List[int] = []
        
        # 日期索引 (与股票共用或独立)
        self.date_to_idx: Dict[date, int] = {}
        self.idx_to_date: List[date] = []
        
        # 复合索引
        self.composite_idx: Dict[tuple, int] = {}
        self.date_range_idx: Dict[int, tuple] = {}
        self.sector_rows_idx: Dict[int, List[int]] = {}
        
        self._initialized = False
    
    def build_sector_index(self, sector_ids: List[int]) -> None:
        """构建板块ID索引"""
        self.sector_id_to_idx.clear()
        self.idx_to_sector_id = list(sector_ids)
        
        for idx, sid in enumerate(sector_ids):
            self.sector_id_to_idx[sid] = idx
        
        logger.debug(f"构建板块索引: {len(sector_ids)} 个板块")
    
    def build_date_index(self, dates: List[date]) -> None:
        """构建日期索引"""
        self.date_to_idx.clear()
        self.idx_to_date = list(dates)
        
        for idx, d in enumerate(dates):
            self.date_to_idx[d] = idx
    
    def build_composite_index(
        self,
        sector_indices: np.ndarray,
        date_indices: np.ndarray
    ) -> None:
        """构建复合索引"""
        self.composite_idx.clear()
        self.date_range_idx.clear()
        self.sector_rows_idx.clear()
        
        n_records = len(sector_indices)
        current_date_idx = -1
        range_start = 0
        
        for row_idx in range(n_records):
            sector_idx = int(sector_indices[row_idx])
            date_idx = int(date_indices[row_idx])
            
            self.composite_idx[(sector_idx, date_idx)] = row_idx
            
            if sector_idx not in self.sector_rows_idx:
                self.sector_rows_idx[sector_idx] = []
            self.sector_rows_idx[sector_idx].append(row_idx)
            
            if date_idx != current_date_idx:
                if current_date_idx >= 0:
                    self.date_range_idx[current_date_idx] = (range_start, row_idx)
                current_date_idx = date_idx
                range_start = row_idx
        
        if current_date_idx >= 0:
            self.date_range_idx[current_date_idx] = (range_start, n_records)
        
        self._initialized = True
    
    def get_sector_idx(self, sector_id: int) -> Optional[int]:
        return self.sector_id_to_idx.get(sector_id)
    
    def get_sector_id(self, sector_idx: int) -> Optional[int]:
        if 0 <= sector_idx < len(self.idx_to_sector_id):
            return self.idx_to_sector_id[sector_idx]
        return None
    
    def get_date_idx(self, target_date: date) -> Optional[int]:
        return self.date_to_idx.get(target_date)
    
    def get_date(self, date_idx: int) -> Optional[date]:
        if 0 <= date_idx < len(self.idx_to_date):
            return self.idx_to_date[date_idx]
        return None
    
    def get_row_idx(self, sector_idx: int, date_idx: int) -> Optional[int]:
        return self.composite_idx.get((sector_idx, date_idx))
    
    def get_rows_by_date(self, date_idx: int) -> Optional[tuple]:
        return self.date_range_idx.get(date_idx)
    
    def get_rows_by_sector(self, sector_idx: int) -> List[int]:
        return self.sector_rows_idx.get(sector_idx, [])
    
    def get_all_dates(self) -> List[date]:
        return self.idx_to_date.copy()
    
    def get_latest_date(self) -> Optional[date]:
        if self.idx_to_date:
            return self.idx_to_date[0]
        return None
    
    def get_dates_range(self, n: int) -> List[date]:
        return self.idx_to_date[:n]
    
    def clear(self) -> None:
        self.sector_id_to_idx.clear()
        self.idx_to_sector_id.clear()
        self.date_to_idx.clear()
        self.idx_to_date.clear()
        self.composite_idx.clear()
        self.date_range_idx.clear()
        self.sector_rows_idx.clear()
        self._initialized = False


class SectorDataStore:
    """
    板块每日数据存储
    """
    
    def __init__(self):
        self.data_array: Optional[np.ndarray] = None
        self._n_records = 0
        self.index_mgr = SectorIndexManager()
    
    def build_from_tuples(
        self,
        rows: List[tuple],
        field_mapping: Dict[str, int]
    ) -> None:
        """
        从数据库查询结果构建数组
        
        Args:
            rows: 数据库查询结果
            field_mapping: 字段名 → tuple索引 的映射
        """
        n_records = len(rows)
        if n_records == 0:
            self.data_array = np.zeros(0, dtype=SECTOR_DTYPE)
            self._n_records = 0
            return
        
        # 先收集所有唯一的 sector_id 和 date
        sector_ids = set()
        dates = set()
        
        f = field_mapping
        for row in rows:
            sector_ids.add(row[f['sector_id']])
            dates.add(row[f['date']])
        
        # 构建索引
        self.index_mgr.build_sector_index(sorted(sector_ids))
        self.index_mgr.build_date_index(sorted(dates, reverse=True))
        
        # 创建数组
        self.data_array = np.zeros(n_records, dtype=SECTOR_DTYPE)
        
        for i, row in enumerate(rows):
            sector_id = row[f['sector_id']]
            row_date = row[f['date']]
            
            sector_idx = self.index_mgr.get_sector_idx(sector_id)
            date_idx = self.index_mgr.get_date_idx(row_date)
            
            if sector_idx is None or date_idx is None:
                continue
            
            self.data_array[i]['sector_idx'] = sector_idx
            self.data_array[i]['date_idx'] = date_idx
            self.data_array[i]['rank'] = _safe_int(row[f.get('rank', -1)], -1)
            self.data_array[i]['total_score'] = _safe_float(row[f.get('total_score', -1)])
            self.data_array[i]['price_change'] = _safe_float(row[f.get('price_change', -1)])
            self.data_array[i]['close_price'] = _safe_float(row[f.get('close_price', -1)])
            self.data_array[i]['open_price'] = _safe_float(row[f.get('open_price', -1)])
            self.data_array[i]['high_price'] = _safe_float(row[f.get('high_price', -1)])
            self.data_array[i]['low_price'] = _safe_float(row[f.get('low_price', -1)])
            self.data_array[i]['volume'] = _safe_int(row[f.get('volume', -1)], 0)
            self.data_array[i]['turnover_rate'] = _safe_float(row[f.get('turnover_rate', -1)])
            self.data_array[i]['volatility'] = _safe_float(row[f.get('volatility', -1)])
            self.data_array[i]['volume_days'] = _safe_float(row[f.get('volume_days', -1)])
            self.data_array[i]['avg_volume_ratio_50'] = _safe_float(row[f.get('avg_volume_ratio_50', -1)])
            
            # 技术指标
            if 'beta' in f:
                self.data_array[i]['beta'] = _safe_float(row[f['beta']])
            if 'correlation' in f:
                self.data_array[i]['correlation'] = _safe_float(row[f['correlation']])
            if 'rsi' in f:
                self.data_array[i]['rsi'] = _safe_float(row[f['rsi']])
            if 'adx' in f:
                self.data_array[i]['adx'] = _safe_float(row[f['adx']])
            if 'slowk' in f:
                self.data_array[i]['slowk'] = _safe_float(row[f['slowk']])
            if 'dif' in f:
                self.data_array[i]['dif'] = _safe_float(row[f['dif']])
            if 'dem' in f:
                self.data_array[i]['dem'] = _safe_float(row[f['dem']])
            if 'macd_signal' in f:
                self.data_array[i]['macd_signal'] = _safe_float(row[f['macd_signal']])
        
        # 构建复合索引
        self.index_mgr.build_composite_index(
            self.data_array['sector_idx'],
            self.data_array['date_idx']
        )
        
        self._n_records = n_records
        logger.info(f"✅ SectorDataStore 构建完成: {n_records} 条记录")
    
    # ========== 查询接口 ==========
    
    def get_row(self, row_idx: int) -> Optional[np.void]:
        """获取指定行的数据"""
        if self.data_array is None or row_idx < 0 or row_idx >= self._n_records:
            return None
        return self.data_array[row_idx]
    
    def get_rows_slice(self, start: int, end: int) -> np.ndarray:
        """获取指定范围的数据"""
        if self.data_array is None:
            return np.zeros(0, dtype=SECTOR_DTYPE)
        return self.data_array[start:end]
    
    def get_top_n_by_rank(self, start: int, end: int, n: int) -> np.ndarray:
        """从指定范围获取排名前N的数据"""
        if self.data_array is None:
            return np.zeros(0, dtype=SECTOR_DTYPE)
        
        slice_data = self.data_array[start:end]
        sorted_indices = np.argsort(slice_data['rank'])
        return slice_data[sorted_indices[:n]]
    
    def row_to_dict(self, row: np.void) -> Dict:
        """将单行数据转换为字典"""
        sector_id = self.index_mgr.get_sector_id(int(row['sector_idx']))
        row_date = self.index_mgr.get_date(int(row['date_idx']))
        
        return {
            'sector_id': sector_id,
            'date': row_date.strftime('%Y%m%d') if row_date else None,
            'rank': int(row['rank']) if row['rank'] >= 0 else None,
            'total_score': float(row['total_score']),
            'price_change': float(row['price_change']),
            'close_price': float(row['close_price']),
            'open_price': float(row['open_price']),
            'high_price': float(row['high_price']),
            'low_price': float(row['low_price']),
            'volume': int(row['volume']),
            'turnover_rate': float(row['turnover_rate']),
            'volatility': float(row['volatility']),
            'volume_days': float(row['volume_days']),  # 🔧 补充缺失字段
            'avg_volume_ratio_50': float(row['avg_volume_ratio_50']),
            'rsi': float(row['rsi']),
            'adx': float(row['adx']),
        }
    
    def rows_to_dicts(self, rows: np.ndarray) -> List[Dict]:
        """将多行数据转换为字典列表"""
        return [self.row_to_dict(row) for row in rows]
    
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
        }
    
    def clear(self) -> None:
        """清空数据"""
        self.data_array = None
        self._n_records = 0
        self.index_mgr.clear()
        logger.debug("SectorDataStore 已清空")
