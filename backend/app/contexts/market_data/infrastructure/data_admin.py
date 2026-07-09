"""Infrastructure adapter for market data admin workflows."""

from __future__ import annotations

import base64
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, text

from ....config import DATA_DIR
from ....core.caching import cache
from ....database import SessionLocal
from ....db_models import DailyStockData, SectorDailyData
from ....services.hot_spots_cache import HotSpotsCache
from ..application.admin_commands import (
    DeleteDataBatchCommand,
    DeleteDataByDateCommand,
    DeleteDataFileCommand,
    PreviewDeleteDataQuery,
    TriggerDataImportCommand,
    UploadDataFileCommand,
)
from ..application.errors import (
    DataAdminConflictError,
    DataAdminNotFoundError,
    InvalidDataAdminRequestError,
)

logger = logging.getLogger(__name__)

MAX_LOGS = 100

import_status: dict[str, Any] = {
    "is_importing": False,
    "current_file": None,
    "progress": 0,
    "last_import": None,
    "last_result": None,
    "history": [],
    "logs": [],
}


def _add_log(message: str, level: str = "info") -> None:
    log_entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
    }
    import_status["logs"].append(log_entry)
    if len(import_status["logs"]) > MAX_LOGS:
        import_status["logs"] = import_status["logs"][-MAX_LOGS:]

    if level == "error":
        logger.error(message)
    else:
        logger.info(message)


def _validate_filename(filename: str) -> None:
    if not filename:
        raise InvalidDataAdminRequestError("文件名不能为空")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise InvalidDataAdminRequestError("无效的文件名")


def _reload_runtime_caches() -> None:
    from ....core.startup import preload_cache

    cache.clear_api_cache()
    HotSpotsCache.clear_cache()
    preload_cache()


