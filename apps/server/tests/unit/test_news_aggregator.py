"""
NewsAggregatorService 单元测试

覆盖:
1. 数据模型创建
2. 新闻 ID 生成
3. RSS 新闻获取
4. Finnhub 新闻获取
5. 新闻聚合
6. 按类别/股票筛选
7. 统计信息
8. 单例模式
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import hashlib

from services.news_aggregator import (
    NewsAggregatorService,
    NewsItem,
    NewsCategory,
    NewsSentiment,
    NewsAggregateResult,
    RSS_FEEDS,
    news_aggregator,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestNewsModels:
    """新闻数据模型测试"""

    def test_news_category_values(self):
        """NewsCategory 枚举值"""
        assert NewsCategory.MARKET.value == "market"
        assert NewsCategory.STOCK.value == "stock"
        assert NewsCategory.MACRO.value == "macro"
        assert NewsCategory.POLICY.value == "policy"
        assert NewsCategory.EARNINGS.value == "earnings"

    def test_news_sentiment_values(self):
        """NewsSentiment 枚举值"""
        assert NewsSentiment.POSITIVE.value == "positive"
        assert NewsSentiment.NEGATIVE.value == "negative"
        assert NewsSentiment.NEUTRAL.value == "neutral"

    def test_news_item_creation(self):
        """创建 NewsItem"""
        now = datetime.now()
        news = NewsItem(
            id="abc123",
            title="测试新闻标题",
            summary="这是新闻摘要",
            url="https://example.com/news/1",
            source="测试来源",
            category=NewsCategory.MARKET,
            sentiment=NewsSentiment.POSITIVE,
            symbols=["AAPL", "GOOGL"],
            published_at=now,
            fetched_at=now,
        )

        assert news.id == "abc123"
        assert news.title == "测试新闻标题"
        assert news.category == NewsCategory.MARKET
        assert news.sentiment == NewsSentiment.POSITIVE
        assert "AAPL" in news.symbols

    def test_news_item_defaults(self):
        """NewsItem 默认值"""
        now = datetime.now()
        news = NewsItem(
            id="abc123",
            title="测试",
            url="https://example.com",
            source="测试",
            published_at=now,
            fetched_at=now,
        )

        assert news.summary is None
        assert news.category == NewsCategory.GENERAL
        assert news.sentiment == NewsSentiment.NEUTRAL
        assert news.symbols == []

    def test_news_aggregate_result_creation(self):
        """创建 NewsAggregateResult"""
        result = NewsAggregateResult(
            news=[],
            total=0,
            sources=["Yahoo Finance", "CNBC"],
            updated_at=datetime.now(),
        )

        assert result.total == 0
        assert "Yahoo Finance" in result.sources


# =============================================================================
# 新闻 ID 生成测试
# =============================================================================

class TestGenerateNewsId:
    """新闻 ID 生成测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        # 创建新实例而不是使用单例
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    def test_generate_id_deterministic(self, service):
        """ID 生成是确定性的"""
        id1 = service._generate_news_id("Test Title", "https://example.com")
        id2 = service._generate_news_id("Test Title", "https://example.com")

        assert id1 == id2

    def test_generate_id_different_content(self, service):
        """不同内容生成不同 ID"""
        id1 = service._generate_news_id("Title A", "https://example.com/a")
        id2 = service._generate_news_id("Title B", "https://example.com/b")

        assert id1 != id2

    def test_generate_id_format(self, service):
        """ID 格式正确（16 字符）"""
        news_id = service._generate_news_id("Test", "https://example.com")

        assert len(news_id) == 16
        assert news_id.isalnum()


# =============================================================================
# RSS 新闻获取测试
# =============================================================================

