"""
MarketWatcherService 单元测试

覆盖:
1. 枚举类型
2. 数据模型
3. 获取市场指数
4. 情绪计算
5. 风险等级计算
6. 市场概览
7. 统计信息
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from services.market_watcher import (
    MarketWatcherService,
    MarketRegion,
    IndexStatus,
    MarketIndex,
    MarketOverview,
    MARKET_INDICES,
    market_watcher,
)


# =============================================================================
# 枚举测试
# =============================================================================

class TestMarketEnums:
    """市场枚举测试"""

    def test_market_region_values(self):
        """MarketRegion 枚举值"""
        assert MarketRegion.CN.value == "CN"
        assert MarketRegion.HK.value == "HK"
        assert MarketRegion.US.value == "US"
        assert MarketRegion.GLOBAL.value == "GLOBAL"

    def test_index_status_values(self):
        """IndexStatus 枚举值"""
        assert IndexStatus.TRADING.value == "trading"
        assert IndexStatus.CLOSED.value == "closed"
        assert IndexStatus.PRE_MARKET.value == "pre_market"
        assert IndexStatus.AFTER_HOURS.value == "after_hours"
        assert IndexStatus.UNKNOWN.value == "unknown"


# =============================================================================
# 数据模型测试
# =============================================================================

class TestMarketModels:
    """市场数据模型测试"""

    def test_market_index_creation(self):
        """创建 MarketIndex"""
        now = datetime.now()
        index = MarketIndex(
            code="^DJI",
            name="道琼斯工业",
            name_en="Dow Jones",
            region=MarketRegion.US,
            current=40000.0,
            change=200.0,
            change_percent=0.5,
            high=40100.0,
            low=39900.0,
            status=IndexStatus.TRADING,
            updated_at=now,
        )

        assert index.code == "^DJI"
        assert index.current == 40000.0
        assert index.region == MarketRegion.US
        assert index.status == IndexStatus.TRADING

    def test_market_index_defaults(self):
        """MarketIndex 默认值"""
        now = datetime.now()
        index = MarketIndex(
            code="^DJI",
            name="道琼斯",
            name_en="Dow Jones",
            region=MarketRegion.US,
            current=40000.0,
            change=0,
            change_percent=0,
            updated_at=now,
        )

        assert index.high is None
        assert index.low is None
        assert index.open is None
        assert index.prev_close is None
        assert index.volume is None
        assert index.status == IndexStatus.UNKNOWN

    def test_market_overview_creation(self):
        """创建 MarketOverview"""
        now = datetime.now()
        overview = MarketOverview(
            indices=[],
            global_sentiment="Bullish",
            risk_level=2,
            updated_at=now,
        )

        assert overview.global_sentiment == "Bullish"
        assert overview.risk_level == 2


# =============================================================================
# 配置测试
# =============================================================================

class TestMarketConfig:
    """市场配置测试"""

    def test_market_indices_not_empty(self):
        """市场指数配置不为空"""
        assert len(MARKET_INDICES) > 0

    def test_market_indices_have_required_fields(self):
        """市场指数配置包含必需字段"""
        for code, config in MARKET_INDICES.items():
            assert "name" in config
            assert "name_en" in config
            assert "region" in config
            assert isinstance(config["region"], MarketRegion)

    def test_cn_indices_have_ak_code(self):
        """中国指数有 akshare 代码"""
        cn_indices = [c for c, cfg in MARKET_INDICES.items() if cfg["region"] == MarketRegion.CN]
        for code in cn_indices:
            assert "ak_code" in MARKET_INDICES[code]


# =============================================================================
# 服务初始化测试
# =============================================================================

class TestMarketWatcherInit:
    """服务初始化测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert market_watcher is not None
        assert isinstance(market_watcher, MarketWatcherService)

    def test_singleton_same_instance(self):
        """多次实例化返回同一对象"""
        instance1 = MarketWatcherService()
        instance2 = MarketWatcherService()
        assert instance1 is instance2


# =============================================================================
# 情绪计算测试
# =============================================================================

