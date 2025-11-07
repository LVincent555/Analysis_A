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
    """记录所有HTTP请求"""
    import sys
    start_time = time.time()
    
    # 请求开始日志 - 强制输出到stderr
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"📨 收到请求: {request.method} {request.url.path}\n")
    if request.query_params:
        sys.stderr.write(f"📝 查询参数: {dict(request.query_params)}\n")
    sys.stderr.write(f"{'='*60}\n")
    sys.stderr.flush()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # 禁用浏览器缓存
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # 请求完成日志
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"✅ 响应完成: {request.method} {request.url.path}\n")
    sys.stderr.write(f"📊 状态码: {response.status_code}\n")
    sys.stderr.write(f"⏱️  耗时: {process_time:.3f}s\n")
    sys.stderr.write(f"{'='*60}\n\n")
    sys.stderr.flush()
    
    return response


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
app.include_router(rank_jump_router)
app.include_router(steady_rise_router)
app.include_router(sector_router)


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