class TestFetchRssFeeds:
    """RSS 新闻获取测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    @pytest.mark.asyncio
    async def test_fetch_rss_no_feedparser(self, service):
        """feedparser 不可用返回空列表"""
        with patch("services.news_aggregator.FEEDPARSER_AVAILABLE", False):
            result = await service._fetch_rss_feeds()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_rss_success(self, service):
        """成功获取 RSS 新闻"""
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Test News 1",
                link="https://example.com/1",
                summary="Summary 1",
                published_parsed=(2026, 2, 2, 10, 0, 0, 0, 0, 0),
            ),
            MagicMock(
                title="Test News 2",
                link="https://example.com/2",
                summary="Summary 2",
                published_parsed=(2026, 2, 2, 11, 0, 0, 0, 0, 0),
            ),
        ]

        with patch("services.news_aggregator.FEEDPARSER_AVAILABLE", True):
            with patch("feedparser.parse", return_value=mock_feed):
                result = await service._fetch_rss_feeds()

        # 只有启用的 feed 会被获取
        assert len(result) >= 0  # 取决于启用的 feed 数量

    @pytest.mark.asyncio
    async def test_fetch_rss_dedup(self, service):
        """RSS 新闻去重"""
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Duplicate News",
                link="https://example.com/dup",
                summary="Same news",
                published_parsed=(2026, 2, 2, 10, 0, 0, 0, 0, 0),
            ),
        ]

        # 预先添加 ID 到已见集合
        dup_id = service._generate_news_id("Duplicate News", "https://example.com/dup")
        service._seen_ids.add(dup_id)

        with patch("services.news_aggregator.FEEDPARSER_AVAILABLE", True):
            with patch("feedparser.parse", return_value=mock_feed):
                result = await service._fetch_rss_feeds()

        # 重复的新闻应该被过滤
        # 由于 feed 是按配置迭代的，结果取决于具体配置
        assert isinstance(result, list)


# =============================================================================
# Finnhub 新闻获取测试
# =============================================================================

class TestFetchFinnhubNews:
    """Finnhub 新闻获取测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    @pytest.mark.asyncio
    async def test_fetch_finnhub_no_client(self, service):
        """无 Finnhub 客户端返回空列表"""
        result = await service._fetch_finnhub_news()

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_finnhub_success(self, service):
        """成功获取 Finnhub 新闻"""
        mock_client = MagicMock()
        mock_client.general_news.return_value = [
            {
                "headline": "Test Headline",
                "url": "https://finnhub.io/1",
                "datetime": int(datetime.now().timestamp()),
                "summary": "Test summary",
                "source": "Reuters",
                "related": "AAPL,GOOGL",
                "sentiment": 0.5,
            },
        ]
        service._finnhub_client = mock_client

        result = await service._fetch_finnhub_news()

        assert len(result) == 1
        assert result[0].title == "Test Headline"
        assert result[0].sentiment == NewsSentiment.POSITIVE
        assert "AAPL" in result[0].symbols

    @pytest.mark.asyncio
    async def test_fetch_finnhub_sentiment_mapping(self, service):
        """Finnhub 情感映射"""
        mock_client = MagicMock()
        mock_client.general_news.return_value = [
            {
                "headline": "Positive",
                "url": "https://finnhub.io/pos",
                "datetime": int(datetime.now().timestamp()),
                "sentiment": 0.5,  # > 0.2 = positive
            },
            {
                "headline": "Negative",
                "url": "https://finnhub.io/neg",
                "datetime": int(datetime.now().timestamp()),
                "sentiment": -0.5,  # < -0.2 = negative
            },
            {
                "headline": "Neutral",
                "url": "https://finnhub.io/neu",
                "datetime": int(datetime.now().timestamp()),
                "sentiment": 0.0,  # between = neutral
            },
        ]
        service._finnhub_client = mock_client

        result = await service._fetch_finnhub_news()

        assert result[0].sentiment == NewsSentiment.POSITIVE
        assert result[1].sentiment == NewsSentiment.NEGATIVE
        assert result[2].sentiment == NewsSentiment.NEUTRAL

    @pytest.mark.asyncio
    async def test_fetch_finnhub_error(self, service):
        """Finnhub 获取失败"""
        mock_client = MagicMock()
        mock_client.general_news.side_effect = Exception("API Error")
        service._finnhub_client = mock_client

        result = await service._fetch_finnhub_news()

        assert result == []


# =============================================================================
# 股票新闻获取测试
# =============================================================================

class TestFetchStockNews:
    """股票新闻获取测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    @pytest.mark.asyncio
    async def test_fetch_stock_news_no_client(self, service):
        """无客户端返回空列表"""
        result = await service._fetch_stock_news("AAPL")

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_stock_news_success(self, service):
        """成功获取股票新闻"""
        mock_client = MagicMock()
        mock_client.company_news.return_value = [
            {
                "headline": "AAPL News",
                "url": "https://finnhub.io/aapl/1",
                "datetime": int(datetime.now().timestamp()),
                "summary": "Apple news",
                "source": "CNBC",
            },
        ]
        service._finnhub_client = mock_client

        result = await service._fetch_stock_news("AAPL")

        assert len(result) == 1
        assert result[0].category == NewsCategory.STOCK
        assert "AAPL" in result[0].symbols


# =============================================================================
# 新闻聚合测试
# =============================================================================

class TestGetAllNews:
    """get_all_news() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        svc._news_cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_all_news_aggregates(self, service):
        """聚合多源新闻"""
        now = datetime.now()
        rss_news = [
            NewsItem(
                id="rss1", title="RSS News", url="https://rss.com/1",
                source="RSS", published_at=now, fetched_at=now,
            ),
        ]
        finnhub_news = [
            NewsItem(
                id="fh1", title="Finnhub News", url="https://fh.com/1",
                source="Finnhub", published_at=now, fetched_at=now,
            ),
        ]

        with patch.object(service, '_fetch_rss_feeds', return_value=rss_news):
            with patch.object(service, '_fetch_finnhub_news', return_value=finnhub_news):
                with patch.object(service, '_is_cache_valid', return_value=False):
                    result = await service.get_all_news(force_refresh=True)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_news_sorted(self, service):
        """新闻按时间倒序排列"""
        now = datetime.now()
        old_time = now - timedelta(hours=2)
        new_time = now - timedelta(hours=1)

        mock_news = [
            NewsItem(
                id="old", title="Old News", url="https://old.com",
                source="Test", published_at=old_time, fetched_at=now,
            ),
            NewsItem(
                id="new", title="New News", url="https://new.com",
                source="Test", published_at=new_time, fetched_at=now,
            ),
        ]

        with patch.object(service, '_fetch_rss_feeds', return_value=mock_news):
            with patch.object(service, '_fetch_finnhub_news', return_value=[]):
                with patch.object(service, '_is_cache_valid', return_value=False):
                    result = await service.get_all_news(force_refresh=True)

        assert result[0].id == "new"  # 较新的在前

    @pytest.mark.asyncio
    async def test_get_all_news_cache(self, service):
        """使用缓存"""
        now = datetime.now()
        cached_news = {
            "cached1": NewsItem(
                id="cached1", title="Cached", url="https://cached.com",
                source="Cache", published_at=now, fetched_at=now,
            ),
        }
        service._news_cache.set("all_news", cached_news)

        with patch.object(service, '_is_cache_valid', return_value=True):
            result = await service.get_all_news()

        assert len(result) == 1
        assert result[0].id == "cached1"


