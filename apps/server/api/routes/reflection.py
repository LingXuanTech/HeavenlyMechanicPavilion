"""反思闭环 API 路由

提供预测追踪、Agent 表现分析、Prompt 优化等功能。
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
import structlog

from services.accuracy_tracker import accuracy_tracker
from services.prompt_optimizer import prompt_optimizer

router = APIRouter(prefix="/reflection", tags=["Reflection"])
logger = structlog.get_logger(__name__)


# ============ Request/Response Models ============


class RecordPredictionRequest(BaseModel):
    """记录预测请求"""
    analysis_id: int
    symbol: str
    signal: str
    confidence: int
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    entry_price: Optional[float] = None
    agent_key: str = "overall"


class EvaluatePredictionResponse(BaseModel):
    """预测评估响应"""
    prediction_id: int
    symbol: str
    outcome: Optional[str]
    is_correct: Optional[bool]
    actual_return: Optional[float]
    message: str


class AgentPerformanceRequest(BaseModel):
    """Agent 表现计算请求"""
    agent_key: str
    period_start: str
    period_end: str


class PromptOptimizationRequest(BaseModel):
    """Prompt 优化请求"""
    agent_key: str
    dry_run: bool = True


class PromptRollbackRequest(BaseModel):
    """Prompt 回滚请求"""
    agent_key: str
    target_version: Optional[int] = None


# ============ 预测追踪端点 ============


@router.post("/predictions")
async def record_prediction(request: RecordPredictionRequest):
    """记录一条预测

    手动记录预测，通常由分析流程自动调用。
    """
    try:
        prediction = await accuracy_tracker.record_prediction(
            analysis_id=request.analysis_id,
            symbol=request.symbol,
            signal=request.signal,
            confidence=request.confidence,
            target_price=request.target_price,
            stop_loss=request.stop_loss,
            entry_price=request.entry_price,
            agent_key=request.agent_key,
        )
        return {
            "status": "success",
            "prediction_id": prediction.id,
            "symbol": prediction.symbol,
            "signal": prediction.signal,
            "entry_price": prediction.entry_price,
        }
    except Exception as e:
        logger.error("Failed to record prediction", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/{prediction_id}/evaluate")
async def evaluate_prediction(
    prediction_id: int,
    evaluation_days: int = Query(default=5, ge=1, le=30),
):
    """评估单条预测

    根据实际价格变化评估预测准确性。
    """
    try:
        result = await accuracy_tracker.evaluate_prediction(
            prediction_id=prediction_id,
            evaluation_days=evaluation_days,
        )
        if result is None:
            return {
                "status": "skipped",
                "prediction_id": prediction_id,
                "message": "Prediction not found, already evaluated, or not yet ready",
            }
        return {
            "status": "success",
            "prediction_id": result.id,
            "symbol": result.symbol,
            "outcome": result.outcome,
            "is_correct": result.is_correct,
            "actual_return": result.actual_return,
        }
    except Exception as e:
        logger.error("Failed to evaluate prediction", error=str(e), prediction_id=prediction_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predictions/evaluate-pending")
async def evaluate_pending_predictions(
    background_tasks: BackgroundTasks,
    evaluation_days: int = Query(default=5, ge=1, le=30),
    limit: int = Query(default=100, ge=1, le=500),
):
    """批量评估待处理预测（后台任务）"""

    async def _run_evaluation():
        try:
            results = await accuracy_tracker.evaluate_pending_predictions(
                evaluation_days=evaluation_days,
                limit=limit,
            )
            logger.info("Batch evaluation completed", evaluated_count=len(results))
        except Exception as e:
            logger.error("Batch evaluation failed", error=str(e))

    background_tasks.add_task(_run_evaluation)
    return {
        "status": "accepted",
        "message": f"Evaluation started for up to {limit} predictions",
    }


@router.get("/predictions")
async def get_prediction_history(
    symbol: Optional[str] = None,
    agent_key: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """获取预测历史"""
    try:
        history = accuracy_tracker.get_prediction_history(
            symbol=symbol,
            agent_key=agent_key,
            limit=limit,
        )
        return {
            "status": "success",
            "count": len(history),
            "predictions": history,
        }
    except Exception as e:
        logger.error("Failed to get prediction history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============ Agent 表现端点 ============


@router.post("/performance/calculate")
async def calculate_agent_performance(request: AgentPerformanceRequest):
    """计算 Agent 表现统计"""
    try:
        perf = accuracy_tracker.calculate_agent_performance(
            agent_key=request.agent_key,
            period_start=request.period_start,
            period_end=request.period_end,
        )
        if perf is None:
            return {
                "status": "no_data",
                "agent_key": request.agent_key,
                "message": "No predictions found in the specified period",
            }
        return {
            "status": "success",
            "agent_key": perf.agent_key,
            "period": f"{perf.period_start} ~ {perf.period_end}",
            "total_predictions": perf.total_predictions,
            "win_rate": perf.win_rate,
            "avg_return": perf.avg_return,
            "avg_confidence": perf.avg_confidence,
            "overconfidence_bias": perf.overconfidence_bias,
            "direction_bias": perf.direction_bias,
        }
    except Exception as e:
        logger.error("Failed to calculate performance", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_agent_performance_summary(
    agent_key: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=50),
):
    """获取 Agent 表现摘要"""
    try:
        summary = accuracy_tracker.get_agent_performance_summary(
            agent_key=agent_key,
            limit=limit,
        )
        return {
            "status": "success",
            "count": len(summary),
            "performance": summary,
        }
    except Exception as e:
        logger.error("Failed to get performance summary", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/{agent_key}/reflection")
async def get_agent_reflection_prompt(
    agent_key: str,
    recent_days: int = Query(default=30, ge=7, le=90),
):
    """获取 Agent 反思提示词

    基于历史表现生成可注入到 Agent Prompt 的反思片段。
    """
    try:
        reflection = accuracy_tracker.generate_reflection_prompt(
            agent_key=agent_key,
            recent_days=recent_days,
        )
        if reflection is None:
            return {
                "status": "insufficient_data",
                "agent_key": agent_key,
                "message": "Not enough predictions for reflection (minimum 5 required)",
            }
        return {
            "status": "success",
            "agent_key": agent_key,
            "recent_days": recent_days,
            "reflection_prompt": reflection,
        }
    except Exception as e:
        logger.error("Failed to generate reflection", error=str(e), agent_key=agent_key)
        raise HTTPException(status_code=500, detail=str(e))


# ============ Prompt 优化端点 ============


@router.get("/optimize/{agent_key}/analyze")
async def analyze_agent_weaknesses(
    agent_key: str,
    recent_days: int = Query(default=30, ge=7, le=90),
):
    """分析 Agent 弱点"""
    try:
        analysis = prompt_optimizer.analyze_agent_weaknesses(
            agent_key=agent_key,
            recent_days=recent_days,
        )
        return analysis
    except Exception as e:
        logger.error("Failed to analyze weaknesses", error=str(e), agent_key=agent_key)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/{agent_key}")
async def optimize_agent_prompt(
    agent_key: str,
    dry_run: bool = Query(default=True),
):
    """优化 Agent Prompt

    Args:
        agent_key: Agent 标识
        dry_run: True 只分析不应用，False 实际应用优化
    """
    try:
        # 分析弱点
        analysis = prompt_optimizer.analyze_agent_weaknesses(agent_key)

        if analysis.get("status") == "insufficient_data":
            return analysis

        if not analysis.get("needs_optimization"):
            return {
                "status": "no_optimization_needed",
                "agent_key": agent_key,
                "statistics": analysis.get("statistics"),
            }

        weaknesses = analysis.get("weaknesses", [])
        improvement = prompt_optimizer.generate_prompt_improvement(agent_key, weaknesses)

        result = {
            "status": "analyzed",
            "agent_key": agent_key,
            "statistics": analysis.get("statistics"),
            "weaknesses": weaknesses,
            "improvement_preview": improvement,
            "dry_run": dry_run,
        }

        if not dry_run and improvement:
            optimized = prompt_optimizer.apply_prompt_optimization(
                agent_key,
                improvement,
                change_note=f"API optimization: {len(weaknesses)} weaknesses",
            )
            if optimized:
                result["status"] = "optimized"
                result["new_version"] = optimized.version

        return result
    except Exception as e:
        logger.error("Failed to optimize prompt", error=str(e), agent_key=agent_key)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize/all")
async def optimize_all_agents(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(default=True),
):
    """批量优化所有 Agent（后台任务）"""

    def _run_optimization():
        try:
            result = prompt_optimizer.auto_optimize_all_agents(dry_run=dry_run)
            logger.info(
                "Batch optimization completed",
                analyzed=result["analyzed"],
                optimized=result["optimized"],
            )
        except Exception as e:
            logger.error("Batch optimization failed", error=str(e))

    background_tasks.add_task(_run_optimization)
    return {
        "status": "accepted",
        "dry_run": dry_run,
        "message": "Optimization started for all agents",
    }


@router.post("/optimize/{agent_key}/rollback")
async def rollback_agent_prompt(
    agent_key: str,
    target_version: Optional[int] = None,
):
    """回滚 Agent Prompt 到指定版本"""
    try:
        result = prompt_optimizer.rollback_prompt(
            agent_key=agent_key,
            target_version=target_version,
        )
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No prompt or version found for agent: {agent_key}",
            )
        return {
            "status": "success",
            "agent_key": agent_key,
            "rolled_back_to_version": result.version,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to rollback prompt", error=str(e), agent_key=agent_key)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimize/{agent_key}/versions")
async def get_prompt_versions(
    agent_key: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """获取 Prompt 版本历史"""
    try:
        versions = prompt_optimizer.get_prompt_versions(
            agent_key=agent_key,
            limit=limit,
        )
        return {
            "status": "success",
            "agent_key": agent_key,
            "count": len(versions),
            "versions": versions,
        }
    except Exception as e:
        logger.error("Failed to get versions", error=str(e), agent_key=agent_key)
        raise HTTPException(status_code=500, detail=str(e))


# ============ 综合看板端点 ============


@router.get("/dashboard")
async def get_reflection_dashboard():
    """获取反思闭环综合看板"""
    try:
        # 获取各 Agent 最新表现
        performance_summary = accuracy_tracker.get_agent_performance_summary(limit=20)

        # 获取最近预测
        recent_predictions = accuracy_tracker.get_prediction_history(limit=10)

        # 计算汇总统计
        total_predictions = sum(p.get("total_predictions", 0) for p in performance_summary)
        avg_win_rate = None
        if performance_summary:
            win_rates = [
                float(p["win_rate"].rstrip("%")) / 100
                for p in performance_summary
                if p.get("win_rate") and p["win_rate"] != "N/A"
            ]
            if win_rates:
                avg_win_rate = sum(win_rates) / len(win_rates)

        # 识别表现最好/最差的 Agent
        best_agent = None
        worst_agent = None
        if performance_summary:
            sorted_by_win_rate = sorted(
                [p for p in performance_summary if p.get("win_rate") and p["win_rate"] != "N/A"],
                key=lambda x: float(x["win_rate"].rstrip("%")),
                reverse=True,
            )
            if sorted_by_win_rate:
                best_agent = sorted_by_win_rate[0]
                worst_agent = sorted_by_win_rate[-1]

        return {
            "status": "success",
            "summary": {
                "total_predictions_tracked": total_predictions,
                "agents_tracked": len(set(p["agent_key"] for p in performance_summary)),
                "avg_win_rate": f"{avg_win_rate:.1%}" if avg_win_rate else "N/A",
            },
            "highlights": {
                "best_performer": best_agent,
                "needs_improvement": worst_agent,
            },
            "recent_predictions": recent_predictions,
            "agent_performance": performance_summary,
        }
    except Exception as e:
        logger.error("Failed to get dashboard", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