class MarketDataAdminAdapter:
    def upload_file(self, command: UploadDataFileCommand) -> dict[str, Any]:
        _validate_filename(command.filename)
        if not command.filename.lower().endswith((".xlsx", ".xls")):
            raise InvalidDataAdminRequestError("只支持 Excel 文件 (.xlsx, .xls)")

        try:
            file_content = base64.b64decode(command.content)
        except Exception as exc:
            raise InvalidDataAdminRequestError(f"Base64 解码失败: {exc}") from exc

        if len(file_content) > 10 * 1024 * 1024:
            raise InvalidDataAdminRequestError("文件大小不能超过 10MB")

        os.makedirs(DATA_DIR, exist_ok=True)
        filepath = os.path.join(DATA_DIR, command.filename)
        with open(filepath, "wb") as file_obj:
            file_obj.write(file_content)

        logger.info("管理员 %s 上传文件: %s", command.username, command.filename)
        return {"success": True, "message": f"文件上传成功: {command.filename}", "filepath": filepath}

    def trigger_import(self, command: TriggerDataImportCommand) -> dict[str, Any]:
        if import_status["is_importing"]:
            raise DataAdminConflictError("正在导入中，请稍后再试")

        import_status["is_importing"] = True
        import_status["progress"] = 0
        import_status["current_file"] = "正在准备导入..."
        import_status["logs"] = []
        _add_log("🚀 开始数据导入任务（后台执行）")

        thread = threading.Thread(target=self._do_import_task, args=(command.username,))
        thread.daemon = True
        thread.start()

        return {"success": True, "message": "导入任务已启动，请通过 /admin/import-status 查看进度", "status": "started"}

    def get_import_status(self) -> dict[str, Any]:
        return {
            "is_importing": import_status["is_importing"],
            "current_file": import_status["current_file"],
            "progress": import_status["progress"],
            "last_import": import_status["last_import"],
            "last_result": import_status["last_result"],
            "history": import_status["history"],
            "logs": import_status["logs"],
        }

    def list_data_files(self) -> dict[str, Any]:
        if not os.path.exists(DATA_DIR):
            return {"files": []}

        files = []
        for filename in os.listdir(DATA_DIR):
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.isfile(filepath) and filename.lower().endswith((".xlsx", ".xls")):
                stat = os.stat(filepath)
                files.append(
                    {
                        "name": filename,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
        files.sort(key=lambda item: item["modified"], reverse=True)
        return {"files": files}

    def delete_data_file(self, command: DeleteDataFileCommand) -> dict[str, Any]:
        _validate_filename(command.filename)
        filepath = os.path.join(DATA_DIR, command.filename)
        if not os.path.exists(filepath):
            raise DataAdminNotFoundError("文件不存在")

        os.remove(filepath)
        logger.info("管理员 %s 删除文件: %s", command.username, command.filename)
        return {"success": True, "message": f"文件已删除: {command.filename}"}

    def get_imported_dates(self) -> dict[str, Any]:
        db = SessionLocal()
        try:
            result = db.execute(
                text(
                    """
                    SELECT DISTINCT date
                    FROM daily_stock_data
                    ORDER BY date DESC
                    LIMIT 30
                    """
                )
            )
            dates = [row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0]) for row in result]
            return {"dates": dates}
        finally:
            db.close()

    def preview_delete_data(self, query: PreviewDeleteDataQuery) -> dict[str, Any]:
        date_str = query.date.replace("-", "")
        db = SessionLocal()
        try:
            result = {"date": date_str, "stock_count": 0, "sector_count": 0}
            if query.data_type in ["stock", "all"]:
                result["stock_count"] = (
                    db.query(func.count(DailyStockData.id))
                    .filter(func.to_char(DailyStockData.date, "YYYYMMDD") == date_str)
                    .scalar()
                    or 0
                )
            if query.data_type in ["sector", "all"]:
                result["sector_count"] = (
                    db.query(func.count(SectorDailyData.id))
                    .filter(func.to_char(SectorDailyData.date, "YYYYMMDD") == date_str)
                    .scalar()
                    or 0
                )
            result["total_count"] = result["stock_count"] + result["sector_count"]
            return {"success": True, "preview": result}
        finally:
            db.close()

    def delete_data_by_date(self, command: DeleteDataByDateCommand) -> dict[str, Any]:
        date_str = command.date.replace("-", "")
        db = SessionLocal()
        try:
            result = self._delete_date(db, date_str, command.data_type)
            db.commit()
            self._mark_deleted([date_str], command.data_type, "manual_delete", command.username)
            logger.info("管理员 %s 删除数据: %s, 共 %s 条", command.username, date_str, result["total_deleted"])
            self._reload_after_delete()
            return {"success": True, "result": result, "message": f"已删除 {date_str} 的数据，共 {result['total_deleted']} 条"}
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def delete_data_batch(self, command: DeleteDataBatchCommand) -> dict[str, Any]:
        db = SessionLocal()
        try:
            results = []
            total_stock = 0
            total_sector = 0
            normalized_dates = [date_value.replace("-", "") for date_value in command.dates]
            for date_str in normalized_dates:
                result = self._delete_date(db, date_str, command.data_type)
                results.append(result)
                total_stock += result["stock_deleted"]
                total_sector += result["sector_deleted"]
            db.commit()
            self._mark_deleted(normalized_dates, command.data_type, "batch_delete", command.username)
            logger.info(
                "管理员 %s 批量删除数据: %s 天, 股票 %s 条, 板块 %s 条",
                command.username,
                len(command.dates),
                total_stock,
                total_sector,
            )
            self._reload_after_delete()
            return {
                "success": True,
                "results": results,
                "summary": {
                    "dates_count": len(command.dates),
                    "stock_deleted": total_stock,
                    "sector_deleted": total_sector,
                    "total_deleted": total_stock + total_sector,
                },
                "message": f"已删除 {len(command.dates)} 天的数据，共 {total_stock + total_sector} 条",
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _do_import_task(self, username: str) -> None:
        try:
            data_dir = Path(DATA_DIR)
            _add_log(f"📂 扫描数据目录: {data_dir}")

            stock_files = list(data_dir.glob("*_data_sma_feature_color.xlsx"))
            sector_files = list(data_dir.glob("*_allbk_sma_feature_color.xlsx"))
            all_files = stock_files + sector_files

            _add_log(f"📊 找到 {len(stock_files)} 个股票数据文件")
            _add_log(f"📊 找到 {len(sector_files)} 个板块数据文件")

            if not all_files:
                import_status["is_importing"] = False
                _add_log("⚠️ 没有找到待导入的文件", "warning")
                return

            total_files = len(all_files)
            imported_count = 0
            errors = []

            def progress_callback(msg: str, progress_pct: int | None = None) -> None:
                if progress_pct is not None:
                    import_status["progress"] = progress_pct
                if msg:
                    _add_log(msg)

            if stock_files:
                import_status["current_file"] = "导入股票数据..."
                _add_log(f"📈 开始导入股票数据 ({len(stock_files)} 个文件)")
                from scripts.import_data_robust import import_excel_file as import_stock_file
                from scripts.import_state_manager import get_state_manager

                state_manager = get_state_manager()
                for index, filepath in enumerate(stock_files):
                    filename = os.path.basename(str(filepath))
                    import_status["current_file"] = f"[股票] {filename}"
                    base_progress = int((index / total_files) * 50)
                    import_status["progress"] = base_progress
                    try:
                        result = import_stock_file(
                            filepath,
                            state_manager,
                            progress_callback=lambda msg, pct=None: progress_callback(
                                msg,
                                base_progress + int((pct or 0) * 0.5 / len(stock_files)) if pct else None,
                            ),
                        )
                        if result[2]:
                            imported_count += 1
                            _add_log(f"✅ [股票] {filename} - 导入成功 ({result[0]} 条)")
                        elif result[1] > 0:
                            imported_count += 1
                            _add_log(f"⏭️ [股票] {filename} - 已存在，跳过")
                        else:
                            errors.append(f"{filename}: 导入返回失败")
                            _add_log(f"❌ [股票] {filename} - 导入失败", "error")
                    except Exception as exc:
                        errors.append(f"[股票] {filename}: {exc}")
                        _add_log(f"❌ [股票] {filename} - 错误: {exc}", "error")

            if sector_files:
                import_status["current_file"] = "导入板块数据..."
                _add_log(f"📊 开始导入板块数据 ({len(sector_files)} 个文件)")
                from scripts.import_sectors_robust import import_sector_excel_file as import_sector_file
                from scripts.import_state_manager import ImportStateManager

                sector_state_manager = ImportStateManager("sector_import_state.json")
                for index, filepath in enumerate(sector_files):
                    filename = os.path.basename(str(filepath))
                    import_status["current_file"] = f"[板块] {filename}"
                    base_progress = int(50 + (index / total_files) * 50)
                    import_status["progress"] = base_progress
                    try:
                        result = import_sector_file(
                            filepath,
                            sector_state_manager,
                            progress_callback=lambda msg, pct=None: progress_callback(
                                msg,
                                base_progress + int((pct or 0) * 0.5 / len(sector_files)) if pct else None,
                            ),
                        )
                        if result[2]:
                            imported_count += 1
                            _add_log(f"✅ [板块] {filename} - 导入成功 ({result[0]} 条)")
                        elif result[1] > 0:
                            imported_count += 1
                            _add_log(f"⏭️ [板块] {filename} - 已存在，跳过")
                        else:
                            errors.append(f"{filename}: 导入返回失败")
                            _add_log(f"❌ [板块] {filename} - 导入失败", "error")
                    except Exception as exc:
                        errors.append(f"[板块] {filename}: {exc}")
                        _add_log(f"❌ [板块] {filename} - 错误: {exc}", "error")

            result = {
                "success": imported_count > 0,
                "message": f"导入完成: {imported_count}/{total_files} 个文件成功",
                "imported": imported_count,
                "total": total_files,
                "errors": errors if errors else None,
            }
            import_status["last_import"] = datetime.now().isoformat()
            import_status["last_result"] = result
            import_status["history"].insert(0, {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "result": result})
            import_status["history"] = import_status["history"][:10]
            _add_log(f"✅ {result['message']}")
            _add_log(f"👤 操作用户: {username}")

            _add_log("🔄 正在重载内存缓存...")
            import_status["current_file"] = "重载缓存..."
            import_status["progress"] = 90
            try:
                _reload_runtime_caches()
                _add_log("✅ 内存缓存重载完成！新数据已生效 (含统一缓存)")
            except Exception as cache_error:
                _add_log(f"⚠️ 缓存重载失败: {cache_error}", "warning")
        except Exception as exc:
            _add_log(f"❌ 导入失败: {exc}", "error")
        finally:
            import_status["is_importing"] = False
            import_status["progress"] = 100
            import_status["current_file"] = None

    @staticmethod
    def _delete_date(db, date_str: str, data_type: str) -> dict[str, Any]:
        result = {"date": date_str, "stock_deleted": 0, "sector_deleted": 0}
        if data_type in ["stock", "all"]:
            result["stock_deleted"] = (
                db.query(DailyStockData)
                .filter(func.to_char(DailyStockData.date, "YYYYMMDD") == date_str)
                .delete(synchronize_session=False)
            )
        if data_type in ["sector", "all"]:
            result["sector_deleted"] = (
                db.query(SectorDailyData)
                .filter(func.to_char(SectorDailyData.date, "YYYYMMDD") == date_str)
                .delete(synchronize_session=False)
            )
        result["total_deleted"] = result["stock_deleted"] + result["sector_deleted"]
        return result

    @staticmethod
    def _mark_deleted(dates: list[str], data_type: str, reason: str, username: str) -> None:
        try:
            from scripts.import_state_manager import ImportStateManager, reload_state_managers

            if data_type in ["stock", "all"]:
                stock_state = ImportStateManager("data_import_state.json")
                for date_str in dates:
                    stock_state.mark_deleted(date_str, reason, username)
            if data_type in ["sector", "all"]:
                sector_state = ImportStateManager("sector_import_state.json")
                for date_str in dates:
                    sector_state.mark_deleted(date_str, reason, username)
            reload_state_managers()
        except Exception as exc:
            logger.warning("更新导入状态失败: %s", exc)

    @staticmethod
    def _reload_after_delete() -> None:
        try:
            logger.info("🔄 删除后重载缓存...")
            _reload_runtime_caches()
            logger.info("✅ 缓存重载完成 (含统一缓存)")
        except Exception as exc:
            logger.warning("⚠️ 缓存重载失败: %s", exc)
