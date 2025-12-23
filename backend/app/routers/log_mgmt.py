"""
操作日志 API 路由
提供日志查询、统计、导出等接口
v1.1.0
"""
import csv
import io
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User
from ..auth.dependencies import get_current_user
from ..services.log_service import LogService, LOG_TYPES, LOG_ACTIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/logs", tags=["操作日志"])


# ==================== 响应模型 ====================

class LogListResponse(BaseModel):
    """日志列表响应"""
    total: int
    page: int
    page_size: int
    items: List[dict]


class LogStatisticsResponse(BaseModel):
    """日志统计响应"""
    period_days: int
    total: int
    type_distribution: dict
    status_distribution: dict
    daily_trend: List[dict]
    login_failed_count: int
    security_event_count: int
    updated_at: str


class LogTypesResponse(BaseModel):
    """日志类型列表"""
    types: dict
    actions: dict


# ==================== 依赖项 ====================

def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """验证管理员权限"""
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ==================== API 端点 ====================

@router.get("/types", response_model=LogTypesResponse)
def get_log_types(admin: User = Depends(get_admin_user)):
    """获取日志类型和操作动作列表"""
    return {
        "types": LOG_TYPES,
        "actions": LOG_ACTIONS
    }


@router.get("", response_model=LogListResponse)
def get_logs(
    page: int = 1,
    page_size: int = 20,
    log_type: Optional[str] = None,
    action: Optional[str] = None,
    operator_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    log_status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    获取操作日志列表
    
    - **log_type**: LOGIN/USER/SESSION/SECURITY/SYSTEM
    - **action**: login_success/login_failed/user_create/...
    - **log_status**: success/failed
    - **start_date**: 开始日期 (YYYY-MM-DD)
    - **end_date**: 结束日期 (YYYY-MM-DD)
    """
    try:
        result = LogService.get_logs(
            db=db,
            page=page,
            page_size=page_size,
            log_type=log_type,
            action=action,
            operator_name=operator_name,
            target_type=target_type,
            target_id=target_id,
            status=log_status,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
        return result
    except Exception as e:
        logger.error(f"获取日志列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=LogStatisticsResponse)
def get_log_statistics(
    days: int = 7,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    获取日志统计信息
    
    - **days**: 统计天数，默认7天
    """
    try:
        return LogService.get_log_statistics(db, days)
    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}", response_model=LogListResponse)
def get_user_activity(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取指定用户的操作记录"""
    try:
        return LogService.get_user_activity(db, user_id, page, page_size)
    except Exception as e:
        logger.error(f"获取用户活动失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{log_id}")
def get_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """获取日志详情"""
    try:
        result = LogService.get_log_detail(db, log_id)
        if not result:
            raise HTTPException(status_code=404, detail="日志不存在")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日志详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/csv")
def export_logs_csv(
    log_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    导出日志为 CSV 文件
    
    - **limit**: 最大导出条数，默认1000
    """
    try:
        logs = LogService.export_logs(db, log_type, start_date, end_date, limit)
        
        if not logs:
            raise HTTPException(status_code=404, detail="没有符合条件的日志")
        
        # 生成 CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)
        
        # 返回文件
        output.seek(0)
        filename = f"operation_logs_{start_date or 'all'}_{end_date or 'now'}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
def cleanup_old_logs(
    days: int = 90,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    清理旧日志
    
    删除超过指定天数的日志记录
    """
    try:
        deleted = LogService.cleanup_old_logs(db, days)
        return {
            "success": True,
            "message": f"已清理 {deleted} 条旧日志",
            "deleted": deleted
        }
    except Exception as e:
        logger.error(f"清理日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
