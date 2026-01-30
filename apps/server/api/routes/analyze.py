import asyncio
import json
import os
import time
import uuid
import structlog
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import AsyncGenerator, Optional, Iterator, Any, List, Literal
from pydantic import BaseModel, Field
from sse_starlette.sse import ServerSentEvent, EventSourceResponse
from sqlmodel import Session, select
from api.sse import sse_manager
from services.synthesizer import synthesizer, SynthesisContext
from services.memory_service import memory_service, layered_memory, AnalysisMemory
from services.cache_service import cache_service
from services.data_router import MarketRouter
from services.market_analyst_router import MarketAnalystRouter
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from config.settings import settings
from db.models import AnalysisResult, engine, get_session
from services.accuracy_tracker import accuracy_tracker
from services.task_queue import task_queue

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = structlog.get_logger()

# Thread pool for running synchronous graph execution
_graph_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="graph_worker")

# 是否使用任务队列（生产环境）而非 BackgroundTasks（开发环境）
# 当配置了 REDIS_URL 且 USE_TASK_QUEUE=true 时启用
USE_TASK_QUEUE = bool(settings.REDIS_URL) and os.getenv("USE_TASK_QUEUE", "false").lower() == "true"


async def async_stream_wrapper(sync_iterator: Iterator[Any]) -> AsyncGenerator[Any, None]:
    """将同步迭代器包装为异步生成器，避免阻塞事件循环。

    使用线程池执行同步迭代器的 next() 调用，让事件循环可以处理其他任务。
    """
    loop = asyncio.get_event_loop()

    def get_next():
        try:
            return next(sync_iterator), False
        except StopIteration:
            return None, True

    while True:
        result, done = await loop.run_in_executor(_graph_executor, get_next)
        if done:
            break
        yield result


