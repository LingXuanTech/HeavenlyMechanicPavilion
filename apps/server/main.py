import os
import structlog
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from config.settings import settings
from api.exceptions import AppException
from services.data_router import close_http_client
from services.cache_service import cache_service
from services.task_queue import task_queue
from services.scheduler import watchlist_scheduler
from db.models import init_db

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Stock Agents Monitoring Dashboard API", env=settings.ENV)
    # Initialize DB
    init_db()
    # Initialize Scheduler, etc.
    watchlist_scheduler.start()
    yield
    # Shutdown logic
    logger.info("Shutting down API")
    watchlist_scheduler.shutdown()
    await close_http_client()
    await cache_service.close()
    await task_queue.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# =============================================================================
# 全局异常处理器
# =============================================================================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理应用自定义异常"""
    logger.warning(
        "Application exception",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__} if settings.ENV == "development" else {}
            }
        }
    )

# =============================================================================
# 中间件
# =============================================================================

from api.middleware import RequestTracingMiddleware
app.add_middleware(RequestTracingMiddleware)

from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
assets_path = os.path.join(os.path.dirname(__file__), "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

@app.get("/")
async def root():
    return {"message": "Stock Agents API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# =============================================================================
# 路由注册 (分组重构)
# =============================================================================

from api.routes import market, analysis, trading, system

# 1. 市场数据模块
app.include_router(market.router, prefix=settings.API_V1_STR)

# 2. 分析决策模块
app.include_router(analysis.router, prefix=settings.API_V1_STR)

# 3. 交易执行模块
app.include_router(trading.router, prefix=settings.API_V1_STR)

# 4. 系统服务模块
app.include_router(system.router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
