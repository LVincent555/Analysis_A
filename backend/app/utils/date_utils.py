"""
日期相关工具函数
"""
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import re


def format_date(date_str: str) -> str:
    """格式化日期字符串，从YYYYMMDD转换为YYYY-MM-DD"""
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str


def parse_date_from_filename(filename: str) -> str:
    """从文件名中提取日期"""
    match = re.search(r'(\d{8})', filename)
    if match:
        return match.group(1)
    return ""


def get_sorted_files(directory: Path, pattern: str = "*_data_sma_feature_color.xlsx") -> List[Tuple[str, Path]]:
    """
    获取目录下的所有数据文件并按日期排序
    
    Args:
        directory: 数据目录路径
        pattern: 文件名模式
    
    Returns:
        List[Tuple[str, Path]]: (日期, 文件路径) 的列表，按日期排序
    """
    files_with_dates = []
    
    for file_path in directory.glob(pattern):
        date_str = parse_date_from_filename(file_path.name)
        if date_str:
            files_with_dates.append((date_str, file_path))
    
    # 按日期排序
    files_with_dates.sort(key=lambda x: x[0])
    
    return files_with_dates
