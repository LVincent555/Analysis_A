#!/usr/bin/env python3
"""
外部板块数据同步脚本
============================
从 AKShare 获取东方财富(EM)和同花顺(THS)的板块数据，写入 ext_* 表

功能:
1. 同步板块列表 -> ext_board_list
2. 同步板块成分股 -> ext_board_daily_snap
3. 自动映射到本地板块 -> ext_board_local_map
4. 状态管理和幂等检查

使用方法:
    python sync_ext_boards.py                    # 同步今天数据
    python sync_ext_boards.py --date 2025-01-10  # 同步指定日期
    python sync_ext_boards.py --provider em      # 只同步东财
    python sync_ext_boards.py --provider ths     # 只同步同花顺
    python sync_ext_boards.py --skip-cons        # 只同步板块列表，跳过成分股
    python sync_ext_boards.py --force            # 强制同步（忽略幂等检查）

作者: AI Assistant
日期: 2025-12-10
版本: v1.1.0 (添加状态管理)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

import random
import requests
import akshare as ak
import pandas as pd
import pywencai  # 同花顺问财 API（替代已失效的 AKShare 接口）
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# 静态黑名单：无分析价值或过宽泛的超大板块，直接跳过成分抓取
BLACKLIST_BOARDS = [
    '融资融券',
    '深股通',
    '沪股通',
    '标普概念',
    '富时罗素概念',
    'MSCI概念',
    '注册制次新股',
    'GDR',
    '电子后视镜',
    '体育产业',
    '单抗概念',
    '专精特新',
]


def _resolve_blacklist_boards() -> set[str]:
    env_raw = os.getenv("SYNC_EXT_BOARD_BLACKLIST", "").strip()
    if not env_raw:
        return set(BLACKLIST_BOARDS)
    env_items = {x.strip() for x in env_raw.split(",") if x.strip()}
    return set(BLACKLIST_BOARDS).union(env_items)

# ============================================================
# 91HTTP 代理管理器
# ============================================================
class ProxyManager:
    """91HTTP 隧道代理管理器，自动获取和轮换代理 IP（线程安全）"""
    
    API_URL = "http://api.91http.com/v1/get-ip"
    
    def __init__(self, trade_no: str = None, secret: str = None, max_ips: int = 200):
        self.trade_no = trade_no or "B200987778609"
        self.secret = secret or "7GJdQkL6G93PcR9o"
        self.max_ips = max_ips  # IP 使用上限
        self._lock = threading.Lock()  # 线程锁
        self._proxy_pool: Dict[int, Dict] = {}  # 线程ID -> 代理信息
        self._total_ips_used: int = 0  # 统计用了多少个 IP
        self._exhausted: bool = False  # 是否已耗尽配额
    
    def get_proxy(self, force_refresh: bool = False) -> Optional[Dict[str, str]]:
        """获取代理，每个线程独立的代理（线程安全）"""
        if self._exhausted:
            return None
        
        thread_id = threading.get_ident()
        now = time.time()
        
        with self._lock:
            # 检查当前线程是否有代理
            if thread_id in self._proxy_pool:
                proxy_info = self._proxy_pool[thread_id]
                if not force_refresh and now < proxy_info['expire_time']:
                    return proxy_info['proxy']
            
            # 需要新代理，检查配额
            if self._total_ips_used >= self.max_ips:
                if not self._exhausted:
                    logger.warning(f"⚠️ 已达到 IP 使用上限 ({self.max_ips})，停止获取新代理")
                    self._exhausted = True
                return None
            
            # 获取新代理
            proxy = self._fetch_new_proxy()
            if proxy:
                self._proxy_pool[thread_id] = {
                    'proxy': proxy,
                    'expire_time': now + 50  # 50秒有效期
                }
                return proxy
            return None
    
    def _fetch_new_proxy(self) -> Optional[Dict[str, str]]:
        """从 91HTTP 获取新的代理 IP（内部调用，已加锁）
        
        基于漏桶原理的流量整形 (Traffic Shaping)
        公式: WaitTime = Max(0, MinInterval - (Now - LastTime))
        MIN_INTERVAL=2.0秒 提供 300% 冗余，彻底避免代理商限流
        """
        MIN_INTERVAL = 2.0  # 智能冷却间隔（秒）
        
        now = time.time()
        last_time = getattr(self, '_last_fetch_time', 0)
        elapsed = now - last_time
        wait_time = MIN_INTERVAL - elapsed
        
        if wait_time > 0:
            # 还没冷透，强制睡够时间
            time.sleep(wait_time)
        
        # 更新最后提取时间
        self._last_fetch_time = time.time()
        
        try:
            params = {
                'trade_no': self.trade_no,
                'secret': self.secret,
                'num': 1,
                'protocol': 1,
                'format': 'text',
                'sep': 1,
                'filter': 1,
                'auto_white': 1
            }
            r = requests.get(self.API_URL, params=params, timeout=10)
            proxy_ip = r.text.strip()
            
            if proxy_ip and ':' in proxy_ip and not proxy_ip.startswith('{'):
                self._total_ips_used += 1
                logger.info(f"获取新代理 #{self._total_ips_used}/{self.max_ips}: {proxy_ip}")
                return {
                    'http': f'http://{proxy_ip}',
                    'https': f'http://{proxy_ip}'
                }
            else:
                logger.warning(f"获取代理失败: {proxy_ip}")
                return None
        except Exception as e:
            logger.error(f"获取代理异常: {e}")
            return None
    
    def mark_failed(self):
        """标记当前线程的代理失败，强制刷新"""
        thread_id = threading.get_ident()
        with self._lock:
            if thread_id in self._proxy_pool:
                del self._proxy_pool[thread_id]
    
    def is_exhausted(self) -> bool:
        """检查是否已耗尽配额"""
        return self._exhausted
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            'total_ips_used': self._total_ips_used,
            'max_ips': self.max_ips,
            'exhausted': self._exhausted,
            'active_threads': len(self._proxy_pool)
        }

# 全局代理管理器
_proxy_manager: Optional[ProxyManager] = None

def get_proxy_manager() -> Optional[ProxyManager]:
    return _proxy_manager

def set_proxy_manager(manager: ProxyManager):
    global _proxy_manager
    _proxy_manager = manager

# ============================================================
# 直接调用东财 API（绕过 AKShare 的重复请求）
# ============================================================
class EastMoneyAPI:
    """东方财富直连 API，支持代理"""
    
    BASE_URL = "https://push2.eastmoney.com/api/qt/clist/get"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://quote.eastmoney.com/center/gridlist.html",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close",
    }
    
    def __init__(self):
        self._industry_code_map: Dict[str, str] = {}
        self._concept_code_map: Dict[str, str] = {}
    
    def cache_board_codes(self, board_type: str, df: pd.DataFrame):
        """缓存板块代码映射"""
        code_map = {}
        for _, row in df.iterrows():
            name = str(row.get('板块名称', row.get('名称', row.get('name', ''))))
            code = str(row.get('板块代码', row.get('代码', row.get('code', ''))))
            if name and code:
                code_map[name] = code
        
        if board_type == 'industry':
            self._industry_code_map = code_map
        else:
            self._concept_code_map = code_map
        
        return len(code_map)
    
    def fetch_board_list(self, board_type: str = 'industry') -> Optional[pd.DataFrame]:
        """直接请求东财 API 获取板块列表（走代理，支持分页，带重试）"""
        # 行业板块和概念板块的 API 参数不同
        if board_type == 'industry':
            fs = "m:90+t:2+f:!50"
        else:
            fs = "m:90+t:3+f:!50"
        
        all_records = []
        page = 1
        page_size = 100  # 每页100条，确保获取完整数据
        
        try:
            proxy_mgr = get_proxy_manager()
            
            while True:
                # 每页请求带重试（最多3次）
                page_success = False
                for retry in range(3):
                    try:
                        # 每次重试都获取新代理
                        proxies = proxy_mgr.get_proxy() if proxy_mgr else None
                        
                        params = {
                            "pn": str(page),
                            "pz": str(page_size),
                            "po": "1",
                            "np": "1",
                            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                            "fltt": "2",
                            "invt": "2",
                            "fid": "f3",
                            "fs": fs,
                            "fields": "f12,f14,f3"
                        }
                        
                        with requests.Session() as s:
                            s.trust_env = False
                            r = s.get(self.BASE_URL, params=params, headers=self.HEADERS, 
                                     proxies=proxies, timeout=15)
                            r.raise_for_status()
                            data = r.json()
                        
                        diff = data.get("data", {}).get("diff") or []
                        if not diff:
                            page_success = True
                            break
                        
                        for item in diff:
                            all_records.append({
                                "板块代码": item.get("f12", ""),
                                "板块名称": item.get("f14", ""),
                                "涨跌幅": item.get("f3", 0),
                            })
                        
                        page_success = True
                        break  # 成功，跳出重试循环
                        
                    except Exception as e:
                        if proxy_mgr:
                            proxy_mgr.mark_failed()
                        logger.warning(f"获取{board_type}板块第{page}页失败(重试{retry+1}/3): {str(e)[:50]}")
                        time.sleep(2 + retry)  # 递增延迟
                
                if not page_success:
                    raise RuntimeError(f"获取{board_type}板块第{page}页失败")
                
                # 检查是否还有下一页
                total = data.get("data", {}).get("total", 0)
                if page * page_size >= total:
                    break
                
                page += 1
                time.sleep(1)  # 分页间延迟增加到1秒
            
            if not all_records:
                return pd.DataFrame()
            
            df = pd.DataFrame(all_records)
            # 自动缓存
            self.cache_board_codes(board_type, df)
            logger.info(f"获取到 {len(df)} 个{board_type}板块")
            return df
            
        except Exception as e:
            proxy_mgr = get_proxy_manager()
            if proxy_mgr:
                proxy_mgr.mark_failed()
            raise Exception(f"获取板块列表失败: {e}")
    
    def fetch_board_cons(self, board_name: str, board_type: str = 'industry') -> Optional[pd.DataFrame]:
        """直接请求东财 API 获取板块成分股（支持分页，突破100条限制）"""
        code_map = self._industry_code_map if board_type == 'industry' else self._concept_code_map
        bk_code = code_map.get(board_name)
        
        if not bk_code:
            return None
        
        all_records = []
        page = 1
        page_size = 100  # 东财 API 每页最多返回 100 条
        
        try:
            proxy_mgr = get_proxy_manager()
            
            while True:
                params = {
                    "pn": str(page),
                    "pz": str(page_size),
                    "po": "1",
                    "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": f"b:{bk_code}+f:!50",
                    "fields": "f12,f14,f2,f3,f4,f5,f6,f7"
                }
                
                proxies = proxy_mgr.get_proxy() if proxy_mgr else None
                
                with requests.Session() as s:
                    s.trust_env = False
                    r = s.get(self.BASE_URL, params=params, headers=self.HEADERS, 
                             proxies=proxies, timeout=15)
                    r.raise_for_status()
                    data = r.json()
                
                diff = data.get("data", {}).get("diff") or []
                if not diff:
                    break  # 没有更多数据
                
                for item in diff:
                    all_records.append({
                        "代码": item.get("f12", ""),
                        "名称": item.get("f14", ""),
                        "最新价": item.get("f2", 0),
                        "涨跌幅": item.get("f3", 0),
                        "涨跌额": item.get("f4", 0),
                        "成交量": item.get("f5", 0),
                        "成交额": item.get("f6", 0),
                        "振幅": item.get("f7", 0),
                    })
                
                # 检查是否还有下一页
                total = data.get("data", {}).get("total", 0)
                if page * page_size >= total:
                    break  # 已获取全部数据
                
                page += 1
                time.sleep(0.1)  # 分页请求间短暂延迟
            
            if not all_records:
                return pd.DataFrame()
            
            return pd.DataFrame(all_records)
            
        except Exception as e:
            # 标记代理失败
            if proxy_mgr and ("RemoteDisconnected" in str(e) or "Connection" in str(e)):
                proxy_mgr.mark_failed()
            raise Exception(f"东财API请求失败: {e}")

# 全局东财 API 实例
_em_api = EastMoneyAPI()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 数据库连接 (从环境变量或配置文件获取)
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# 尝试从 app.database 获取数据库 URL
DATABASE_URL = None
try:
    # 添加 backend 目录到路径
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from app.database import DATABASE_URL as APP_DB_URL
    DATABASE_URL = APP_DB_URL
    logger.info("使用 app.database 中的数据库配置")
except ImportError:
    pass

# 如果没有从 app 获取到，则从环境变量构建
if not DATABASE_URL:
    DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('DB_URL')
    
    if not DATABASE_URL:
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'stock_analysis')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'password')
        DATABASE_URL = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

# 数据目录
try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')


def find_latest_trade_date(engine, target_date: date) -> Optional[date]:
    sql_legacy = """
    SELECT MAX(date) FROM daily_stock_data
    WHERE rank IS NOT NULL AND date <= :d
    """
    sql_crawler = """
    SELECT MAX(trade_date)::date FROM crawler.raw_stock_daily
    WHERE trade_date <= :d
    """
    with engine.connect() as conn:
        row = conn.execute(text(sql_legacy), {"d": target_date}).fetchone()
        row2 = conn.execute(text(sql_crawler), {"d": target_date}).fetchone()

        candidates = []
        if row and row[0]:
            candidates.append(row[0])
        if row2 and row2[0]:
            candidates.append(row2[0])

        return max(candidates) if candidates else None


# ============================================================
# 状态管理器
# ============================================================

class ExtBoardStateManager:
    """外部板块同步状态管理器"""
    
    def __init__(self, state_file: str = "ext_board_sync_state.json"):
        self.state_file = Path(DATA_DIR) / state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态文件"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"状态文件读取失败，创建新文件: {e}")
        return self._create_empty_state()
    
    def _create_empty_state(self) -> Dict:
        """创建空状态"""
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "syncs": {},
            "config": {
                "auto_sync_on_import": True,
                "sync_providers": ["em", "ths"],
                "skip_cons_if_slow": False
            }
        }
    
    def _save_state(self):
        """保存状态"""
        self.state["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def is_synced_today(self, date_str: str, provider: str = None) -> bool:
        """检查指定日期是否已同步成功
        
        Args:
            date_str: 日期字符串
            provider: 可选，指定数据源。如果指定，则只检查该 provider 的状态
        """
        sync_info = self.state["syncs"].get(date_str)
        if sync_info is None:
            return False
        
        if provider:
            # 检查指定 provider 的状态
            provider_info = sync_info.get("providers", {}).get(provider)
            return provider_info is not None and provider_info.get("status") == "success"
        else:
            # 检查整体状态
            return sync_info.get("status") == "success"
    
    def start_sync(self, date_str: str, provider: str = None):
        """开始同步（不覆盖已有 provider 数据）"""
        if date_str not in self.state["syncs"]:
            # 新日期，创建新记录
            self.state["syncs"][date_str] = {
                "status": "in_progress",
                "start_time": datetime.now().isoformat(),
                "providers": {},
                "metrics": {}
            }
        else:
            # 已有记录，只更新状态，保留 providers 数据
            self.state["syncs"][date_str]["status"] = "in_progress"
            # 不覆盖 start_time 和 providers
        self._save_state()
    
    def update_provider_status(self, date_str: str, provider: str, 
                                board_count: int, cons_count: int, 
                                status: str, duration: float,
                                failed_boards: List[str] = None):
        """更新数据源状态"""
        if date_str in self.state["syncs"]:
            self.state["syncs"][date_str]["providers"][provider] = {
                "board_count": board_count,
                "cons_count": cons_count,
                "status": status,
                "duration_seconds": round(duration, 2),
                "failed_boards": failed_boards or []
            }
            self._save_state()
    
    def mark_success(self, date_str: str, metrics: Dict):
        """标记同步成功"""
        if date_str in self.state["syncs"]:
            self.state["syncs"][date_str].update({
                "status": "success",
                "end_time": datetime.now().isoformat(),
                "metrics": metrics
            })
            # 计算总耗时
            start = datetime.fromisoformat(self.state["syncs"][date_str]["start_time"])
            end = datetime.fromisoformat(self.state["syncs"][date_str]["end_time"])
            self.state["syncs"][date_str]["duration_seconds"] = round((end - start).total_seconds(), 2)
            self._save_state()
    
    def mark_failed(self, date_str: str, error: str):
        """标记同步失败"""
        if date_str in self.state["syncs"]:
            self.state["syncs"][date_str].update({
                "status": "failed",
                "end_time": datetime.now().isoformat(),
                "error": error
            })
            self._save_state()
    
    def get_sync_info(self, date_str: str) -> Optional[Dict]:
        """获取同步信息"""
        return self.state["syncs"].get(date_str)


class ExtBoardSyncer:
    """外部板块数据同步器"""
    
    def __init__(self, db_url: str = DATABASE_URL, delay: float = 1.5):
        self.engine = create_engine(db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.blacklist_boards = _resolve_blacklist_boards()
        
        # 请求间隔（秒）
        self.delay = delay
        self.delay_ths = delay * 1.5  # 同花顺限制更严格
        
        # 缓存 provider_id
        self._provider_cache: Dict[str, int] = {}
        self._load_providers()
        
        # 缓存已有股票代码
        self._stock_codes: set = set()
        self._load_stock_codes()

    def _split_boards_by_blacklist(self, boards: List[tuple]) -> tuple[List[tuple], List[str]]:
        kept: List[tuple] = []
        skipped: List[str] = []
        for board_id, board_name in boards:
            if str(board_name) in self.blacklist_boards:
                skipped.append(str(board_name))
                continue
            kept.append((board_id, board_name))
        return kept, skipped
    
    def _load_providers(self):
        """加载数据源 ID"""
        result = self.session.execute(text("SELECT id, code FROM ext_providers"))
        for row in result:
            self._provider_cache[row.code] = row.id
        logger.info(f"已加载数据源: {self._provider_cache}")
    
    def _load_stock_codes(self):
        """加载已有股票代码（用于过滤无效成分股）"""
        result = self.session.execute(text("SELECT stock_code FROM stocks"))
        self._stock_codes = {row.stock_code for row in result}
        logger.info(f"已加载 {len(self._stock_codes)} 个股票代码")
    
    def normalize_stock_code(self, raw_code: str) -> Optional[str]:
        """
        标准化股票代码，使其与 stocks 表一致
        
        输入格式可能是:
        - 000001 (纯数字)
        - 000001.SZ / 000001.SH (带后缀)
        - sz000001 / sh000001 (带前缀)
        - S00001 (带S前缀的旧格式)
        
        输出格式: 与 stocks.stock_code 一致
        """
        if not raw_code:
            return None
        
        code = str(raw_code).strip().upper()
        
        # 移除常见前后缀
        for suffix in ['.SZ', '.SH', '.BJ']:
            if code.endswith(suffix):
                code = code[:-3]
                break
        
        for prefix in ['SZ', 'SH', 'BJ']:
            if code.startswith(prefix):
                code = code[2:]
                break
        
        # 处理 S 前缀 (旧格式如 S00001)
        if code.startswith('S') and len(code) == 6:
            code = code[1:]
        
        # 确保是6位数字
        if len(code) == 6 and code.isdigit():
            # 检查是否在已知股票列表中
            # 尝试多种格式匹配
            for fmt in [code, f'S{code[1:]}', f's{code[1:]}']:
                if fmt in self._stock_codes:
                    return fmt
            
            # 如果都没匹配上，返回原始6位代码（可能是新股）
            return code
        
        return None
    
    # ==================== 东方财富 (EM) ====================
    
    def sync_em_boards(self, target_date: date, skip_cons: bool = False):
        """同步东方财富板块数据"""
        provider_id = self._provider_cache.get('em')
        if not provider_id:
            logger.error("未找到 em 数据源配置")
            return
        
        logger.info("=" * 60)
        logger.info("开始同步东方财富板块数据...")
        
        # 1. 同步行业板块
        self._sync_em_industry_boards(provider_id)
        
        # 2. 同步概念板块
        self._sync_em_concept_boards(provider_id)
        
        # 3. 同步成分股
        if not skip_cons:
            self._sync_em_board_cons(provider_id, target_date, 'industry')
            self._sync_em_board_cons(provider_id, target_date, 'concept')
        
        self.session.commit()
        logger.info("东方财富板块数据同步完成")
    
    def sync_em_boards_with_metrics(self, target_date: date, skip_cons: bool = False) -> tuple:
        """同步东方财富板块数据（带运维指标）
        
        Returns:
            tuple: (板块数, 成分股数, 失败板块列表)
        """
        provider_id = self._provider_cache.get('em')
        if not provider_id:
            logger.error("未找到 em 数据源配置")
            return 0, 0, []
        
        logger.info("=" * 60)
        logger.info("开始同步东方财富板块数据...")
        
        total_boards = 0
        total_cons = 0
        all_failed = []
        
        # 1. 同步行业板块
        industry_count = self._sync_em_industry_boards_with_count(provider_id)
        total_boards += industry_count
        
        # 2. 同步概念板块
        concept_count = self._sync_em_concept_boards_with_count(provider_id)
        total_boards += concept_count
        
        # 3. 同步成分股（支持 board_type 和 limit 参数）
        if not skip_cons:
            board_type = getattr(self, '_board_type', 'all')
            limit = getattr(self, '_limit', None)
            
            # 并发模式参数
            use_concurrent = getattr(self, '_concurrent', False)
            workers = getattr(self, '_workers', 10)
            ip_ttl = getattr(self, '_ip_ttl', 50.0)  # IP 复用时间（秒）
            req_delay_min = getattr(self, '_req_delay_min', 1.0)
            req_delay_max = getattr(self, '_req_delay_max', 3.0)
            
            if board_type in ('industry', 'all'):
                if use_concurrent:
                    cons1, failed1 = self._sync_em_board_cons_concurrent(
                        provider_id, target_date, 'industry', limit, workers, ip_ttl,
                        req_delay_min, req_delay_max
                    )
                else:
                    cons1, failed1 = self._sync_em_board_cons_with_metrics(provider_id, target_date, 'industry', limit)
                total_cons += cons1
                all_failed.extend(failed1)
            
            if board_type in ('concept', 'all'):
                if use_concurrent:
                    cons2, failed2 = self._sync_em_board_cons_concurrent(
                        provider_id, target_date, 'concept', limit, workers, ip_ttl,
                        req_delay_min, req_delay_max
                    )
                else:
                    cons2, failed2 = self._sync_em_board_cons_with_metrics(provider_id, target_date, 'concept', limit)
                total_cons += cons2
                all_failed.extend(failed2)
        
        self.session.commit()
        logger.info("东方财富板块数据同步完成")
        
        return total_boards, total_cons, all_failed
    
    def _sync_em_industry_boards_with_count(self, provider_id: int) -> int:
        """同步东财行业板块列表（返回数量）"""
        logger.info("获取东财行业板块列表...")
        try:
            # 优先使用代理直连 API
            proxy_mgr = get_proxy_manager()
            if proxy_mgr:
                try:
                    df = _em_api.fetch_board_list('industry')
                    logger.info(f"已通过代理获取并缓存 {len(_em_api._industry_code_map)} 个行业板块代码")
                except Exception as proxy_exc:
                    logger.warning(f"代理直连行业板块失败，回退 AKShare: {proxy_exc}")
                    df = ak.stock_board_industry_name_em()
                    if df is not None and not df.empty:
                        cached = _em_api.cache_board_codes('industry', df)
                        logger.info(f"已缓存 {cached} 个行业板块代码")
            else:
                df = ak.stock_board_industry_name_em()
                if df is not None and not df.empty:
                    cached = _em_api.cache_board_codes('industry', df)
                    logger.info(f"已缓存 {cached} 个行业板块代码")
            
            if df is None or df.empty:
                logger.warning("东财行业板块列表为空")
                return 0
            
            count = 0
            for _, row in df.iterrows():
                board_code = str(row.get('板块代码', row.get('代码', '')))
                board_name = str(row.get('板块名称', row.get('名称', '')))
                
                if not board_code or not board_name:
                    continue
                
                self._upsert_board(provider_id, board_code, board_name, 'industry')
                count += 1
            
            self.session.commit()
            logger.info(f"同步东财行业板块: {count} 个")
            return count
        except Exception as e:
            logger.error(f"同步东财行业板块失败: {e}")
            return 0
    
    def _sync_em_concept_boards_with_count(self, provider_id: int) -> int:
        """同步东财概念板块列表（返回数量）"""
        logger.info("获取东财概念板块列表...")
        try:
            # 优先使用代理直连 API
            proxy_mgr = get_proxy_manager()
            if proxy_mgr:
                try:
                    df = _em_api.fetch_board_list('concept')
                    logger.info(f"已通过代理获取并缓存 {len(_em_api._concept_code_map)} 个概念板块代码")
                except Exception as proxy_exc:
                    logger.warning(f"代理直连概念板块失败，回退 AKShare: {proxy_exc}")
                    df = ak.stock_board_concept_name_em()
                    if df is not None and not df.empty:
                        cached = _em_api.cache_board_codes('concept', df)
                        logger.info(f"已缓存 {cached} 个概念板块代码")
            else:
                df = ak.stock_board_concept_name_em()
                if df is not None and not df.empty:
                    cached = _em_api.cache_board_codes('concept', df)
                    logger.info(f"已缓存 {cached} 个概念板块代码")
            
            if df is None or df.empty:
                logger.warning("东财概念板块列表为空")
                return 0
            
            count = 0
            for _, row in df.iterrows():
                board_code = str(row.get('板块代码', row.get('代码', '')))
                board_name = str(row.get('板块名称', row.get('名称', '')))
                
                if not board_code or not board_name:
                    continue
                
                self._upsert_board(provider_id, board_code, board_name, 'concept')
                count += 1
            
            self.session.commit()
            logger.info(f"同步东财概念板块: {count} 个")
            return count
        except Exception as e:
            import traceback
            logger.error(f"同步东财概念板块失败: {e}")
            logger.error(f"详细错误: {traceback.format_exc()}")
            return 0
    
    def _sync_em_board_cons_with_metrics(self, provider_id: int, target_date: date, board_type: str, limit: int = None) -> tuple:
        """同步东财板块成分股（带运维指标）
        
        使用直连东财 API，避免 AKShare 内部重复请求板块列表
        
        Args:
            limit: 限制同步板块数量（测试用）
        
        Returns:
            tuple: (成分股数, 失败板块列表)
        """
        logger.info(f"获取东财{board_type}板块成分股（直连API）...")
        
        boards = self._get_boards(provider_id, board_type)
        boards, skipped_blacklist = self._split_boards_by_blacklist(boards)
        if skipped_blacklist:
            logger.info(
                f"{board_type} 黑名单跳过 {len(skipped_blacklist)} 个板块: {skipped_blacklist[:10]}"
            )
        
        # 限制数量（测试用）
        if limit and limit > 0:
            boards = boards[:limit]
            logger.info(f"限制同步前 {limit} 个板块（测试模式）")
        
        logger.info(f"共 {len(boards)} 个{board_type}板块需要同步成分股（黑名单跳过 {len(skipped_blacklist)}）")
        
        total_cons = 0
        failed_boards = []
        max_retries = 2
        
        # 使用 tqdm 进度条
        pbar = tqdm(boards, desc=f"东财{board_type}成分股", unit="板块", ncols=100)
        
        for board_id, board_name in pbar:
            success = False
            
            for attempt in range(max_retries):
                try:
                    # 使用直连 API（单次 HTTP 请求，不会重复获取板块列表）
                    df = _em_api.fetch_board_cons(board_name, board_type)
                    
                    if df is None or df.empty:
                        success = True
                        break
                    
                    cons_count = self._save_board_cons(board_id, target_date, df)
                    total_cons += cons_count
                    success = True
                    
                    # 更新进度条信息
                    proxy_mgr = get_proxy_manager()
                    proxy_info = f"IP#{proxy_mgr.get_stats()['total_ips_used']}" if proxy_mgr else ""
                    pbar.set_postfix({"成分股": total_cons, "失败": len(failed_boards), "代理": proxy_info})
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    # 失败时换 IP 重试
                    proxy_mgr = get_proxy_manager()
                    if proxy_mgr:
                        proxy_mgr.mark_failed()  # 立即换 IP
                    
                    if attempt < max_retries - 1:
                        wait_time = 1  # 换 IP 后只等 1 秒
                        pbar.set_postfix({"重试": f"{attempt+1}/{max_retries}", "换IP中": "..."})
                        time.sleep(wait_time)
                    else:
                        failed_boards.append(board_name)
                        if len(failed_boards) <= 5:
                            logger.warning(f"板块 {board_name} 失败: {error_msg[:60]}")
            
            # 正常请求间隔 + 随机抖动
            jitter = random.random() * 0.3
            time.sleep(self.delay + jitter)
            
            # 每50个提交一次
            if pbar.n > 0 and pbar.n % 50 == 0:
                self.session.commit()
        
        pbar.close()
        self.session.commit()
        logger.info(
            f"同步东财{board_type}板块成分股完成: success={len(boards)-len(failed_boards)}, "
            f"skip={len(skipped_blacklist)}, fail={len(failed_boards)}, cons={total_cons}"
        )
        
        return total_cons, failed_boards
    
    def _sync_em_board_cons_concurrent(self, provider_id: int, target_date: date, board_type: str, 
                                        limit: int = None, workers: int = 6, 
                                        ip_ttl: float = 45.0,
                                        req_delay_min: float = 1.0, req_delay_max: float = 2.0) -> tuple:
        """
        [终极版] 单队列 + 重试计数 + 统一错误处理 + 死磕到100%
        
        架构设计：
        - 单队列循环：任务结构 (retry_count, board_id, board_name)
        - 失败回炉：retry_count + 1，放回队列尾部
        - 超过 max_retry 才记为永久失败
        - 6 线程（利特尔定律算出的黄金分割点）
        - 2秒冷却（300% IP 供给冗余）
        """
        import queue
        
        MAX_RETRY = 20  # 单个任务最大重试次数
        
        logger.info(f"🚀 启动死磕模式: {workers}线程, TTL={ip_ttl}s, 最大重试={MAX_RETRY}次")
        
        # ============ 1. 任务装载 ============
        boards = self._get_boards(provider_id, board_type)
        boards, skipped_blacklist = self._split_boards_by_blacklist(boards)
        if skipped_blacklist:
            logger.info(
                f"{board_type} 黑名单跳过 {len(skipped_blacklist)} 个板块: {skipped_blacklist[:10]}"
            )
        if limit and limit > 0:
            boards = boards[:limit]
        
        total_tasks = len(boards)
        if total_tasks == 0:
            return 0, []
        
        # 任务队列：(retry_count, board_id, board_name)
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        
        seen = set()
        for b_id, b_name in boards:
            if b_id not in seen:
                seen.add(b_id)
                task_queue.put((0, b_id, b_name))  # 初始重试次数为 0
        
        logger.info(f"共 {total_tasks} 个{board_type}板块，目标: 100% 成功（黑名单跳过 {len(skipped_blacklist)}）")
        
        # ============ 2. 统一请求函数（集中处理所有错误） ============
        def fetch_board_members(session, board_name: str) -> dict:
            """
            统一的请求+校验+解析函数
            返回: {'ok': bool, 'data': list or None, 'error': str or None, 'error_type': str}
            """
            code_map = _em_api._industry_code_map if board_type == 'industry' else _em_api._concept_code_map
            
            # 错误类型分类
            if code_map is None:
                return {'ok': False, 'data': None, 'error': '代码映射表未初始化', 'error_type': 'init_error'}
            
            bk_code = code_map.get(board_name)
            if not bk_code:
                return {'ok': False, 'data': None, 'error': f'无板块代码: {board_name}', 'error_type': 'no_code'}
            
            try:
                all_records = []
                page = 1
                
                while True:
                    params = {
                        "pn": str(page), "pz": "100", "po": "1", "np": "1",
                        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                        "fltt": "2", "invt": "2", "fid": "f3",
                        "fs": f"b:{bk_code}+f:!50", "fields": "f12,f14"
                    }

                    resp = None
                    for page_retry in range(3):
                        try:
                            resp = session.get(
                                "https://push2.eastmoney.com/api/qt/clist/get",
                                params=params,
                                timeout=12,
                            )
                            resp.raise_for_status()
                            break
                        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                            if page_retry >= 2:
                                raise
                            time.sleep(0.8 + page_retry * 0.8 + random.random() * 0.4)
                        except requests.exceptions.HTTPError:
                            if page_retry >= 2:
                                raise
                            time.sleep(0.8 + page_retry * 0.8 + random.random() * 0.4)

                    if resp is None:
                        raise requests.exceptions.ConnectionError("empty response after page retries")
                    
                    # 安全解析 JSON
                    try:
                        j = resp.json()
                    except ValueError:
                        return {'ok': False, 'data': None, 'error': 'JSON解析失败', 'error_type': 'invalid_json'}
                    
                    data = j.get("data")
                    if not data:
                        return {'ok': False, 'data': None, 'error': '返回数据为空', 'error_type': 'empty_data'}
                    
                    diff = data.get("diff")
                    if not diff:
                        break  # 没有更多数据了
                    
                    for item in diff:
                        all_records.append({
                            "代码": item.get("f12", ""),
                            "名称": item.get("f14", "")
                        })
                    
                    total = data.get("total", 0)
                    if page * 100 >= total:
                        break
                    page += 1
                    time.sleep(random.uniform(0.08, 0.18))
                
                return {'ok': True, 'data': all_records, 'error': None, 'error_type': None}
                
            except requests.exceptions.Timeout:
                return {'ok': False, 'data': None, 'error': '请求超时', 'error_type': 'timeout'}
            except requests.exceptions.ConnectionError as e:
                return {'ok': False, 'data': None, 'error': f'连接错误: {str(e)[:30]}', 'error_type': 'connection'}
            except Exception as e:
                return {'ok': False, 'data': None, 'error': f'{str(e)[:40]}', 'error_type': 'unknown'}
        
        # ============ 3. Worker 定义 ============
        def worker_routine(worker_id: int):
            t_name = f"W{worker_id}"
            
            # 错峰启动
            time.sleep(random.uniform(0, 5))
            
            session = None
            proxy_start_time = 0
            current_ip = "无"
            
            proxy_mgr = get_proxy_manager()
            
            while True:
                # 1. 取任务
                try:
                    item = task_queue.get(timeout=5)
                except queue.Empty:
                    continue
                
                if item is None:  # 毒丸
                    task_queue.task_done()
                    break
                
                retry_count, board_id, board_name = item
                
                # 2. 请求前睡眠（Just-In-Time，不浪费 IP）
                time.sleep(random.uniform(req_delay_min, req_delay_max))
                
                # 3. IP 维护
                now = time.time()
                current_ttl = ip_ttl + random.uniform(-5, 5)
                is_expired = (session is None) or (now - proxy_start_time > current_ttl)
                
                if is_expired:
                    if session:
                        try: session.close()
                        except: pass
                        session = None
                    
                    # 顽强获取 IP
                    if proxy_mgr:
                        for p_retry in range(5):
                            if proxy_mgr.is_exhausted():
                                result_queue.put({'type': 'FATAL', 'msg': 'IP配额耗尽'})
                                task_queue.task_done()
                                return
                            
                            try:
                                proxies = proxy_mgr.get_proxy()
                                if proxies:
                                    session = requests.Session()
                                    session.proxies = proxies
                                    session.trust_env = False
                                    session.headers.update({
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                        "Connection": "keep-alive"
                                    })
                                    proxy_start_time = time.time()
                                    current_ip = proxies['http'].split('//')[1] if proxies else "无"
                                    break
                            except Exception:
                                pass
                            
                            # 动态等待：2s, 5s, 5s...
                            time.sleep(2.0 if p_retry == 0 else 5.0)
                    
                    # 无代理模式：直接建会话（仍遵守 req_delay 频控）
                    if session is None and proxy_mgr is None:
                        session = requests.Session()
                        session.trust_env = False
                        session.headers.update({
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Connection": "keep-alive"
                        })
                        proxy_start_time = time.time()
                        current_ip = "direct"

                    # 如果实在拿不到可用会话，任务回炉，线程休息
                    if session is None:
                        task_queue.put((retry_count, board_id, board_name))  # 原样放回
                        task_queue.task_done()
                        time.sleep(10)  # 休息久一点
                        continue
                
                # 4. 执行请求（使用统一函数）
                result = fetch_board_members(session, board_name)
                
                if result['ok']:
                    # 成功！
                    result_queue.put({
                        'type': 'SUCCESS',
                        'board_id': board_id,
                        'board_name': board_name,
                        'data': result['data'],
                        'ip': current_ip
                    })
                else:
                    # 失败处理
                    error_type = result['error_type']
                    
                    # 销毁可能坏掉的 session
                    if error_type in ('timeout', 'connection', 'invalid_json', 'unknown', 'empty_data'):
                        if session:
                            session.close()
                        session = None
                        
                        # 【核心修复】显式标记当前 IP 已失效，避免僵尸 IP 循环！
                        if proxy_mgr:
                            proxy_mgr.mark_failed()
                    
                    if retry_count >= MAX_RETRY:
                        # 彻底放弃
                        result_queue.put({
                            'type': 'FAIL_PERM',
                            'board_name': board_name,
                            'error': result['error'],
                            'error_type': error_type,
                            'retries': retry_count
                        })
                    else:
                        # 任务回炉
                        task_queue.put((retry_count + 1, board_id, board_name))
                        result_queue.put({
                            'type': 'RETRY',
                            'board_name': board_name,
                            'retry_count': retry_count + 1,
                            'error_type': error_type
                        })
                
                task_queue.task_done()
            
            if session:
                session.close()
        
        # ============ 4. 启动线程 ============
        threads = []
        for i in range(workers):
            t = threading.Thread(target=worker_routine, args=(i,), daemon=True)
            t.start()
            threads.append(t)
        
        # ============ 5. 主线程监控 ============
        success_count = 0
        perm_fail_count = 0
        total_cons = 0
        retry_stats = {}  # 统计各类错误
        perm_failed_boards = []
        
        pbar = tqdm(total=total_tasks, desc=f"东财{board_type}", unit="板块", ncols=100)
        
        while success_count + perm_fail_count < total_tasks:
            try:
                res = result_queue.get(timeout=2)
                
                if res['type'] == 'SUCCESS':
                    if res['data']:
                        df = pd.DataFrame(res['data'])
                        cons = self._save_board_cons(res['board_id'], target_date, df)
                        total_cons += cons
                    
                    success_count += 1
                    pbar.update(1)
                    
                    proxy_mgr = get_proxy_manager()
                    ip_used = proxy_mgr.get_stats()['total_ips_used'] if proxy_mgr else 0
                    pbar.set_postfix({"成功": success_count, "IP": ip_used, "重试中": task_queue.qsize()})
                    
                    if success_count % 50 == 0:
                        self.session.commit()
                
                elif res['type'] == 'FAIL_PERM':
                    perm_fail_count += 1
                    perm_failed_boards.append(res['board_name'])
                    pbar.update(1)
                    logger.error(f"❌ {res['board_name']} 彻底失败({res['retries']}次): {res['error']}")
                    
                    # 统计错误类型
                    et = res.get('error_type', 'unknown')
                    retry_stats[et] = retry_stats.get(et, 0) + 1
                
                elif res['type'] == 'FATAL':
                    logger.error(f"🚨 系统熔断: {res['msg']}")
                    break
                
                elif res['type'] == 'RETRY':
                    # 统计重试
                    et = res.get('error_type', 'unknown')
                    retry_stats[et] = retry_stats.get(et, 0) + 1
                    
            except queue.Empty:
                if not any(t.is_alive() for t in threads):
                    logger.warning("所有线程意外退出")
                    break
        
        pbar.close()
        
        # 清理
        for _ in threads:
            task_queue.put(None)
        for t in threads:
            t.join(timeout=2)
        
        self.session.commit()
        
        # 统计报告
        proxy_mgr = get_proxy_manager()
        ip_stats = proxy_mgr.get_stats() if proxy_mgr else {}
        
        logger.info("=" * 50)
        logger.info(f"🏁 {board_type} 同步完成:")
        logger.info(f"   成功: {success_count}/{total_tasks} ({100*success_count/total_tasks:.1f}%)")
        logger.info(f"   黑名单跳过: {len(skipped_blacklist)}")
        logger.info(f"   永久失败: {perm_fail_count}")
        logger.info(f"   成分股: {total_cons} 条")
        logger.info(f"   IP消耗: {ip_stats.get('total_ips_used', 0)}/{ip_stats.get('max_ips', 0)}")
        if retry_stats:
            logger.info(f"   错误分布: {retry_stats}")
        logger.info(
            f"   快照口径: success={success_count}, skip={len(skipped_blacklist)}, fail={perm_fail_count}"
        )
        logger.info("=" * 50)
        
        return total_cons, perm_failed_boards
    
    def _save_board_cons_with_session(self, session, board_id: int, target_date: date, df: pd.DataFrame) -> int:
        """使用指定会话保存板块成分股（线程安全）"""
        if df is None or df.empty:
            return 0
        
        # 先删除当天数据
        session.execute(text("""
            DELETE FROM ext_board_daily_snap 
            WHERE board_id = :board_id AND snap_date = :snap_date
        """), {"board_id": board_id, "snap_date": target_date})
        
        count = 0
        for _, row in df.iterrows():
            raw_code = str(row.get('代码', ''))
            stock_code = self._normalize_stock_code(raw_code)
            
            if not stock_code:
                continue
            
            if stock_code not in self.stock_codes:
                continue
            
            session.execute(text("""
                INSERT INTO ext_board_daily_snap (board_id, stock_code, snap_date, created_at)
                VALUES (:board_id, :stock_code, :snap_date, NOW())
            """), {
                "board_id": board_id,
                "stock_code": stock_code,
                "snap_date": target_date
            })
            count += 1
        
        return count
    
    def _sync_em_industry_boards(self, provider_id: int):
        """同步东财行业板块列表"""
        logger.info("获取东财行业板块列表...")
        try:
            df = ak.stock_board_industry_name_em()
            if df is None or df.empty:
                logger.warning("东财行业板块列表为空")
                return
            
            count = 0
            for _, row in df.iterrows():
                board_code = str(row.get('板块代码', row.get('代码', '')))
                board_name = str(row.get('板块名称', row.get('名称', '')))
                
                if not board_code or not board_name:
                    continue
                
                self._upsert_board(provider_id, board_code, board_name, 'industry')
                count += 1
            
            logger.info(f"同步东财行业板块: {count} 个")
        except Exception as e:
            logger.error(f"同步东财行业板块失败: {e}")
    
    def _sync_em_concept_boards(self, provider_id: int):
        """同步东财概念板块列表"""
        logger.info("获取东财概念板块列表...")
        try:
            df = ak.stock_board_concept_name_em()
            if df is None or df.empty:
                logger.warning("东财概念板块列表为空")
                return
            
            count = 0
            for _, row in df.iterrows():
                board_code = str(row.get('板块代码', row.get('代码', '')))
                board_name = str(row.get('板块名称', row.get('名称', '')))
                
                if not board_code or not board_name:
                    continue
                
                self._upsert_board(provider_id, board_code, board_name, 'concept')
                count += 1
            
            logger.info(f"同步东财概念板块: {count} 个")
        except Exception as e:
            logger.error(f"同步东财概念板块失败: {e}")
    
    def _sync_em_board_cons(self, provider_id: int, target_date: date, board_type: str):
        """同步东财板块成分股"""
        logger.info(f"获取东财{board_type}板块成分股...")
        
        # 获取该类型的所有板块
        boards = self._get_boards(provider_id, board_type)
        boards, skipped_blacklist = self._split_boards_by_blacklist(boards)
        logger.info(f"共 {len(boards)} 个{board_type}板块需要同步成分股（黑名单跳过 {len(skipped_blacklist)}）")
        
        total_cons = 0
        failed_boards = []
        
        for i, (board_id, board_name) in enumerate(boards):
            try:
                if board_type == 'industry':
                    df = ak.stock_board_industry_cons_em(symbol=board_name)
                else:
                    df = ak.stock_board_concept_cons_em(symbol=board_name)
                
                if df is None or df.empty:
                    continue
                
                cons_count = self._save_board_cons(board_id, target_date, df)
                total_cons += cons_count
                
                if (i + 1) % 50 == 0:
                    logger.info(f"进度: {i+1}/{len(boards)}, 已同步 {total_cons} 条成分股")
                    self.session.commit()
                
                # 避免请求过快
                time.sleep(0.1)
                
            except Exception as e:
                failed_boards.append(board_name)
                if "请求" in str(e) or "频繁" in str(e):
                    logger.warning(f"请求频繁，暂停5秒...")
                    time.sleep(5)
        
        self.session.commit()
        logger.info(f"同步东财{board_type}板块成分股完成: {total_cons} 条")
        if failed_boards:
            logger.warning(f"失败板块 ({len(failed_boards)}): {failed_boards[:10]}...")
    
    # ==================== 同花顺 (THS) ====================
    
    def sync_ths_boards(self, target_date: date, skip_cons: bool = False):
        """同步同花顺板块数据"""
        provider_id = self._provider_cache.get('ths')
        if not provider_id:
            logger.error("未找到 ths 数据源配置")
            return
        
        logger.info("=" * 60)
        logger.info("开始同步同花顺板块数据...")
        
        # 1. 同步概念板块
        self._sync_ths_concept_boards(provider_id)
        
        # 2. 同步成分股
        if not skip_cons:
            self._sync_ths_board_cons(provider_id, target_date)
        
        self.session.commit()
        logger.info("同花顺板块数据同步完成")
    
    def sync_ths_boards_with_metrics(self, target_date: date, skip_cons: bool = False) -> tuple:
        """同步同花顺板块数据（带运维指标）
        
        Returns:
            tuple: (板块数, 成分股数, 失败板块列表)
        """
        provider_id = self._provider_cache.get('ths')
        if not provider_id:
            logger.error("未找到 ths 数据源配置")
            return 0, 0, []
        
        logger.info("=" * 60)
        logger.info("开始同步同花顺板块数据...")
        
        total_boards = 0
        total_cons = 0
        all_failed = []
        
        # 1. 同步概念板块
        board_count = self._sync_ths_concept_boards_with_count(provider_id)
        total_boards = board_count
        
        # 2. 同步成分股
        if not skip_cons:
            cons, failed = self._sync_ths_board_cons_with_metrics(provider_id, target_date)
            total_cons = cons
            all_failed = failed
        
        self.session.commit()
        logger.info("同花顺板块数据同步完成")
        
        return total_boards, total_cons, all_failed
    
    def _sync_ths_concept_boards_with_count(self, provider_id: int) -> int:
        """同步同花顺概念板块列表（返回数量）"""
        logger.info("获取同花顺概念板块列表...")
        try:
            df = ak.stock_board_concept_name_ths()
            if df is None or df.empty:
                logger.warning("同花顺概念板块列表为空")
                return 0
            
            logger.info(f"同花顺 API 返回列名: {df.columns.tolist()}")
            
            count = 0
            for _, row in df.iterrows():
                # 同花顺返回的列名是 'name' 和 'code'
                board_code = str(row.get('code', row.get('代码', row.get('板块代码', f'THS_{count}'))))
                board_name = str(row.get('name', row.get('概念名称', row.get('名称', ''))))
                
                if not board_name:
                    continue
                
                self._upsert_board(provider_id, board_code, board_name, 'concept')
                count += 1
            
            self.session.commit()
            logger.info(f"同步同花顺概念板块: {count} 个")
            return count
        except Exception as e:
            logger.error(f"同步同花顺概念板块失败: {e}")
            return 0
    
    def _sync_ths_board_cons_with_metrics(self, provider_id: int, target_date: date) -> tuple:
        """同步同花顺板块成分股（使用问财 API）
        
        Returns:
            tuple: (成分股数, 失败板块列表)
        """
        logger.info("获取同花顺板块成分股（使用问财 API）...")
        
        boards = self._get_boards(provider_id, 'concept')
        
        # 支持 limit 参数
        limit = getattr(self, '_limit', None)
        if limit and limit > 0:
            boards = boards[:limit]
            logger.info(f"限制同步前 {limit} 个板块（测试模式）")
        
        logger.info(f"共 {len(boards)} 个同花顺板块需要同步成分股")
        
        total_cons = 0
        failed_boards = []
        max_retries = 2
        
        # 使用 tqdm 进度条
        pbar = tqdm(boards, desc="同花顺成分股(问财)", unit="板块", ncols=100)
        
        for board_id, board_name in pbar:
            success = False
            
            for attempt in range(max_retries):
                try:
                    # 使用问财 API 获取成分股
                    query = f"{board_name}概念成分股"
                    df = pywencai.get(question=query, loop=True)
                    
                    if df is None or df.empty:
                        success = True
                        break
                    
                    # 问财返回的列名不同，需要转换
                    # 问财的股票代码格式: 601933.SH -> 需要提取纯数字
                    if '股票代码' in df.columns:
                        df['代码'] = df['股票代码'].astype(str).str.extract(r'(\d{6})')[0]
                    elif 'code' in df.columns:
                        df['代码'] = df['code'].astype(str).str.zfill(6)
                    
                    if '股票简称' in df.columns:
                        df['名称'] = df['股票简称']
                    
                    cons_count = self._save_board_cons(board_id, target_date, df)
                    total_cons += cons_count
                    success = True
                    
                    pbar.set_postfix({"成分股": total_cons, "失败": len(failed_boards)})
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    if attempt < max_retries - 1:
                        wait_time = 3  # 问财 API 不需要太长等待
                        pbar.set_postfix({"重试": f"{attempt+1}/{max_retries}", "等待": f"{wait_time}s"})
                        time.sleep(wait_time)
                    else:
                        failed_boards.append(board_name)
                        if len(failed_boards) <= 5:
                            logger.warning(f"板块 {board_name} 失败: {error_msg[:50]}")
            
            # 问财 API 延迟（不需要太长）
            jitter = random.random() * 0.5
            time.sleep(self.delay + jitter)
            
            # 每50个提交一次
            if pbar.n % 50 == 0:
                self.session.commit()
        
        pbar.close()
        self.session.commit()
        logger.info(f"同步同花顺板块成分股完成: {total_cons} 条, 失败 {len(failed_boards)} 个")
        
        return total_cons, failed_boards
    
    def _sync_ths_concept_boards(self, provider_id: int):
        """同步同花顺概念板块列表"""
        logger.info("获取同花顺概念板块列表...")
        try:
            df = ak.stock_board_concept_name_ths()
            if df is None or df.empty:
                logger.warning("同花顺概念板块列表为空")
                return
            
            count = 0
            for _, row in df.iterrows():
                # 同花顺返回的列名是 'name' 和 'code'
                board_code = str(row.get('code', row.get('代码', f'THS_{count}')))
                board_name = str(row.get('name', row.get('概念名称', '')))
                
                if not board_name:
                    continue
                
                self._upsert_board(provider_id, board_code, board_name, 'concept')
                count += 1
            
            logger.info(f"同步同花顺概念板块: {count} 个")
        except Exception as e:
            logger.error(f"同步同花顺概念板块失败: {e}")
    
    def _sync_ths_board_cons(self, provider_id: int, target_date: date):
        """同步同花顺板块成分股"""
        logger.info("获取同花顺板块成分股...")
        
        boards = self._get_boards(provider_id, 'concept')
        logger.info(f"共 {len(boards)} 个同花顺板块需要同步成分股")
        
        total_cons = 0
        failed_boards = []
        
        for i, (board_id, board_name) in enumerate(boards):
            try:
                df = ak.stock_board_concept_cons_ths(symbol=board_name)
                
                if df is None or df.empty:
                    continue
                
                cons_count = self._save_board_cons(board_id, target_date, df)
                total_cons += cons_count
                
                if (i + 1) % 50 == 0:
                    logger.info(f"进度: {i+1}/{len(boards)}, 已同步 {total_cons} 条成分股")
                    self.session.commit()
                
                time.sleep(0.2)  # 同花顺限制更严格
                
            except Exception as e:
                failed_boards.append(board_name)
                if "请求" in str(e) or "频繁" in str(e) or "限制" in str(e):
                    logger.warning(f"请求频繁，暂停10秒...")
                    time.sleep(10)
        
        self.session.commit()
        logger.info(f"同步同花顺板块成分股完成: {total_cons} 条")
        if failed_boards:
            logger.warning(f"失败板块 ({len(failed_boards)}): {failed_boards[:10]}...")
    
    # ==================== 通用方法 ====================
    
    def _upsert_board(self, provider_id: int, board_code: str, board_name: str, board_type: str):
        """插入或更新板块"""
        sql = text("""
            INSERT INTO ext_board_list (provider_id, board_code, board_name, board_type, updated_at)
            VALUES (:provider_id, :board_code, :board_name, :board_type, NOW())
            ON CONFLICT (provider_id, board_code) 
            DO UPDATE SET 
                board_name = EXCLUDED.board_name,
                board_type = EXCLUDED.board_type,
                updated_at = NOW()
        """)
        self.session.execute(sql, {
            'provider_id': provider_id,
            'board_code': board_code,
            'board_name': board_name,
            'board_type': board_type
        })
    
    def _get_boards(self, provider_id: int, board_type: str) -> List[tuple]:
        """获取指定类型的板块列表"""
        sql = text("""
            SELECT id, board_name FROM ext_board_list 
            WHERE provider_id = :provider_id AND board_type = :board_type AND is_active = true
        """)
        result = self.session.execute(sql, {'provider_id': provider_id, 'board_type': board_type})
        return [(row.id, row.board_name) for row in result]
    
    def _save_board_cons(self, board_id: int, target_date: date, df: pd.DataFrame) -> int:
        """保存板块成分股"""
        count = 0
        
        # 尝试多种列名
        code_col = None
        for col in ['代码', '股票代码', 'code']:
            if col in df.columns:
                code_col = col
                break
        
        if not code_col:
            return 0
        
        for _, row in df.iterrows():
            raw_code = str(row[code_col])
            stock_code = self.normalize_stock_code(raw_code)
            
            if not stock_code or stock_code not in self._stock_codes:
                continue
            
            try:
                sql = text("""
                    INSERT INTO ext_board_daily_snap (stock_code, board_id, date)
                    VALUES (:stock_code, :board_id, :date)
                    ON CONFLICT (stock_code, board_id, date) DO NOTHING
                """)
                self.session.execute(sql, {
                    'stock_code': stock_code,
                    'board_id': board_id,
                    'date': target_date
                })
                count += 1
            except Exception as e:
                # 跳过外键约束错误（股票不存在）
                pass
        
        return count
    
    def update_board_stock_count(self):
        """更新板块成分股数量"""
        logger.info("更新板块成分股数量...")
        sql = text("""
            UPDATE ext_board_list b
            SET stock_count = (
                SELECT COUNT(DISTINCT stock_code) 
                FROM ext_board_daily_snap s 
                WHERE s.board_id = b.id
            )
        """)
        self.session.execute(sql)
        self.session.commit()
        logger.info("板块成分股数量更新完成")
    
    def auto_map_local_sectors(self):
        """自动映射外部板块到本地 sectors"""
        logger.info("自动映射外部板块到本地 sectors...")
        
        # 精确匹配
        sql = text("""
            INSERT INTO ext_board_local_map (ext_board_id, local_sector_id, match_type, confidence)
            SELECT b.id, s.id, 'auto', 100.00
            FROM ext_board_list b
            JOIN ext_providers p ON p.id = b.provider_id AND p.code = 'em'
            JOIN sectors s ON s.sector_name = b.board_name
            ON CONFLICT DO NOTHING
        """)
        result = self.session.execute(sql)
        self.session.commit()
        
        # 统计映射数量
        count_sql = text("SELECT COUNT(*) FROM ext_board_local_map")
        count = self.session.execute(count_sql).scalar()
        logger.info(f"自动映射完成，共 {count} 条映射关系")
    
    def close(self):
        """关闭数据库连接"""
        self.session.close()
        self.engine.dispose()


def main():
    parser = argparse.ArgumentParser(description='同步外部板块数据')
    parser.add_argument('--date', type=str, help='目标日期 (YYYY-MM-DD)，默认今天')
    parser.add_argument('--provider', type=str, choices=['em', 'ths', 'all'], default='all',
                        help='数据源: em(东财), ths(同花顺), all(全部)')
    parser.add_argument('--skip-cons', action='store_true', help='跳过成分股同步')
    parser.add_argument('--skip-map', action='store_true', help='跳过自动映射')
    parser.add_argument('--force', action='store_true', help='强制同步（忽略幂等检查）')
    parser.add_argument('--db-url', type=str, help='数据库连接URL (覆盖环境变量)')
    parser.add_argument('--delay', type=float, default=1.5, help='请求间隔秒数 (默认1.5秒，被封禁后建议3-5秒)')
    parser.add_argument('--proxy', action='store_true', help='启用91HTTP隧道代理')
    parser.add_argument('--proxy-trade-no', type=str, help='91HTTP业务编号')
    parser.add_argument('--proxy-secret', type=str, help='91HTTP密钥')
    parser.add_argument('--board-type', type=str, choices=['industry', 'concept', 'all'], default='all',
                        help='板块类型: industry(行业), concept(概念), all(全部)')
    parser.add_argument('--limit', type=int, help='限制同步板块数量（测试用）')
    
    # 并发模式参数 (Manager-Worker 架构)
    parser.add_argument('--concurrent', action='store_true', help='启用并发模式（Manager-Worker 架构）')
    parser.add_argument('--workers', type=int, default=6, help='并发线程数 (默认6)')
    parser.add_argument('--max-ips', type=int, default=200, help='最大代理IP数量 (默认200，防止打穿号池)')
    parser.add_argument('--ip-ttl', type=float, default=50.0, help='单个IP复用时间秒数 (默认50，留10秒缓冲)')
    parser.add_argument('--req-delay-min', type=float, default=1.0, help='请求间最小延迟秒数 (默认1)')
    parser.add_argument('--req-delay-max', type=float, default=3.0, help='请求间最大延迟秒数 (默认3)')
    
    args = parser.parse_args()

    # 频控保护：避免误设过高并发或过低延迟触发风控
    if args.workers <= 0:
        logger.warning(f"workers={args.workers} 非法，回退为 6")
        args.workers = 6

    if args.req_delay_min < 0.6:
        logger.warning(f"req-delay-min={args.req_delay_min} 过小，回退为 0.6")
        args.req_delay_min = 0.6

    if args.req_delay_max < args.req_delay_min:
        logger.warning(
            f"req-delay-max({args.req_delay_max}) < req-delay-min({args.req_delay_min})，自动对齐"
        )
        args.req_delay_max = args.req_delay_min
    
    # 初始化代理
    if args.proxy:
        proxy_mgr = ProxyManager(
            trade_no=args.proxy_trade_no,
            secret=args.proxy_secret,
            max_ips=args.max_ips
        )
        set_proxy_manager(proxy_mgr)
        logger.info(f"已启用91HTTP隧道代理 (IP上限: {args.max_ips})")
    
    # 数据库 URL
    db_url = args.db_url or DATABASE_URL
    logger.info(f"数据库: {db_url.split('@')[-1] if '@' in db_url else db_url}")  # 隐藏密码
    
    # 解析日期
    if args.date:
        requested_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        requested_date = date.today()

    trade_date = None
    try:
        _cal_engine = create_engine(db_url)
        trade_date = find_latest_trade_date(_cal_engine, requested_date)
    except Exception as e:
        logger.warning(f"⚠️ 交易日寻址失败，使用原始日期 {requested_date}: {e}")

    if trade_date and trade_date != requested_date:
        logger.info(f"📅 {requested_date} 非交易日/无数据，使用最近交易日 {trade_date} 作为同步日期")
        target_date = trade_date
    else:
        target_date = requested_date
    
    date_str = target_date.isoformat()
    
    logger.info("=" * 60)
    logger.info(f"外部板块数据同步 v1.1.0")
    logger.info("=" * 60)
    logger.info(f"目标日期: {target_date}")
    logger.info(f"数据源: {args.provider}")
    logger.info(f"跳过成分股: {args.skip_cons}")
    logger.info(f"强制同步: {args.force}")
    
    # 状态管理器
    state_manager = ExtBoardStateManager()
    
    # 幂等检查（按 provider 分别检查）
    providers_to_sync = []
    if args.provider in ['em', 'all']:
        if args.force or not state_manager.is_synced_today(date_str, 'em'):
            providers_to_sync.append('em')
        else:
            logger.info(f"⏭️ 东财(em) {date_str} 已同步成功，跳过")
    
    if args.provider in ['ths', 'all']:
        if args.force or not state_manager.is_synced_today(date_str, 'ths'):
            providers_to_sync.append('ths')
        else:
            logger.info(f"⏭️ 同花顺(ths) {date_str} 已同步成功，跳过")
    
    if not providers_to_sync:
        logger.info("所有数据源都已同步，无需重复执行（使用 --force 强制重新同步）")
        return
    
    logger.info(f"待同步数据源: {providers_to_sync}")
    
    # 开始同步（不覆盖已有 provider 数据）
    state_manager.start_sync(date_str)
    
    syncer = ExtBoardSyncer(db_url, delay=args.delay)
    syncer._board_type = args.board_type  # 板块类型过滤
    syncer._limit = args.limit  # 数量限制
    
    # 并发模式参数
    syncer._concurrent = args.concurrent
    syncer._workers = args.workers
    syncer._ip_ttl = args.ip_ttl
    syncer._req_delay_min = args.req_delay_min
    syncer._req_delay_max = args.req_delay_max
    
    if args.concurrent:
        logger.info(f"🚀 并发模式 (Manager-Worker): {args.workers}线程, IP复用{args.ip_ttl}秒, 请求间隔{args.req_delay_min}-{args.req_delay_max}秒, IP上限{args.max_ips}")
    else:
        logger.info(f"请求间隔: {args.delay}秒 (同花顺: {args.delay * 1.5}秒)")
    
    if args.board_type != 'all':
        logger.info(f"板块类型: {args.board_type}")
    if args.limit:
        logger.info(f"数量限制: {args.limit} 个板块")
    
    # 运维数据
    metrics = {
        "total_boards": 0,
        "total_cons": 0,
        "matched_stocks": 0,
        "unmatched_stocks": 0,
        "api_success_rate": 0,
        "providers": {}
    }
    
    try:
        total_start = time.time()
        
        # 同步东方财富（只在需要时执行）
        if 'em' in providers_to_sync:
            em_start = time.time()
            em_boards, em_cons, em_failed = syncer.sync_em_boards_with_metrics(
                target_date, skip_cons=args.skip_cons
            )
            em_duration = time.time() - em_start
            
            metrics["providers"]["em"] = {
                "board_count": em_boards,
                "cons_count": em_cons,
                "duration_seconds": round(em_duration, 2),
                "failed_count": len(em_failed)
            }
            metrics["total_boards"] += em_boards
            metrics["total_cons"] += em_cons
            
            state_manager.update_provider_status(
                date_str, "em", em_boards, em_cons,
                "success" if len(em_failed) == 0 else "partial",
                em_duration, em_failed
            )
            
            logger.info(f"📊 东财同步完成: {em_boards} 板块, {em_cons} 成分股, 耗时 {em_duration:.1f}秒")
        
        # 同步同花顺（只在需要时执行）
        if 'ths' in providers_to_sync:
            ths_start = time.time()
            ths_boards, ths_cons, ths_failed = syncer.sync_ths_boards_with_metrics(
                target_date, skip_cons=args.skip_cons
            )
            ths_duration = time.time() - ths_start
            
            metrics["providers"]["ths"] = {
                "board_count": ths_boards,
                "cons_count": ths_cons,
                "duration_seconds": round(ths_duration, 2),
                "failed_count": len(ths_failed)
            }
            metrics["total_boards"] += ths_boards
            metrics["total_cons"] += ths_cons
            
            state_manager.update_provider_status(
                date_str, "ths", ths_boards, ths_cons,
                "success" if len(ths_failed) == 0 else "partial",
                ths_duration, ths_failed
            )
            
            logger.info(f"📊 同花顺同步完成: {ths_boards} 板块, {ths_cons} 成分股, 耗时 {ths_duration:.1f}秒")
        
        # 更新统计
        syncer.update_board_stock_count()
        
        # 自动映射
        if not args.skip_map:
            syncer.auto_map_local_sectors()
        
        total_duration = time.time() - total_start
        metrics["total_duration_seconds"] = round(total_duration, 2)
        
        # 标记成功
        state_manager.mark_success(date_str, metrics)
        
        logger.info("=" * 60)
        logger.info("✅ 全部同步完成！")
        logger.info("=" * 60)
        logger.info(f"📈 运维数据汇总:")
        logger.info(f"   总板块数: {metrics['total_boards']}")
        logger.info(f"   总成分股记录: {metrics['total_cons']}")
        logger.info(f"   总耗时: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)")
        for provider, pdata in metrics["providers"].items():
            logger.info(f"   {provider}: {pdata['board_count']} 板块, {pdata['cons_count']} 成分股, "
                       f"耗时 {pdata['duration_seconds']:.1f}秒, 失败 {pdata['failed_count']} 个")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("用户中断")
        state_manager.mark_failed(date_str, "用户中断")
    except Exception as e:
        logger.error(f"同步失败: {e}")
        state_manager.mark_failed(date_str, str(e))
        raise
    finally:
        syncer.close()


if __name__ == '__main__':
    main()
