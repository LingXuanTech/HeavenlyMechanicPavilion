"""自动交易 API 端点."""

import asyncio
import logging
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..db.models import User, UserRole
from ..dependencies import get_event_manager, get_graph_service
from ..schemas.auto_trading import (
    AutoTradingStatusResponse,
    RunOnceRequest,
    RunOnceResponse,
    StartAutoTradingRequest,
    StopAutoTradingRequest,
    TradingCycleResult,
)
from ..security.dependencies import get_current_active_user, require_role
from ..services.auto_trading_orchestrator import AutoTradingOrchestrator
from ..services.events import SessionEventManager
from ..services.graph import TradingGraphService
from ..services.trading_session import TradingSessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auto-trading", tags=["auto-trading"])

# 全局状态管理 - 追踪活跃的自动交易任务
active_trading_tasks: Dict[int, Dict] = {}


def get_orchestrator(
    graph_service: TradingGraphService = Depends(get_graph_service),
    event_manager: SessionEventManager = Depends(get_event_manager),
) -> AutoTradingOrchestrator:
    """获取自动交易协调器实例.
    
    Args:
        graph_service: Agent 图谱服务
        event_manager: 事件管理器
        
    Returns:
        AutoTradingOrchestrator 实例
    """
    from ..services.market_calendar import MarketCalendarService
    
    trading_session_service = TradingSessionService()
    
    # 尝试获取市场日历服务
    market_calendar = None
    try:
        # 从 trading_session_service 中获取 broker 的 trading_client
        # 如果有活跃的会话，使用其 market_calendar
        if trading_session_service.active_sessions:
            first_session_id = next(iter(trading_session_service.active_sessions))
            execution_service = trading_session_service.get_execution_service(first_session_id)
            if execution_service and hasattr(execution_service.broker, 'market_calendar'):
                market_calendar = execution_service.broker.market_calendar
    except Exception as e:
        logger.warning(f"无法初始化市场日历服务: {e}")
    
    return AutoTradingOrchestrator(
        graph_service=graph_service,
        trading_session_service=trading_session_service,
        event_manager=event_manager,
        market_calendar=market_calendar,
    )


@router.post("/start", response_model=AutoTradingStatusResponse)
async def start_auto_trading(
    request: StartAutoTradingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    orchestrator: AutoTradingOrchestrator = Depends(get_orchestrator),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
):
    """
    启动自动交易.
    
    系统将自动循环执行: Agent分析 → 决策提取 → 订单执行
    - 可设置执行间隔 (默认30分钟)
    - 可设置是否仅在交易时间内运行
    - 需要先创建交易会话 (trading_session_id)
    
    Args:
        request: 启动自动交易请求
        background_tasks: FastAPI 后台任务管理器
        db: 数据库会话
        orchestrator: 自动交易协调器
        
    Returns:
        自动交易状态响应
        
    Raises:
        HTTPException: 如果portfolio已有运行中的自动交易
    """
    portfolio_id = request.portfolio_id
    
    # 检查是否已在运行
    if portfolio_id in active_trading_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Portfolio {portfolio_id} 的自动交易已在运行中",
        )
    
    logger.info(
        f"启动自动交易 - Portfolio: {portfolio_id}, "
        f"Symbols: {request.symbols}, "
        f"Interval: {request.interval_minutes}分钟, "
        f"Session: {request.trading_session_id}"
    )
    
    # 在后台任务中启动连续交易
    async def run_continuous_trading():
        """后台任务: 运行连续自动交易."""
        try:
            await orchestrator.start_continuous_trading(
                db=db,
                portfolio_id=portfolio_id,
                symbols=request.symbols,
                interval_minutes=request.interval_minutes,
                trading_hours_only=request.trading_hours_only,
                trading_session_id=request.trading_session_id,
            )
        except Exception as e:
            logger.error(
                f"连续自动交易失败 - Portfolio: {portfolio_id}, Error: {e}",
                exc_info=True,
            )
            # 清理状态
            active_trading_tasks.pop(portfolio_id, None)
    
    # 创建并启动后台任务
    task = asyncio.create_task(run_continuous_trading())
    
    active_trading_tasks[portfolio_id] = {
        "symbols": request.symbols,
        "interval_minutes": request.interval_minutes,
        "trading_session_id": request.trading_session_id,
        "started_at": None,  # Will be set by orchestrator
        "task": task,
    }
    
    return AutoTradingStatusResponse(
        status="running",
        portfolio_id=portfolio_id,
        symbols=request.symbols,
        interval_minutes=request.interval_minutes,
    )