async def run_analysis_task(
    task_id: str,
    symbol: str,
    trade_date: str,
    override_analysts: Optional[list] = None,
    exclude_analysts: Optional[list] = None,
    analysis_level: Literal["L1", "L2"] = "L2",
    use_planner: bool = True,
):
    """执行分析任务并将结果保存到数据库

    Args:
        task_id: 任务唯一 ID
        symbol: 股票代码
        trade_date: 分析日期
        override_analysts: 完全覆盖默认分析师配置
        exclude_analysts: 排除指定分析师
        analysis_level: 分析深度级别 (L1: 快速扫描, L2: 完整分析)
        use_planner: 是否使用 Planner 动态选择分析师
    """
    logger.info(
        "Starting analysis task",
        task_id=task_id,
        symbol=symbol,
        analysis_level=analysis_level,
        use_planner=use_planner,
    )
    start_time = time.time()

    # 初始化任务状态（缓存层）和 SSE 事件队列（分布式）
    await cache_service.set_task(task_id, {"status": "running", "symbol": symbol, "progress": 0})
    await cache_service.init_sse_task(task_id, symbol)

    try:
        # 获取历史反思信息（用于增强分析决策）
        historical_reflection = ""
        if memory_service.is_available():
            try:
                reflection = await memory_service.generate_reflection(symbol)
                if reflection:
                    # 格式化反思信息供 Agent 使用
                    historical_reflection = f"""
## 历史分析反思 (基于 {len(reflection.historical_analyses)} 条历史记录)

### 识别的模式
{chr(10).join(f"- {p}" for p in reflection.patterns)}

### 历史教训
{chr(10).join(f"- {l}" for l in reflection.lessons)}

### 置信度调整建议: {reflection.confidence_adjustment:+d}%
"""
                    logger.info("Historical reflection loaded", symbol=symbol, patterns=len(reflection.patterns))
            except Exception as ref_err:
                logger.warning("Failed to load reflection", error=str(ref_err))

        # Initialize graph with custom config if needed
        config = DEFAULT_CONFIG.copy()
        config["analysis_level"] = analysis_level
        config["use_planner"] = use_planner
        market = MarketRouter.get_market(symbol)

        # 使用智能路由器选择分析师
        selected_analysts = MarketAnalystRouter.get_analysts(
            symbol=symbol,
            override_analysts=override_analysts,
            exclude_analysts=exclude_analysts,
        )
        logger.info(
            "Analyst selection",
            symbol=symbol,
            market=market,
            analysts=selected_analysts,
            override=override_analysts is not None,
        )

        ta = TradingAgentsGraph(
            selected_analysts=selected_analysts,
            debug=True,
            config=config,
            market=market,
        )

        # Initial state (with historical reflection and market)
        init_state = ta.propagator.create_initial_state(
            symbol, trade_date, market=market, historical_reflection=historical_reflection
        )
        args = ta.propagator.get_graph_args()

        agent_reports = {}

        # Stream graph execution (wrapped in async to avoid blocking event loop)
        sync_stream = ta.graph.stream(init_state, **args)
        async for chunk in async_stream_wrapper(sync_stream):
            for node_name, node_data in chunk.items():
                logger.info("Graph node completed", node=node_name)

                # Map node names to frontend stages
                stage_map = {
                    "Macro Analyst": "stage_analyst",
                    "Market Analyst": "stage_analyst",
                    "News Analyst": "stage_analyst",
                    "Fundamentals Analyst": "stage_analyst",
                    "Social Analyst": "stage_analyst",
                    "Sentiment Analyst": "stage_analyst",  # A股散户情绪分析师
                    "Policy Analyst": "stage_analyst",     # A股政策分析师
                    "Bull Researcher": "stage_debate",
                    "Bear Researcher": "stage_debate",
                    "Risk Judge": "stage_risk",
                    "Portfolio Agent": "stage_final",
                    "Trader": "stage_final"
                }

                current_stage = stage_map.get(node_name, "progress")

                # Collect reports for synthesis
                if "macro_report" in node_data:
                    agent_reports["macro"] = node_data["macro_report"]
                if "market_report" in node_data:
                    agent_reports["market"] = node_data["market_report"]
                if "news_report" in node_data:
                    agent_reports["news"] = node_data["news_report"]
                if "fundamentals_report" in node_data:
                    agent_reports["fundamentals"] = node_data["fundamentals_report"]
                if "portfolio_report" in node_data:
                    agent_reports["portfolio"] = node_data["portfolio_report"]
                # A股专用报告
                if "retail_sentiment_report" in node_data:
                    agent_reports["retail_sentiment"] = node_data["retail_sentiment_report"]
                if "policy_report" in node_data:
                    agent_reports["policy"] = node_data["policy_report"]

                event_data = {
                    "node": node_name,
                    "stage": current_stage,
                    "status": "completed",
                    "message": f"Node {node_name} finished"
                }
                await cache_service.push_sse_event(task_id, current_stage, event_data)

                # 收集 Planner 决策信息（如有）
                if "recommended_analysts" in node_data:
                    planner_decision = f"Planner 推荐使用: {', '.join(node_data['recommended_analysts'])}"
                elif "planner_decision" not in locals():
                    planner_decision = None

        # 计算耗时
        elapsed_seconds = round(time.time() - start_time, 2)

        # 构建合成上下文
        historical_cases_count = None
        if 'reflection' in locals() and reflection:
            historical_cases_count = len(reflection.historical_analyses)

        synthesis_context = SynthesisContext(
            analysis_level=analysis_level,
            task_id=task_id,
            elapsed_seconds=elapsed_seconds,
            analysts_used=selected_analysts,
            planner_decision=planner_decision if 'planner_decision' in locals() else None,
            data_quality_issues=None,  # 未来可集成 DataValidator
            historical_cases_count=historical_cases_count,
            market=market,
        )

        # Final Synthesis
        logger.info("Starting final synthesis", symbol=symbol)
        final_json = await synthesizer.synthesize(symbol, agent_reports, synthesis_context)

        elapsed_seconds = round(time.time() - start_time, 2)

        # 保存到数据库
        with Session(engine) as session:
            analysis_result = AnalysisResult(
                symbol=symbol,
                date=trade_date,
                signal=final_json.get("signal", "Hold"),
                confidence=final_json.get("confidence", 50),
                full_report_json=json.dumps(final_json, ensure_ascii=False),
                anchor_script=final_json.get("anchor_script", ""),
                task_id=task_id,
                status="completed",
                elapsed_seconds=elapsed_seconds,
            )
            session.add(analysis_result)
            session.commit()
            session.refresh(analysis_result)
            logger.info("Analysis result saved to database", symbol=symbol, task_id=task_id)

        # 记录预测到反思闭环追踪
        try:
            recommendation = final_json.get("recommendation", {})
            await accuracy_tracker.record_prediction(
                analysis_id=analysis_result.id,
                symbol=symbol,
                signal=final_json.get("signal", "Hold"),
                confidence=final_json.get("confidence", 50),
                target_price=recommendation.get("target_price"),
                stop_loss=recommendation.get("stop_loss"),
                entry_price=recommendation.get("entry_price"),
                agent_key="overall",
            )
            logger.info("Prediction recorded for reflection loop", symbol=symbol)
        except Exception as pred_err:
            logger.warning("Failed to record prediction", error=str(pred_err))

        # 存储到向量记忆库（用于反思机制）
        try:
            analysis_memory = AnalysisMemory(
                symbol=symbol,
                date=trade_date,
                signal=final_json.get("signal", "Hold"),
                confidence=final_json.get("confidence", 50),
                reasoning_summary=final_json.get("recommendation", {}).get("reasoning", "")[:500],
                debate_winner=final_json.get("debate_summary", {}).get("winner"),
                risk_score=final_json.get("risk_assessment", {}).get("score"),
                entry_price=final_json.get("recommendation", {}).get("entry_price"),
                target_price=final_json.get("recommendation", {}).get("target_price"),
                stop_loss=final_json.get("recommendation", {}).get("stop_loss"),
            )

            # 使用分层记忆存储（同时存入 macro_cycles 和 pattern_cases 集合）
            sector = final_json.get("company_overview", {}).get("sector")
            await layered_memory.store_layered_analysis(
                analysis_memory,
                sector=sector,
                macro_cycle=None,  # 自动推断
                pattern_type=None,  # 自动推断
            )
            logger.info("Analysis stored to layered memory service", symbol=symbol)
        except Exception as mem_err:
            logger.warning("Failed to store analysis to memory", error=str(mem_err))

        # 确保 diagnostics 存在（synthesizer 应已添加，此处为降级保护）
        if "diagnostics" not in final_json:
            final_json["diagnostics"] = {
                "task_id": task_id,
                "elapsed_seconds": elapsed_seconds,
                "analysts_used": selected_analysts,
            }

        await cache_service.push_sse_event(task_id, "stage_final", final_json)
        await cache_service.set_sse_status(task_id, "completed")
        await cache_service.set_task(task_id, {"status": "completed", "symbol": symbol})

    except Exception as e:
        logger.error("Analysis task failed", task_id=task_id, error=str(e))
        elapsed_seconds = round(time.time() - start_time, 2)

        # 保存失败记录到数据库
        with Session(engine) as session:
            analysis_result = AnalysisResult(
                symbol=symbol,
                date=trade_date,
                signal="Error",
                confidence=0,
                full_report_json="{}",
                anchor_script="",
                task_id=task_id,
                status="failed",
                error_message=str(e),
                elapsed_seconds=elapsed_seconds,
            )
            session.add(analysis_result)
            session.commit()

        await cache_service.push_sse_event(task_id, "error", {"message": str(e)})
        await cache_service.set_sse_status(task_id, "failed")
        await cache_service.set_task(task_id, {"status": "failed", "symbol": symbol, "error": str(e)})


