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
from .core import preload_cache, run_startup_checks
from .core.logging_config import setup_logging

# 配置日志系统（控制台INFO，文件DEBUG）
setup_logging(console_level=logging.INFO, file_level=logging.DEBUG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")
    
    # 1. 数据导入和一致性检验
    if not run_startup_checks():
        logger.error("❌ 启动检查失败，请检查数据库和数据文件")
        raise RuntimeError("启动检查失败")
    
    # 2. 预加载缓存
    preload_cache()
    
    logger.info("✅ 应用启动完成！")
    yield
    # 关闭时执行
    logger.info("应用关闭")


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
