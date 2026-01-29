import asyncio
import json
import time
import uuid
import structlog
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import AsyncGenerator, Optional, Iterator, Any
from sse_starlette.sse import ServerSentEvent, EventSourceResponse
from sqlmodel import Session, select
from api.sse import sse_manager
from services.synthesizer import synthesizer
from services.memory_service import memory_service, AnalysisMemory
from services.cache_service import cache_service
from services.data_router import MarketRouter
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from config.settings import settings
from db.models import AnalysisResult, engine, get_session
from services.accuracy_tracker import accuracy_tracker

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = structlog.get_logger()

# Thread pool for running synchronous graph execution
_graph_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="graph_worker")


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


async def run_analysis_task(task_id: str, symbol: str, trade_date: str):
    """执行分析任务并将结果保存到数据库"""
    logger.info("Starting analysis task", task_id=task_id, symbol=symbol)
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
        market = MarketRouter.get_market(symbol)
        ta = TradingAgentsGraph(debug=True, config=config, market=market)

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

        # Final Synthesis
        logger.info("Starting final synthesis", symbol=symbol)
        final_json = await synthesizer.synthesize(symbol, agent_reports)

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
            await memory_service.store_analysis(analysis_memory)
            logger.info("Analysis stored to memory service", symbol=symbol)
        except Exception as mem_err:
            logger.warning("Failed to store analysis to memory", error=str(mem_err))

        # 添加诊断信息到返回结果
        final_json["diagnostics"] = {
            "task_id": task_id,
            "elapsed_seconds": elapsed_seconds,
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


@router.post("/{symbol}")
async def trigger_analysis(symbol: str, background_tasks: BackgroundTasks, trade_date: str = None):
    """触发股票分析任务"""
    if not trade_date:
        trade_date = date.today().isoformat()

    task_id = f"task_{symbol}_{uuid.uuid4().hex[:8]}"
    background_tasks.add_task(run_analysis_task, task_id, symbol, trade_date)

    return {"task_id": task_id, "symbol": symbol, "status": "accepted"}


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