class AnalyzeRequest(BaseModel):
    """分析请求参数"""
    trade_date: Optional[str] = Field(None, description="分析日期 (ISO 格式)，默认今天")
    analysts: Optional[List[str]] = Field(None, description="指定分析师列表（覆盖默认配置）")
    exclude_analysts: Optional[List[str]] = Field(None, description="排除指定分析师")
    analysis_level: Literal["L1", "L2"] = Field(
        "L2",
        description="分析深度: L1=快速扫描(15-20秒), L2=完整分析(30-60秒)"
    )
    use_planner: bool = Field(
        True,
        description="是否使用 Planner 动态选择分析师"
    )


@router.post("/{symbol}")
async def trigger_analysis(symbol: str, background_tasks: BackgroundTasks, body: AnalyzeRequest = None):
    """触发股票分析任务

    支持自定义分析师配置：
    - 不传参数：根据市场类型自动选择（A股 7 个分析师、港股 5 个、美股 4 个）
    - analysts: 完全覆盖，使用指定分析师列表
    - exclude_analysts: 排除某些分析师（如排除 policy 仅做技术面分析）

    支持分析级别：
    - L1: 快速扫描 (Market + News + Macro, 无辩论, 15-20秒)
    - L2: 完整分析 (所有分析师 + 辩论 + 风险评估, 30-60秒)

    执行模式：
    - 开发环境（默认）: 使用 BackgroundTasks 直接执行
    - 生产环境（USE_TASK_QUEUE=true）: 入队到 Redis Stream，由 worker 处理
    """
    if body is None:
        body = AnalyzeRequest()

    trade_date = body.trade_date or date.today().isoformat()

    task_id = f"task_{symbol}_{uuid.uuid4().hex[:8]}"

    # 返回将使用的分析师配置供前端展示
    market_config = MarketAnalystRouter.get_market_config(symbol)
    effective_analysts = body.analysts or MarketAnalystRouter.get_analysts(
        symbol=symbol,
        override_analysts=body.analysts,
        exclude_analysts=body.exclude_analysts,
    )

    if USE_TASK_QUEUE:
        # 生产模式：入队到 Redis Stream
        await task_queue.enqueue_analysis(
            task_id=task_id,
            symbol=symbol,
            trade_date=trade_date,
            analysis_level=body.analysis_level,
            use_planner=body.use_planner,
            override_analysts=body.analysts,
            exclude_analysts=body.exclude_analysts,
        )
        logger.info("Task enqueued", task_id=task_id, symbol=symbol, mode="queue")
    else:
        # 开发模式：使用 BackgroundTasks 直接执行
        background_tasks.add_task(
            run_analysis_task,
            task_id,
            symbol,
            trade_date,
            override_analysts=body.analysts,
            exclude_analysts=body.exclude_analysts,
            analysis_level=body.analysis_level,
            use_planner=body.use_planner,
        )
        logger.info("Task scheduled", task_id=task_id, symbol=symbol, mode="background")

    return {
        "task_id": task_id,
        "symbol": symbol,
        "status": "accepted",
        "market": market_config["market"],
        "analysts": effective_analysts,
        "analysis_level": body.analysis_level,
        "use_planner": body.use_planner,
        "execution_mode": "queue" if USE_TASK_QUEUE else "background",
    }


