"""
管理员路由 - 文件上传和数据导入
仅 admin 角色可访问

v0.5.0: 数据删除时清理统一缓存
"""
import os
import base64
import logging
import threading
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth.dependencies import get_current_user
from ..db_models import User
from ..core.caching import cache  # v0.5.0: 统一缓存
from ..services.hot_spots_cache import HotSpotsCache  # v0.5.0: 热点榜缓存

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# 数据目录（使用 config 中的统一配置）
from ..config import DATA_DIR

# 导入状态存储（简单的内存存储，重启后清空）
import_status = {
    "is_importing": False,
    "current_file": None,
    "progress": 0,
    "last_import": None,
    "last_result": None,
    "history": [],
    "logs": []  # 实时日志
}

# 最大日志条数
MAX_LOGS = 100

def add_log(message: str, level: str = "info"):
    """添加日志到状态"""
    from datetime import datetime
    log_entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message
    }
    import_status["logs"].append(log_entry)
    # 保持日志数量限制
    if len(import_status["logs"]) > MAX_LOGS:
        import_status["logs"] = import_status["logs"][-MAX_LOGS:]
    # 同时输出到服务器日志
    if level == "error":
        logger.error(message)
    else:
        logger.info(message)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """要求管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


class FileUploadRequest(BaseModel):
    """文件上传请求"""
    filename: str  # 文件名
    content: str   # Base64 编码的文件内容
    

class ImportRequest(BaseModel):
    """导入请求"""
    date: Optional[str] = None  # 可选的日期参数 YYYYMMDD


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool
    message: str
    filepath: Optional[str] = None


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file_data: FileUploadRequest,
    current_user: User = Depends(require_admin)
):
    """
    上传文件到服务器 data 目录
    文件内容需要 Base64 编码
    """
    try:
        # 验证文件名
        filename = file_data.filename
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 只允许 xlsx 和 xls 文件
        if not filename.lower().endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="只支持 Excel 文件 (.xlsx, .xls)")
        
        # 解码 Base64 内容
        try:
            file_content = base64.b64decode(file_data.content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Base64 解码失败: {str(e)}")
        
        # 检查文件大小（限制 10MB）
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过 10MB")
        
        # 确保 data 目录存在
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # 保存文件
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"管理员 {current_user.username} 上传文件: {filename}")
        
        return UploadResponse(
            success=True,
            message=f"文件上传成功: {filename}",
            filepath=filepath
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


def _do_import_task(username: str):
    """后台执行导入任务"""
    global import_status
    from pathlib import Path
    
    try:
        data_dir = Path(DATA_DIR)
        add_log(f"📂 扫描数据目录: {data_dir}")
        
        # 分类文件
        stock_files = list(data_dir.glob("*_data_sma_feature_color.xlsx"))
        sector_files = list(data_dir.glob("*_allbk_sma_feature_color.xlsx"))
        
        all_files = stock_files + sector_files
        
        add_log(f"📊 找到 {len(stock_files)} 个股票数据文件")
        add_log(f"📊 找到 {len(sector_files)} 个板块数据文件")
        
        if not all_files:
            import_status["is_importing"] = False
            add_log("⚠️ 没有找到待导入的文件", "warning")
            return
        
        total_files = len(all_files)
        imported_count = 0
        errors = []
        
        # 进度回调函数
        def progress_callback(msg: str, progress_pct: int = None):
            """导入进度回调"""
            if progress_pct is not None:
                import_status["progress"] = progress_pct
            if msg:
                add_log(msg)
        
        # 导入股票数据
        if stock_files:
            import_status["current_file"] = "导入股票数据..."
            add_log(f"📈 开始导入股票数据 ({len(stock_files)} 个文件)")
            
            from scripts.import_data_robust import import_excel_file as import_stock_file
            from scripts.import_state_manager import get_state_manager
            
            state_manager = get_state_manager()
            
            for i, filepath in enumerate(stock_files):
                filename = os.path.basename(str(filepath))
                import_status["current_file"] = f"[股票] {filename}"
                base_progress = int((i / total_files) * 50)
                import_status["progress"] = base_progress
                
                try:
                    # 传递进度回调
                    result = import_stock_file(filepath, state_manager, progress_callback=lambda msg, pct=None: progress_callback(msg, base_progress + int((pct or 0) * 0.5 / len(stock_files)) if pct else None))
                    if result[2]:  # success flag
                        imported_count += 1
                        add_log(f"✅ [股票] {filename} - 导入成功 ({result[0]} 条)")
                    else:
                        if result[1] > 0:  # skipped
                            add_log(f"⏭️ [股票] {filename} - 已存在，跳过")
                            imported_count += 1
                        else:
                            add_log(f"❌ [股票] {filename} - 导入失败", "error")
                            errors.append(f"{filename}: 导入返回失败")
                except Exception as e:
                    errors.append(f"[股票] {filename}: {str(e)}")
                    add_log(f"❌ [股票] {filename} - 错误: {str(e)}", "error")
        
        # 导入板块数据
        if sector_files:
            import_status["current_file"] = "导入板块数据..."
            add_log(f"📊 开始导入板块数据 ({len(sector_files)} 个文件)")
            
            from scripts.import_sectors_robust import import_sector_excel_file as import_sector_file
            from scripts.import_state_manager import ImportStateManager
            
            sector_state_manager = ImportStateManager("sector_import_state.json")
            
            for i, filepath in enumerate(sector_files):
                filename = os.path.basename(str(filepath))
                import_status["current_file"] = f"[板块] {filename}"
                base_progress = int(50 + (i / total_files) * 50)
                import_status["progress"] = base_progress
                
                try:
                    # 传递进度回调
                    result = import_sector_file(filepath, sector_state_manager, progress_callback=lambda msg, pct=None: progress_callback(msg, base_progress + int((pct or 0) * 0.5 / len(sector_files)) if pct else None))
                    if result[2]:  # success flag
                        imported_count += 1
                        add_log(f"✅ [板块] {filename} - 导入成功 ({result[0]} 条)")
                    else:
                        if result[1] > 0:  # skipped
                            add_log(f"⏭️ [板块] {filename} - 已存在，跳过")
                            imported_count += 1
                        else:
                            add_log(f"❌ [板块] {filename} - 导入失败", "error")
                            errors.append(f"{filename}: 导入返回失败")
                except Exception as e:
                    errors.append(f"[板块] {filename}: {str(e)}")
                    add_log(f"❌ [板块] {filename} - 错误: {str(e)}", "error")
        
        # 记录结果
        result = {
            "success": imported_count > 0,
            "message": f"导入完成: {imported_count}/{total_files} 个文件成功",
            "imported": imported_count,
            "total": total_files,
            "errors": errors if errors else None
        }
        
        import_status["last_import"] = datetime.now().isoformat()
        import_status["last_result"] = result
        import_status["history"].insert(0, {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result": result
        })
        
        # 只保留最近 10 条记录
        import_status["history"] = import_status["history"][:10]
        
        add_log(f"✅ {result['message']}")
        add_log(f"👤 操作用户: {username}")
        
        # 重载内存缓存（确保最新数据立即可用）
        add_log("🔄 正在重载内存缓存...")
        import_status["current_file"] = "重载缓存..."
        import_status["progress"] = 90
        try:
            from ..core.startup import preload_cache
            preload_cache()
            # v0.5.0: 清理统一缓存系统的 API 缓存和热点榜缓存
            cache.clear_api_cache()
            HotSpotsCache.clear_cache()
            add_log("✅ 内存缓存重载完成！新数据已生效 (含统一缓存)")
        except Exception as cache_error:
            add_log(f"⚠️ 缓存重载失败: {str(cache_error)}", "warning")
        
    except Exception as e:
        add_log(f"❌ 导入失败: {str(e)}", "error")
    finally:
        import_status["is_importing"] = False
        import_status["progress"] = 100
        import_status["current_file"] = None


@router.post("/import")
async def trigger_import(
    import_params: ImportRequest = None,
    current_user: User = Depends(require_admin)
):
    """
    触发数据导入（异步执行，立即返回）
    前端通过 /admin/import-status 轮询进度
    """
    global import_status
    
    if import_status["is_importing"]:
        raise HTTPException(status_code=400, detail="正在导入中，请稍后再试")
    
    # 初始化状态
    import_status["is_importing"] = True
    import_status["progress"] = 0
    import_status["current_file"] = "正在准备导入..."
    import_status["logs"] = []
    
    add_log("🚀 开始数据导入任务（后台执行）")
    
    # 使用 threading 在后台执行（加密网关不支持 BackgroundTasks）
    thread = threading.Thread(target=_do_import_task, args=(current_user.username,))
    thread.daemon = True
    thread.start()
    
    return {
        "success": True,
        "message": "导入任务已启动，请通过 /admin/import-status 查看进度",
        "status": "started"
    }


@router.get("/import-status")
async def get_import_status(current_user: User = Depends(require_admin)):
    """
    获取导入状态
    """
    return {
        "is_importing": import_status["is_importing"],
        "current_file": import_status["current_file"],
        "progress": import_status["progress"],
        "last_import": import_status["last_import"],
        "last_result": import_status["last_result"],
        "history": import_status["history"],
        "logs": import_status["logs"]  # 实时日志
    }


@router.get("/data-files")
async def list_data_files(current_user: User = Depends(require_admin)):
    """
    列出 data 目录中的文件
    """
    try:
        if not os.path.exists(DATA_DIR):
            return {"files": []}
        
        files = []
        for filename in os.listdir(DATA_DIR):
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(('.xlsx', '.xls')):
                stat = os.stat(filepath)
                files.append({
                    "name": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # 按修改时间倒序
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files}
        
    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


@router.delete("/data-files/{filename}")
async def delete_data_file(
    filename: str,
    current_user: User = Depends(require_admin)
):
    """
    删除 data 目录中的文件
    """
    try:
        # 防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        filepath = os.path.join(DATA_DIR, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        os.remove(filepath)
        logger.info(f"管理员 {current_user.username} 删除文件: {filename}")
        
        return {"success": True, "message": f"文件已删除: {filename}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.get("/dates")
async def get_imported_dates(current_user: User = Depends(require_admin)):
    """
    获取已导入数据的日期列表
    """
    try:
        from ..database import SessionLocal
        from sqlalchemy import text
        
        db = SessionLocal()
        try:
            # 查询已导入的日期
            result = db.execute(text("""
                SELECT DISTINCT date 
                FROM daily_stock_data 
                ORDER BY date DESC 
                LIMIT 30
            """))
            dates = [row[0].strftime("%Y-%m-%d") if hasattr(row[0], 'strftime') else str(row[0]) for row in result]
            
            return {"dates": dates}
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"获取日期列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取日期列表失败: {str(e)}")


@router.get("/login-history")
async def get_login_history(current_user: User = Depends(require_admin)):
    """
    获取用户登录历史和活跃会话
    仅管理员可访问
    """
    try:
        from ..database import SessionLocal
        from ..db_models import User as UserModel, UserSession
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        try:
            # 1. 获取所有用户信息
            users_query = db.query(
                UserModel.id,
                UserModel.username,
                UserModel.role,
                UserModel.is_active,
                UserModel.created_at,
                UserModel.last_login,
                func.count(UserSession.id).label('session_count')
            ).outerjoin(
                UserSession, UserModel.id == UserSession.user_id
            ).group_by(
                UserModel.id
            ).order_by(
                UserModel.last_login.desc().nullslast()
            ).all()
            
            users = []
            for u in users_query:
                users.append({
                    'id': u.id,
                    'username': u.username,
                    'role': u.role,
                    'is_active': u.is_active,
                    'created_at': u.created_at.isoformat() if u.created_at else None,
                    'last_login': u.last_login.isoformat() if u.last_login else None,
                    'session_count': u.session_count or 0
                })
            
            # 2. 获取所有活跃会话
            sessions_query = db.query(
                UserSession.id,
                UserSession.user_id,
                UserSession.device_id,
                UserSession.device_name,
                UserSession.created_at,
                UserSession.expires_at,
                UserSession.last_active,
                UserModel.username,
                UserModel.role
            ).join(
                UserModel, UserSession.user_id == UserModel.id
            ).order_by(
                UserSession.last_active.desc().nullslast()
            ).all()
            
            sessions = []
            for s in sessions_query:
                sessions.append({
                    'id': s.id,
                    'user_id': s.user_id,
                    'username': s.username,
                    'role': s.role,
                    'device_id': s.device_id,
                    'device_name': s.device_name,
                    'created_at': s.created_at.isoformat() if s.created_at else None,
                    'expires_at': s.expires_at.isoformat() if s.expires_at else None,
                    'last_active': s.last_active.isoformat() if s.last_active else None
                })
            
            # 3. 计算统计数据
            now = datetime.now()
            active_threshold = now - timedelta(hours=24)
            session_active_threshold = now - timedelta(hours=1)
            
            total_users = len(users)
            active_users = sum(1 for u in users if u['last_login'] and 
                             datetime.fromisoformat(u['last_login']) > active_threshold)
            total_sessions = len(sessions)
            active_sessions = sum(1 for s in sessions if s['last_active'] and 
                                datetime.fromisoformat(s['last_active']) > session_active_threshold)
            
            return {
                'success': True,
                'data': {
                    'users': users,
                    'sessions': sessions,
                    'stats': {
                        'totalUsers': total_users,
                        'activeUsers': active_users,
                        'totalSessions': total_sessions,
                        'activeSessions': active_sessions
                    }
                }
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"获取登录历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取登录历史失败: {str(e)}")


# ==================== 数据删除功能 ====================

class DeleteDataRequest(BaseModel):
    """删除数据请求"""
    dates: list[str]  # 日期列表，格式 YYYYMMDD 或 YYYY-MM-DD
    data_type: str = "all"  # stock, sector, all


@router.get("/data/preview/{date}")
async def preview_delete_data(
    date: str,
    data_type: str = "all",
    current_user: User = Depends(require_admin)
):
    """
    预览删除数据的影响
    
    Args:
        date: 日期，格式 YYYYMMDD 或 YYYY-MM-DD
        data_type: stock, sector, all
    """
    try:
        from ..database import SessionLocal
        from ..db_models import DailyStockData, SectorDailyData
        from sqlalchemy import func
        
        # 标准化日期格式
        date_str = date.replace("-", "")
        
        db = SessionLocal()
        try:
            result = {
                "date": date_str,
                "stock_count": 0,
                "sector_count": 0
            }
            
            if data_type in ["stock", "all"]:
                stock_count = db.query(func.count(DailyStockData.id)).filter(
                    func.to_char(DailyStockData.date, 'YYYYMMDD') == date_str
                ).scalar()
                result["stock_count"] = stock_count or 0
            
            if data_type in ["sector", "all"]:
                sector_count = db.query(func.count(SectorDailyData.id)).filter(
                    func.to_char(SectorDailyData.date, 'YYYYMMDD') == date_str
                ).scalar()
                result["sector_count"] = sector_count or 0
            
            result["total_count"] = result["stock_count"] + result["sector_count"]
            
            return {
                "success": True,
                "preview": result
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"预览删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预览删除失败: {str(e)}")


@router.delete("/data/{date}")
async def delete_data_by_date(
    date: str,
    data_type: str = "all",
    current_user: User = Depends(require_admin)
):
    """
    删除指定日期的数据
    
    Args:
        date: 日期，格式 YYYYMMDD 或 YYYY-MM-DD
        data_type: stock, sector, all
    """
    try:
        from ..database import SessionLocal
        from ..db_models import DailyStockData, SectorDailyData
        from sqlalchemy import func
        
        # 标准化日期格式
        date_str = date.replace("-", "")
        
        db = SessionLocal()
        try:
            result = {
                "date": date_str,
                "stock_deleted": 0,
                "sector_deleted": 0
            }
            
            if data_type in ["stock", "all"]:
                stock_deleted = db.query(DailyStockData).filter(
                    func.to_char(DailyStockData.date, 'YYYYMMDD') == date_str
                ).delete(synchronize_session=False)
                result["stock_deleted"] = stock_deleted
                logger.info(f"删除股票数据: {date_str}, {stock_deleted} 条")
            
            if data_type in ["sector", "all"]:
                sector_deleted = db.query(SectorDailyData).filter(
                    func.to_char(SectorDailyData.date, 'YYYYMMDD') == date_str
                ).delete(synchronize_session=False)
                result["sector_deleted"] = sector_deleted
                logger.info(f"删除板块数据: {date_str}, {sector_deleted} 条")
            
            db.commit()
            
            result["total_deleted"] = result["stock_deleted"] + result["sector_deleted"]
            
            # 更新导入状态
            try:
                from scripts.import_state_manager import ImportStateManager, reload_state_managers
                
                if data_type in ["stock", "all"]:
                    stock_state = ImportStateManager("data_import_state.json")
                    stock_state.mark_deleted(date_str, "manual_delete", current_user.username)
                
                if data_type in ["sector", "all"]:
                    sector_state = ImportStateManager("sector_import_state.json")
                    sector_state.mark_deleted(date_str, "manual_delete", current_user.username)
                
                # 刷新单例状态
                reload_state_managers()
                    
            except Exception as state_err:
                logger.warning(f"更新导入状态失败: {state_err}")
            
            logger.info(f"管理员 {current_user.username} 删除数据: {date_str}, 共 {result['total_deleted']} 条")
            
            # 重载缓存
            try:
                from ..core.startup import preload_cache
                logger.info("🔄 删除后重载缓存...")
                preload_cache()
                # v0.5.0: 清理统一缓存系统的 API 缓存和热点榜缓存
                cache.clear_api_cache()
                HotSpotsCache.clear_cache()
                logger.info("✅ 缓存重载完成 (含统一缓存)")
            except Exception as cache_err:
                logger.warning(f"⚠️ 缓存重载失败: {cache_err}")
            
            return {
                "success": True,
                "result": result,
                "message": f"已删除 {date_str} 的数据，共 {result['total_deleted']} 条"
            }
            
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除数据失败: {str(e)}")


@router.post("/data/delete-batch")
async def delete_data_batch(
    delete_req: DeleteDataRequest,
    current_user: User = Depends(require_admin)
):
    """
    批量删除多个日期的数据
    """
    try:
        from ..database import SessionLocal
        from ..db_models import DailyStockData, SectorDailyData
        from sqlalchemy import func
        
        results = []
        total_stock = 0
        total_sector = 0
        
        db = SessionLocal()
        try:
            for date in delete_req.dates:
                date_str = date.replace("-", "")
                result = {"date": date_str, "stock_deleted": 0, "sector_deleted": 0}
                
                if delete_req.data_type in ["stock", "all"]:
                    stock_deleted = db.query(DailyStockData).filter(
                        func.to_char(DailyStockData.date, 'YYYYMMDD') == date_str
                    ).delete(synchronize_session=False)
                    result["stock_deleted"] = stock_deleted
                    total_stock += stock_deleted
                
                if delete_req.data_type in ["sector", "all"]:
                    sector_deleted = db.query(SectorDailyData).filter(
                        func.to_char(SectorDailyData.date, 'YYYYMMDD') == date_str
                    ).delete(synchronize_session=False)
                    result["sector_deleted"] = sector_deleted
                    total_sector += sector_deleted
                
                results.append(result)
            
            db.commit()
            
            # 更新导入状态
            try:
                from scripts.import_state_manager import ImportStateManager, reload_state_managers
                
                if delete_req.data_type in ["stock", "all"]:
                    stock_state = ImportStateManager("data_import_state.json")
                    for date in delete_req.dates:
                        stock_state.mark_deleted(date.replace("-", ""), "batch_delete", current_user.username)
                
                if delete_req.data_type in ["sector", "all"]:
                    sector_state = ImportStateManager("sector_import_state.json")
                    for date in delete_req.dates:
                        sector_state.mark_deleted(date.replace("-", ""), "batch_delete", current_user.username)
                
                # 刷新单例状态（确保下次导入能正确读取 deleted 状态）
                reload_state_managers()
                        
            except Exception as state_err:
                logger.warning(f"更新导入状态失败: {state_err}")
            
            logger.info(f"管理员 {current_user.username} 批量删除数据: {len(delete_req.dates)} 天, 股票 {total_stock} 条, 板块 {total_sector} 条")
            
            # 重载缓存
            try:
                from ..core.startup import preload_cache
                logger.info("🔄 删除后重载缓存...")
                preload_cache()
                # v0.5.0: 清理统一缓存系统的 API 缓存和热点榜缓存
                cache.clear_api_cache()
                HotSpotsCache.clear_cache()
                logger.info("✅ 缓存重载完成 (含统一缓存)")
            except Exception as cache_err:
                logger.warning(f"⚠️ 缓存重载失败: {cache_err}")
            
            return {
                "success": True,
                "results": results,
                "summary": {
                    "dates_count": len(delete_req.dates),
                    "stock_deleted": total_stock,
                    "sector_deleted": total_sector,
                    "total_deleted": total_stock + total_sector
                },
                "message": f"已删除 {len(delete_req.dates)} 天的数据，共 {total_stock + total_sector} 条"
            }
            
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量删除数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量删除数据失败: {str(e)}")
