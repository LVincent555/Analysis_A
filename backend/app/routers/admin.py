"""
管理员路由 - 文件上传和数据导入
仅 admin 角色可访问
"""
import os
import base64
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth.dependencies import get_current_user
from ..db_models import User

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


@router.post("/import")
async def trigger_import(
    import_params: ImportRequest = None,
    current_user: User = Depends(require_admin)
):
    """
    触发数据导入（同时支持股票数据和板块数据）
    """
    global import_status
    
    if import_status["is_importing"]:
        raise HTTPException(status_code=400, detail="正在导入中，请稍后再试")
    
    try:
        import_status["is_importing"] = True
        import_status["progress"] = 0
        import_status["current_file"] = "正在准备导入..."
        import_status["logs"] = []  # 清空之前的日志
        
        add_log("🚀 开始数据导入任务")
        
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
                return {
                    "success": False,
                    "message": "没有找到待导入的 Excel 文件（支持股票数据和板块数据）"
                }
            
            total_files = len(all_files)
            imported_count = 0
            errors = []
            
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
                    import_status["progress"] = int((i / total_files) * 50)
                    
                    try:
                        result = import_stock_file(filepath, state_manager)
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
                    import_status["progress"] = int(50 + (i / total_files) * 50)
                    
                    try:
                        result = import_sector_file(filepath, sector_state_manager)
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
            add_log(f"👤 操作用户: {current_user.username}")
            
            # 重载内存缓存（确保最新数据立即可用）
            add_log("🔄 正在重载内存缓存...")
            import_status["current_file"] = "重载缓存..."
            try:
                from ..core.startup import preload_cache
                preload_cache()
                add_log("✅ 内存缓存重载完成！新数据已生效")
            except Exception as cache_error:
                add_log(f"⚠️ 缓存重载失败: {str(cache_error)}", "warning")
            
            return result
            
        finally:
            import_status["is_importing"] = False
            import_status["progress"] = 100
            import_status["current_file"] = None
            
    except Exception as e:
        import_status["is_importing"] = False
        add_log(f"❌ 导入失败: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


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
