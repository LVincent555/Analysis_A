"""
应用主入口文件
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import PROJECT_NAME, VERSION, ALLOWED_ORIGINS
from .routers import analysis_router, stock_router, industry_router, rank_jump_router, steady_rise_router, sector_router
from .routers.cache_mgmt import router as cache_mgmt_router
from .routers.industry_detail import router as industry_detail_router
from .core import preload_cache, run_startup_checks

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
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
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    description="A股数据分析系统API",
    lifespan=lifespan
)

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

# 注册路由
app.include_router(analysis_router)
app.include_router(stock_router)
app.include_router(industry_router)
app.include_router(industry_detail_router)  # 板块成分股详细分析
app.include_router(rank_jump_router)
app.include_router(steady_rise_router)
app.include_router(sector_router)
app.include_router(cache_mgmt_router)  # 缓存管理API


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
