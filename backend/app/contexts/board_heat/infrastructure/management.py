"""Infrastructure adapters for external board management tasks."""

from __future__ import annotations

import asyncio
import json
import locale
import subprocess
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..application.commands import (
    CalculateBoardHeatCommand,
    ListExternalBoardsQuery,
    ListSyncHistoryQuery,
    SyncExternalBoardsCommand,
)

BACKEND_ROOT = Path(__file__).resolve().parents[4]
PROJECT_ROOT = Path(__file__).resolve().parents[5]
STATE_FILE = PROJECT_ROOT / "data" / "ext_board_sync_state.json"

_sync_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sync_task")
_heat_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="heat_task")

_sync_task_status: dict[str, Any] = {
    "is_syncing": False,
    "task_id": None,
    "process": None,
    "task": None,
    "cancel_requested": False,
    "start_time": None,
    "provider": None,
    "logs": [],
}

_heat_task_status: dict[str, Any] = {
    "is_running": False,
    "task_id": None,
    "process": None,
    "cancel_requested": False,
    "start_time": None,
    "logs": [],
}


class BoardHeatTaskConflictError(Exception):
    """Raised when a board heat background task is already running."""


class BoardHeatTaskNotRunningError(Exception):
    """Raised when a cancel request has no running task."""


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"syncs": {}, "config": {}}


def _sync_script_path() -> Path:
    return BACKEND_ROOT / "scripts" / "sync_ext_boards.py"


def _heat_script_path() -> Path:
    return BACKEND_ROOT / "scripts" / "task_board_heat.py"


def _run_process_blocking(cmd: list[str], cwd: str, status: dict[str, Any], *, done_message: str, fail_message: str) -> None:
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        status["process"] = process

        if status.get("cancel_requested"):
            process.terminate()
            return

        encoding = locale.getpreferredencoding(False) or "utf-8"
        assert process.stdout is not None
        for line in iter(process.stdout.readline, b""):
            if status.get("cancel_requested"):
                process.terminate()
                status["logs"].append(f"[{_timestamp()}] 用户取消任务")
                break

            try:
                decoded_line = line.decode("utf-8").strip()
            except UnicodeDecodeError:
                decoded_line = line.decode(encoding, errors="replace").strip()

            if decoded_line:
                if len(status["logs"]) > 100:
                    status["logs"] = status["logs"][-50:]
                status["logs"].append(decoded_line)

        process.wait()
        exit_code = process.returncode
        if not status.get("cancel_requested"):
            if exit_code == 0:
                status["logs"].append(f"[{_timestamp()}] {done_message}，退出码: {exit_code}")
            else:
                status["logs"].append(f"[{_timestamp()}] [ERROR] {fail_message}，退出码: {exit_code}")
    except Exception as exc:
        status["logs"].append(f"[ERROR] {fail_message}: {exc}")
        tb = traceback.format_exc()
        if tb:
            status["logs"].append("\n".join(tb.strip().splitlines()[-20:]))
    finally:
        if "is_syncing" in status:
            status["is_syncing"] = False
        if "is_running" in status:
            status["is_running"] = False
        status["process"] = None
        status["cancel_requested"] = False


