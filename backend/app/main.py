"""
应用主入口文件
"""
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import PROJECT_NAME, VERSION, ALLOWED_ORIGINS, API_REQUIRE_AUTH, ENABLE_DOCS
from .middleware import AuthMiddleware
from .contexts.analysis.api.basic_router import router as basic_analysis_router
from .contexts.analysis.api.hot_spots_router import router as hot_spots_router
from .contexts.analysis.api.industry_detail_router import router as industry_detail_router
from .contexts.analysis.api.industry_router import router as industry_router
from .contexts.analysis.api.rank_router import rank_jump_router, steady_rise_router
from .contexts.analysis.api.strategy_router import router as strategies_router
from .contexts.identity.api.router import router as identity_router
from .contexts.identity.api.login_history_router import router as login_history_router
from .contexts.market_data.api.admin_router import router as market_data_admin_router
from .contexts.market_data.api.sector_router import router as sector_router
from .contexts.market_data.api.stock_router import router as stock_router
from .contexts.market_data.api.sync_router import router as sync_router
from .contexts.operations.api.cache_router import router as cache_mgmt_router
from .routers.secure import router as secure_router
from .contexts.operations.api.log_router import router as log_mgmt_router
from .contexts.operations.api.config_router import router as config_mgmt_router
from .contexts.board_heat.api.management_router import router as ext_board_mgmt_router
from .contexts.board_heat.api.query_router import router as board_heat_router
from .core import preload_cache, run_startup_checks
from .core.security_settings import validate_runtime_security_config
from .core.logging_config import setup_logging
from .core.caching import cache, init_default_cache_regions
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
    - L1 内存: sessions, session_keys, users, config
    - L2 磁盘: api_response, reports
    """
    region_names = init_default_cache_regions(Path(__file__).resolve().parent)
    
    logger.info("✅ 统一缓存系统初始化完成")
    logger.info(f"   已注册分区: {region_names}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ========== 启动时执行 ==========
    logger.info("应用启动中...")

    # 0. 安全配置校验
    validate_runtime_security_config()
    
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
    if os.getenv("PRELOAD_CACHE_ON_STARTUP", "true").lower() == "false":
        logger.warning("⚠️ 已跳过启动 Numpy 缓存预热 (PRELOAD_CACHE_ON_STARTUP=false)")
    else:
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
app.include_router(basic_analysis_router)
app.include_router(hot_spots_router)
app.include_router(stock_router)
app.include_router(industry_router)
app.include_router(industry_detail_router)  # 板块成分股详细分析
app.include_router(rank_jump_router)
app.include_router(steady_rise_router)
app.include_router(sector_router)
app.include_router(cache_mgmt_router)  # 缓存管理API
app.include_router(strategies_router)  # 策略模块（单针下二十等）
app.include_router(identity_router)  # Identity（认证/用户/会话/角色）
app.include_router(secure_router)  # 加密网关（统一加密入口）
app.include_router(sync_router)  # 数据同步（离线功能）
app.include_router(market_data_admin_router)  # 管理员模块（文件上传/导入）
app.include_router(login_history_router)  # 登录历史管理
app.include_router(log_mgmt_router)  # 操作日志模块（v1.1.0）
app.include_router(config_mgmt_router)  # 系统配置模块（v1.1.0）
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