@router.get("/stream/{task_id}")
async def stream_analysis(task_id: str):
    """SSE 流式获取分析进度（支持分布式）"""
    # 检查任务是否存在
    sse_data = await cache_service.get_sse_events(task_id)
    if not sse_data:
        # 检查缓存中是否存在任务状态
        cached_task = await cache_service.get_task(task_id)
        if not cached_task:
            raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator() -> AsyncGenerator:
        sent_count = 0
        max_wait_cycles = 600  # 最多等待 10 分钟 (600 * 1s)
        wait_cycles = 0

        while wait_cycles < max_wait_cycles:
            sse_data = await cache_service.get_sse_events(task_id, from_index=sent_count)
            if not sse_data:
                break

            # Send new events
            for event in sse_data["events"]:
                yield ServerSentEvent(event=event["event"], data=json.dumps(event["data"]))
                sent_count += 1

            if sse_data["status"] in ["completed", "failed"]:
                # 任务完成，延迟清理 SSE 事件（允许客户端重连获取最终结果）
                # 清理由 TTL 自动处理
                break

            await asyncio.sleep(1)
            wait_cycles += 1

    return EventSourceResponse(event_generator())


@router.get("/latest/{symbol}")
async def get_latest_analysis(symbol: str, session: Session = Depends(get_session)):
    """获取指定股票的最新分析结果"""
    statement = (
        select(AnalysisResult)
        .where(AnalysisResult.symbol == symbol)
        .where(AnalysisResult.status == "completed")
        .order_by(AnalysisResult.created_at.desc())
        .limit(1)
    )
    result = session.exec(statement).first()

    if not result:
        raise HTTPException(status_code=404, detail=f"No analysis found for symbol: {symbol}")

    return {
        "symbol": result.symbol,
        "date": result.date,
        "signal": result.signal,
        "confidence": result.confidence,
        "full_report": json.loads(result.full_report_json),
        "anchor_script": result.anchor_script,
        "created_at": result.created_at.isoformat(),
        "task_id": result.task_id,
        "diagnostics": {
            "elapsed_seconds": result.elapsed_seconds,
        }
    }


