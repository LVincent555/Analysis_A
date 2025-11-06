"""
数据加载服务
负责从Excel文件读取数据
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DataLoader:
    """数据加载器"""
    
    @staticmethod
    def load_stock_data(
        file_path: Path,
        filter_stocks: bool = True,
        include_details: bool = False,
        max_count: int = 100
    ) -> List[Dict]:
        """
        加载股票数据
        
        Args:
            file_path: Excel文件路径
            filter_stocks: 是否过滤特定板块股票（创业板、科创板等）
            include_details: 是否包含详细数据
            max_count: 最多加载的股票数量
        
        Returns:
            股票数据列表
        """
        df = pd.read_excel(file_path)
        
        # 找到关键列
        code_column = DataLoader._find_column(df, ['代码', 'code'])
        name_column = DataLoader._find_column(df, ['名称', 'name'])
        industry_column = DataLoader._find_column(df, ['行业', 'industry'])
        
        if code_column is None:
            code_column = df.columns[1]
        if name_column is None:
            name_column = df.columns[2]
        
        # 获取股票数据
        stocks_data = []
        count_limit = len(df) if max_count is None else min(max_count, len(df))
        for idx in range(count_limit):
            stock_code = str(df[code_column].iloc[idx]).strip()
            stock_name = str(df[name_column].iloc[idx]).strip() if name_column else stock_code
            stock_industry = str(df[industry_column].iloc[idx]).strip() if industry_column and pd.notna(df[industry_column].iloc[idx]) else "未知"
            
            # 根据filter_stocks参数过滤
            if filter_stocks and DataLoader._should_filter_stock(stock_code):
                continue
            
            stock_item = {
                'code': stock_code,
                'name': stock_name,
                'industry': stock_industry,
                'rank': idx + 1
            }
            
            # 如果需要详细信息，添加更多字段
            if include_details:
                stock_item.update(DataLoader._extract_details(df, idx))
            
            stocks_data.append(stock_item)
        
        return stocks_data
    
    @staticmethod
    def load_top_n_stocks(file_path: Path, top_n: int = 1000) -> List[Dict]:
        """
        专门用于读取前N名的所有股票数据（不过滤，用于行业统计）
        
        Args:
            file_path: Excel文件路径
            top_n: 读取前多少名
        
        Returns:
            股票数据列表
        """
        df = pd.read_excel(file_path)
        
        # 找到关键列
        code_column = DataLoader._find_column(df, ['代码', 'code'])
        industry_column = DataLoader._find_column(df, ['行业', 'industry'])
        
        if code_column is None:
            code_column = df.columns[1]
        
        stocks_data = []
        for idx in range(min(top_n, len(df))):
            stock_code = str(df[code_column].iloc[idx]).strip()
            stock_industry = str(df[industry_column].iloc[idx]).strip() if industry_column and pd.notna(df[industry_column].iloc[idx]) else "未知"
            
            stocks_data.append({
                'code': stock_code,
                'industry': stock_industry,
                'rank': idx + 1
            })
        
        return stocks_data
    
    @staticmethod
    def _find_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
        """查找包含关键字的列名"""
        col_str_lower = {col: str(col).lower() for col in df.columns}
        
        # 首先尝试精确匹配
        for col, col_lower in col_str_lower.items():
            for keyword in keywords:
                if col_lower == keyword.lower():
                    return col
        
        # 如果没有精确匹配，尝试包含匹配（但排除unnamed列）
        for col, col_lower in col_str_lower.items():
            # 跳过unnamed列
            if 'unnamed' in col_lower:
                continue
            for keyword in keywords:
                if keyword.lower() in col_lower:
                    return col
        
        return None
    
    @staticmethod
    def _should_filter_stock(stock_code: str) -> bool:
        """判断是否应该过滤该股票"""
        return (stock_code.startswith('300') or 
                stock_code.startswith('301') or 
                stock_code.startswith('688') or 
                stock_code.startswith('920'))
    
    @staticmethod
    def _extract_details(df: pd.DataFrame, idx: int) -> Dict:
        """提取股票详细数据"""
        row = df.iloc[idx]
        details = {}
        
        detail_fields = {
            'price_change': '涨跌幅',
            'turnover_rate': '换手率%',
            'volume_days': '放量天数',
            'avg_volume_ratio_50': '平均量比_50天',
            'volatility': '波动率'
        }
        
        for field, column in detail_fields.items():
            if column in df.columns and pd.notna(row[column]):
                details[field] = float(row[column])
            else:
                details[field] = 0.0
        
        return details
