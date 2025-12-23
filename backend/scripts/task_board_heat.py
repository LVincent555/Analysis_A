#!/usr/bin/env python3
"""
板块热度计算 ETL 脚本
============================
从 ext_board_daily_snap + daily_stock_data 计算板块热度，写入 ext_board_heat_daily

核心算法:
1. 计算分摊权重 share_ij（热度守恒）
2. 聚合 B1/B2/C1/C2 指标
3. 计算综合热度 heat_raw → heat_pct

使用方法:
    python task_board_heat.py                     # 计算最新交集日期
    python task_board_heat.py --date 2025-12-04   # 计算指定日期
    python task_board_heat.py --all               # 计算所有可用日期
    python task_board_heat.py --force             # 强制重算（覆盖已有数据）

作者: AI Assistant
日期: 2025-12-11
版本: v1.0.0
"""

import argparse
import logging
import os
import sys
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from tqdm import tqdm

# ============================================================
# 配置
# ============================================================
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 数据库连接
DB_HOST = os.getenv("DB_HOST", "192.168.182.128")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "db_20251106_analysis_a")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# ============================================================
# 配置加载器
# ============================================================
class ConfigLoader:
    """从 system_configs 表加载配置"""
    
    def __init__(self, engine):
        self.engine = engine
        self._cache: Dict[str, Any] = {}
        self._load_board_configs()
        self._load_blacklist()
    
    def _load_board_configs(self):
        """加载 board 类别的配置"""
        sql = "SELECT config_key, config_value, config_type FROM system_configs WHERE category = 'board'"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            for row in result:
                key, value, vtype = row[0], row[1], row[2]
                if vtype == 'float':
                    self._cache[key] = float(value)
                elif vtype == 'int':
                    self._cache[key] = int(value)
                elif vtype == 'bool':
                    self._cache[key] = value.lower() in ('true', '1', 'yes')
                else:
                    self._cache[key] = value
        logger.info(f"已加载 {len(self._cache)} 个板块配置项")

    def _load_blacklist(self):
        """加载黑名单/灰名单配置"""
        self.blacklist = {} # keyword -> level (BLACK/GREY)
        sql = "SELECT keyword, level FROM board_blacklist WHERE is_active = true"
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                for row in result:
                    self.blacklist[row[0]] = row[1]
            logger.info(f"已加载 {len(self.blacklist)} 条黑/灰名单规则")
        except Exception as e:
            logger.warning(f"加载黑名单失败 (可能是表未创建): {e}")
            # 默认硬编码一些
            self.blacklist = {
                '融资融券': 'BLACK', '转融通': 'BLACK', '深股通': 'BLACK', '沪股通': 'BLACK',
                '大盘股': 'GREY', '中盘股': 'GREY', '创业板综': 'GREY', '上证180': 'GREY'
            }
    
    def get_blacklist_level(self, board_name: str) -> Optional[str]:
        """检查板块是否命中黑/灰名单，返回级别"""
        for keyword, level in self.blacklist.items():
            if keyword in board_name:
                return level
        return None
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)
    
    # 快捷属性
    @property
    def w_industry(self) -> float:
        return self.get('board_w_industry', 1.0)
    
    @property
    def w_concept(self) -> float:
        return self.get('board_w_concept', 0.7)
    
    @property
    def w_region(self) -> float:
        return self.get('board_w_region', 0.5)
    
    @property
    def heat_alpha(self) -> float:
        return self.get('board_heat_alpha', 0.4)
    
    @property
    def heat_beta(self) -> float:
        return self.get('board_heat_beta', 0.2)
    
    @property
    def heat_gamma(self) -> float:
        return self.get('board_heat_gamma', 0.3)
    
    @property
    def heat_delta(self) -> float:
        return self.get('board_heat_delta', 0.1)


