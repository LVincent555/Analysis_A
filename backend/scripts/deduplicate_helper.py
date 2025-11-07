"""
Excel数据去重辅助工具
专门处理：同一股票代码出现多次，且评分异常的情况

策略：
1. 检测重复的股票代码
2. 比较total_score（综合评分）
3. 保留评分更合理的那条（基于排名上下文）
4. 严格条件：只在明确异常时才去重
"""
import pandas as pd
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


class DataDeduplicator:
    """数据去重器"""
    
    def __init__(self):
        self.removed_count = 0
        self.removed_details = []
    
    def deduplicate_stock_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
        """
        去重股票数据
        
        策略：
        1. 检测重复的股票代码
        2. 对于重复记录，计算每条的"合理性分数"
        3. 保留最合理的那条，删除其他
        
        Args:
            df: 原始DataFrame
        
        Returns:
            (去重后的DataFrame, 统计信息)
        """
        self.removed_count = 0
        self.removed_details = []
        
        # 0. 检查必需的列是否存在（支持多种列名）
        score_col = None
        for col_name in ['总分', '综合评分', 'score']:
            if col_name in df.columns:
                score_col = col_name
                break
        
        if score_col is None:
            logger.warning(f"⚠️  Excel缺少评分列（总分/综合评分/score），跳过智能去重")
            logger.warning(f"   可用列: {', '.join(df.columns.tolist()[:10])}")
            return df, {
                'has_duplicates': False,
                'removed_count': 0,
                'removed_details': [],
                'duplicate_codes': [],
                'skip_reason': 'missing_score_column'
            }
        
        # 保存列名供后续使用
        self.score_column = score_col
        logger.info(f"使用评分列: {score_col}")
        
        # 1. 标准化股票代码列
        df['代码_normalized'] = df['代码'].astype(str).str.strip()
        
        # 2. 检测重复
        duplicates = df[df.duplicated(subset=['代码_normalized'], keep=False)]
        
        if duplicates.empty:
            # 清理临时列
            df = df.drop(columns=['代码_normalized'])
            return df, {
                'has_duplicates': False,
                'removed_count': 0,
                'removed_details': [],
                'duplicate_codes': []
            }
        
        # 3. 处理所有重复（新策略：一次性处理完）
        dup_codes = duplicates['代码_normalized'].unique()
        logger.warning(f"⚠️  检测到 {len(dup_codes)} 个重复的股票代码: {', '.join(dup_codes)}")
        
        # 显示重复详情
        for code in dup_codes:
            dup_rows = df[df['代码_normalized'] == code]
            rows_info = ', '.join([str(idx + 2) for idx in dup_rows.index])
            logger.warning(f"   股票 {code} 出现了 {len(dup_rows)} 次，在行: [{rows_info}]")
        
        # 一次性处理所有重复
        indices_to_remove = []
        for code in dup_codes:
            dup_rows = df[df['代码_normalized'] == code]
            
            if len(dup_rows) > 1:
                # 保留最接近全局均值的，删除其他
                removed_idx = self._select_rows_to_remove(df, dup_rows, code)
                indices_to_remove.extend(removed_idx)
        
        # 4. 删除异常行
        if indices_to_remove:
            df_cleaned = df.drop(indices_to_remove).reset_index(drop=True)
            logger.warning(f"✅ 智能去重完成：删除 {len(indices_to_remove)} 条异常记录")
        else:
            df_cleaned = df
            logger.warning(f"⚠️  去重条件不满足：保留所有重复记录（将在后续严格检查中报错）")
        
        # 5. 清理临时列
        if '代码_normalized' in df_cleaned.columns:
            df_cleaned = df_cleaned.drop(columns=['代码_normalized'])
        
        return df_cleaned, {
            'has_duplicates': True,
            'duplicate_codes': list(dup_codes),
            'removed_count': self.removed_count,
            'removed_details': self.removed_details
        }
    
    def _select_rows_to_remove(
        self, 
        df: pd.DataFrame, 
        dup_rows: pd.DataFrame, 
        code: str
    ) -> List[int]:
        """
        选择要删除的行（基于全局离群值检测）
        
        策略：
        1. 计算全局分数的均值和标准差
        2. 对于重复的记录，保留最接近全局均值的那条
        3. 删除其他明显偏离的
        
        Args:
            df: 完整DataFrame
            dup_rows: 重复的行
            code: 股票代码
        
        Returns:
            要删除的索引列表
        """
        indices_to_remove = []
        score_col = self.score_column  # 使用之前检测到的列名
        
        # === 计算全局统计 ===
        global_scores = df[score_col].dropna()
        if len(global_scores) == 0:
            return indices_to_remove
        
        global_mean = global_scores.mean()
        global_std = global_scores.std()
        
        # === 获取重复行的信息 ===
        dup_info = []
        for idx, row in dup_rows.iterrows():
            rank = idx + 1  # Excel行号（1-based）
            total_score = row.get(score_col, None)
            name = row.get('名称', 'N/A')
            
            # 计算与全局均值的距离
            if pd.notna(total_score):
                distance_from_mean = abs(total_score - global_mean)
                # Z-score：标准化偏离度
                z_score = distance_from_mean / global_std if global_std > 0 else 0
            else:
                distance_from_mean = float('inf')
                z_score = float('inf')
            
            dup_info.append({
                'index': idx,
                'rank': rank,
                'total_score': total_score,
                'name': name,
                'distance_from_mean': distance_from_mean,
                'z_score': z_score
            })
        
        # === 新策略：保留最接近全局均值的，删除其他 ===
        # 1. 检查分数是否存在
        scores = [d['total_score'] for d in dup_info if pd.notna(d['total_score'])]
        if len(scores) < 2:
            # 无法比较，保留所有（交给数据库报错）
            logger.warning(f"  股票 {code} 重复但缺少分数数据，保留所有行（将触发数据库ERROR）")
            return indices_to_remove
        
        # 2. 找出最接近全局均值的记录（保留它）
        closest_to_mean = min(dup_info, key=lambda x: x['distance_from_mean'])
        
        # 3. 删除其他所有记录
        for info in dup_info:
            if info['index'] != closest_to_mean['index']:
                indices_to_remove.append(info['index'])
                
                self.removed_count += 1
                detail = {
                    'code': code,
                    'name': info['name'],
                    'rank': info['rank'],
                    'total_score': info['total_score'],
                    'global_mean': global_mean,
                    'distance_from_mean': info['distance_from_mean'],
                    'z_score': info['z_score'],
                    'reason': f'重复记录中偏离全局均值较远（保留最接近均值的）'
                }
                self.removed_details.append(detail)
                
                logger.warning(
                    f"  [去重] 股票 {code}({info['name']}) "
                    f"行{info['rank']} "
                    f"分数={info['total_score']:.2f} "
                    f"全局均值={global_mean:.2f} "
                    f"距离={info['distance_from_mean']:.2f} "
                    f"Z-score={info['z_score']:.2f} → 删除（保留行{closest_to_mean['rank']}）"
                )
        
        return indices_to_remove


