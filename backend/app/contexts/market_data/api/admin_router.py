"""Market data admin routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ....auth.dependencies import require_admin
from ..application.admin_commands import (
    DeleteDataBatchCommand,
    DeleteDataByDateCommand,
    DeleteDataFileCommand,
    PreviewDeleteDataQuery,
    TriggerDataImportCommand,
    UploadDataFileCommand,
)
from ..application.admin_services import MarketDataAdminService
from ..application.errors import (
    DataAdminConflictError,
    DataAdminNotFoundError,
    InvalidDataAdminRequestError,
)
from ..infrastructure.data_admin import MarketDataAdminAdapter

router = APIRouter(prefix="/admin", tags=["admin"])


class FileUploadRequest(BaseModel):
    filename: str
    content: str


class ImportRequest(BaseModel):
    date: str | None = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    filepath: str | None = None


class DeleteDataRequest(BaseModel):
    dates: list[str]
    data_type: str = "all"


def _admin_service() -> MarketDataAdminService:
    return MarketDataAdminService(MarketDataAdminAdapter())


def _map_admin_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidDataAdminRequestError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, DataAdminNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DataAdminConflictError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file_data: FileUploadRequest, current_user=Depends(require_admin)):
    try:
        return _admin_service().upload_file(
            UploadDataFileCommand(
                filename=file_data.filename,
                content=file_data.content,
                username=current_user.username,
            )
        )
    except (InvalidDataAdminRequestError, DataAdminNotFoundError, DataAdminConflictError) as exc:
        raise _map_admin_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {exc}") from exc


@router.post("/import")
async def trigger_import(import_params: ImportRequest | None = None, current_user=Depends(require_admin)):
    try:
        return _admin_service().trigger_import(
            TriggerDataImportCommand(
                username=current_user.username,
                date=import_params.date if import_params else None,
            )
        )
    except DataAdminConflictError as exc:
        raise _map_admin_error(exc) from exc


@router.get("/import-status")
async def get_import_status(current_user=Depends(require_admin)):
    return _admin_service().get_import_status()


@router.get("/data-files")
async def list_data_files(current_user=Depends(require_admin)):
    try:
        return _admin_service().list_data_files()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"列出文件失败: {exc}") from exc


@router.delete("/data-files/{filename}")
async def delete_data_file(filename: str, current_user=Depends(require_admin)):
    try:
        return _admin_service().delete_data_file(
            DeleteDataFileCommand(filename=filename, username=current_user.username)
        )
    except (InvalidDataAdminRequestError, DataAdminNotFoundError) as exc:
        raise _map_admin_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {exc}") from exc


@router.get("/dates")
async def get_imported_dates(current_user=Depends(require_admin)):
    try:
        return _admin_service().get_imported_dates()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"获取日期列表失败: {exc}") from exc


@router.get("/data/preview/{date}")
async def preview_delete_data(date: str, data_type: str = "all", current_user=Depends(require_admin)):
    try:
        return _admin_service().preview_delete_data(PreviewDeleteDataQuery(date=date, data_type=data_type))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"预览删除失败: {exc}") from exc


@router.delete("/data/{date}")
async def delete_data_by_date(date: str, data_type: str = "all", current_user=Depends(require_admin)):
    try:
        return _admin_service().delete_data_by_date(
            DeleteDataByDateCommand(date=date, data_type=data_type, username=current_user.username)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"删除数据失败: {exc}") from exc


@router.post("/data/delete-batch")
async def delete_data_batch(delete_req: DeleteDataRequest, current_user=Depends(require_admin)):
    try:
        return _admin_service().delete_data_batch(
            DeleteDataBatchCommand(
                dates=delete_req.dates,
                data_type=delete_req.data_type,
                username=current_user.username,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"批量删除数据失败: {exc}") from exc