# ============================================================
# 板块热度计算器
# ============================================================
class BoardHeatCalculator:
    """板块热度计算器"""
    
    def __init__(self, engine, config: ConfigLoader, allow_latest_snap_fallback: bool = False):
        self.engine = engine
        self.config = config
        self.allow_latest_snap_fallback = allow_latest_snap_fallback
        self.Session = sessionmaker(bind=engine)
    
    def get_available_dates(self) -> List[date]:
        """获取 daily_stock_data 中有数据的日期（不再要求与 snap 交集）"""
        sql = """
        SELECT DISTINCT date FROM daily_stock_data 
        WHERE rank IS NOT NULL 
        ORDER BY date DESC
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [row[0] for row in result]
    
    def get_snap_dates(self) -> List[date]:
        """获取所有快照日期（稀疏）"""
        sql = "SELECT DISTINCT date FROM ext_board_daily_snap ORDER BY date DESC"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            return [row[0] for row in result]
    
    def find_nearest_snap_date(self, target_date: date) -> Optional[date]:
        """
        【寻址】找到离 target_date 最近的快照日期
        逻辑：找一个 <= 目标日期的最大日期
        """
        sql = """
        SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"d": target_date})
            row = result.fetchone()
            nearest = row[0] if row and row[0] else None

            if nearest:
                return nearest

            # 临时兜底：如果目标日期之前没有任何快照，则直接借用最新快照
            if not self.allow_latest_snap_fallback:
                return None

            latest_row = conn.execute(text("SELECT MAX(date) FROM ext_board_daily_snap")).fetchone()
            latest = latest_row[0] if latest_row and latest_row[0] else None
            if latest:
                logger.warning(f"⚠️ {target_date} 之前无任何板块关系快照，临时借用最新快照 {latest} (可能存在未来关系偏差)")
            return latest
    
    def get_latest_date(self) -> Optional[date]:
        """获取最新的可计算日期"""
        dates = self.get_available_dates()
        return dates[0] if dates else None
    
    def check_existing(self, trade_date: date) -> bool:
        """检查指定日期是否已有计算结果"""
        sql = "SELECT COUNT(*) FROM ext_board_heat_daily WHERE trade_date = :d"
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"d": trade_date})
            return result.scalar() > 0
    
    def delete_existing(self, trade_date: date):
        """删除指定日期的已有结果"""
        sql = "DELETE FROM ext_board_heat_daily WHERE trade_date = :d"
        with self.engine.connect() as conn:
            conn.execute(text(sql), {"d": trade_date})
            conn.commit()
        logger.info(f"已删除 {trade_date} 的旧数据")
    
    def calculate(self, trade_date: date, force: bool = False) -> int:
        """
        计算指定日期的板块热度
        
        【稀疏快照】使用"寻址"逻辑：
        - 个股数据用 trade_date（实时）
        - 板块关系用最近的快照日期（稀疏）
        
        Returns:
            写入的记录数
        """
        try:
            logger.info(f"开始计算 {trade_date} 的板块热度...")
            sys.stdout.flush()
            
            # 检查是否已存在
            if self.check_existing(trade_date) and not force:
                logger.warning(f"{trade_date} 已有计算结果，跳过（使用 --force 强制重算）")
                return 0
            
            if force and self.check_existing(trade_date):
                self.delete_existing(trade_date)
            
            # 【寻址】找到最近的快照日期
            snap_date = self.find_nearest_snap_date(trade_date)
            if not snap_date:
                logger.error(f"截止到 {trade_date} 没有任何板块关系数据，无法计算！")
                return 0
            
            if snap_date != trade_date:
                logger.info(f"  📅 计算日期: {trade_date} | 🔗 借用关系: {snap_date} (复用历史快照)")
            
            # Step 1: 加载原始数据（混合日期）
            df_snap, df_stock, df_board = self._load_data(trade_date, snap_date)
            if df_snap.empty:
                logger.warning(f"{snap_date} 无快照数据")
                return 0
            if df_stock.empty:
                logger.warning(f"{trade_date} 无个股数据")
                return 0
            
            logger.info(f"  快照数据: {len(df_snap)} 条 ({snap_date}), 个股数据: {len(df_stock)} 条 ({trade_date}), 板块: {len(df_board)} 个")
            sys.stdout.flush()
            
            # Step 2: 计算分摊权重 share_ij (含黑名单/灰名单逻辑)
            df_share = self._calc_share_weight(df_snap, df_board)
            logger.info(f"  分摊权重计算完成: {len(df_share)} 条")
            
            # Step 3: 合并个股数据
            df_merged = df_share.merge(
                df_stock[['stock_code', 'rank', 'total_score', 'turnover_rate_percent', 'volume_days']], 
                on='stock_code', 
                how='inner'
            )
            logger.info(f"  合并后: {len(df_merged)} 条（交集）")
            
            if df_merged.empty:
                logger.warning(f"{trade_date} 快照与个股数据无交集")
                return 0
                
            # Step 3.5: 计算 Contribution Score 并更新回 ext_board_daily_snap
            self._update_contribution_score(df_merged, snap_date)
            
            # Step 4: 聚合 B/C 指标
            df_heat = self._aggregate_bc(df_merged, trade_date)
            logger.info(f"  聚合完成: {len(df_heat)} 个板块")
            
            # Step 5: 计算综合热度和分位
            df_heat = self._calc_heat_pct(df_heat)
            
            # Step 6: 写入数据库
            count = self._save_results(df_heat, trade_date)
            logger.info(f"✅ {trade_date} 写入 {count} 条板块热度数据")
            sys.stdout.flush()
            
            # Step 7: 计算并写入个股板块信号（含全市场分位 + DNA）
            signal_count = self._calc_and_save_stock_signals(
                trade_date, snap_date, df_merged, df_heat, df_stock
            )
            logger.info(f"✅ {trade_date} 写入 {signal_count} 条个股信号数据")
            
            return count

        except Exception as e:
            logger.error(f"❌ 计算过程中发生严重错误: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            return 0
    
    def _load_data(self, trade_date: date, snap_date: date):
        """
        加载原始数据（混合日期）
        """
        # 快照数据 - 用 snap_date
        sql_snap = """
        SELECT stock_code, board_id, board_rank, weight
        FROM ext_board_daily_snap
        WHERE date = :snap_d
        """
        
        # 个股数据 - 用 trade_date（实时）
        # 【V4.0】增加 turnover_rate_percent, volume_days 用于计算个股硬实力
        sql_stock = """
        SELECT stock_code, rank, total_score, turnover_rate_percent, volume_days
        FROM daily_stock_data
        WHERE date = :trade_d AND rank IS NOT NULL AND total_score IS NOT NULL
        """
        
        # 板块列表（获取类型）
        sql_board = """
        SELECT id, board_name, board_type FROM ext_board_list WHERE is_active = true
        """
        
        with self.engine.connect() as conn:
            df_snap = pd.read_sql(text(sql_snap), conn, params={"snap_d": snap_date})
            df_stock = pd.read_sql(text(sql_stock), conn, params={"trade_d": trade_date})
            df_board = pd.read_sql(text(sql_board), conn)
        
        return df_snap, df_stock, df_board
    
    def _calc_share_weight(self, df_snap: pd.DataFrame, df_board: pd.DataFrame) -> pd.DataFrame:
        """
        计算分摊权重 share_ij（热度守恒）
        【V4.0 升级】：黑名单/灰名单逻辑
        """
        # 合并板块类型和名称
        df = df_snap.merge(df_board, left_on='board_id', right_on='id', how='left')
        
        # 分配类型权重
        type_weights = {
            'industry': self.config.w_industry,
            'concept': self.config.w_concept,
            'region': self.config.w_region
        }
        df['type_weight'] = df['board_type'].map(type_weights).fillna(self.config.w_concept)
        
        # 【V4.0】黑名单/灰名单权重调整
        def apply_blacklist_penalty(row):
            level = self.config.get_blacklist_level(row['board_name'])
            if level == 'BLACK':
                return 0.01 # 接近0但保留，避免除零错误或完全丢失
            elif level == 'GREY':
                return 0.1  # 灰名单，保留底色
            return 1.0
        
        df['penalty_factor'] = df.apply(apply_blacklist_penalty, axis=1)
        df['type_weight'] = df['type_weight'] * df['penalty_factor']
        
        # 标记是否黑名单（用于后续逻辑）
        df['blacklist_level'] = df['board_name'].apply(self.config.get_blacklist_level)
        
        # 计算每只股票的权重总和
        stock_weight_sum = df.groupby('stock_code')['type_weight'].transform('sum')
        
        # 计算分摊权重
        # 避免分母为0
        df['share_ij'] = df.apply(
            lambda row: row['type_weight'] / stock_weight_sum[row.name] if stock_weight_sum[row.name] > 0 else 0, 
            axis=1
        )
        
        return df[['stock_code', 'board_id', 'board_type', 'board_name', 'share_ij', 'blacklist_level', 'type_weight']]
    
    def _update_contribution_score(self, df_merged: pd.DataFrame, snap_date: date):
        """
        【V4.0】计算并更新 Contribution Score 到 ext_board_daily_snap
        contribution_score = share_ij * total_score
        """
        logger.info("  更新 Contribution Score 到物理表...")
        
        df_merged['contribution_score'] = df_merged['share_ij'] * df_merged['total_score']
        
        # 批量更新
        # 由于 sqlalchemy 不支持批量 update from values 这种高效语法（取决于DB），
        # 这里使用临时表方式或逐条更新。为了性能，使用临时表 + UPDATE FROM
        
        # 提取需要更新的数据
        update_data = df_merged[['stock_code', 'board_id', 'contribution_score']].to_dict('records')
        if not update_data:
            return

        # 创建临时表并批量更新
        try:
            with self.engine.begin() as conn: # Transaction
                # 1. 创建临时表
                conn.execute(text("""
                    CREATE TEMP TABLE temp_contrib_update (
                        stock_code VARCHAR(10),
                        board_id INT,
                        contribution_score DECIMAL(20,8)
                    ) ON COMMIT DROP
                """))
                
                # 2. 插入数据
                conn.execute(
                    text("INSERT INTO temp_contrib_update (stock_code, board_id, contribution_score) VALUES (:stock_code, :board_id, :contribution_score)"),
                    update_data
                )
                
                # 3. 执行更新
                conn.execute(text("""
                    UPDATE ext_board_daily_snap t
                    SET contribution_score = temp.contribution_score
                    FROM temp_contrib_update temp
                    WHERE t.stock_code = temp.stock_code 
                      AND t.board_id = temp.board_id
                      AND t.date = :snap_date
                """), {"snap_date": snap_date})
                
            logger.info(f"  已更新 {len(update_data)} 条 contribution_score")
        except Exception as e:
            logger.error(f"更新 contribution_score 失败: {e}")

    def _aggregate_bc(self, df: pd.DataFrame, trade_date: date) -> pd.DataFrame:
        """
        聚合 B/C 指标 + 【V4.0】标准差
        """
        k = 1.0  # 排名指数
        
        # 计算加权贡献
        df['b1_contrib'] = df['share_ij'] * (1.0 / np.power(df['rank'].clip(lower=1), k))
        df['c1_contrib'] = df['share_ij'] * df['total_score']
        
        # 按板块聚合
        agg = df.groupby('board_id').agg(
            stock_count=('stock_code', 'count'),
            b1_rank_sum=('b1_contrib', 'sum'),
            c1_score_sum=('c1_contrib', 'sum'),
            # 【V4.0】分歧监测：计算 total_score 的标准差
            score_stddev=('total_score', 'std')
        ).reset_index()
        
        # 计算密度指标
        agg['b2_rank_avg'] = agg['b1_rank_sum'] / agg['stock_count'].clip(lower=1)
        agg['c2_score_avg'] = agg['c1_score_sum'] / agg['stock_count'].clip(lower=1)
        
        agg['trade_date'] = trade_date
        
        return agg
    
    def _calc_heat_pct(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算综合热度和分位值
        """
        # 标准化各指标（Min-Max）
        def normalize(series):
            min_val, max_val = series.min(), series.max()
            if max_val - min_val < 1e-10:
                return pd.Series([0.5] * len(series), index=series.index)
            return (series - min_val) / (max_val - min_val)
        
        norm_b1 = normalize(df['b1_rank_sum'])
        norm_b2 = normalize(df['b2_rank_avg'])
        norm_c2 = normalize(df['c2_score_avg'])
        
        alpha = self.config.heat_alpha
        beta = self.config.heat_beta
        gamma = self.config.heat_gamma
        
        total = alpha + beta + gamma
        alpha, beta, gamma = alpha/total, beta/total, gamma/total
        
        df['heat_raw'] = alpha * norm_b1 + beta * norm_b2 + gamma * norm_c2
        
        # 计算分位值
        df['heat_pct'] = df['heat_raw'].rank(pct=True)
        
        return df
    
    def _save_results(self, df: pd.DataFrame, trade_date: date) -> int:
        """保存结果到数据库"""
        records = []
        for _, row in df.iterrows():
            records.append({
                'trade_date': trade_date,
                'board_id': int(row['board_id']),
                'stock_count': int(row['stock_count']),
                'b1_rank_sum': float(row['b1_rank_sum']),
                'b2_rank_avg': float(row['b2_rank_avg']),
                'c1_score_sum': float(row['c1_score_sum']),
                'c2_score_avg': float(row['c2_score_avg']),
                'heat_raw': float(row['heat_raw']),
                'heat_pct': float(row['heat_pct']),
                'score_stddev': float(row['score_stddev']) if not pd.isna(row['score_stddev']) else 0.0
            })
        
        if not records:
            return 0
        
        # 批量插入
        sql = """
        INSERT INTO ext_board_heat_daily 
            (trade_date, board_id, stock_count, b1_rank_sum, b2_rank_avg, 
             c1_score_sum, c2_score_avg, heat_raw, heat_pct, score_stddev)
        VALUES 
            (:trade_date, :board_id, :stock_count, :b1_rank_sum, :b2_rank_avg,
             :c1_score_sum, :c2_score_avg, :heat_raw, :heat_pct, :score_stddev)
        """
        
        with self.engine.connect() as conn:
            for record in records:
                conn.execute(text(sql), record)
            conn.commit()
        
        return len(records)
    
    # ==================== 个股板块信号计算 ====================
    
    def _calc_and_save_stock_signals(
        self, 
        trade_date: date, 
        snap_date: date,
        df_merged: pd.DataFrame, 
        df_heat: pd.DataFrame,
        df_stock: pd.DataFrame
    ) -> int:
        """
        计算并保存个股板块信号
        【V4.0 升级】：全市场分位 + DNA JSON
        """
        logger.info("  开始计算个股板块信号...")
        
        industry_map = self._load_stock_industries()
        board_info = self._load_board_info(df_heat)
        stock_names = self._load_stock_names()
        
        stock_signals = []
        grouped = df_merged.groupby('stock_code')
        
        w_stock = self.config.get('board_w_stock', 1.5) # V4.0 提高个股权重
        w_exposure = self.config.get('board_w_exposure', 0.5)
        w_max_concept = self.config.get('board_w_max_concept', 0.3)
        penalty_unsafe = self.config.get('board_penalty_unsafe', 0.5)
        safe_pct = self.config.get('board_safe_pct', 0.3)
        
        # 临时存储，用于计算分位
        temp_results = []
        
        logger.info(f"待处理个股数量: {len(grouped)}")
        processed_count = 0

        try:
            for stock_code, group in grouped:
                processed_count += 1
                if processed_count % 1000 == 0:
                    logger.info(f"已处理 {processed_count} 只股票...")
                    
                try:
                    stock_row = df_stock[df_stock['stock_code'] == stock_code].iloc[0]
                    market_rank = int(stock_row['rank'])
                    total_score = float(stock_row['total_score'])
                    stock_name = stock_names.get(stock_code, '')
                    
                    board_ids = group['board_id'].tolist()
                    shares = group['share_ij'].tolist()
                    blacklist_levels = group['blacklist_level'].tolist()
                    
                    # 计算 Exposure 和收集板块信息
                    exposure = 0.0
                    boards_details = []
                    
                    for bid, share, bl_level in zip(board_ids, shares, blacklist_levels):
                        info = board_info.get(bid, {})
                        heat_pct = info.get('heat_pct', 0)
                        exposure += share * heat_pct
                        
                        boards_details.append({
                            'id': bid,
                            'name': info.get('name', ''),
                            'type': info.get('type', ''),
                            'heat_pct': heat_pct,
                            'share': share,
                            'blacklist_level': bl_level
                        })
                    
                    # Fallback 策略选择最佳驱动
                    # 优先级: 非黑名单S/A概念 > 非黑名单S/A行业 > 非黑名单B > 其它
                    max_driver = self._select_best_driver(boards_details)
                    max_heat = max_driver.get('heat_pct', 0)
                    
                    # 行业安全
                    industry_id = industry_map.get(stock_code)
                    industry_info = board_info.get(industry_id, {}) if industry_id else {}
                    industry_heat_pct = industry_info.get('heat_pct', 0)
                    industry_safe = industry_heat_pct >= safe_pct if industry_id else True
                    
                    # 计算合成分 (Final Score)
                    final_score = (
                        w_stock * (total_score / 100) +
                        w_exposure * exposure +
                        w_max_concept * max_heat
                    )
                    
                    if not industry_safe:
                        final_score *= penalty_unsafe
                    
                    # 【V4.0】计算个股硬实力子分数 (0-100归一化)
                    # C2: 量能爆发 (volume_days) - 假设 >0 为强，映射 -20~20 -> 0~100
                    raw_vol = float(stock_row.get('volume_days', 0) or 0)
                    vol_score = min(100, max(0, 50 + raw_vol * 2.5))
                    
                    # C1: 资金强度 (turnover) - 20%换手 = 100分
                    raw_turnover = float(stock_row.get('turnover_rate_percent', 0) or 0)
                    turnover_score = min(100, max(0, raw_turnover * 5))
                    
                    # B2: 趋势形态 (total_score) - 假设 -50~50 -> 0~100
                    trend_score = min(100, max(0, 50 + total_score))
                    
                    # 生成 DNA JSON
                    stock_detail_json = {
                         "vol_score": round(vol_score, 1),
                         "turnover_score": round(turnover_score, 1),
                         "trend_score": round(trend_score, 1),
                         "rank": market_rank,
                         "contribution_score": group['contribution_score'].max() if 'contribution_score' in group.columns else 0
                    }
                    
                    dna_data = {
                        "score_breakdown": {
                            "stock": round(w_stock * (total_score / 100), 4),
                            "exposure": round(w_exposure * exposure, 4),
                            "driver": round(w_max_concept * max_heat, 4),
                            "formula": f"{w_stock}*Stock + {w_exposure}*Expo + {w_max_concept}*Driver"
                        },
                        "boards": sorted(boards_details, key=lambda x: x['share'], reverse=True),
                        "fallback_selected": max_driver.get('name', 'None'),
                        "max_concept_name": max_driver.get('name', ''),
                        "max_concept_heat": max_heat,
                        "industry_name": industry_info.get('name', ''),
                        "industry_heat": industry_heat_pct,
                        "industry_safe": industry_safe,
                        "stock_details": stock_detail_json
                    }
                    
                    temp_results.append({
                        'trade_date': trade_date,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'market_rank': market_rank,
                        'total_score': total_score,
                        'final_score': final_score,
                        'max_driver': max_driver,
                        'industry_id': industry_id,
                        'industry_name': industry_info.get('name', ''),
                        'industry_heat_pct': industry_heat_pct,
                        'industry_safe': industry_safe,
                        'exposure': exposure,
                        'board_count': len(board_ids),
                        'top_boards_json': json.dumps([
                            {k: v for k, v in b.items() if k in ['id', 'name', 'type', 'heat_pct']} 
                            for b in sorted(boards_details, key=lambda x: x['heat_pct'], reverse=True)[:5]
                        ], ensure_ascii=False),
                        'dna_json': json.dumps(dna_data, ensure_ascii=False),
                        'snap_date': snap_date
                    })
                except Exception as inner_e:
                    logger.error(f"处理股票 {stock_code} 失败: {inner_e}")
                    continue

        except Exception as e:
            logger.error(f"计算个股信号循环失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
            
        # 【V4.0】全市场分位计算
        df_res = pd.DataFrame(temp_results)
        if not df_res.empty:
            df_res['final_score_pct'] = df_res['final_score'].rank(pct=True)
            
            s_pct = self.config.get('board_signal_S_pct', 0.97)
            a_pct = self.config.get('board_signal_A_pct', 0.90)
            b_pct = self.config.get('board_signal_B_pct', 0.80)
            
            def get_level(pct):
                if pct >= s_pct: return 'S'
                if pct >= a_pct: return 'A'
                if pct >= b_pct: return 'B'
                return 'NONE'
            
            df_res['signal_level'] = df_res['final_score_pct'].apply(get_level)
            
            # 转回 dict 列表
            stock_signals = df_res.to_dict('records')
            
            # 5. 批量写入
            count = self._save_stock_signals(stock_signals, trade_date)
            return count
        return 0

    def _select_best_driver(self, boards: list) -> dict:
        """
        【V3.5/4.0】Fallback 策略选择最佳驱动
        """
        # 过滤掉 BLACK 名单 (但 GREY 保留)
        candidates = [b for b in boards if b.get('blacklist_level') != 'BLACK']
        if not candidates:
            return {}
        
        s_pct = self.config.get('board_signal_S_pct', 0.97)
        a_pct = self.config.get('board_signal_A_pct', 0.90)
        
        # 1. 非黑名单 S/A 级概念
        tier1 = [b for b in candidates if b['type'] == 'concept' and b['heat_pct'] >= a_pct]
        if tier1: return max(tier1, key=lambda x: x['heat_pct'])
        
        # 2. 非黑名单 S/A 级行业
        tier2 = [b for b in candidates if b['type'] == 'industry' and b['heat_pct'] >= a_pct]
        if tier2: return max(tier2, key=lambda x: x['heat_pct'])
        
        # 3. 其它 (取热度最高)
        return max(candidates, key=lambda x: x['heat_pct'])

    def _load_stock_industries(self) -> Dict[str, int]:
        """加载个股主营行业映射 {stock_code: industry_board_id}"""
        sql = """
        SELECT s.stock_code, b.id as industry_board_id
        FROM stocks s
        JOIN ext_board_list b ON b.board_name = TRIM(BOTH '[]''' FROM s.industry)
            AND b.board_type = 'industry'
        WHERE s.industry IS NOT NULL 
            AND s.industry != '[]'
            AND s.industry != ''
        """
        result = {}
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql))
            for row in rows:
                result[row[0]] = row[1]
        return result
    
    def _load_board_info(self, df_heat: pd.DataFrame) -> Dict[int, Dict]:
        """构建板块信息字典 {board_id: {name, type, heat_pct}}"""
        sql = """
        SELECT id, board_name, board_type FROM ext_board_list WHERE is_active = true
        """
        board_info = {}
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql))
            for row in rows:
                board_info[row[0]] = {
                    'name': row[1],
                    'type': row[2],
                    'heat_pct': 0
                }
        
        # 填充热度分位
        for _, row in df_heat.iterrows():
            bid = int(row['board_id'])
            if bid in board_info:
                board_info[bid]['heat_pct'] = float(row['heat_pct'])
        
        return board_info
    
    def _load_stock_names(self) -> Dict[str, str]:
        """加载股票名称映射"""
        sql = "SELECT stock_code, stock_name FROM stocks"
        result = {}
        with self.engine.connect() as conn:
            rows = conn.execute(text(sql))
            for row in rows:
                result[row[0]] = row[1]
        return result
    
    def _save_stock_signals(self, signals: list, trade_date: date) -> int:
        """批量保存个股信号到缓存表 (分批写入 + 数据清洗)"""
        if not signals:
            return 0
        
        # 先删除已有数据
        delete_sql = "DELETE FROM cache_stock_board_signal WHERE trade_date = :d"
        
        insert_sql = """
        INSERT INTO cache_stock_board_signal (
            trade_date, stock_code, stock_name, market_rank, total_score,
            signal_level, final_score,
            max_driver_board_id, max_driver_name, max_driver_type, max_driver_heat_pct,
            primary_industry_id, primary_industry_name, primary_industry_heat_pct, industry_safe,
            board_exposure, board_count, top_boards_json, snap_date,
            dna_json, final_score_pct, fallback_reason
        ) VALUES (
            :trade_date, :stock_code, :stock_name, :market_rank, :total_score,
            :signal_level, :final_score,
            :max_driver_board_id, :max_driver_name, :max_driver_type, :max_driver_heat_pct,
            :industry_id, :industry_name, :industry_heat_pct, :industry_safe,
            :board_exposure, :board_count, :top_boards_json, :snap_date,
            :dna_json, :final_score_pct, :fallback_reason
        )
        """
        
        def safe_int(val):
            """Convert to int64-safe value; return None on NaN/None/overflow."""
            try:
                if pd.isna(val) or val is None:
                    return None
                v = float(val)
                if np.isnan(v) or np.isinf(v):
                    return None
                v_int = int(v)
                # guard bigint overflow
                int64_max = 2**63 - 1
                int64_min = -2**63
                if v_int > int64_max or v_int < int64_min:
                    logger.warning(f"  safe_int overflow drop: {v_int}")
                    return None
                return v_int
            except Exception:
                return None

        def safe_float(val):
            try:
                if pd.isna(val) or val is None or np.isinf(val): return None
                return float(val)
            except:
                return None

        total_inserted = 0
        batch_size = 1000
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(delete_sql), {"d": trade_date})
                conn.commit()
                
                # 分批处理
                for i in range(0, len(signals), batch_size):
                    batch = signals[i:i+batch_size]
                    final_records = []
                    
                    for sig in batch:
                        md = sig.get('max_driver', {})
                        
                        rec = {
                            'trade_date': sig['trade_date'],
                            'stock_code': sig['stock_code'],
                            'stock_name': sig['stock_name'],
                            'market_rank': safe_int(sig['market_rank']),
                            'total_score': safe_float(sig['total_score']),
                            'signal_level': sig['signal_level'],
                            'final_score': safe_float(sig.get('final_score', 0)),
                            'max_driver_board_id': safe_int(md.get('id')),
                            'max_driver_name': md.get('name', ''),
                            'max_driver_type': md.get('type', ''),
                            'max_driver_heat_pct': safe_float(md.get('heat_pct', 0)),
                            'industry_id': safe_int(sig['industry_id']),
                            'industry_name': sig['industry_name'],
                            'industry_heat_pct': safe_float(sig['industry_heat_pct']),
                            'industry_safe': bool(sig['industry_safe']),
                            'board_exposure': safe_float(sig['exposure']),
                            'board_count': safe_int(sig['board_count']),
                            'top_boards_json': sig['top_boards_json'],
                            'snap_date': sig['snap_date'],
                            'dna_json': sig['dna_json'],
                            'final_score_pct': safe_float(sig.get('final_score_pct', 0)),
                            'fallback_reason': sig.get('fallback_reason', '')
                        }
                        final_records.append(rec)

                    try:
                        conn.execute(text(insert_sql), final_records)
                        conn.commit()
                        total_inserted += len(final_records)
                        logger.info(f"  已写入 {total_inserted}/{len(signals)} 条信号数据")
                    except Exception as e:
                        logger.error(f"  ❌ 批量写入失败 (Batch {i//batch_size}): {e}")
                        logger.error(f"  Sample Record: {final_records[0] if final_records else 'Empty'}")
                        # Don't raise, try next batch? No, data integrity matters.
                        raise e
                        
        except Exception as e:
            logger.error(f"保存信号数据时发生错误: {e}")
            return total_inserted
        
        return total_inserted


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='板块热度计算 ETL')
    parser.add_argument('--date', type=str, help='指定计算日期 (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='计算所有可用日期')
    parser.add_argument('--force', action='store_true', help='强制重算（覆盖已有数据）')
    parser.add_argument('--dry-run', action='store_true', help='只显示可用日期，不执行计算')
    parser.add_argument('--allow-latest-snap-fallback', action='store_true', help='当目标日期之前无任何快照时，允许借用最新快照（默认关闭）')
    args = parser.parse_args()
    
    # 创建引擎
    engine = create_engine(DATABASE_URL)
    
    # 加载配置
    config = ConfigLoader(engine)
    
    # 创建计算器
    calc = BoardHeatCalculator(engine, config, allow_latest_snap_fallback=args.allow_latest_snap_fallback)
    
    # 获取可用日期
    available_dates = calc.get_available_dates()
    if not available_dates:
        logger.error("没有可用的计算日期（snap 和 daily_stock_data 无交集）")
        return 1
    
    logger.info(f"可用日期范围: {available_dates[-1]} ~ {available_dates[0]}，共 {len(available_dates)} 天")
    
    if args.dry_run:
        logger.info("--dry-run 模式，不执行计算")
        for d in available_dates[:10]:
            exists = "✓" if calc.check_existing(d) else "○"
            logger.info(f"  {exists} {d}")
        if len(available_dates) > 10:
            logger.info(f"  ... 还有 {len(available_dates) - 10} 天")
        return 0
    
    # 确定要计算的日期
    if args.all:
        # --all 优先：计算所有可用日期
        dates_to_calc = available_dates
        logger.info(f"📅 计算全部日期模式，共 {len(dates_to_calc)} 天")
    elif args.date:
        requested_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        
        if requested_date in available_dates:
            target_date = requested_date
        else:
            target_date = None
            for d in available_dates:
                if d <= requested_date:
                    target_date = d
                    break
            
            if not target_date:
                logger.error(f"{requested_date} 不在可用日期范围内")
                return 1

            logger.info(f"📅 {requested_date} 非交易日/无数据，回退到最近交易日 {target_date}")
        
        dates_to_calc = [target_date]
    else:
        # 默认只计算最新日期
        dates_to_calc = [available_dates[0]]
    
    # 执行计算
    total_count = 0
    for d in tqdm(dates_to_calc, desc="计算板块热度"):
        count = calc.calculate(d, force=args.force)
        total_count += count
    
    logger.info(f"🎉 完成！共计算 {len(dates_to_calc)} 天，写入 {total_count} 条记录")
    return 0


if __name__ == '__main__':
    sys.exit(main())
