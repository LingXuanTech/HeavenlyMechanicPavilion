import asyncio
import json
import time
import uuid
import structlog
from datetime import date
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import AsyncGenerator, Optional
from sse_starlette.sse import ServerSentEvent, EventSourceResponse
from sqlmodel import Session, select
from api.sse import sse_manager
from services.synthesizer import synthesizer
from services.memory_service import memory_service, AnalysisMemory
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from config.settings import settings
from db.models import AnalysisResult, engine, get_session

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = structlog.get_logger()

# In-memory task tracking (could be moved to DB/Redis)
tasks = {}


async def run_analysis_task(task_id: str, symbol: str, trade_date: str):
    """执行分析任务并将结果保存到数据库"""
    logger.info("Starting analysis task", task_id=task_id, symbol=symbol)
    start_time = time.time()
    tasks[task_id] = {"status": "running", "progress": 0, "events": []}

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
        ta = TradingAgentsGraph(debug=True, config=config)

        # Initial state (with historical reflection)
        init_state = ta.propagator.create_initial_state(symbol, trade_date, historical_reflection)
        args = ta.propagator.get_graph_args()

        agent_reports = {}

        # Stream graph execution
        for chunk in ta.graph.stream(init_state, **args):
            for node_name, node_data in chunk.items():
                logger.info("Graph node completed", node=node_name)

                # Map node names to frontend stages
                stage_map = {
                    "Macro Analyst": "stage_analyst",
                    "Market Analyst": "stage_analyst",
                    "News Analyst": "stage_analyst",
                    "Fundamentals Analyst": "stage_analyst",
                    "Social Analyst": "stage_analyst",
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

                event_data = {
                    "node": node_name,
                    "stage": current_stage,
                    "status": "completed",
                    "message": f"Node {node_name} finished"
                }
                tasks[task_id]["events"].append({"event": current_stage, "data": event_data})

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
            logger.info("Analysis result saved to database", symbol=symbol, task_id=task_id)

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

        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = final_json
        tasks[task_id]["events"].append({"event": "stage_final", "data": final_json})

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

        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["events"].append({"event": "error", "data": {"message": str(e)}})


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
    """SSE 流式获取分析进度"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator() -> AsyncGenerator:
        sent_count = 0
        while True:
            task = tasks.get(task_id)
            if not task:
                break

            # Send new events
            while sent_count < len(task["events"]):
                event = task["events"][sent_count]
                yield ServerSentEvent(event=event["event"], data=json.dumps(event["data"]))
                sent_count += 1

            if task["status"] in ["completed", "failed"]:
                while sent_count < len(task["events"]):
                    event = task["events"][sent_count]
                    yield ServerSentEvent(event=event["event"], data=json.dumps(event["data"]))
                    sent_count += 1
                break

            await asyncio.sleep(1)

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
    session: Session = Depends(get_session)
):
    """获取指定股票的历史分析记录"""
    statement = (
        select(AnalysisResult)
        .where(AnalysisResult.symbol == symbol)
        .order_by(AnalysisResult.created_at.desc())
        .limit(limit)
    )
    results = session.exec(statement).all()

    return [
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
    ]


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, session: Session = Depends(get_session)):
    """查询分析任务状态"""
    # 先检查内存中的任务
    if task_id in tasks:
        return {
            "task_id": task_id,
            "status": tasks[task_id]["status"],
            "in_memory": True
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
        "in_memory": False
    }
