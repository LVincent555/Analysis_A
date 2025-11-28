"""
使用Numpy优化的数据缓存
将数值型数据存储为numpy数组，大幅减少内存占用
"""
import numpy as np
from typing import Dict, List, Optional
from datetime import date
import logging

logger = logging.getLogger(__name__)


class NumpyStockCache:
    """使用Numpy数组存储股票每日数据"""
    
    def __init__(self):
        # 股票代码映射 {stock_code: index}
        self.stock_code_to_idx: Dict[str, int] = {}
        self.idx_to_stock_code: Dict[int, str] = {}
        
        # 日期映射 {date: index}
        self.date_to_idx: Dict[date, int] = {}
        self.idx_to_date: Dict[int, date] = {}
        
        # Numpy数组存储（行=股票×日期，列=指标）
        # 使用结构化数组，更节省内存
        self.data_array: Optional[np.ndarray] = None
        
        # 索引数组：用于快速查找 [stock_idx, date_idx] -> data_row_idx
        self.index_map: Dict[tuple, int] = {}
        
        self._initialized = False
    
    def build_from_data(self, daily_data_list: List):
        """
        从DailyStockData列表构建numpy数组
        
        Args:
            daily_data_list: DailyStockData对象列表
        """
        if not daily_data_list:
            logger.warning("没有数据可加载到Numpy缓存")
            return
        
        logger.info(f"🔄 构建Numpy缓存，共 {len(daily_data_list)} 条数据...")
        
        # 1. 构建股票代码和日期的映射
        stock_codes = sorted(set(d.stock_code for d in daily_data_list))
        dates = sorted(set(d.date for d in daily_data_list))
        
        for idx, code in enumerate(stock_codes):
            self.stock_code_to_idx[code] = idx
            self.idx_to_stock_code[idx] = code
        
        for idx, dt in enumerate(dates):
            self.date_to_idx[dt] = idx
            self.idx_to_date[idx] = dt
        
        logger.info(f"  ✅ {len(stock_codes)} 只股票, {len(dates)} 个交易日")
        
        # 2. 定义结构化数组的dtype（只存储数值型字段）
        dtype = np.dtype([
            ('stock_idx', np.int32),      # 股票索引
            ('date_idx', np.int32),       # 日期索引
            ('rank', np.int32),           # 排名
            ('price_change', np.float32), # 涨跌幅
            ('turnover_rate', np.float32),# 换手率
            ('volume', np.int64),         # 成交量
            ('volatility', np.float32),   # 波动率
            ('close_price', np.float32),  # 收盘价
            ('open_price', np.float32),   # 开盘价
            ('high_price', np.float32),   # 最高价
            ('low_price', np.float32),    # 最低价
            ('total_score', np.float32),  # 总分
            ('market_cap', np.float32),   # 总市值(亿)
        ])
        
        # 3. 创建numpy数组
        n_rows = len(daily_data_list)
        self.data_array = np.zeros(n_rows, dtype=dtype)
        
        # 4. 填充数据
        for i, data in enumerate(daily_data_list):
            stock_idx = self.stock_code_to_idx[data.stock_code]
            date_idx = self.date_to_idx[data.date]
            
            self.data_array[i] = (
                stock_idx,
                date_idx,
                data.rank if data.rank else 0,
                float(data.price_change) if data.price_change else 0.0,
                float(data.turnover_rate_percent) if data.turnover_rate_percent else 0.0,
                data.volume if data.volume else 0,
                float(data.volatility) if data.volatility else 0.0,
                float(data.close_price) if data.close_price else 0.0,
                float(data.open_price) if data.open_price else 0.0,
                float(data.high_price) if data.high_price else 0.0,
                float(data.low_price) if data.low_price else 0.0,
                float(data.total_score) if data.total_score else 0.0,
                float(data.market_cap_billions) if data.market_cap_billions else 0.0,
            )
            
            # 建立索引
            self.index_map[(stock_idx, date_idx)] = i
        
        self._initialized = True
        
        # 计算内存占用
        memory_mb = self.data_array.nbytes / 1024 / 1024
        logger.info(f"  ✅ Numpy数组构建完成，内存占用: {memory_mb:.2f} MB")
    
    def get_data(self, stock_code: str, target_date: date) -> Optional[Dict]:
        """
        获取指定股票在指定日期的数据
        
        Args:
            stock_code: 股票代码
            target_date: 日期
            
        Returns:
            数据字典，如果不存在返回None
        """
        if not self._initialized:
            return None
        
        stock_idx = self.stock_code_to_idx.get(stock_code)
        date_idx = self.date_to_idx.get(target_date)
        
        if stock_idx is None or date_idx is None:
            return None
        
        row_idx = self.index_map.get((stock_idx, date_idx))
        if row_idx is None:
            return None
        
        row = self.data_array[row_idx]
        
        return {
            'rank': int(row['rank']),
            'price_change': float(row['price_change']),
            'turnover_rate': float(row['turnover_rate']),
            'volume': int(row['volume']),
            'volatility': float(row['volatility']),
            'close_price': float(row['close_price']),
            'open_price': float(row['open_price']),
            'high_price': float(row['high_price']),
            'low_price': float(row['low_price']),
            'total_score': float(row['total_score']),
            'market_cap': float(row['market_cap']),
        }
    
    def get_stock_history(self, stock_code: str, days: int = 7) -> List[Dict]:
        """
        获取指定股票的历史数据
        
        Args:
            stock_code: 股票代码
            days: 返回最近N天
            
        Returns:
            数据列表（按日期降序）
        """
        if not self._initialized:
            return []
        
        stock_idx = self.stock_code_to_idx.get(stock_code)
        if stock_idx is None:
            return []
        
        # 找到该股票的所有数据
        mask = self.data_array['stock_idx'] == stock_idx
        stock_data = self.data_array[mask]
        
        # 按日期降序排序
        stock_data = stock_data[np.argsort(stock_data['date_idx'])[::-1]]
        
        # 只取最近days天
        stock_data = stock_data[:days]
        
        # 转换为字典列表
        result = []
        for row in stock_data:
            date_idx = int(row['date_idx'])
            result.append({
                'date': self.idx_to_date[date_idx],
                'rank': int(row['rank']),
                'price_change': float(row['price_change']),
                'turnover_rate': float(row['turnover_rate']),
                'volume': int(row['volume']),
                'volatility': float(row['volatility']),
                'close_price': float(row['close_price']),
                'open_price': float(row['open_price']),
                'high_price': float(row['high_price']),
                'low_price': float(row['low_price']),
                'total_score': float(row['total_score']),
                'market_cap': float(row['market_cap']),
            })
        
        return result
    
    def get_top_n_by_rank(self, target_date: date, n: int = 100) -> List[str]:
        """
        获取指定日期排名前N的股票代码
        
        Args:
            target_date: 日期
            n: 返回前N名
            
        Returns:
            股票代码列表
        """
        if not self._initialized:
            return []
        
        date_idx = self.date_to_idx.get(target_date)
        if date_idx is None:
            return []
        
        # 找到该日期的所有数据
        mask = self.data_array['date_idx'] == date_idx
        date_data = self.data_array[mask]
        
        # 按rank排序
        sorted_data = date_data[np.argsort(date_data['rank'])]
        
        # 取前N个
        top_n = sorted_data[:n]
        
        # 转换为股票代码
        return [self.idx_to_stock_code[int(row['stock_idx'])] for row in top_n]
    
    def get_memory_usage(self) -> Dict:
        """获取内存使用情况"""
        if not self._initialized or self.data_array is None:
            return {'total_mb': 0, 'initialized': False}
        
        array_mb = self.data_array.nbytes / 1024 / 1024
        
        # 估算字典开销
        dict_mb = (
            len(self.stock_code_to_idx) * 100 +  # 每个映射约100字节
            len(self.date_to_idx) * 100 +
            len(self.index_map) * 50
        ) / 1024 / 1024
        
        return {
            'array_mb': round(array_mb, 2),
            'dict_mb': round(dict_mb, 2),
            'total_mb': round(array_mb + dict_mb, 2),
            'n_stocks': len(self.stock_code_to_idx),
            'n_dates': len(self.date_to_idx),
            'n_records': len(self.data_array),
            'initialized': True
        }
    
    def get_market_volatility_summary(self, days: int = 3) -> Dict:
        """
        获取市场波动率汇总数据（最近N天）
        
        Args:
            days: 返回最近N天的数据
            
        Returns:
            包含每天平均波动率的字典
        """
        if not self._initialized or self.data_array is None:
            return {'error': 'Cache not initialized'}
        
        # 获取最近N天的日期索引
        sorted_dates = sorted(self.date_to_idx.items(), key=lambda x: x[0], reverse=True)
        recent_dates = sorted_dates[:days]
        
        result = {
            'days': [],
            'trend': 'flat',
            'stock_count': len(self.stock_code_to_idx)
        }
        
        volatility_values = []
        
        for dt, date_idx in recent_dates:
            # 找到该日期的所有数据
            mask = self.data_array['date_idx'] == date_idx
            date_data = self.data_array[mask]
            
            # 过滤掉波动率为0或异常值的数据
            valid_volatility = date_data['volatility']
            valid_volatility = valid_volatility[(valid_volatility > 0) & (valid_volatility < 100)]
            
            if len(valid_volatility) > 0:
                avg_volatility = float(np.mean(valid_volatility))
                volatility_values.append(avg_volatility)
                result['days'].append({
                    'date': dt.strftime('%Y%m%d'),
                    'avg_volatility': round(avg_volatility, 4),
                    'stock_count': len(valid_volatility)
                })
        
        # 计算趋势
        if len(volatility_values) >= 2:
            if volatility_values[0] > volatility_values[1] * 1.05:
                result['trend'] = 'up'
            elif volatility_values[0] < volatility_values[1] * 0.95:
                result['trend'] = 'down'
            else:
                result['trend'] = 'flat'
        
        # 添加当前值（最新一天）
        if volatility_values:
            result['current'] = round(volatility_values[0], 4)
        
        return result


# 创建全局实例
numpy_stock_cache = NumpyStockCache()