class BoardHeatManagementAdapter:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    async def start_sync(self, command: SyncExternalBoardsCommand) -> dict[str, Any]:
        global _sync_task_status

        if _sync_task_status["is_syncing"]:
            raise BoardHeatTaskConflictError("同步任务正在执行中")

        task_id = datetime.now().strftime("%Y%m%d%H%M%S")
        _sync_task_status = {
            "is_syncing": True,
            "task_id": task_id,
            "process": None,
            "task": None,
            "cancel_requested": False,
            "start_time": datetime.now().isoformat(),
            "provider": command.provider,
            "logs": [],
        }
        _sync_task_status["task"] = asyncio.create_task(self._run_sync_task(command))
        return {"success": True, "message": "同步任务已启动", "task_id": task_id}

    def get_sync_status(self) -> dict[str, Any]:
        return {
            "is_syncing": _sync_task_status["is_syncing"],
            "task_id": _sync_task_status["task_id"],
            "provider": _sync_task_status["provider"],
            "start_time": _sync_task_status["start_time"],
            "logs": _sync_task_status["logs"][-50:],
            "progress": None,
        }

    def cancel_sync(self) -> dict[str, Any]:
        if not _sync_task_status["is_syncing"]:
            raise BoardHeatTaskNotRunningError("没有正在执行的同步任务")

        _sync_task_status["cancel_requested"] = True
        if _sync_task_status["process"]:
            try:
                _sync_task_status["process"].terminate()
                _sync_task_status["logs"].append(f"[{_timestamp()}] 用户取消同步任务")
            except Exception:
                pass
        return {"success": True, "message": "已取消同步任务"}

    async def start_heat_calculation(self, command: CalculateBoardHeatCommand) -> dict[str, Any]:
        global _heat_task_status

        if _heat_task_status["is_running"]:
            raise BoardHeatTaskConflictError("热度计算任务正在执行中")

        task_id = datetime.now().strftime("%Y%m%d%H%M%S")
        _heat_task_status = {
            "is_running": True,
            "task_id": task_id,
            "process": None,
            "cancel_requested": False,
            "start_time": datetime.now().isoformat(),
            "logs": [],
        }
        asyncio.create_task(self._run_heat_task(command))
        return {"success": True, "message": "热度计算任务已启动", "task_id": task_id}

    def get_heat_status(self) -> dict[str, Any]:
        return {
            "is_running": _heat_task_status["is_running"],
            "task_id": _heat_task_status["task_id"],
            "start_time": _heat_task_status["start_time"],
            "logs": _heat_task_status["logs"][-50:],
        }

    def cancel_heat_calculation(self) -> dict[str, Any]:
        if not _heat_task_status["is_running"]:
            raise BoardHeatTaskNotRunningError("没有正在执行的热度计算任务")

        _heat_task_status["cancel_requested"] = True
        if _heat_task_status["process"]:
            try:
                _heat_task_status["process"].terminate()
                _heat_task_status["logs"].append(f"[{_timestamp()}] 用户取消热度计算任务")
            except Exception:
                pass
        return {"success": True, "message": "已取消热度计算任务"}

    def auto_mapping(self) -> dict[str, Any]:
        db = self._require_db()
        _sync_task_status["logs"].append(f"[{_timestamp()}] 开始编制数据库关系（自动映射）...")
        try:
            result = db.execute(
                text(
                    """
                    INSERT INTO ext_board_local_map (ext_board_id, local_sector_id, match_type, confidence)
                    SELECT b.id, s.id, 'auto', 100.00
                    FROM ext_board_list b
                    JOIN ext_providers p ON p.id = b.provider_id AND p.code = 'em'
                    JOIN sectors s ON s.sector_name = b.board_name
                    ON CONFLICT DO NOTHING
                    """
                )
            )
            db.commit()
            total_count = db.execute(text("SELECT COUNT(*) FROM ext_board_local_map")).scalar() or 0
            inserted = getattr(result, "rowcount", 0) or 0
            _sync_task_status["logs"].append(f"[{_timestamp()}] 自动映射完成，新增 {inserted} 条，总计 {total_count} 条")
            return {"success": True, "message": "自动映射完成", "inserted": inserted, "total": total_count}
        except Exception:
            db.rollback()
            raise

    def get_sync_history(self, query: ListSyncHistoryQuery) -> dict[str, Any]:
        syncs = _load_state().get("syncs", {})
        history = []
        for date_str in sorted(syncs.keys(), reverse=True)[: query.limit]:
            sync_info = syncs[date_str]
            history.append(
                {
                    "date": date_str,
                    "status": sync_info.get("status", "unknown"),
                    "start_time": sync_info.get("start_time"),
                    "end_time": sync_info.get("end_time"),
                    "duration_seconds": sync_info.get("duration_seconds"),
                    "providers": sync_info.get("providers", {}),
                    "error": sync_info.get("error"),
                }
            )
        return {"history": history, "total": len(syncs)}

    def get_stats(self) -> dict[str, Any]:
        db = self._require_db()
        boards_result = db.execute(
            text(
                """
                SELECT p.code as provider_code, p.name as provider_name, b.board_type, COUNT(*) as board_count
                FROM ext_board_list b
                JOIN ext_providers p ON p.id = b.provider_id
                GROUP BY p.code, p.name, b.board_type
                ORDER BY p.code, b.board_type
                """
            )
        ).fetchall()
        cons_result = db.execute(
            text(
                """
                SELECT p.code as provider_code, COUNT(*) as cons_count, COUNT(DISTINCT s.stock_code) as stock_count
                FROM ext_board_daily_snap s
                JOIN ext_board_list b ON b.id = s.board_id
                JOIN ext_providers p ON p.id = b.provider_id
                GROUP BY p.code
                """
            )
        ).fetchall()
        mapping_count = db.execute(text("SELECT COUNT(*) FROM ext_board_local_map")).scalar() or 0

        cons_map = {row.provider_code: {"cons_count": row.cons_count, "stock_count": row.stock_count} for row in cons_result}
        provider_data: dict[str, Any] = {}
        for row in boards_result:
            if row.provider_code not in provider_data:
                provider_data[row.provider_code] = {
                    "code": row.provider_code,
                    "name": row.provider_name,
                    "boards": {},
                    "total_boards": 0,
                }
            provider_data[row.provider_code]["boards"][row.board_type] = row.board_count
            provider_data[row.provider_code]["total_boards"] += row.board_count

        providers = []
        for code, data in provider_data.items():
            cons_info = cons_map.get(code, {})
            providers.append(
                {
                    **data,
                    "cons_count": cons_info.get("cons_count", 0),
                    "stock_count": cons_info.get("stock_count", 0),
                }
            )

        syncs = _load_state().get("syncs", {})
        last_sync = None
        if syncs:
            last_date = max(syncs.keys())
            last_sync = {"date": last_date, **syncs[last_date]}

        return {
            "total_boards": sum(provider["total_boards"] for provider in providers),
            "total_cons_records": sum(provider.get("cons_count", 0) for provider in providers),
            "providers": providers,
            "last_sync": last_sync,
            "mapping_count": mapping_count,
        }

    def get_boards(self, query: ListExternalBoardsQuery) -> dict[str, Any]:
        db = self._require_db()
        where_clauses = ["1=1"]
        params: dict[str, Any] = {}

        if query.provider:
            where_clauses.append("p.code = :provider")
            params["provider"] = query.provider
        if query.board_type:
            where_clauses.append("b.board_type = :board_type")
            params["board_type"] = query.board_type
        if query.search:
            where_clauses.append("b.board_name ILIKE :search")
            params["search"] = f"%{query.search}%"

        where_sql = " AND ".join(where_clauses)
        total = db.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM ext_board_list b
                JOIN ext_providers p ON p.id = b.provider_id
                WHERE {where_sql}
                """
            ),
            params,
        ).scalar()

        offset = (query.page - 1) * query.page_size
        params["limit"] = query.page_size
        params["offset"] = offset
        rows = db.execute(
            text(
                f"""
                SELECT
                    b.id, b.board_code, b.board_name, b.board_type,
                    b.stock_count, b.updated_at,
                    p.code as provider_code, p.name as provider_name
                FROM ext_board_list b
                JOIN ext_providers p ON p.id = b.provider_id
                WHERE {where_sql}
                ORDER BY b.stock_count DESC, b.board_name
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        total = total or 0
        return {
            "boards": [
                {
                    "id": row.id,
                    "board_code": row.board_code,
                    "board_name": row.board_name,
                    "board_type": row.board_type,
                    "stock_count": row.stock_count,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "provider_code": row.provider_code,
                    "provider_name": row.provider_name,
                }
                for row in rows
            ],
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "total_pages": (total + query.page_size - 1) // query.page_size,
        }

    async def _run_sync_task(self, command: SyncExternalBoardsCommand) -> None:
        script_path = _sync_script_path()
        if not script_path.exists():
            _sync_task_status["logs"] = [
                f"[{_timestamp()}] 启动同步任务...",
                f"[ERROR] 同步脚本不存在: {script_path}",
            ]
            _sync_task_status["is_syncing"] = False
            return

        cmd = [sys.executable, "-u", str(script_path), "--provider", command.provider]
        if command.date:
            cmd.extend(["--date", command.date])
        if command.skip_cons:
            cmd.append("--skip-cons")
        if command.skip_map:
            cmd.append("--skip-map")
        if command.force:
            cmd.append("--force")
        if command.use_proxy:
            cmd.append("--proxy")
        if command.board_type:
            cmd.extend(["--board-type", command.board_type])
        if command.limit is not None:
            cmd.extend(["--limit", str(command.limit)])
        if command.concurrent:
            cmd.append("--concurrent")
            cmd.extend(["--workers", str(command.workers)])
            cmd.extend(["--max-ips", str(command.max_ips)])
            cmd.extend(["--ip-ttl", str(command.ip_ttl)])
            cmd.extend(["--req-delay-min", str(command.req_delay_min)])
            cmd.extend(["--req-delay-max", str(command.req_delay_max)])
        if command.delay is not None:
            cmd.extend(["--delay", str(command.delay)])

        _sync_task_status["logs"] = [f"[{_timestamp()}] 启动同步任务...", f"[{_timestamp()}] 命令: {' '.join(cmd)}"]
        if _sync_task_status.get("cancel_requested"):
            _sync_task_status["logs"].append(f"[{_timestamp()}] 同步任务已取消（启动前）")
            _sync_task_status["is_syncing"] = False
            return

        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _sync_executor,
            _run_process_blocking,
            cmd,
            str(BACKEND_ROOT),
            _sync_task_status,
            done_message="同步完成",
            fail_message="同步失败",
        )

    async def _run_heat_task(self, command: CalculateBoardHeatCommand) -> None:
        script_path = _heat_script_path()
        if not script_path.exists():
            _heat_task_status["logs"] = [
                f"[{_timestamp()}] 启动热度计算任务...",
                f"[ERROR] 热度计算脚本不存在: {script_path}",
            ]
            _heat_task_status["is_running"] = False
            return

        cmd = [sys.executable, "-u", str(script_path)]
        if command.date:
            cmd.extend(["--date", command.date])
        if command.calc_all:
            cmd.append("--all")
        if command.force:
            cmd.append("--force")
        if command.allow_fallback:
            cmd.append("--allow-latest-snap-fallback")

        _heat_task_status["logs"] = [f"[{_timestamp()}] 启动热度计算任务...", f"[{_timestamp()}] 命令: {' '.join(cmd)}"]
        if _heat_task_status.get("cancel_requested"):
            _heat_task_status["logs"].append(f"[{_timestamp()}] 热度计算任务已取消（启动前）")
            _heat_task_status["is_running"] = False
            return

        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _heat_executor,
            _run_process_blocking,
            cmd,
            str(BACKEND_ROOT),
            _heat_task_status,
            done_message="热度计算完成",
            fail_message="热度计算失败",
        )

    def _require_db(self) -> Session:
        if self.db is None:
            raise RuntimeError("Database session is required for this operation")
        return self.db
