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

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # 支持上下文变量（request_id）
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

from services.scheduler import watchlist_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Stock Agents Monitoring Dashboard API", env=settings.ENV)
    # Initialize DB, Scheduler, etc.
    watchlist_scheduler.start()
    yield
    # Shutdown logic
    logger.info("Shutting down API")
    watchlist_scheduler.shutdown()
    await close_http_client()  # 关闭共享 HTTP 客户端
    await cache_service.close()  # 关闭缓存连接

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

# 请求追踪（必须在 CORS 之前添加，以确保所有请求都有 request_id）
from api.middleware import RequestTracingMiddleware
app.add_middleware(RequestTracingMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for agent avatars and other assets
assets_path = os.path.join(os.path.dirname(__file__), "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

@app.get("/")
async def root():
    return {"message": "Stock Agents API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Import and include routers
from api.routes import analyze, watchlist, market
from db.models import init_db

app.include_router(analyze.router, prefix=settings.API_V1_STR)
app.include_router(watchlist.router, prefix=settings.API_V1_STR)
app.include_router(market.router, prefix=settings.API_V1_STR)

from api.routes import discover, news, chat
app.include_router(discover.router, prefix=settings.API_V1_STR)
app.include_router(news.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)

from api.routes import portfolio
app.include_router(portfolio.router, prefix=settings.API_V1_STR)

from api.routes import macro
app.include_router(macro.router, prefix=settings.API_V1_STR)

from api.routes import memory
app.include_router(memory.router, prefix=settings.API_V1_STR)

from api.routes import admin
from api.dependencies import verify_api_key
# Admin 路由需要 API Key 认证
app.include_router(
    admin.router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)]
)

from api.routes import settings as settings_routes
app.include_router(settings_routes.router, prefix=settings.API_V1_STR)

from api.routes import market_watcher
app.include_router(market_watcher.router, prefix=settings.API_V1_STR)

from api.routes import news_aggregator
app.include_router(news_aggregator.router, prefix=settings.API_V1_STR)

from api.routes import health as health_routes
app.include_router(health_routes.router, prefix=settings.API_V1_STR)

from api.routes import ai_config
app.include_router(ai_config.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
