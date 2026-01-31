"""
MemoryService 单元测试

测试内容：
1. 时间衰减权重计算
2. 相似度阈值过滤
3. 组合评分排序
"""
import pytest
import math
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from services.memory_service import (
    MemoryService,
    AnalysisMemory,
    MemoryRetrievalResult,
    SIMILARITY_THRESHOLD,
    TIME_DECAY_HALF_LIFE_DAYS,
    MIN_TIME_WEIGHT,
)


class TestTimeDecayCalculation:
    """测试时间衰减权重计算"""

    @pytest.fixture
    def memory_service(self):
        """创建 MemoryService 实例（不依赖 ChromaDB）"""
        with patch("services.memory_service.CHROMADB_AVAILABLE", False):
            service = MemoryService.__new__(MemoryService)
            service._client = None
            service._collection = None
            return service

    def test_today_has_full_weight(self, memory_service):
        """今天的记忆权重为 1.0"""
        weight = memory_service._calculate_time_weight(0)
        assert weight == 1.0

    def test_half_life_has_half_weight(self, memory_service):
        """经过半衰期后权重减半"""
        weight = memory_service._calculate_time_weight(TIME_DECAY_HALF_LIFE_DAYS)
        assert abs(weight - 0.5) < 0.01

    def test_double_half_life_has_quarter_weight(self, memory_service):
        """经过两个半衰期后权重为 0.25"""
        weight = memory_service._calculate_time_weight(TIME_DECAY_HALF_LIFE_DAYS * 2)
        assert abs(weight - 0.25) < 0.01

    def test_very_old_memory_has_min_weight(self, memory_service):
        """非常久远的记忆权重不低于最小值"""
        # 1000 天前的记忆
        weight = memory_service._calculate_time_weight(1000)
        assert weight >= MIN_TIME_WEIGHT
        assert weight <= 1.0

    def test_negative_days_returns_full_weight(self, memory_service):
        """负数天数返回完整权重（边界情况）"""
        weight = memory_service._calculate_time_weight(-10)
        assert weight == 1.0

    @pytest.mark.parametrize("days_ago,expected_min,expected_max", [
        (0, 1.0, 1.0),
        (30, 0.75, 0.85),    # 30天：约0.79
        (90, 0.45, 0.55),    # 90天（半衰期）：约0.5
        (180, 0.20, 0.30),   # 180天：约0.25
        (365, 0.10, 0.15),   # 365天：约0.1（接近MIN_TIME_WEIGHT）
    ])
    def test_decay_curve_shape(self, memory_service, days_ago, expected_min, expected_max):
        """验证衰减曲线形状符合预期"""
        weight = memory_service._calculate_time_weight(days_ago)
        assert expected_min <= weight <= expected_max, \
            f"days_ago={days_ago}: expected {expected_min}-{expected_max}, got {weight}"


class TestSimilarityThreshold:
    """测试相似度阈值过滤"""

    def test_default_threshold_value(self):
        """验证默认阈值配置"""
        assert SIMILARITY_THRESHOLD == 0.3

    def test_min_time_weight_value(self):
        """验证最小时间权重配置"""
        assert MIN_TIME_WEIGHT == 0.1

    def test_half_life_value(self):
        """验证半衰期配置"""
        assert TIME_DECAY_HALF_LIFE_DAYS == 90


class TestMemoryRetrievalResult:
    """测试检索结果模型"""

    def test_combined_score_calculation(self):
        """测试组合评分计算"""
        memory = AnalysisMemory(
            symbol="AAPL",
            date="2025-01-01",
            signal="Buy",
            confidence=80,
            reasoning_summary="Test",
        )

        result = MemoryRetrievalResult(
            memory=memory,
            similarity=0.8,
            days_ago=90,
            time_weight=0.5,
            combined_score=0.4,  # 0.8 * 0.5
        )

        assert result.similarity == 0.8
        assert result.time_weight == 0.5
        assert result.combined_score == 0.4

    def test_default_values(self):
        """测试默认值"""
        memory = AnalysisMemory(
            symbol="AAPL",
            date="2025-01-01",
            signal="Buy",
            confidence=80,
            reasoning_summary="Test",
        )

        result = MemoryRetrievalResult(
            memory=memory,
            similarity=0.8,
            days_ago=0,
        )

        assert result.time_weight == 1.0
        assert result.combined_score == 0.0


