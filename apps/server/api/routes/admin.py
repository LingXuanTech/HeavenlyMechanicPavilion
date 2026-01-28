import os
import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException

from services.scheduler import watchlist_scheduler

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = structlog.get_logger()


@router.post("/trigger-daily-analysis")
async def trigger_daily_analysis(background_tasks: BackgroundTasks):
    """手动触发每日全量分析"""
    background_tasks.add_task(watchlist_scheduler.run_daily_analysis)
    return {"status": "accepted", "message": "Daily analysis triggered"}


@router.get("/scheduler/jobs")
async def get_scheduler_jobs():
    """获取所有调度任务"""
    return {"jobs": watchlist_scheduler.get_jobs()}


@router.get("/scheduler/status")
async def get_scheduler_status():
    """获取调度器状态"""
    return {
        "running": watchlist_scheduler.scheduler.running,
        "analysis_in_progress": watchlist_scheduler._analysis_running,
        "jobs_count": len(watchlist_scheduler.scheduler.get_jobs())
    }


# ============ 可观测性端点 ============

@router.get("/observability/langsmith-status")
async def get_langsmith_status():
    """获取 LangSmith 连接状态"""
    try:
        from services.langsmith_service import langsmith_service
        return langsmith_service.get_status()
    except Exception as e:
        logger.error("Failed to get LangSmith status", error=str(e))
        return {
            "enabled": False,
            "status": "error",
            "error": str(e),
        }


@router.post("/observability/langsmith-refresh")
async def refresh_langsmith():
    """刷新 LangSmith 连接"""
    try:
        from services.langsmith_service import langsmith_service
        return langsmith_service.refresh()
    except Exception as e:
        logger.error("Failed to refresh LangSmith", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observability/token-usage")
async def get_token_usage():
    """获取 Token 消耗摘要"""
    try:
        from services.token_monitor import token_monitor
        return token_monitor.get_usage_summary()
    except Exception as e:
        logger.error("Failed to get token usage", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observability/token-usage/{model}")
async def get_model_token_usage(model: str):
    """获取特定模型的 Token 消耗"""
    try:
        from services.token_monitor import token_monitor
        stats = token_monitor.get_model_stats(model)
        if stats is None:
            raise HTTPException(status_code=404, detail=f"No stats found for model: {model}")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get model token usage", error=str(e), model=model)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/observability/token-usage/reset")
async def reset_token_usage():
    """重置 Token 消耗统计"""
    try:
        from services.token_monitor import token_monitor
        return token_monitor.reset()
    except Exception as e:
        logger.error("Failed to reset token usage", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observability/summary")
async def get_observability_summary():
    """获取可观测性总览"""
    try:
        from services.langsmith_service import langsmith_service
        from services.token_monitor import token_monitor

        return {
            "langsmith": langsmith_service.get_status(),
            "token_usage": token_monitor.get_usage_summary(),
        }
    except Exception as e:
        logger.error("Failed to get observability summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
