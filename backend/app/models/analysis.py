"""
分析相关数据模型
"""
from typing import List
from pydantic import BaseModel, model_serializer
from .stock import StockInfo


class AnalysisResult(BaseModel):
    """分析结果"""
    period: int
    total_stocks: int
    stocks: List[StockInfo]
    start_date: str
    end_date: str
    all_dates: List[str] = []  # 所有分析的日期
    
    @model_serializer
    def ser_model(self) -> dict:
        """序列化时添加兼容字段"""
        # 基础字段
        result = {
            "period": f"{self.period}天",  # 旧前端期望字符串格式
            "total_stocks": self.total_stocks,
            "stocks": [stock.model_dump() if hasattr(stock, 'model_dump') else stock for stock in self.stocks],
            "start_date": self.start_date,
            "end_date": self.end_date,
        }
        
        # 添加 analysis_dates 以兼容旧前端
        result["analysis_dates"] = self.all_dates if self.all_dates else [self.start_date, self.end_date]
        
        return result


class AvailableDates(BaseModel):
    """可用日期"""
    dates: List[str]
    latest_date: str