@router.post("/stop", response_model=AutoTradingStatusResponse)
async def stop_auto_trading(
    request: StopAutoTradingRequest,
    orchestrator: AutoTradingOrchestrator = Depends(get_orchestrator),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
):
    """
    停止自动交易.
    
    Args:
        request: 停止自动交易请求
        orchestrator: 自动交易协调器
        
    Returns:
        自动交易状态响应
        
    Raises:
        HTTPException: 如果portfolio没有运行中的自动交易
    """
    portfolio_id = request.portfolio_id
    
    if portfolio_id not in active_trading_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio {portfolio_id} 没有运行中的自动交易",
        )
    
    logger.info(f"停止自动交易 - Portfolio: {portfolio_id}")
    
    # 停止协调器
    orchestrator.stop_continuous_trading(portfolio_id)
    
    # 获取任务信息
    task_info = active_trading_tasks.pop(portfolio_id)
    
    # 取消后台任务
    if "task" in task_info:
        task = task_info["task"]
        if not task.done():
            task.cancel()
    
    return AutoTradingStatusResponse(
        status="stopped",
        portfolio_id=portfolio_id,
        symbols=task_info.get("symbols"),
    )


@router.get("/status/{portfolio_id}", response_model=AutoTradingStatusResponse)
async def get_auto_trading_status(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
):
    """
    查询自动交易状态.
    
    Args:
        portfolio_id: 投资组合ID
        
    Returns:
        自动交易状态响应
    """
    if portfolio_id in active_trading_tasks:
        task_info = active_trading_tasks[portfolio_id]
        return AutoTradingStatusResponse(
            status="running",
            portfolio_id=portfolio_id,
            symbols=task_info.get("symbols"),
            interval_minutes=task_info.get("interval_minutes"),
            started_at=task_info.get("started_at"),
        )
    else:
        return AutoTradingStatusResponse(
            status="stopped",
            portfolio_id=portfolio_id,
        )


@router.post("/run-once", response_model=RunOnceResponse)
async def run_once(
    request: RunOnceRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: AutoTradingOrchestrator = Depends(get_orchestrator),
    current_user: User = Depends(require_role(UserRole.TRADER, UserRole.ADMIN)),
):
    """
    手动触发一次完整的分析+交易流程.
    
    适用于:
    - 测试自动交易功能
    - 即时执行特定标的的分析和交易
    - 不启动连续循环
    
    Args:
        request: 单次执行请求
        db: 数据库会话
        orchestrator: 自动交易协调器
        
    Returns:
        单次执行响应，包含每个标的的执行结果
    """
    logger.info(
        f"手动触发单次交易 - Portfolio: {request.portfolio_id}, "
        f"Symbols: {request.symbols}"
    )
    
    # 检查市场状态（如果配置了市场日历服务）
    if orchestrator.market_calendar:
        try:
            is_open = await orchestrator.market_calendar.is_market_open()
            if not is_open:
                next_open = await orchestrator.market_calendar.get_next_market_open()
                logger.warning(
                    f"市场当前关闭，下次开盘时间: {next_open}"
                )
                # 仍然允许执行，但记录警告
        except Exception as e:
            logger.warning(f"无法检查市场状态: {e}")
    
    try:
        results = await orchestrator.run_single_cycle(
            db=db,
            portfolio_id=request.portfolio_id,
            symbols=request.symbols,
            trading_session_id=request.trading_session_id,
        )
        
        # 转换为响应格式
        cycle_results = [
            TradingCycleResult(**result) for result in results
        ]
        
        # 计算执行摘要
        summary = {
            "total": len(cycle_results),
            "executed": sum(1 for r in cycle_results if r.status == "executed"),
            "filtered": sum(1 for r in cycle_results if r.status == "filtered"),
            "no_action": sum(1 for r in cycle_results if r.status == "no_action"),
            "error": sum(1 for r in cycle_results if r.status == "error"),
            "timeout": sum(1 for r in cycle_results if r.status == "timeout"),
        }
        
        from datetime import datetime
        return RunOnceResponse(
            portfolio_id=request.portfolio_id,
            results=cycle_results,
            executed_at=datetime.utcnow(),
            summary=summary,
        )
        
    except Exception as e:
        logger.error(
            f"单次交易执行失败: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败: {str(e)}",
        )


@router.get("/active", response_model=Dict[int, AutoTradingStatusResponse])
async def list_active_trading(
    current_user: User = Depends(get_current_active_user),
):
    """
    列出所有活跃的自动交易.
    
    Returns:
        活跃自动交易的映射 (portfolio_id -> status)
    """
    result = {}
    for portfolio_id, task_info in active_trading_tasks.items():
        result[portfolio_id] = AutoTradingStatusResponse(
            status="running",
            portfolio_id=portfolio_id,
            symbols=task_info.get("symbols"),
            interval_minutes=task_info.get("interval_minutes"),
            started_at=task_info.get("started_at"),
        )
    return result