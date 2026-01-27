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
