"""记忆与反思 API 路由"""
import structlog
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from services.memory_service import (
    memory_service,
    layered_memory,
    AnalysisMemory,
    MemoryRetrievalResult,
    ReflectionReport
)

router = APIRouter(prefix="/memory", tags=["Memory"])
logger = structlog.get_logger()


@router.get("/status")
async def get_memory_status():
    """
    获取记忆服务状态

    返回 ChromaDB 连接状态和统计信息。
    """
    stats = memory_service.get_stats()
    return stats


@router.get("/retrieve/{symbol}", response_model=List[MemoryRetrievalResult])
async def retrieve_memories(
    symbol: str,
    n_results: int = Query(5, ge=1, le=20),
    max_days: int = Query(365, ge=1, le=1000)
):
    """
    检索股票的历史分析记忆

    基于向量相似度返回相关的历史分析记录。
    """
    if not memory_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="记忆服务不可用。请确保 ChromaDB 已正确配置。"
        )

    memories = await memory_service.retrieve_similar(
        symbol=symbol,
        n_results=n_results,
        max_days=max_days
    )

    return memories


@router.get("/reflection/{symbol}", response_model=Optional[ReflectionReport])
async def get_reflection(symbol: str):
    """
    获取股票的反思报告

    基于历史分析识别模式并提取教训。
    """
    if not memory_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="记忆服务不可用。请确保 ChromaDB 已正确配置。"
        )

    reflection = await memory_service.generate_reflection(symbol)

    if not reflection:
        raise HTTPException(
            status_code=404,
            detail=f"无法为 {symbol} 生成反思报告。可能历史数据不足。"
        )

    return reflection


@router.post("/store")
async def store_memory(memory: AnalysisMemory):
    """
    手动存储分析记忆

    通常由分析流程自动调用，也可手动存储。
    """
    if not memory_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="记忆服务不可用"
        )

    success = await memory_service.store_analysis(memory)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="存储失败"
        )

    return {
        "status": "success",
        "message": f"已存储 {memory.symbol} 的分析记忆",
        "date": memory.date
    }


@router.delete("/clear")
async def clear_memories(symbol: Optional[str] = None):
    """
    清除记忆

    不指定 symbol 则清除所有记忆。
    """
    if not memory_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="记忆服务不可用"
        )

    count = memory_service.clear_memories(symbol)

    return {
        "status": "success",
        "message": f"已清除 {count} 条记忆",
        "symbol": symbol or "all"
    }


@router.get("/search")
async def search_memories(
    query: str = Query(..., min_length=2),
    n_results: int = Query(10, ge=1, le=50)
):
    """
    跨股票搜索相似分析

    使用自然语言查询搜索所有历史分析。
    """
    if not memory_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="记忆服务不可用"
        )

    try:
        # 直接查询 ChromaDB（不限制 symbol）
        results = memory_service._collection.query(
            query_texts=[query],
            n_results=n_results
        )

        memories = []
        for i, doc_id in enumerate(results.get("ids", [[]])[0]):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if "distances" in results else 0

            memories.append({
                "symbol": metadata["symbol"],
                "date": metadata["date"],
                "signal": metadata["signal"],
                "confidence": metadata["confidence"],
                "similarity": round(1 - distance, 3) if distance else 0.5,
                "reasoning_summary": metadata.get("reasoning_summary", "")[:200]
            })

        return {
            "query": query,
            "results": memories,
            "count": len(memories)
        }

    except Exception as e:
        logger.error("Memory search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


# ============ 分层记忆 API ============


@router.get("/layered/status")
async def get_layered_memory_status():
    """获取分层记忆服务统计"""
    return layered_memory.get_layered_stats()


@router.get("/layered/macro/{cycle}")
async def retrieve_by_macro_cycle(
    cycle: str,
    n_results: int = Query(10, ge=1, le=50),
):
    """按宏观周期检索历史分析案例

    Args:
        cycle: 宏观周期标签（rate_cut, rate_hike, bull_market, bear_market, recovery, recession, neutral）
        n_results: 返回结果数量
    """
    results = await layered_memory.retrieve_by_macro_cycle(
        macro_cycle=cycle,
        n_results=n_results,
    )

    return {
        "macro_cycle": cycle,
        "results": [
            {
                "symbol": r.memory.symbol,
                "date": r.memory.date,
                "signal": r.memory.signal,
                "confidence": r.memory.confidence,
                "similarity": round(r.similarity, 3),
                "outcome": r.memory.outcome or "pending",
            }
            for r in results
        ],
        "count": len(results),
    }


@router.get("/layered/pattern/{pattern}")
async def retrieve_by_pattern(
    pattern: str,
    sector: Optional[str] = None,
    n_results: int = Query(10, ge=1, le=50),
):
    """按技术形态/基本面特征检索历史案例

    Args:
        pattern: 形态类型（strong_conviction, uncertain, normal, breakout, double_bottom 等）
        sector: 行业筛选（可选）
        n_results: 返回结果数量
    """
    results = await layered_memory.retrieve_by_pattern(
        pattern_type=pattern,
        sector=sector,
        n_results=n_results,
    )

    return {
        "pattern_type": pattern,
        "sector": sector,
        "results": [
            {
                "symbol": r.memory.symbol,
                "date": r.memory.date,
                "signal": r.memory.signal,
                "confidence": r.memory.confidence,
                "similarity": round(r.similarity, 3),
                "outcome": r.memory.outcome or "pending",
            }
            for r in results
        ],
        "count": len(results),
    }
