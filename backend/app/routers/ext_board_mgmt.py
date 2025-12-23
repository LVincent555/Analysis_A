"""
外部板块同步管理 API
用于管理员手动触发外部板块数据同步
"""
import asyncio
import locale
import subprocess
import sys
import json
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin/ext-boards", tags=["外部板块管理"])

# 状态文件路径 (backend/app/routers/ → stock_analysis_app/ = 4个parent)
STATE_FILE = Path(__file__).parent.parent.parent.parent / "data" / "ext_board_sync_state.json"

# 同步任务状态（内存中）
_sync_task_status = {
    "is_syncing": False,
    "task_id": None,
    "process": None,
    "task": None,
    "cancel_requested": False,
    "start_time": None,
    "provider": None,
    "logs": []
}

# 板块热度计算任务状态（内存中）
_heat_task_status = {
    "is_running": False,
    "task_id": None,
    "process": None,
    "cancel_requested": False,
    "start_time": None,
    "logs": []
}


# ========== Pydantic Models ==========

class SyncRequest(BaseModel):
    """同步请求"""
    provider: str = "all"  # em, ths, all
    force: bool = False    # 强制同步（忽略幂等）
    use_proxy: bool = True # 使用代理
    date: Optional[str] = None
    board_type: str = "all"
    delay: float = 1.0
    concurrent: bool = False
    workers: int = 10
    max_ips: int = 200
    ip_ttl: float = 50.0
    req_delay_min: float = 1.0
    req_delay_max: float = 3.0
    limit: Optional[int] = None
    skip_cons: bool = False
    skip_map: bool = False


class HeatCalcRequest(BaseModel):
    """板块热度计算请求"""
    date: Optional[str] = None  # 指定日期 (YYYY-MM-DD)
    calc_all: bool = False      # 计算所有可用日期
    force: bool = False         # 强制重算（覆盖已有数据）
    allow_fallback: bool = True # 允许借用最新快照

class SyncHistoryRequest(BaseModel):
    """历史补录请求"""
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    provider: str = "all"

class SyncStatusResponse(BaseModel):
    """同步状态响应"""
    is_syncing: bool
    task_id: Optional[str]
    provider: Optional[str]
    start_time: Optional[str]
    logs: List[str]
    progress: Optional[Dict[str, Any]]

class SyncHistoryItem(BaseModel):
    """同步历史记录"""
    date: str
    status: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[int]
    providers: Dict[str, Any]
    error: Optional[str]

class StatsResponse(BaseModel):
    """运维统计响应"""
    total_boards: int
    total_cons_records: int
    providers: List[Dict[str, Any]]
    last_sync: Optional[Dict[str, Any]]
    mapping_count: int


# ========== Helper Functions ==========