class TestCalculateSentiment:
    """情绪计算测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        return svc

    def test_bullish_sentiment(self, service):
        """利好情绪"""
        indices = [
            MarketIndex(code="A", name="", name_en="", region=MarketRegion.US,
                       current=100, change=1, change_percent=1.0, updated_at=datetime.now()),
            MarketIndex(code="B", name="", name_en="", region=MarketRegion.US,
                       current=100, change=2, change_percent=2.0, updated_at=datetime.now()),
            MarketIndex(code="C", name="", name_en="", region=MarketRegion.US,
                       current=100, change=1.5, change_percent=1.5, updated_at=datetime.now()),
        ]

        sentiment = service._calculate_sentiment(indices)
        assert sentiment == "Bullish"

    def test_bearish_sentiment(self, service):
        """利空情绪"""
        indices = [
            MarketIndex(code="A", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-1, change_percent=-1.0, updated_at=datetime.now()),
            MarketIndex(code="B", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-2, change_percent=-2.0, updated_at=datetime.now()),
            MarketIndex(code="C", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-1.5, change_percent=-1.5, updated_at=datetime.now()),
        ]

        sentiment = service._calculate_sentiment(indices)
        assert sentiment == "Bearish"

    def test_neutral_sentiment(self, service):
        """中性情绪"""
        indices = [
            MarketIndex(code="A", name="", name_en="", region=MarketRegion.US,
                       current=100, change=0.5, change_percent=0.5, updated_at=datetime.now()),
            MarketIndex(code="B", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-0.5, change_percent=-0.5, updated_at=datetime.now()),
            MarketIndex(code="C", name="", name_en="", region=MarketRegion.US,
                       current=100, change=0.1, change_percent=0.1, updated_at=datetime.now()),
        ]

        sentiment = service._calculate_sentiment(indices)
        assert sentiment == "Neutral"

    def test_empty_indices(self, service):
        """空指数列表"""
        sentiment = service._calculate_sentiment([])
        assert sentiment == "Neutral"


# =============================================================================
# 风险等级计算测试
# =============================================================================

class TestCalculateRiskLevel:
    """风险等级计算测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        return svc

    def test_low_risk_strong_rally(self, service):
        """低风险 - 强劲上涨"""
        indices = [
            MarketIndex(code="A", name="", name_en="", region=MarketRegion.US,
                       current=100, change=4, change_percent=4.0, updated_at=datetime.now()),
            MarketIndex(code="B", name="", name_en="", region=MarketRegion.US,
                       current=100, change=3, change_percent=3.0, updated_at=datetime.now()),
        ]

        risk = service._calculate_risk_level(indices)
        assert risk <= 2

    def test_high_risk_strong_decline(self, service):
        """高风险 - 强劲下跌"""
        indices = [
            MarketIndex(code="A", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-4, change_percent=-4.0, updated_at=datetime.now()),
            MarketIndex(code="B", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-3, change_percent=-3.0, updated_at=datetime.now()),
        ]

        risk = service._calculate_risk_level(indices)
        assert risk >= 4

    def test_medium_risk_mixed(self, service):
        """中等风险 - 混合"""
        indices = [
            MarketIndex(code="A", name="", name_en="", region=MarketRegion.US,
                       current=100, change=0.5, change_percent=0.5, updated_at=datetime.now()),
            MarketIndex(code="B", name="", name_en="", region=MarketRegion.US,
                       current=100, change=-0.5, change_percent=-0.5, updated_at=datetime.now()),
        ]

        risk = service._calculate_risk_level(indices)
        assert 2 <= risk <= 4

    def test_empty_indices_default_risk(self, service):
        """空指数默认风险"""
        risk = service._calculate_risk_level([])
        assert risk == 3


# =============================================================================
# 获取指数测试
# =============================================================================

