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
    # 价格验证反馈（后续更新）
    actual_price_1d: Optional[float] = None  # 1天后实际价格
    actual_price_5d: Optional[float] = None  # 5天后实际价格
    actual_price_20d: Optional[float] = None  # 20天后实际价格
    outcome: Optional[str] = None  # "correct", "incorrect", "partial", "pending"


class AnalysisOutcome(BaseModel):
    """分析结果验证"""
    symbol: str
    date: str
    original_signal: str
    entry_price: Optional[float] = None
    actual_price_1d: Optional[float] = None
    actual_price_5d: Optional[float] = None
    actual_price_20d: Optional[float] = None
    outcome: str  # "correct", "incorrect", "partial"
    return_1d_pct: Optional[float] = None
    return_5d_pct: Optional[float] = None
    return_20d_pct: Optional[float] = None


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
                except ValueError as e:
                    logger.debug("Could not parse date, using 0", date=metadata.get("date"), error=str(e))
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

        基于历史分析记录和实际表现，识别模式并提取教训。

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

            # ===== 新增：基于实际表现的反馈 =====
            # 获取历史准确率
            accuracy_stats = await self.get_historical_accuracy(symbol)
            if accuracy_stats.get("status") == "available" and accuracy_stats.get("total", 0) >= 3:
                accuracy_rate = accuracy_stats.get("accuracy_rate", 0)
                total_verified = accuracy_stats.get("total", 0)

                if accuracy_rate >= 70:
                    patterns.append(f"历史预测准确率较高 ({accuracy_rate:.0f}%，基于 {total_verified} 次验证)")
                    confidence_adjustment += 10
                    lessons.append("历史表现优秀，可适当提高仓位")
                elif accuracy_rate >= 50:
                    patterns.append(f"历史预测准确率一般 ({accuracy_rate:.0f}%，基于 {total_verified} 次验证)")
                else:
                    patterns.append(f"历史预测准确率偏低 ({accuracy_rate:.0f}%，基于 {total_verified} 次验证)")
                    confidence_adjustment -= 15
                    lessons.append("历史预测表现不佳，建议降低仓位或观望")

                # 分析近期表现趋势
                correct_count = accuracy_stats.get("correct", 0)
                incorrect_count = accuracy_stats.get("incorrect", 0)
                if correct_count > incorrect_count * 2:
                    lessons.append("近期预测准确率提升，策略可能正在适应市场")
                elif incorrect_count > correct_count * 2:
                    lessons.append("近期预测频繁失误，需警惕策略失效风险")

            # 生成基础教训
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

    async def update_analysis_outcome(
        self,
        symbol: str,
        date: str,
        actual_price_1d: Optional[float] = None,
        actual_price_5d: Optional[float] = None,
        actual_price_20d: Optional[float] = None
    ) -> Optional[AnalysisOutcome]:
        """
        更新分析结果的实际价格表现（反馈循环）

        Args:
            symbol: 股票代码
            date: 原分析日期
            actual_price_1d: 1天后实际价格
            actual_price_5d: 5天后实际价格
            actual_price_20d: 20天后实际价格

        Returns:
            分析结果验证
        """
        if not self.is_available():
            return None

        try:
            doc_id = self._generate_id(symbol, date)
            result = self._collection.get(ids=[doc_id])

            if not result["ids"]:
                logger.warning("Analysis not found for outcome update", symbol=symbol, date=date)
                return None

            metadata = result["metadatas"][0]
            entry_price = metadata.get("entry_price", 0)
            original_signal = metadata.get("signal", "")

            # 计算收益率
            return_1d_pct = None
            return_5d_pct = None
            return_20d_pct = None

            if entry_price and entry_price > 0:
                if actual_price_1d:
                    return_1d_pct = ((actual_price_1d - entry_price) / entry_price) * 100
                if actual_price_5d:
                    return_5d_pct = ((actual_price_5d - entry_price) / entry_price) * 100
                if actual_price_20d:
                    return_20d_pct = ((actual_price_20d - entry_price) / entry_price) * 100

            # 判断预测是否正确
            outcome = self._evaluate_outcome(original_signal, return_5d_pct, return_20d_pct)

            # 更新元数据
            updated_metadata = metadata.copy()
            if actual_price_1d:
                updated_metadata["actual_price_1d"] = actual_price_1d
            if actual_price_5d:
                updated_metadata["actual_price_5d"] = actual_price_5d
            if actual_price_20d:
                updated_metadata["actual_price_20d"] = actual_price_20d
            updated_metadata["outcome"] = outcome
            if return_5d_pct is not None:
                updated_metadata["return_5d_pct"] = return_5d_pct
            if return_20d_pct is not None:
                updated_metadata["return_20d_pct"] = return_20d_pct

            # 更新到 ChromaDB
            self._collection.update(
                ids=[doc_id],
                metadatas=[updated_metadata]
            )

            logger.info("Analysis outcome updated",
                       symbol=symbol, date=date, outcome=outcome,
                       return_5d_pct=return_5d_pct)

            return AnalysisOutcome(
                symbol=symbol,
                date=date,
                original_signal=original_signal,
                entry_price=entry_price if entry_price else None,
                actual_price_1d=actual_price_1d,
                actual_price_5d=actual_price_5d,
                actual_price_20d=actual_price_20d,
                outcome=outcome,
                return_1d_pct=return_1d_pct,
                return_5d_pct=return_5d_pct,
                return_20d_pct=return_20d_pct
            )

        except Exception as e:
            logger.error("Failed to update analysis outcome", error=str(e))
            return None

    def _evaluate_outcome(
        self,
        signal: str,
        return_5d_pct: Optional[float],
        return_20d_pct: Optional[float]
    ) -> str:
        """
        评估预测结果

        Args:
            signal: 原始信号 (Buy/Sell/Hold)
            return_5d_pct: 5天收益率
            return_20d_pct: 20天收益率

        Returns:
            "correct", "incorrect", "partial", "pending"
        """
        if return_5d_pct is None and return_20d_pct is None:
            return "pending"

        # 使用5天收益为主，20天为辅
        primary_return = return_5d_pct if return_5d_pct is not None else return_20d_pct

        is_buy = "Buy" in signal or "Strong Buy" in signal
        is_sell = "Sell" in signal or "Strong Sell" in signal

        if is_buy:
            if primary_return > 2:  # 2%+ 收益视为正确
                return "correct"
            elif primary_return > -2:  # -2% ~ 2% 视为部分正确
                return "partial"
            else:
                return "incorrect"
        elif is_sell:
            if primary_return < -2:  # -2%- 跌幅视为正确
                return "correct"
            elif primary_return < 2:
                return "partial"
            else:
                return "incorrect"
        else:  # Hold
            if abs(primary_return) < 3:  # 波动 <3% 视为正确
                return "correct"
            else:
                return "partial"

    async def get_historical_accuracy(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        获取历史预测准确率

        Args:
            symbol: 股票代码（可选，不指定则统计全部）

        Returns:
            准确率统计
        """
        if not self.is_available():
            return {"status": "unavailable"}

        try:
            # 获取有 outcome 的记录
            where_filter = {"outcome": {"$ne": "pending"}}
            if symbol:
                where_filter = {"$and": [{"symbol": symbol}, {"outcome": {"$ne": "pending"}}]}

            results = self._collection.get(where=where_filter)

            if not results["ids"]:
                return {
                    "status": "no_data",
                    "total": 0,
                    "accuracy_rate": 0
                }

            outcomes = [m.get("outcome", "pending") for m in results["metadatas"]]
            total = len(outcomes)
            correct = outcomes.count("correct")
            partial = outcomes.count("partial")
            incorrect = outcomes.count("incorrect")

            # 计算加权准确率（partial 算 0.5）
            accuracy_rate = ((correct + partial * 0.5) / total) * 100 if total > 0 else 0

            return {
                "status": "available",
                "symbol": symbol or "all",
                "total": total,
                "correct": correct,
                "partial": partial,
                "incorrect": incorrect,
                "accuracy_rate": round(accuracy_rate, 1)
            }

        except Exception as e:
            logger.error("Failed to get accuracy", error=str(e))
            return {"status": "error", "reason": str(e)}


# 全局单例
memory_service = MemoryService()