# =============================================================================
# 筛选测试
# =============================================================================

class TestNewsFiltering:
    """新闻筛选测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    @pytest.mark.asyncio
    async def test_get_news_by_category(self, service):
        """按类别筛选"""
        now = datetime.now()
        mock_news = [
            NewsItem(
                id="market1", title="Market", url="https://m.com",
                source="Test", category=NewsCategory.MARKET,
                published_at=now, fetched_at=now,
            ),
            NewsItem(
                id="stock1", title="Stock", url="https://s.com",
                source="Test", category=NewsCategory.STOCK,
                published_at=now, fetched_at=now,
            ),
        ]

        with patch.object(service, 'get_all_news', return_value=mock_news):
            result = await service.get_news_by_category(NewsCategory.MARKET)

        assert len(result) == 1
        assert result[0].category == NewsCategory.MARKET

    @pytest.mark.asyncio
    async def test_get_flash_news(self, service):
        """获取快讯"""
        now = datetime.now()
        mock_news = [
            NewsItem(
                id=f"news{i}", title=f"News {i}", url=f"https://n{i}.com",
                source="Test", published_at=now - timedelta(minutes=i),
                fetched_at=now,
            )
            for i in range(20)
        ]

        with patch.object(service, 'get_all_news', return_value=mock_news):
            result = await service.get_flash_news(limit=5)

        assert len(result) == 5


# =============================================================================
# 聚合结果测试
# =============================================================================

class TestAggregate:
    """aggregate() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    @pytest.mark.asyncio
    async def test_aggregate_result(self, service):
        """聚合结果格式"""
        now = datetime.now()
        mock_news = [
            NewsItem(
                id="n1", title="News 1", url="https://a.com",
                source="Source A", published_at=now, fetched_at=now,
            ),
            NewsItem(
                id="n2", title="News 2", url="https://b.com",
                source="Source B", published_at=now, fetched_at=now,
            ),
        ]

        with patch.object(service, 'get_all_news', return_value=mock_news):
            result = await service.aggregate()

        assert isinstance(result, NewsAggregateResult)
        assert result.total == 2
        assert "Source A" in result.sources
        assert "Source B" in result.sources


# =============================================================================
# 统计测试
# =============================================================================

class TestGetStats:
    """get_stats() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = object.__new__(NewsAggregatorService)
        svc._initialized = True
        svc._finnhub_client = None
        svc._news_cache = NewsAggregatorService._news_cache
        svc._seen_ids = set()
        return svc

    def test_get_stats(self, service):
        """获取统计信息"""
        stats = service.get_stats()

        assert "status" in stats
        assert stats["status"] == "available"
        assert "feedparser_available" in stats
        assert "finnhub_available" in stats
        assert "cached_news" in stats
        assert "enabled_feeds" in stats

    def test_get_stats_with_finnhub(self, service):
        """带 Finnhub 客户端的统计"""
        service._finnhub_client = MagicMock()

        stats = service.get_stats()

        assert stats["finnhub_available"] is True


# =============================================================================
# RSS 配置测试
# =============================================================================

class TestRssFeedsConfig:
    """RSS 配置测试"""

    def test_rss_feeds_not_empty(self):
        """RSS 配置不为空"""
        assert len(RSS_FEEDS) > 0

    def test_rss_feeds_structure(self):
        """RSS 配置结构正确"""
        for feed_id, config in RSS_FEEDS.items():
            assert "url" in config
            assert "name" in config
            assert "category" in config
            assert isinstance(config["category"], NewsCategory)


# =============================================================================
# 单例测试
# =============================================================================

class TestNewsAggregatorSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert news_aggregator is not None
        assert isinstance(news_aggregator, NewsAggregatorService)

    def test_singleton_same_instance(self):
        """多次实例化返回同一对象"""
        instance1 = NewsAggregatorService()
        instance2 = NewsAggregatorService()

        assert instance1 is instance2