class TestRetrieveSimilarEnhanced:
    """测试增强版相似检索"""

    @pytest.fixture
    def mock_memory_service(self):
        """创建带 mock ChromaDB 的 MemoryService"""
        with patch("services.memory_service.CHROMADB_AVAILABLE", True):
            service = MemoryService.__new__(MemoryService)
            service._client = MagicMock()
            service._collection = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_filters_by_similarity_threshold(self, mock_memory_service):
        """测试相似度阈值过滤"""
        today = datetime.now().date()
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

        # Mock ChromaDB 返回结果：一个高相似度，一个低相似度
        mock_memory_service._collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "metadatas": [[
                {
                    "symbol": "AAPL",
                    "date": yesterday,
                    "signal": "Buy",
                    "confidence": 80,
                    "reasoning_summary": "High similarity",
                },
                {
                    "symbol": "AAPL",
                    "date": yesterday,
                    "signal": "Hold",
                    "confidence": 50,
                    "reasoning_summary": "Low similarity",
                },
            ]],
            "distances": [[0.1, 0.8]],  # 距离：0.1 -> 相似度0.9, 0.8 -> 相似度0.2
        }

        results = await mock_memory_service.retrieve_similar(
            symbol="AAPL",
            n_results=10,
            similarity_threshold=0.3,
        )

        # 只有高相似度的结果应该被返回
        assert len(results) == 1
        assert results[0].similarity == 0.9

    @pytest.mark.asyncio
    async def test_sorts_by_combined_score(self, mock_memory_service):
        """测试按组合评分排序"""
        today = datetime.now().date()
        recent = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        old = (today - timedelta(days=180)).strftime("%Y-%m-%d")

        # Mock：旧记忆相似度更高，但新记忆应该排在前面（因为时间权重）
        mock_memory_service._collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "metadatas": [[
                {
                    "symbol": "AAPL",
                    "date": old,  # 180天前
                    "signal": "Buy",
                    "confidence": 90,
                    "reasoning_summary": "Old but high similarity",
                },
                {
                    "symbol": "AAPL",
                    "date": recent,  # 10天前
                    "signal": "Buy",
                    "confidence": 70,
                    "reasoning_summary": "Recent but lower similarity",
                },
            ]],
            "distances": [[0.05, 0.2]],  # 相似度：0.95 vs 0.8
        }

        results = await mock_memory_service.retrieve_similar(
            symbol="AAPL",
            n_results=10,
            time_decay_enabled=True,
        )

        # 两个结果都应该返回
        assert len(results) == 2

        # 组合评分应该考虑时间衰减
        # 旧记忆：0.95 * ~0.25 = ~0.24
        # 新记忆：0.8 * ~0.93 = ~0.74
        # 新记忆应该排在前面
        assert results[0].days_ago < results[1].days_ago

    @pytest.mark.asyncio
    async def test_time_decay_disabled(self, mock_memory_service):
        """测试禁用时间衰减"""
        today = datetime.now().date()
        old = (today - timedelta(days=180)).strftime("%Y-%m-%d")

        mock_memory_service._collection.query.return_value = {
            "ids": [["id1"]],
            "metadatas": [[
                {
                    "symbol": "AAPL",
                    "date": old,
                    "signal": "Buy",
                    "confidence": 90,
                    "reasoning_summary": "Old memory",
                },
            ]],
            "distances": [[0.1]],
        }

        results = await mock_memory_service.retrieve_similar(
            symbol="AAPL",
            n_results=10,
            time_decay_enabled=False,
        )

        # 禁用时间衰减时，time_weight 应该是 1.0
        assert len(results) == 1
        assert results[0].time_weight == 1.0
        assert results[0].combined_score == results[0].similarity

    @pytest.mark.asyncio
    async def test_custom_similarity_threshold(self, mock_memory_service):
        """测试自定义相似度阈值"""
        today = datetime.now().date()
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")

        mock_memory_service._collection.query.return_value = {
            "ids": [["id1", "id2", "id3"]],
            "metadatas": [[
                {"symbol": "AAPL", "date": yesterday, "signal": "Buy", "confidence": 80, "reasoning_summary": "High"},
                {"symbol": "AAPL", "date": yesterday, "signal": "Hold", "confidence": 60, "reasoning_summary": "Mid"},
                {"symbol": "AAPL", "date": yesterday, "signal": "Sell", "confidence": 40, "reasoning_summary": "Low"},
            ]],
            "distances": [[0.1, 0.4, 0.7]],  # 相似度：0.9, 0.6, 0.3
        }

        # 使用高阈值 0.7
        results = await mock_memory_service.retrieve_similar(
            symbol="AAPL",
            n_results=10,
            similarity_threshold=0.7,
        )

        # 只有相似度 >= 0.7 的结果
        assert len(results) == 1
        assert results[0].similarity == 0.9


class TestGetStats:
    """测试统计信息"""

    def test_stats_include_retrieval_config(self):
        """测试统计信息包含检索配置"""
        with patch("services.memory_service.CHROMADB_AVAILABLE", True):
            service = MemoryService.__new__(MemoryService)
            service._client = MagicMock()
            service._collection = MagicMock()
            service._collection.count.return_value = 100

            stats = service.get_stats()

            assert stats["status"] == "available"
            assert stats["total_memories"] == 100
            assert "retrieval_config" in stats
            assert stats["retrieval_config"]["similarity_threshold"] == SIMILARITY_THRESHOLD
            assert stats["retrieval_config"]["time_decay_half_life_days"] == TIME_DECAY_HALF_LIFE_DAYS
            assert stats["retrieval_config"]["min_time_weight"] == MIN_TIME_WEIGHT