@router.get("/history/{symbol}")
async def get_analysis_history(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None, description="Filter by status: completed, failed"),
    session: Session = Depends(get_session)
):
    """获取指定股票的历史分析记录（支持分页和状态筛选）"""
    statement = select(AnalysisResult).where(AnalysisResult.symbol == symbol)

    if status:
        statement = statement.where(AnalysisResult.status == status)

    # 使用复合索引 ix_analysis_symbol_created
    statement = statement.order_by(AnalysisResult.created_at.desc())

    # 先获取总数
    from sqlmodel import func
    count_stmt = select(func.count()).select_from(AnalysisResult).where(AnalysisResult.symbol == symbol)
    if status:
        count_stmt = count_stmt.where(AnalysisResult.status == status)
    total = session.exec(count_stmt).one()

    # 分页
    statement = statement.offset(offset).limit(limit)
    results = session.exec(statement).all()

    return {
        "items": [
            {
                "id": r.id,
                "date": r.date,
                "signal": r.signal,
                "confidence": r.confidence,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "task_id": r.task_id,
            }
            for r in results
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, session: Session = Depends(get_session)):
    """查询分析任务状态"""
    # 先检查缓存中的任务（含进程内和分布式）
    cached_task = await cache_service.get_task(task_id)
    if cached_task:
        return {
            "task_id": task_id,
            "status": cached_task.get("status", "unknown"),
            "symbol": cached_task.get("symbol"),
            "source": "cache"
        }

    # 再检查数据库
    statement = select(AnalysisResult).where(AnalysisResult.task_id == task_id)
    result = session.exec(statement).first()

    if not result:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return {
        "task_id": task_id,
        "status": result.status,
        "symbol": result.symbol,
        "created_at": result.created_at.isoformat(),
        "source": "database"
    }


@router.get("/analysts/config/{symbol}")
async def get_analyst_config(symbol: str):
    """获取指定 symbol 的分析师路由配置

    返回该股票市场类型、默认分析师列表、所有可用分析师。
    前端可用此接口渲染分析师选择 UI。
    """
    return MarketAnalystRouter.get_market_config(symbol)


@router.get("/analysts/available")
async def get_available_analysts():
    """获取所有可用的分析师及其描述"""
    return MarketAnalystRouter.get_available_analysts()


@router.post("/quick/{symbol}")
async def quick_scan(symbol: str, background_tasks: BackgroundTasks):
    """快速扫描（L1 模式）

    便捷端点，等同于 POST /{symbol} with analysis_level=L1。
    适用于批量扫描、watchlist 快速刷新等场景。

    特点：
    - 仅运行 Market + News + Macro 三个分析师
    - 跳过辩论和风险评估阶段
    - 预计 15-20 秒完成
    """
    task_id = f"quick_{symbol}_{uuid.uuid4().hex[:8]}"
    trade_date = date.today().isoformat()

    if USE_TASK_QUEUE:
        await task_queue.enqueue_analysis(
            task_id=task_id,
            symbol=symbol,
            trade_date=trade_date,
            analysis_level="L1",
            use_planner=False,
            override_analysts=["market", "news", "macro"],
        )
    else:
        background_tasks.add_task(
            run_analysis_task,
            task_id,
            symbol,
            trade_date,
            override_analysts=["market", "news", "macro"],
            exclude_analysts=None,
            analysis_level="L1",
            use_planner=False,
        )

    return {
        "task_id": task_id,
        "symbol": symbol,
        "status": "accepted",
        "analysis_level": "L1",
        "analysts": ["market", "news", "macro"],
        "estimated_time_seconds": 20,
        "execution_mode": "queue" if USE_TASK_QUEUE else "background",
    }
