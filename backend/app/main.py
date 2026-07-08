"""
应用主入口文件
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import PROJECT_NAME, VERSION, ALLOWED_ORIGINS, API_REQUIRE_AUTH, ENABLE_DOCS
from .routers import analysis_router, stock_router, industry_router, rank_jump_router, steady_rise_router, sector_router
from .middleware import AuthMiddleware
from .routers.cache_mgmt import router as cache_mgmt_router
from .routers.industry_detail import router as industry_detail_router
from .routers.strategies import router as strategies_router
from .routers.auth import router as auth_router
from .routers.secure import router as secure_router
from .routers.sync import router as sync_router
from .routers.admin import router as admin_router
from .routers.user_mgmt import router as user_mgmt_router
from .routers.session_mgmt import router as session_mgmt_router
from .routers.log_mgmt import router as log_mgmt_router
from .routers.config_mgmt import router as config_mgmt_router
from .routers.role_mgmt import router as role_mgmt_router
from .routers.ext_board_mgmt import router as ext_board_mgmt_router
from .routers.board_heat import router as board_heat_router
from .core import preload_cache, run_startup_checks
from .core.logging_config import setup_logging
from .core.caching import cache
from .core.caching.manager import UnifiedCache
from .core.caching.store import ObjectStore, FileStore
from .core.caching.policies import WriteBehindPolicy, CacheAsidePolicy, WriteThroughPolicy
from .core.caching.syncer import get_syncer, start_syncer, stop_syncer
from .core.audit import audit_log, create_audit_sync_callback
from .database import SessionLocal

# 配置日志系统（控制台INFO，文件DEBUG）
setup_logging(console_level=logging.INFO, file_level=logging.DEBUG)
logger = logging.getLogger(__name__)


def init_cache_system():
    """
    初始化统一缓存系统
    
    注册所有缓存分区:
    - L1 内存: sessions, users, config
    - L2 磁盘: api_response, reports
    """
    import os
    
    # 1. 注册会话心跳缓存 (Write-Behind, 不自动过期)
    # 仅用于 session_id -> last_active/status/ip 等高频心跳状态，后台同步到 user_sessions。
    UnifiedCache.register(
        "sessions",
        ObjectStore("sessions", WriteBehindPolicy(ttl=0, sync_interval=10))
    )

    # 2. 注册加密会话密钥缓存 (Write-Through, 不自动过期)
    # session_key 是 /api/secure 解密所需的运行时密钥，按 user_id:device_id 存储。
    # 不放入 sessions 分区，避免被 Write-Behind 同步器误写到 user_sessions 表。
    UnifiedCache.register(
        "session_keys",
        ObjectStore("session_keys", WriteThroughPolicy(ttl=0))
    )
    
    # 3. 注册用户缓存 (Cache-Aside, 1小时过期)
    UnifiedCache.register(
        "users",
        ObjectStore("users", CacheAsidePolicy(ttl=3600))
    )
    
    # 4. [v2.2.1] 配置缓存改用 Write-Through (TTL=0 永不过期)
    # 这样 reload_configs() 调用 set() 时会真正写入内存，而非删除
    UnifiedCache.register(
        "config",
        ObjectStore("config", WriteThroughPolicy(ttl=0))
    )
    
    # 5. 注册 API 响应缓存 (磁盘, 200MB上限)
    cache_dir = os.path.join(os.path.dirname(__file__), ".cache", "api")
    UnifiedCache.register(
        "api_response",
        FileStore("api_response", cache_dir=cache_dir, size_limit_gb=0.2)
    )
    
    # 6. 注册报表文件缓存 (磁盘, 500MB上限)
    report_cache_dir = os.path.join(os.path.dirname(__file__), ".cache", "reports")
    UnifiedCache.register(
        "reports",
        FileStore("reports", cache_dir=report_cache_dir, size_limit_gb=0.5)
    )
    
    logger.info("✅ 统一缓存系统初始化完成")
    logger.info(f"   已注册分区: {UnifiedCache.region_names()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ========== 启动时执行 ==========
    logger.info("应用启动中...")
    
    # 1. 数据导入和一致性检验
    if not run_startup_checks():
        logger.error("❌ 启动检查失败，请检查数据库和数据文件")
        raise RuntimeError("启动检查失败")
    
    # 2. 初始化统一缓存系统
    init_cache_system()
    
    # 3. [v2.2.1] 预热系统配置到内存
    db = SessionLocal()
    try:
        cache.reload_configs(db)
        logger.info("✅ 系统配置预热完成 (Write-Through)")
    except Exception as e:
        logger.error(f"❌ 配置预热失败: {e}")
    finally:
        db.close()
    
    # 4. 预加载 Numpy 缓存 (原有逻辑)
    preload_cache()
    
    # 5. 配置并启动数据库同步器
    syncer = get_syncer()
    syncer.set_audit_sync_callback(create_audit_sync_callback(audit_log))
    start_syncer()
    logger.info("✅ 数据库同步器已启动")
    
    logger.info("✅ 应用启动完成！")
    
    yield
    
    # ========== 关闭时执行 ==========
    logger.info("应用关闭中...")
    
    # 1. 停止同步器 (会先执行 force_sync)
    stop_syncer()
    logger.info("✅ 数据库同步器已停止")
    
    logger.info("应用关闭完成")


# 创建FastAPI应用
# 根据 ENABLE_DOCS 配置决定是否启用 Swagger/OpenAPI 文档
# 本地开发：ENABLE_DOCS=true python -m uvicorn app.main:app --reload
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="A股数据分析系统API",
    lifespan=lifespan,
    # 生产环境禁用文档
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None
)

# 日志记录文档状态
logger.info(f"API文档状态: {'启用' if ENABLE_DOCS else '禁用'} (设置 ENABLE_DOCS=true 启用)")

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录慢请求和错误（优化版-减少90%日志IO）"""
    import sys
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # 禁用浏览器缓存
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # 🔥 优化：只记录慢请求(>0.5s)或错误请求，减少90%磁盘IO
    if process_time > 0.5 or response.status_code >= 400:
        sys.stderr.write(f"\n⚠️  {request.method} {request.url.path} - {process_time:.3f}s - {response.status_code}\n")
        if request.query_params:
            sys.stderr.write(f"   参数: {dict(request.query_params)}\n")
        sys.stderr.flush()
    
    return response