class TestGetIndices:
    """获取指数测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        svc._cache = MarketWatcherService._cache
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_all_indices_from_cache(self, service):
        """从缓存获取指数"""
        now = datetime.now()
        cached_indices = {
            "^DJI": MarketIndex(
                code="^DJI", name="道琼斯", name_en="Dow Jones",
                region=MarketRegion.US, current=40000, change=100,
                change_percent=0.25, updated_at=now
            )
        }
        service._cache.set("indices", cached_indices)

        result = await service.get_all_indices()

        assert len(result) == 1
        assert result[0].code == "^DJI"

    @pytest.mark.asyncio
    async def test_get_all_indices_force_refresh(self, service):
        """强制刷新"""
        now = datetime.now()
        cached_indices = {
            "^DJI": MarketIndex(
                code="^DJI", name="道琼斯", name_en="Dow Jones",
                region=MarketRegion.US, current=40000, change=100,
                change_percent=0.25, updated_at=now
            )
        }
        service._cache.set("indices", cached_indices)

        with patch.object(service, '_fetch_cn_indices', new_callable=AsyncMock) as mock_cn:
            with patch.object(service, '_fetch_global_indices', new_callable=AsyncMock) as mock_global:
                mock_cn.return_value = []
                mock_global.return_value = []

                result = await service.get_all_indices(force_refresh=True)

        mock_cn.assert_called_once()
        mock_global.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_index_by_code(self, service):
        """获取单个指数"""
        now = datetime.now()
        cached_indices = {
            "^DJI": MarketIndex(
                code="^DJI", name="道琼斯", name_en="Dow Jones",
                region=MarketRegion.US, current=40000, change=100,
                change_percent=0.25, updated_at=now
            ),
            "^GSPC": MarketIndex(
                code="^GSPC", name="标普500", name_en="S&P 500",
                region=MarketRegion.US, current=5000, change=50,
                change_percent=1.0, updated_at=now
            ),
        }
        service._cache.set("indices", cached_indices)

        result = await service.get_index("^DJI")

        assert result is not None
        assert result.code == "^DJI"

    @pytest.mark.asyncio
    async def test_get_index_not_found(self, service):
        """指数未找到"""
        service._cache.set("indices", {})

        with patch.object(service, 'get_all_indices', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            result = await service.get_index("INVALID")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_indices_by_region(self, service):
        """按区域获取指数"""
        now = datetime.now()
        mock_indices = [
            MarketIndex(code="^DJI", name="道琼斯", name_en="Dow Jones",
                       region=MarketRegion.US, current=40000, change=100,
                       change_percent=0.25, updated_at=now),
            MarketIndex(code="000001.SS", name="上证指数", name_en="SSE",
                       region=MarketRegion.CN, current=3000, change=10,
                       change_percent=0.33, updated_at=now),
        ]

        with patch.object(service, 'get_all_indices', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_indices
            result = await service.get_indices_by_region(MarketRegion.US)

        assert len(result) == 1
        assert result[0].region == MarketRegion.US


# =============================================================================
# 市场概览测试
# =============================================================================

class TestGetMarketOverview:
    """市场概览测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        return svc

    @pytest.mark.asyncio
    async def test_get_market_overview(self, service):
        """获取市场概览"""
        now = datetime.now()
        mock_indices = [
            MarketIndex(code="^DJI", name="道琼斯", name_en="Dow Jones",
                       region=MarketRegion.US, current=40000, change=100,
                       change_percent=0.25, updated_at=now),
        ]

        with patch.object(service, 'get_all_indices', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_indices
            result = await service.get_market_overview()

        assert isinstance(result, MarketOverview)
        assert len(result.indices) == 1
        assert result.global_sentiment in ["Bullish", "Bearish", "Neutral"]
        assert 1 <= result.risk_level <= 5


# =============================================================================
# 获取 CN 指数测试
# =============================================================================

class TestFetchCnIndices:
    """获取 CN 指数测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        return svc

    @pytest.mark.asyncio
    async def test_fetch_cn_no_akshare(self, service):
        """无 akshare 返回空"""
        with patch("services.market_watcher.AKSHARE_AVAILABLE", False):
            result = await service._fetch_cn_indices()

        assert result == []


# =============================================================================
# 获取 Global 指数测试
# =============================================================================

class TestFetchGlobalIndices:
    """获取 Global 指数测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        return svc

    @pytest.mark.asyncio
    async def test_fetch_global_no_yfinance(self, service):
        """无 yfinance 返回空"""
        with patch("services.market_watcher.YFINANCE_AVAILABLE", False):
            result = await service._fetch_global_indices()

        assert result == []


# =============================================================================
# 统计信息测试
# =============================================================================

class TestGetStats:
    """统计信息测试"""

    @pytest.fixture
    def service(self):
        svc = object.__new__(MarketWatcherService)
        svc._initialized = True
        svc._cache = MarketWatcherService._cache
        return svc

    def test_get_stats(self, service):
        """获取统计信息"""
        stats = service.get_stats()

        assert "status" in stats
        assert stats["status"] == "available"
        assert "akshare_available" in stats
        assert "yfinance_available" in stats
        assert "cached_indices" in stats

    def test_get_stats_with_cache(self, service):
        """有缓存时的统计"""
        now = datetime.now()
        service._cache.set("indices", {
            "^DJI": MarketIndex(code="^DJI", name="道琼斯", name_en="Dow Jones",
                               region=MarketRegion.US, current=40000, change=0,
                               change_percent=0, updated_at=now)
        })

        stats = service.get_stats()

        assert stats["cached_indices"] == 1
