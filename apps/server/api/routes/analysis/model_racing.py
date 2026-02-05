"""多模型赛马 API 路由

提供多模型并行分析、共识计算、模型表现追踪等功能。
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
import structlog

from services.model_racing import model_racing, ConsensusMethod, ConsensusResult
from db.models import ModelPerformance, RacingAnalysisResult, engine

router = APIRouter(prefix="/model-racing", tags=["Model Racing"])
logger = structlog.get_logger(__name__)


# ============ Request/Response Models ============


class RacingAnalysisRequest(BaseModel):
    """赛马分析请求"""
    symbol: str
    market: str = "US"
    selected_analysts: Optional[List[str]] = None
    consensus_method: str = "confidence_weighted"
    timeout: int = 300


class RacingAnalysisResponse(BaseModel):
    """赛马分析响应"""
    symbol: str
    final_signal: str
    final_confidence: int
    consensus_method: str
    agreement_rate: float
    model_count: int
    successful_count: int
    dissenting_models: List[str]
    analysis_summary: str
    model_details: List[dict]


class ModelPerformanceResponse(BaseModel):
    """模型表现响应"""
    model_key: str
    model_name: str
    provider: str
    period: str
    total_predictions: int
    win_rate: float
    avg_confidence: float
    avg_response_time: float
    consensus_agreement_rate: float


# ============ 赛马分析端点 ============


@router.post("/analyze", response_model=RacingAnalysisResponse)
async def run_racing_analysis(request: RacingAnalysisRequest):
    """运行多模型赛马分析

    并行调用多个 LLM 分析同一股票，通过共识引擎综合结果。
    """
    try:
        # 解析共识方法
        try:
            method = ConsensusMethod(request.consensus_method)
        except ValueError:
            method = ConsensusMethod.CONFIDENCE_WEIGHTED

        # 运行赛马分析
        result = await model_racing.run_racing_analysis(
            symbol=request.symbol,
            market=request.market,
            selected_analysts=request.selected_analysts,
            consensus_method=method,
            timeout=request.timeout,
        )

        # 保存结果到数据库
        await _save_racing_result(request.symbol, request.market, result)

        # 构造响应
        return RacingAnalysisResponse(
            symbol=request.symbol,
            final_signal=result.final_signal,
            final_confidence=result.final_confidence,
            consensus_method=result.consensus_method,
            agreement_rate=result.agreement_rate,
            model_count=len(result.model_results),
            successful_count=sum(1 for r in result.model_results if r.error is None),
            dissenting_models=result.dissenting_models,
            analysis_summary=result.analysis_summary,
            model_details=[r.to_dict() for r in result.model_results],
        )

    except Exception as e:
        logger.error("Racing analysis failed", error=str(e), symbol=request.symbol)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/background")
async def run_racing_analysis_background(
    background_tasks: BackgroundTasks,
    request: RacingAnalysisRequest,
):
    """后台运行多模型赛马分析"""

    async def _run_analysis():
        try:
            method = ConsensusMethod(request.consensus_method)
        except ValueError:
            method = ConsensusMethod.CONFIDENCE_WEIGHTED

        try:
            result = await model_racing.run_racing_analysis(
                symbol=request.symbol,
                market=request.market,
                selected_analysts=request.selected_analysts,
                consensus_method=method,
                timeout=request.timeout,
            )
            await _save_racing_result(request.symbol, request.market, result)
            logger.info(
                "Background racing analysis completed",
                symbol=request.symbol,
                signal=result.final_signal,
            )
        except Exception as e:
            logger.error("Background racing analysis failed", error=str(e))

    background_tasks.add_task(_run_analysis)

    return {
        "status": "accepted",
        "symbol": request.symbol,
        "message": "Racing analysis started in background",
    }


async def _save_racing_result(symbol: str, market: str, result: ConsensusResult):
    """保存赛马分析结果"""
    with Session(engine) as session:
        model_results_dict = {
            r.model_id: {
                "model_name": r.model_name,
                "provider": r.provider,
                "signal": r.signal,
                "confidence": r.confidence,
                "elapsed_seconds": r.elapsed_seconds,
                "error": r.error,
            }
            for r in result.model_results
        }

        record = RacingAnalysisResult(
            symbol=symbol,
            market=market,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            consensus_signal=result.final_signal,
            consensus_confidence=result.final_confidence,
            consensus_method=result.consensus_method,
            agreement_rate=result.agreement_rate,
            model_results_json=json.dumps(model_results_dict, ensure_ascii=False),
            dissenting_models=json.dumps(result.dissenting_models),
            total_models=len(result.model_results),
            successful_models=sum(1 for r in result.model_results if r.error is None),
            total_elapsed_seconds=sum(r.elapsed_seconds for r in result.model_results),
        )

        session.add(record)
        session.commit()


# ============ 历史记录端点 ============


@router.get("/history/{symbol}")
async def get_racing_history(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """获取股票的赛马分析历史"""
    with Session(engine) as session:
        statement = (
            select(RacingAnalysisResult)
            .where(RacingAnalysisResult.symbol == symbol)
            .order_by(RacingAnalysisResult.created_at.desc())
            .limit(limit)
        )
        records = session.exec(statement).all()

        return {
            "status": "success",
            "symbol": symbol,
            "count": len(records),
            "history": [
                {
                    "id": r.id,
                    "analysis_date": r.analysis_date,
                    "consensus_signal": r.consensus_signal,
                    "consensus_confidence": r.consensus_confidence,
                    "consensus_method": r.consensus_method,
                    "agreement_rate": r.agreement_rate,
                    "total_models": r.total_models,
                    "successful_models": r.successful_models,
                    "dissenting_models": json.loads(r.dissenting_models),
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ],
        }


@router.get("/history/{symbol}/{record_id}")
async def get_racing_detail(symbol: str, record_id: int):
    """获取单条赛马分析详情"""
    with Session(engine) as session:
        record = session.get(RacingAnalysisResult, record_id)

        if not record or record.symbol != symbol:
            raise HTTPException(status_code=404, detail="Record not found")

        return {
            "status": "success",
            "id": record.id,
            "symbol": record.symbol,
            "market": record.market,
            "analysis_date": record.analysis_date,
            "consensus_signal": record.consensus_signal,
            "consensus_confidence": record.consensus_confidence,
            "consensus_method": record.consensus_method,
            "agreement_rate": record.agreement_rate,
            "model_results": json.loads(record.model_results_json),
            "dissenting_models": json.loads(record.dissenting_models),
            "total_models": record.total_models,
            "successful_models": record.successful_models,
            "total_elapsed_seconds": record.total_elapsed_seconds,
            "created_at": record.created_at.isoformat(),
        }


# ============ 模型表现端点 ============


@router.get("/performance")
async def get_model_performance_summary(
    limit: int = Query(default=20, ge=1, le=100),
):
    """获取所有模型的表现摘要"""
    with Session(engine) as session:
        statement = (
            select(ModelPerformance)
            .order_by(ModelPerformance.calculated_at.desc())
            .limit(limit)
        )
        records = session.exec(statement).all()

        return {
            "status": "success",
            "count": len(records),
            "performance": [
                {
                    "model_key": r.model_key,
                    "model_name": r.model_name,
                    "provider": r.provider,
                    "period": f"{r.period_start} ~ {r.period_end}",
                    "total_predictions": r.total_predictions,
                    "win_rate": f"{r.win_rate:.1%}" if r.win_rate else "N/A",
                    "avg_confidence": f"{r.avg_confidence:.1f}" if r.avg_confidence else "N/A",
                    "avg_response_time": f"{r.avg_response_time:.1f}s" if r.avg_response_time else "N/A",
                    "consensus_agreement_rate": f"{r.consensus_agreement_rate:.1%}" if r.consensus_agreement_rate else "N/A",
                    "direction_bias": r.direction_bias or "N/A",
                }
                for r in records
            ],
        }


@router.get("/performance/{model_key}")
async def get_model_performance_detail(
    model_key: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    """获取特定模型的表现详情"""
    with Session(engine) as session:
        statement = (
            select(ModelPerformance)
            .where(ModelPerformance.model_key == model_key)
            .order_by(ModelPerformance.calculated_at.desc())
            .limit(limit)
        )
        records = session.exec(statement).all()

        if not records:
            raise HTTPException(status_code=404, detail=f"No performance data for model: {model_key}")

        return {
            "status": "success",
            "model_key": model_key,
            "count": len(records),
            "performance": [
                {
                    "period": f"{r.period_start} ~ {r.period_end}",
                    "total_predictions": r.total_predictions,
                    "correct_predictions": r.correct_predictions,
                    "win_rate": r.win_rate,
                    "avg_return": r.avg_return,
                    "avg_confidence": r.avg_confidence,
                    "avg_response_time": r.avg_response_time,
                    "consensus_agreement_rate": r.consensus_agreement_rate,
                    "strong_buy_accuracy": r.strong_buy_accuracy,
                    "buy_accuracy": r.buy_accuracy,
                    "sell_accuracy": r.sell_accuracy,
                    "overconfidence_bias": r.overconfidence_bias,
                    "direction_bias": r.direction_bias,
                    "calculated_at": r.calculated_at.isoformat(),
                }
                for r in records
            ],
        }


@router.post("/performance/calculate")
async def calculate_model_performance(
    background_tasks: BackgroundTasks,
    period_days: int = Query(default=30, ge=7, le=90),
):
    """计算所有模型的表现（后台任务）"""

    def _calculate():
        period_end = datetime.now().strftime("%Y-%m-%d")
        period_start = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")

        with Session(engine) as session:
            # 获取该周期内的所有赛马分析结果
            statement = (
                select(RacingAnalysisResult)
                .where(RacingAnalysisResult.analysis_date >= period_start)
                .where(RacingAnalysisResult.analysis_date <= period_end)
            )
            results = session.exec(statement).all()

            if not results:
                logger.info("No racing results found for period", period_start=period_start, period_end=period_end)
                return

            # 按模型聚合统计
            model_stats: dict = {}
            for result in results:
                model_results = json.loads(result.model_results_json)
                for model_key, model_data in model_results.items():
                    if model_key not in model_stats:
                        model_stats[model_key] = {
                            "model_name": model_data.get("model_name", ""),
                            "provider": model_data.get("provider", ""),
                            "total": 0,
                            "confidences": [],
                            "response_times": [],
                            "agreement_count": 0,
                        }

                    stats = model_stats[model_key]
                    stats["total"] += 1
                    if model_data.get("confidence"):
                        stats["confidences"].append(model_data["confidence"])
                    if model_data.get("elapsed_seconds"):
                        stats["response_times"].append(model_data["elapsed_seconds"])
                    if model_data.get("signal") == result.consensus_signal:
                        stats["agreement_count"] += 1

            # 保存统计结果
            for model_key, stats in model_stats.items():
                perf = ModelPerformance(
                    model_key=model_key,
                    model_name=stats["model_name"],
                    provider=stats["provider"],
                    period_start=period_start,
                    period_end=period_end,
                    total_predictions=stats["total"],
                    avg_confidence=sum(stats["confidences"]) / len(stats["confidences"]) if stats["confidences"] else 0,
                    avg_response_time=sum(stats["response_times"]) / len(stats["response_times"]) if stats["response_times"] else 0,
                    consensus_agreement_rate=stats["agreement_count"] / stats["total"] if stats["total"] > 0 else 0,
                )
                session.add(perf)

            session.commit()
            logger.info(
                "Model performance calculated",
                period=f"{period_start} ~ {period_end}",
                models_count=len(model_stats),
            )

    background_tasks.add_task(_calculate)

    return {
        "status": "accepted",
        "message": f"Performance calculation started for last {period_days} days",
    }


# ============ 共识方法配置端点 ============


@router.get("/consensus-methods")
async def get_consensus_methods():
    """获取支持的共识方法列表"""
    return {
        "status": "success",
        "methods": [
            {
                "value": method.value,
                "name": method.name,
                "description": _get_method_description(method),
            }
            for method in ConsensusMethod
        ],
    }


def _get_method_description(method: ConsensusMethod) -> str:
    """获取共识方法描述"""
    descriptions = {
        ConsensusMethod.MAJORITY_VOTE: "简单多数投票：票数最多的信号获胜",
        ConsensusMethod.WEIGHTED_VOTE: "加权投票：根据模型历史准确率加权",
        ConsensusMethod.CONFIDENCE_WEIGHTED: "置信度加权：根据各模型的置信度加权平均",
        ConsensusMethod.UNANIMOUS: "全票一致：只有所有模型一致时才采纳，否则返回 Hold",
    }
    return descriptions.get(method, "")


# ============ 综合看板端点 ============


@router.get("/dashboard")
async def get_racing_dashboard():
    """获取赛马分析综合看板"""
    with Session(engine) as session:
        # 最近的赛马分析
        recent_analyses = session.exec(
            select(RacingAnalysisResult)
            .order_by(RacingAnalysisResult.created_at.desc())
            .limit(5)
        ).all()

        # 模型表现统计
        model_performance = session.exec(
            select(ModelPerformance)
            .order_by(ModelPerformance.calculated_at.desc())
            .limit(10)
        ).all()

        # 统计摘要
        total_analyses = session.exec(
            select(RacingAnalysisResult)
        ).all()

        avg_agreement = 0
        if total_analyses:
            avg_agreement = sum(a.agreement_rate for a in total_analyses) / len(total_analyses)

        return {
            "status": "success",
            "summary": {
                "total_racing_analyses": len(total_analyses),
                "avg_agreement_rate": f"{avg_agreement:.1%}",
                "models_tracked": len(set(p.model_key for p in model_performance)),
            },
            "recent_analyses": [
                {
                    "symbol": a.symbol,
                    "consensus_signal": a.consensus_signal,
                    "agreement_rate": f"{a.agreement_rate:.1%}",
                    "total_models": a.total_models,
                    "created_at": a.created_at.isoformat(),
                }
                for a in recent_analyses
            ],
            "model_rankings": [
                {
                    "model_key": p.model_key,
                    "model_name": p.model_name,
                    "consensus_agreement_rate": f"{p.consensus_agreement_rate:.1%}",
                    "avg_confidence": f"{p.avg_confidence:.1f}",
                }
                for p in sorted(
                    model_performance,
                    key=lambda x: x.consensus_agreement_rate,
                    reverse=True,
                )[:5]
            ],
        }