def print_dedup_summary(dedup_stats: dict):
    """打印去重摘要"""
    if not dedup_stats.get('has_duplicates'):
        return
    
    removed_count = dedup_stats.get('removed_count', 0)
    
    if removed_count == 0:
        logger.warning("📊 数据去重摘要")
        logger.warning("  未删除任何记录（去重条件不满足）")
        return
    
    logger.warning("")
    logger.warning("=" * 70)
    logger.warning("📊 数据去重摘要（基于全局离群值检测）")
    logger.warning("=" * 70)
    logger.warning(f"去重条数: {removed_count}")
    
    for detail in dedup_stats.get('removed_details', []):
        logger.warning(
            f"  • 股票 {detail['code']}({detail['name']}) "
            f"行{detail['rank']} 原因: {detail['reason']}"
        )
        
        # 兼容新旧格式
        if 'global_mean' in detail:
            # 新格式：全局均值
            logger.warning(
                f"    分数={detail['total_score']:.2f}, "
                f"全局均值={detail['global_mean']:.2f}, "
                f"距离={detail['distance_from_mean']:.2f}, "
                f"Z-score={detail['z_score']:.2f}"
            )
        else:
            # 旧格式：周围均值（向后兼容）
            logger.warning(
                f"    分数={detail['total_score']:.2f}, "
                f"周围均值={detail.get('context_mean', 'N/A'):.2f}, "
                f"偏离={detail.get('deviation', 'N/A'):.2f}σ"
            )
    
    logger.warning("=" * 70)
    logger.warning("")