# 🔥 优化：添加Gzip压缩中间件，减少带宽占用50-80%
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)  # 1KB以上压缩

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加认证中间件（根据配置决定是否强制认证）
app.add_middleware(AuthMiddleware)
logger.info(f"🔐 API认证模式: {'强制认证' if API_REQUIRE_AUTH else '开放访问'}")

# 注册路由
app.include_router(analysis_router)
app.include_router(stock_router)
app.include_router(industry_router)
app.include_router(industry_detail_router)  # 板块成分股详细分析
app.include_router(rank_jump_router)
app.include_router(steady_rise_router)
app.include_router(sector_router)
app.include_router(cache_mgmt_router)  # 缓存管理API
app.include_router(strategies_router)  # 策略模块（单针下二十等）
app.include_router(auth_router)  # 认证模块（登录/注册）
app.include_router(secure_router)  # 加密网关（统一加密入口）
app.include_router(sync_router)  # 数据同步（离线功能）
app.include_router(admin_router)  # 管理员模块（文件上传/导入）
app.include_router(user_mgmt_router)  # 用户管理模块（v1.1.0）
app.include_router(session_mgmt_router)  # 会话管理模块（v1.1.0）
app.include_router(log_mgmt_router)  # 操作日志模块（v1.1.0）
app.include_router(config_mgmt_router)  # 系统配置模块（v1.1.0）
app.include_router(role_mgmt_router)  # 角色权限模块（v1.1.0）
app.include_router(ext_board_mgmt_router)  # 外部板块同步模块
app.include_router(board_heat_router)  # 板块热度API（多对多系统）


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": PROJECT_NAME,
        "version": VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 挂载客户端更新文件目录（用于 Electron 自动更新）
UPDATES_DIR = Path("/var/www/stock-analysis/updates")
if UPDATES_DIR.exists():
    app.mount("/updates", StaticFiles(directory=str(UPDATES_DIR)), name="updates")
    logger.info(f"📦 客户端更新目录已挂载: {UPDATES_DIR}")