def load_state() -> Dict[str, Any]:
    """加载状态文件"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding='utf-8'))
        except:
            pass
    return {"syncs": {}, "config": {}}

def get_sync_script_path() -> Path:
    """获取同步脚本路径"""
    return Path(__file__).parent.parent.parent / "scripts" / "sync_ext_boards.py"


_sync_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sync_task")


def _run_sync_blocking(cmd: list, cwd: str):
    """在线程中阻塞执行同步脚本（Windows 兼容）"""
    global _sync_task_status
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        _sync_task_status["process"] = process
        
        if _sync_task_status.get("cancel_requested"):
            process.terminate()
            return
        
        encoding = locale.getpreferredencoding(False) or 'utf-8'
        
        for line in iter(process.stdout.readline, b''):
            if _sync_task_status.get("cancel_requested"):
                process.terminate()
                _sync_task_status["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 用户取消同步任务"
                )
                break
            
            try:
                decoded_line = line.decode('utf-8').strip()
            except UnicodeDecodeError:
                decoded_line = line.decode(encoding, errors='replace').strip()
            
            if decoded_line:
                if len(_sync_task_status["logs"]) > 100:
                    _sync_task_status["logs"] = _sync_task_status["logs"][-50:]
                _sync_task_status["logs"].append(decoded_line)
        
        process.wait()
        exit_code = process.returncode
        
        if not _sync_task_status.get("cancel_requested"):
            if exit_code == 0:
                _sync_task_status["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 同步完成，退出码: {exit_code}"
                )
            else:
                _sync_task_status["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 同步失败，退出码: {exit_code}"
                )
    
    except Exception as e:
        _sync_task_status["logs"].append(f"[ERROR] 同步失败: {str(e)}")
        tb = traceback.format_exc()
        if tb:
            tb_lines = tb.strip().splitlines()[-20:]
            _sync_task_status["logs"].append("\n".join(tb_lines))
    
    finally:
        _sync_task_status["is_syncing"] = False
        _sync_task_status["process"] = None
        _sync_task_status["cancel_requested"] = False


async def run_sync_task(request: SyncRequest):
    """后台执行同步任务（Windows 兼容：使用线程池 + subprocess.Popen）"""
    global _sync_task_status
    
    script_path = get_sync_script_path()

    if not script_path.exists():
        _sync_task_status["logs"] = [
            f"[{datetime.now().strftime('%H:%M:%S')}] 启动同步任务...",
            f"[ERROR] 同步脚本不存在: {str(script_path)}"
        ]
        _sync_task_status["is_syncing"] = False
        return

    cmd = [sys.executable, "-u", str(script_path)]

    if request.date:
        cmd.extend(["--date", request.date])

    cmd.extend(["--provider", request.provider])

    if request.skip_cons:
        cmd.append("--skip-cons")
    if request.skip_map:
        cmd.append("--skip-map")
    if request.force:
        cmd.append("--force")
    if request.use_proxy:
        cmd.append("--proxy")

    if request.board_type:
        cmd.extend(["--board-type", request.board_type])
    if request.limit is not None:
        cmd.extend(["--limit", str(request.limit)])

    if request.concurrent:
        cmd.append("--concurrent")
        if request.workers is not None:
            cmd.extend(["--workers", str(request.workers)])
        if request.max_ips is not None:
            cmd.extend(["--max-ips", str(request.max_ips)])
        if request.ip_ttl is not None:
            cmd.extend(["--ip-ttl", str(request.ip_ttl)])
        if request.req_delay_min is not None:
            cmd.extend(["--req-delay-min", str(request.req_delay_min)])
        if request.req_delay_max is not None:
            cmd.extend(["--req-delay-max", str(request.req_delay_max)])

    if request.delay is not None:
        cmd.extend(["--delay", str(request.delay)])

    _sync_task_status["logs"] = [f"[{datetime.now().strftime('%H:%M:%S')}] 启动同步任务..."]
    _sync_task_status["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 命令: {' '.join(cmd)}")

    if _sync_task_status.get("cancel_requested"):
        _sync_task_status["logs"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 同步任务已取消（启动前）"
        )
        _sync_task_status["is_syncing"] = False
        return

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_sync_executor, _run_sync_blocking, cmd, str(script_path.parent.parent))


# ========== 板块热度计算任务 ==========

_heat_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="heat_task")


def get_heat_script_path() -> Path:
    """获取热度计算脚本路径"""
    return Path(__file__).parent.parent.parent / "scripts" / "task_board_heat.py"


def _run_heat_blocking(cmd: list, cwd: str):
    """在线程中阻塞执行热度计算脚本（Windows 兼容）"""
    global _heat_task_status
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        _heat_task_status["process"] = process
        
        if _heat_task_status.get("cancel_requested"):
            process.terminate()
            return
        
        encoding = locale.getpreferredencoding(False) or 'utf-8'
        
        for line in iter(process.stdout.readline, b''):
            if _heat_task_status.get("cancel_requested"):
                process.terminate()
                _heat_task_status["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 用户取消热度计算任务"
                )
                break
            
            try:
                decoded_line = line.decode('utf-8').strip()
            except UnicodeDecodeError:
                decoded_line = line.decode(encoding, errors='replace').strip()
            
            if decoded_line:
                if len(_heat_task_status["logs"]) > 100:
                    _heat_task_status["logs"] = _heat_task_status["logs"][-50:]
                _heat_task_status["logs"].append(decoded_line)
        
        process.wait()
        exit_code = process.returncode
        
        if not _heat_task_status.get("cancel_requested"):
            if exit_code == 0:
                _heat_task_status["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 热度计算完成，退出码: {exit_code}"
                )
            else:
                _heat_task_status["logs"].append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 热度计算失败，退出码: {exit_code}"
                )
    
    except Exception as e:
        _heat_task_status["logs"].append(f"[ERROR] 热度计算失败: {str(e)}")
        tb = traceback.format_exc()
        if tb:
            tb_lines = tb.strip().splitlines()[-20:]
            _heat_task_status["logs"].append("\n".join(tb_lines))
    
    finally:
        _heat_task_status["is_running"] = False
        _heat_task_status["process"] = None
        _heat_task_status["cancel_requested"] = False


async def run_heat_task(request: HeatCalcRequest):
    """后台执行热度计算任务（Windows 兼容：使用线程池 + subprocess.Popen）"""
    global _heat_task_status
    
    script_path = get_heat_script_path()

    if not script_path.exists():
        _heat_task_status["logs"] = [
            f"[{datetime.now().strftime('%H:%M:%S')}] 启动热度计算任务...",
            f"[ERROR] 热度计算脚本不存在: {str(script_path)}"
        ]
        _heat_task_status["is_running"] = False
        return

    cmd = [sys.executable, "-u", str(script_path)]

    if request.date:
        cmd.extend(["--date", request.date])
    if request.calc_all:
        cmd.append("--all")
    if request.force:
        cmd.append("--force")
    if request.allow_fallback:
        cmd.append("--allow-latest-snap-fallback")

    _heat_task_status["logs"] = [f"[{datetime.now().strftime('%H:%M:%S')}] 启动热度计算任务..."]
    _heat_task_status["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] 命令: {' '.join(cmd)}")

    if _heat_task_status.get("cancel_requested"):
        _heat_task_status["logs"].append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 热度计算任务已取消（启动前）"
        )
        _heat_task_status["is_running"] = False
        return

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_heat_executor, _run_heat_blocking, cmd, str(script_path.parent.parent))


# ========== API Endpoints ==========

@router.post("/sync", summary="触发今日同步")
async def trigger_sync(
    request: SyncRequest,
    current_user = Depends(require_admin)
):
    """
    触发外部板块数据同步
    - 后台异步执行
    - 返回任务ID供轮询进度
    """
    global _sync_task_status
    
    if _sync_task_status["is_syncing"]:
        raise HTTPException(status_code=409, detail="同步任务正在执行中")
    
    task_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    _sync_task_status = {
        "is_syncing": True,
        "task_id": task_id,
        "process": None,
        "task": None,
        "cancel_requested": False,
        "start_time": datetime.now().isoformat(),
        "provider": request.provider,
        "logs": []
    }
    
    _sync_task_status["task"] = asyncio.create_task(
        run_sync_task(
            request
        )
    )
    
    return {
        "success": True,
        "message": "同步任务已启动",
        "task_id": task_id
    }


@router.get("/sync-status", response_model=SyncStatusResponse, summary="获取同步状态")
async def get_sync_status(current_user = Depends(require_admin)):
    """
    获取当前同步任务状态
    - 轮询此接口获取进度
    """
    return SyncStatusResponse(
        is_syncing=_sync_task_status["is_syncing"],
        task_id=_sync_task_status["task_id"],
        provider=_sync_task_status["provider"],
        start_time=_sync_task_status["start_time"],
        logs=_sync_task_status["logs"][-50:],  # 只返回最新50条
        progress=None  # TODO: 解析进度
    )


@router.post("/sync/cancel", summary="取消同步任务")
async def cancel_sync(current_user = Depends(require_admin)):
    """取消正在执行的同步任务"""
    global _sync_task_status
    
    if not _sync_task_status["is_syncing"]:
        raise HTTPException(status_code=400, detail="没有正在执行的同步任务")

    _sync_task_status["cancel_requested"] = True
    
    if _sync_task_status["process"]:
        try:
            _sync_task_status["process"].terminate()
            _sync_task_status["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 用户取消同步任务"
            )
        except:
            pass
    
    return {"success": True, "message": "已取消同步任务"}


# ========== 板块热度计算 API ==========

@router.post("/heat/calc", summary="触发板块热度计算")
async def trigger_heat_calc(
    request: HeatCalcRequest,
    current_user = Depends(require_admin)
):
    """
    触发板块热度计算 ETL
    - 后台异步执行
    - 返回任务ID供轮询进度
    """
    global _heat_task_status
    
    if _heat_task_status["is_running"]:
        raise HTTPException(status_code=409, detail="热度计算任务正在执行中")
    
    task_id = datetime.now().strftime("%Y%m%d%H%M%S")
    
    _heat_task_status = {
        "is_running": True,
        "task_id": task_id,
        "process": None,
        "cancel_requested": False,
        "start_time": datetime.now().isoformat(),
        "logs": []
    }
    
    asyncio.create_task(run_heat_task(request))
    
    return {
        "success": True,
        "message": "热度计算任务已启动",
        "task_id": task_id
    }


@router.get("/heat/status", summary="获取热度计算状态")
async def get_heat_status(current_user = Depends(require_admin)):
    """获取当前热度计算任务状态"""
    return {
        "is_running": _heat_task_status["is_running"],
        "task_id": _heat_task_status["task_id"],
        "start_time": _heat_task_status["start_time"],
        "logs": _heat_task_status["logs"][-50:]
    }


@router.post("/heat/cancel", summary="取消热度计算任务")
async def cancel_heat_calc(current_user = Depends(require_admin)):
    """取消正在执行的热度计算任务"""
    global _heat_task_status
    
    if not _heat_task_status["is_running"]:
        raise HTTPException(status_code=400, detail="没有正在执行的热度计算任务")

    _heat_task_status["cancel_requested"] = True
    
    if _heat_task_status["process"]:
        try:
            _heat_task_status["process"].terminate()
            _heat_task_status["logs"].append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 用户取消热度计算任务"
            )
        except:
            pass
    
    return {"success": True, "message": "已取消热度计算任务"}


@router.post("/mapping/auto", summary="编制数据库关系（自动映射）")
async def auto_mapping(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """自动生成外部板块到本地 sectors 的映射关系"""
    global _sync_task_status

    started_at = datetime.now().strftime('%H:%M:%S')
    _sync_task_status["logs"].append(f"[{started_at}] 开始编制数据库关系（自动映射）...")

    try:
        sql = text("""
            INSERT INTO ext_board_local_map (ext_board_id, local_sector_id, match_type, confidence)
            SELECT b.id, s.id, 'auto', 100.00
            FROM ext_board_list b
            JOIN ext_providers p ON p.id = b.provider_id AND p.code = 'em'
            JOIN sectors s ON s.sector_name = b.board_name
            ON CONFLICT DO NOTHING
        """)
        result = db.execute(sql)
        db.commit()

        count_sql = text("SELECT COUNT(*) FROM ext_board_local_map")
        total_count = db.execute(count_sql).scalar() or 0

        finished_at = datetime.now().strftime('%H:%M:%S')
        _sync_task_status["logs"].append(
            f"[{finished_at}] 自动映射完成，新增 {getattr(result, 'rowcount', 0) or 0} 条，总计 {total_count} 条"
        )

        return {
            "success": True,
            "message": "自动映射完成",
            "inserted": getattr(result, 'rowcount', 0) or 0,
            "total": total_count
        }
    except Exception as e:
        db.rollback()
        _sync_task_status["logs"].append(f"[ERROR] 自动映射失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"自动映射失败: {str(e)}")


@router.get("/sync-history", summary="获取同步历史")
async def get_sync_history(
    limit: int = 30,
    current_user = Depends(require_admin)
):
    """获取同步历史记录列表"""
    state = load_state()
    syncs = state.get("syncs", {})
    
    # 按日期排序
    sorted_dates = sorted(syncs.keys(), reverse=True)[:limit]
    
    history = []
    for date_str in sorted_dates:
        sync_info = syncs[date_str]
        history.append({
            "date": date_str,
            "status": sync_info.get("status", "unknown"),
            "start_time": sync_info.get("start_time"),
            "end_time": sync_info.get("end_time"),
            "duration_seconds": sync_info.get("duration_seconds"),
            "providers": sync_info.get("providers", {}),
            "error": sync_info.get("error")
        })
    
    return {"history": history, "total": len(syncs)}


@router.get("/stats", response_model=StatsResponse, summary="获取运维统计")
async def get_stats(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """获取外部板块运维统计数据"""
    
    # 查询板块统计
    boards_sql = text("""
        SELECT 
            p.code as provider_code,
            p.name as provider_name,
            b.board_type,
            COUNT(*) as board_count
        FROM ext_board_list b
        JOIN ext_providers p ON p.id = b.provider_id
        GROUP BY p.code, p.name, b.board_type
        ORDER BY p.code, b.board_type
    """)
    boards_result = db.execute(boards_sql).fetchall()
    
    # 查询成分股统计
    cons_sql = text("""
        SELECT 
            p.code as provider_code,
            COUNT(*) as cons_count,
            COUNT(DISTINCT s.stock_code) as stock_count
        FROM ext_board_daily_snap s
        JOIN ext_board_list b ON b.id = s.board_id
        JOIN ext_providers p ON p.id = b.provider_id
        GROUP BY p.code
    """)
    cons_result = db.execute(cons_sql).fetchall()
    
    # 查询映射数量
    map_sql = text("SELECT COUNT(*) FROM ext_board_local_map")
    mapping_count = db.execute(map_sql).scalar() or 0
    
    # 组装数据
    providers = []
    cons_map = {row.provider_code: {"cons_count": row.cons_count, "stock_count": row.stock_count} 
                for row in cons_result}
    
    provider_data = {}
    for row in boards_result:
        if row.provider_code not in provider_data:
            provider_data[row.provider_code] = {
                "code": row.provider_code,
                "name": row.provider_name,
                "boards": {},
                "total_boards": 0
            }
        provider_data[row.provider_code]["boards"][row.board_type] = row.board_count
        provider_data[row.provider_code]["total_boards"] += row.board_count
    
    for code, data in provider_data.items():
        cons_info = cons_map.get(code, {})
        providers.append({
            **data,
            "cons_count": cons_info.get("cons_count", 0),
            "stock_count": cons_info.get("stock_count", 0)
        })
    
    # 计算总数
    total_boards = sum(p["total_boards"] for p in providers)
    total_cons = sum(p.get("cons_count", 0) for p in providers)
    
    # 获取最近一次同步信息
    state = load_state()
    syncs = state.get("syncs", {})
    last_sync = None
    if syncs:
        last_date = max(syncs.keys())
        last_sync = {"date": last_date, **syncs[last_date]}
    
    return StatsResponse(
        total_boards=total_boards,
        total_cons_records=total_cons,
        providers=providers,
        last_sync=last_sync,
        mapping_count=mapping_count
    )


@router.get("/boards", summary="查询板块列表")
async def get_boards(
    provider: Optional[str] = None,
    board_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """查询外部板块列表"""
    
    where_clauses = ["1=1"]
    params = {}
    
    if provider:
        where_clauses.append("p.code = :provider")
        params["provider"] = provider
    
    if board_type:
        where_clauses.append("b.board_type = :board_type")
        params["board_type"] = board_type
    
    if search:
        where_clauses.append("b.board_name ILIKE :search")
        params["search"] = f"%{search}%"
    
    where_sql = " AND ".join(where_clauses)
    
    # 查询总数
    count_sql = text(f"""
        SELECT COUNT(*)
        FROM ext_board_list b
        JOIN ext_providers p ON p.id = b.provider_id
        WHERE {where_sql}
    """)
    total = db.execute(count_sql, params).scalar()
    
    # 查询数据
    offset = (page - 1) * page_size
    data_sql = text(f"""
        SELECT 
            b.id, b.board_code, b.board_name, b.board_type,
            b.stock_count, b.updated_at,
            p.code as provider_code, p.name as provider_name
        FROM ext_board_list b
        JOIN ext_providers p ON p.id = b.provider_id
        WHERE {where_sql}
        ORDER BY b.stock_count DESC, b.board_name
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset
    
    result = db.execute(data_sql, params).fetchall()
    
    boards = [
        {
            "id": row.id,
            "board_code": row.board_code,
            "board_name": row.board_name,
            "board_type": row.board_type,
            "stock_count": row.stock_count,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "provider_code": row.provider_code,
            "provider_name": row.provider_name
        }
        for row in result
    ]
    
    return {
        "boards": boards,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
