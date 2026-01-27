"""记忆与反思服务 - ChromaDB 集成"""
import structlog
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import hashlib

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

from config.settings import settings

logger = structlog.get_logger()


class AnalysisMemory(BaseModel):
    """分析记忆条目"""
    symbol: str
    date: str
    signal: str
    confidence: int
    reasoning_summary: str
    debate_winner: Optional[str] = None
    risk_score: Optional[int] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None


class MemoryRetrievalResult(BaseModel):
    """记忆检索结果"""
    memory: AnalysisMemory
    similarity: float
    days_ago: int


class ReflectionReport(BaseModel):
    """反思报告"""
    symbol: str
    historical_analyses: List[MemoryRetrievalResult]
    patterns: List[str]
    lessons: List[str]
    confidence_adjustment: int  # 基于历史表现的置信度调整 (-20 到 +20)


class MemoryService:
    """
    记忆服务 - 基于 ChromaDB 的向量存储

    功能：
    1. 存储分析结果为向量
    2. 检索相似历史分析
    3. 生成反思报告
    """

    _instance = None
    _client = None
    _collection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not installed. Memory service disabled.")
            return

        if self._client is None:
            self._initialize()

    def _initialize(self):
        """初始化 ChromaDB"""
        try:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_DB_PATH,
                settings=ChromaSettings(anonymized_telemetry=False)
            )

            # 创建或获取分析记忆集合
            self._collection = self._client.get_or_create_collection(
                name="analysis_memories",
                metadata={"description": "Stock analysis memories for reflection"}
            )

            logger.info("ChromaDB initialized", path=settings.CHROMA_DB_PATH)

        except Exception as e:
            logger.error("Failed to initialize ChromaDB", error=str(e))
            self._client = None
            self._collection = None

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return CHROMADB_AVAILABLE and self._collection is not None

    def _generate_id(self, symbol: str, date: str) -> str:
        """生成唯一 ID"""
        return hashlib.md5(f"{symbol}_{date}".encode()).hexdigest()

    def _create_embedding_text(self, memory: AnalysisMemory) -> str:
        """创建用于嵌入的文本"""
        return f"""
        Stock: {memory.symbol}
        Date: {memory.date}
        Signal: {memory.signal} (Confidence: {memory.confidence}%)
        Debate Winner: {memory.debate_winner or 'N/A'}
        Risk Score: {memory.risk_score or 'N/A'}/10
        Analysis: {memory.reasoning_summary}
        Trade Setup: Entry {memory.entry_price or 'N/A'}, Target {memory.target_price or 'N/A'}, Stop {memory.stop_loss or 'N/A'}
        """

    async def store_analysis(self, memory: AnalysisMemory) -> bool:
        """
        存储分析结果到向量数据库

        Args:
            memory: 分析记忆条目

        Returns:
            是否存储成功
        """
        if not self.is_available():
            logger.warning("Memory service not available, skipping storage")
            return False

        try:
            doc_id = self._generate_id(memory.symbol, memory.date)
            embedding_text = self._create_embedding_text(memory)

            # 存储到 ChromaDB
            self._collection.upsert(
                ids=[doc_id],
                documents=[embedding_text],
                metadatas=[{
                    "symbol": memory.symbol,
                    "date": memory.date,
                    "signal": memory.signal,
                    "confidence": memory.confidence,
                    "debate_winner": memory.debate_winner or "",
                    "risk_score": memory.risk_score or 0,
                    "entry_price": memory.entry_price or 0,
                    "target_price": memory.target_price or 0,
                    "stop_loss": memory.stop_loss or 0,
                    "reasoning_summary": memory.reasoning_summary[:500],  # 截断
                }]
            )

            logger.info("Analysis stored to memory", symbol=memory.symbol, date=memory.date)
            return True

        except Exception as e:
            logger.error("Failed to store analysis to memory", error=str(e))
            return False

    async def retrieve_similar(
        self,
        symbol: str,
        query_text: str = "",
        n_results: int = 5,
        max_days: int = 365
    ) -> List[MemoryRetrievalResult]:
        """
        检索相似的历史分析

        Args:
            symbol: 股票代码
            query_text: 查询文本（可选）
            n_results: 返回结果数量
            max_days: 最大历史天数

        Returns:
            相似记忆列表
        """
        if not self.is_available():
            return []

        try:
            # 构建查询
            if not query_text:
                query_text = f"Stock analysis for {symbol}"

            # 查询 ChromaDB
            results = self._collection.query(
                query_texts=[query_text],
                n_results=n_results * 2,  # 获取更多以便过滤
                where={"symbol": symbol}
            )

            memories = []
            today = datetime.now().date()

            for i, doc_id in enumerate(results.get("ids", [[]])[0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i] if "distances" in results else 0

                # 计算天数
                try:
                    analysis_date = datetime.strptime(metadata["date"], "%Y-%m-%d").date()
                    days_ago = (today - analysis_date).days
                except:
                    days_ago = 0

                # 过滤超出时间范围的
                if days_ago > max_days:
                    continue

                memory = AnalysisMemory(
                    symbol=metadata["symbol"],
                    date=metadata["date"],
                    signal=metadata["signal"],
                    confidence=metadata["confidence"],
                    reasoning_summary=metadata["reasoning_summary"],
                    debate_winner=metadata.get("debate_winner") or None,
                    risk_score=metadata.get("risk_score") or None,
                    entry_price=metadata.get("entry_price") or None,
                    target_price=metadata.get("target_price") or None,
                    stop_loss=metadata.get("stop_loss") or None,
                )

                memories.append(MemoryRetrievalResult(
                    memory=memory,
                    similarity=1 - distance if distance else 0.5,  # 转换距离为相似度
                    days_ago=days_ago
                ))

            # 按日期排序（最近优先）
            memories.sort(key=lambda x: x.days_ago)

            return memories[:n_results]

        except Exception as e:
            logger.error("Failed to retrieve memories", error=str(e))
            return []

    async def generate_reflection(self, symbol: str) -> Optional[ReflectionReport]:
        """
        生成反思报告

        基于历史分析记录，识别模式并提取教训。

        Args:
            symbol: 股票代码

        Returns:
            反思报告
        """
        if not self.is_available():
            return None

        try:
            # 检索历史分析
            memories = await self.retrieve_similar(symbol, n_results=10, max_days=180)

            if len(memories) < 2:
                return None

            patterns = []
            lessons = []
            confidence_adjustment = 0

            # 分析信号一致性
            signals = [m.memory.signal for m in memories]
            bull_count = sum(1 for s in signals if 'Buy' in s)
            bear_count = sum(1 for s in signals if 'Sell' in s)

            if bull_count > bear_count * 2:
                patterns.append(f"历史上对 {symbol} 多数看涨 ({bull_count}/{len(signals)})")
            elif bear_count > bull_count * 2:
                patterns.append(f"历史上对 {symbol} 多数看跌 ({bear_count}/{len(signals)})")
            else:
                patterns.append(f"历史信号分歧较大，需谨慎判断")

            # 分析置信度变化
            confidences = [m.memory.confidence for m in memories]
            avg_confidence = sum(confidences) / len(confidences)

            if avg_confidence > 75:
                patterns.append(f"历史分析置信度普遍较高 (平均 {avg_confidence:.0f}%)")
            elif avg_confidence < 50:
                patterns.append(f"历史分析置信度普遍较低 (平均 {avg_confidence:.0f}%)")
                confidence_adjustment = -5

            # 分析风险评分
            risk_scores = [m.memory.risk_score for m in memories if m.memory.risk_score]
            if risk_scores:
                avg_risk = sum(risk_scores) / len(risk_scores)
                if avg_risk > 6:
                    lessons.append(f"该股票历史风险评分较高 (平均 {avg_risk:.1f}/10)，建议控制仓位")
                    confidence_adjustment -= 5

            # 分析辩论胜负
            debate_winners = [m.memory.debate_winner for m in memories if m.memory.debate_winner]
            if debate_winners:
                bull_wins = debate_winners.count('Bull')
                bear_wins = debate_winners.count('Bear')
                if bull_wins > bear_wins:
                    patterns.append(f"历史辩论中多方胜出较多 ({bull_wins}/{len(debate_winners)})")
                elif bear_wins > bull_wins:
                    patterns.append(f"历史辩论中空方胜出较多 ({bear_wins}/{len(debate_winners)})")

            # 生成教训
            if len(memories) >= 5:
                lessons.append("有足够的历史数据支持决策，但需注意市场环境变化")
            else:
                lessons.append("历史数据较少，建议增加观察期")

            # 限制置信度调整范围
            confidence_adjustment = max(-20, min(20, confidence_adjustment))

            return ReflectionReport(
                symbol=symbol,
                historical_analyses=memories,
                patterns=patterns,
                lessons=lessons,
                confidence_adjustment=confidence_adjustment
            )

        except Exception as e:
            logger.error("Failed to generate reflection", error=str(e))
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆服务统计信息"""
        if not self.is_available():
            return {"status": "unavailable", "reason": "ChromaDB not initialized"}

        try:
            count = self._collection.count()
            return {
                "status": "available",
                "total_memories": count,
                "chroma_path": settings.CHROMA_DB_PATH
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def clear_memories(self, symbol: Optional[str] = None) -> int:
        """
        清除记忆

        Args:
            symbol: 指定股票代码（不指定则清除全部）

        Returns:
            删除的记忆数量
        """
        if not self.is_available():
            return 0

        try:
            if symbol:
                # 删除特定股票的记忆
                results = self._collection.get(where={"symbol": symbol})
                if results["ids"]:
                    self._collection.delete(ids=results["ids"])
                    return len(results["ids"])
                return 0
            else:
                # 清除所有记忆（重新创建集合）
                count = self._collection.count()
                self._client.delete_collection("analysis_memories")
                self._collection = self._client.create_collection(
                    name="analysis_memories",
                    metadata={"description": "Stock analysis memories for reflection"}
                )
                return count

        except Exception as e:
            logger.error("Failed to clear memories", error=str(e))
            return 0


# 全局单例
memory_service = MemoryService()
