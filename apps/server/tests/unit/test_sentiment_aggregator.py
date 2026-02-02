"""
SentimentAggregator 单元测试

覆盖:
1. 枚举类型
2. 数据类
3. 情绪分数计算
4. 关键词提取
5. 情绪分析
6. 聚合功能
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from services.sentiment_aggregator import (
    SentimentAggregator,
    SentimentSource,
    SentimentLevel,
    SentimentPost,
    SentimentSummary,
    sentiment_aggregator,
)


# =============================================================================
# 枚举测试
# =============================================================================

class TestSentimentEnums:
    """情绪枚举测试"""

    def test_sentiment_source_values(self):
        """SentimentSource 枚举值"""
        assert SentimentSource.EASTMONEY_GUBA.value == "eastmoney_guba"
        assert SentimentSource.XUEQIU.value == "xueqiu"
        assert SentimentSource.WEIBO.value == "weibo"
        assert SentimentSource.REDDIT.value == "reddit"
        assert SentimentSource.TWITTER.value == "twitter"
        assert SentimentSource.NEWS.value == "news"

    def test_sentiment_level_values(self):
        """SentimentLevel 枚举值"""
        assert SentimentLevel.VERY_BULLISH.value == "very_bullish"
        assert SentimentLevel.BULLISH.value == "bullish"
        assert SentimentLevel.NEUTRAL.value == "neutral"
        assert SentimentLevel.BEARISH.value == "bearish"
        assert SentimentLevel.VERY_BEARISH.value == "very_bearish"


# =============================================================================
# SentimentPost 测试
# =============================================================================

class TestSentimentPost:
    """SentimentPost 数据类测试"""

    def test_post_creation(self):
        """创建 SentimentPost"""
        post = SentimentPost(
            source="reddit",
            title="AAPL to the moon!",
            content="Apple is going to break new highs",
            url="https://reddit.com/r/wallstreetbets/abc",
            author="user123",
            publish_time="2026-02-01T10:00:00",
            likes=100,
            comments=50,
            sentiment_score=0.8,
            keywords=["moon", "new high"],
        )

        assert post.source == "reddit"
        assert post.title == "AAPL to the moon!"
        assert post.sentiment_score == 0.8
        assert "moon" in post.keywords

    def test_post_defaults(self):
        """SentimentPost 默认值"""
        post = SentimentPost(
            source="news",
            title="Test",
            content="Test content",
        )

        assert post.url is None
        assert post.author is None
        assert post.likes == 0
        assert post.comments == 0
        assert post.sentiment_score == 0
        assert post.keywords == []

    def test_post_to_dict(self):
        """SentimentPost to_dict"""
        post = SentimentPost(
            source="news",
            title="Test",
            content="Content",
            sentiment_score=0.5,
        )

        d = post.to_dict()

        assert d["source"] == "news"
        assert d["title"] == "Test"
        assert d["sentiment_score"] == 0.5


# =============================================================================
# SentimentSummary 测试
# =============================================================================

class TestSentimentSummary:
    """SentimentSummary 数据类测试"""

    def test_summary_creation(self):
        """创建 SentimentSummary"""
        summary = SentimentSummary(
            symbol="AAPL",
            market="US",
            analysis_time="2026-02-02T10:00:00",
            overall_sentiment="bullish",
            sentiment_score=0.45,
            confidence=75,
            total_posts=100,
            bullish_count=60,
            bearish_count=20,
            neutral_count=20,
            top_keywords=["growth", "beat"],
            hot_topics=["AAPL earnings beat"],
            sources_summary={"reddit": {"posts_count": 50}},
            sample_posts=[],
        )

        assert summary.symbol == "AAPL"
        assert summary.overall_sentiment == "bullish"
        assert summary.confidence == 75

    def test_summary_to_dict(self):
        """SentimentSummary to_dict"""
        post = SentimentPost(source="news", title="Test", content="Content")
        summary = SentimentSummary(
            symbol="AAPL",
            market="US",
            analysis_time="2026-02-02T10:00:00",
            overall_sentiment="neutral",
            sentiment_score=0,
            confidence=50,
            total_posts=1,
            bullish_count=0,
            bearish_count=0,
            neutral_count=1,
            top_keywords=[],
            hot_topics=[],
            sources_summary={},
            sample_posts=[post],
        )

        d = summary.to_dict()

        assert d["symbol"] == "AAPL"
        assert len(d["sample_posts"]) == 1
        assert d["sample_posts"][0]["source"] == "news"


# =============================================================================
# 情绪分数计算测试
# =============================================================================

class TestCalculateSentimentScore:
    """情绪分数计算测试"""

    @pytest.fixture
    def aggregator(self):
        return SentimentAggregator()

    def test_bullish_chinese_text(self, aggregator):
        """中文利好文本"""
        text = "这只股票涨停了，利好消息不断，看多加仓"
        score = aggregator._calculate_sentiment_score(text, is_chinese=True)

        assert score > 0

    def test_bearish_chinese_text(self, aggregator):
        """中文利空文本"""
        text = "利空消息，股价跌停，风险加大，建议减仓"
        score = aggregator._calculate_sentiment_score(text, is_chinese=True)

        assert score < 0

    def test_neutral_chinese_text(self, aggregator):
        """中文中性文本"""
        text = "今天天气不错，适合出门散步"
        score = aggregator._calculate_sentiment_score(text, is_chinese=True)

        assert score == 0

    def test_bullish_english_text(self, aggregator):
        """英文利好文本"""
        text = "AAPL is bullish, going to the moon, buy now!"
        score = aggregator._calculate_sentiment_score(text, is_chinese=False)

        assert score > 0

    def test_bearish_english_text(self, aggregator):
        """英文利空文本"""
        text = "This stock is bearish, going to crash, sell now!"
        score = aggregator._calculate_sentiment_score(text, is_chinese=False)

        assert score < 0

    def test_neutral_english_text(self, aggregator):
        """英文中性文本"""
        text = "The weather is nice today"
        score = aggregator._calculate_sentiment_score(text, is_chinese=False)

        assert score == 0

    def test_empty_text(self, aggregator):
        """空文本"""
        score = aggregator._calculate_sentiment_score("", is_chinese=True)
        assert score == 0

    def test_mixed_sentiment(self, aggregator):
        """混合情绪"""
        text = "bullish on earnings but bearish on valuation"
        score = aggregator._calculate_sentiment_score(text, is_chinese=False)

        # 混合情绪，接近中性
        assert -0.5 <= score <= 0.5


# =============================================================================
# 关键词提取测试
# =============================================================================

class TestExtractKeywords:
    """关键词提取测试"""

    @pytest.fixture
    def aggregator(self):
        return SentimentAggregator()

    def test_extract_chinese_keywords(self, aggregator):
        """提取中文关键词"""
        text = "利好消息，股价涨停，龙头股强势"
        keywords = aggregator._extract_keywords(text, "CN", max_keywords=5)

        assert len(keywords) > 0
        assert "利好" in keywords or "涨停" in keywords or "龙头" in keywords

    def test_extract_english_keywords(self, aggregator):
        """提取英文关键词"""
        text = "Stock is bullish with strong growth potential, buy now"
        keywords = aggregator._extract_keywords(text, "US", max_keywords=5)

        assert len(keywords) > 0
        assert "bullish" in keywords or "growth" in keywords or "buy" in keywords

    def test_extract_no_keywords(self, aggregator):
        """无关键词"""
        text = "The weather is nice today"
        keywords = aggregator._extract_keywords(text, "US", max_keywords=5)

        assert keywords == []

    def test_extract_empty_text(self, aggregator):
        """空文本"""
        keywords = aggregator._extract_keywords("", "US")
        assert keywords == []

    def test_max_keywords_limit(self, aggregator):
        """最大关键词限制"""
        text = "bullish buy long moon rocket breakout growth strong upgrade"
        keywords = aggregator._extract_keywords(text, "US", max_keywords=3)

        assert len(keywords) <= 3


# =============================================================================
# 情绪分析测试
# =============================================================================

class TestAnalyzeSentiment:
    """情绪分析测试"""

    @pytest.fixture
    def aggregator(self):
        return SentimentAggregator()

    def test_analyze_bullish_posts(self, aggregator):
        """分析利好帖子"""
        posts = [
            SentimentPost(source="reddit", title="Buy", content="Bull", sentiment_score=0.8, likes=100, keywords=["buy"]),
            SentimentPost(source="reddit", title="Long", content="Moon", sentiment_score=0.6, likes=50, keywords=["long"]),
            SentimentPost(source="news", title="Strong", content="Growth", sentiment_score=0.4, keywords=["growth"]),
        ]

        result = aggregator._analyze_sentiment("AAPL", "US", posts, {"reddit": {}})

        assert result.overall_sentiment in [SentimentLevel.BULLISH.value, SentimentLevel.VERY_BULLISH.value]
        assert result.sentiment_score > 0
        assert result.bullish_count >= 2

    def test_analyze_bearish_posts(self, aggregator):
        """分析利空帖子"""
        posts = [
            SentimentPost(source="reddit", title="Sell", content="Crash", sentiment_score=-0.8, keywords=["sell"]),
            SentimentPost(source="reddit", title="Short", content="Dump", sentiment_score=-0.6, keywords=["short"]),
            SentimentPost(source="news", title="Weak", content="Decline", sentiment_score=-0.5, keywords=["weak"]),
        ]

        result = aggregator._analyze_sentiment("AAPL", "US", posts, {"reddit": {}})

        assert result.overall_sentiment in [SentimentLevel.BEARISH.value, SentimentLevel.VERY_BEARISH.value]
        assert result.sentiment_score < 0
        assert result.bearish_count >= 2

    def test_analyze_neutral_posts(self, aggregator):
        """分析中性帖子"""
        posts = [
            SentimentPost(source="news", title="News 1", content="Content", sentiment_score=0),
            SentimentPost(source="news", title="News 2", content="Content", sentiment_score=0.1),
            SentimentPost(source="news", title="News 3", content="Content", sentiment_score=-0.1),
        ]

        result = aggregator._analyze_sentiment("AAPL", "US", posts, {"news": {}})

        assert result.overall_sentiment == SentimentLevel.NEUTRAL.value
        assert -0.15 <= result.sentiment_score <= 0.15

    def test_analyze_confidence(self, aggregator):
        """分析置信度"""
        # 一致的情绪应该有更高的置信度
        consistent_posts = [
            SentimentPost(source="reddit", title="Bull", content="", sentiment_score=0.8),
            SentimentPost(source="reddit", title="Bull", content="", sentiment_score=0.7),
            SentimentPost(source="reddit", title="Bull", content="", sentiment_score=0.9),
        ]

        result = aggregator._analyze_sentiment("AAPL", "US", consistent_posts, {})

        assert result.confidence > 0

    def test_analyze_top_keywords(self, aggregator):
        """分析热门关键词"""
        posts = [
            SentimentPost(source="reddit", title="", content="", keywords=["buy", "growth"]),
            SentimentPost(source="reddit", title="", content="", keywords=["buy", "strong"]),
            SentimentPost(source="news", title="", content="", keywords=["buy"]),
        ]

        result = aggregator._analyze_sentiment("AAPL", "US", posts, {})

        assert "buy" in result.top_keywords  # 出现 3 次

    def test_analyze_hot_topics(self, aggregator):
        """分析热点话题"""
        posts = [
            SentimentPost(source="reddit", title="Big News!", content="", likes=1000, comments=500),
            SentimentPost(source="reddit", title="Small Update", content="", likes=10, comments=5),
        ]

        result = aggregator._analyze_sentiment("AAPL", "US", posts, {})

        # 高互动帖子应该在热点话题中
        assert "Big News!" in result.hot_topics


# =============================================================================
# 聚合功能测试
# =============================================================================

class TestAggregateSentiment:
    """聚合功能测试"""

    @pytest.fixture
    def aggregator(self):
        return SentimentAggregator()

    @pytest.mark.asyncio
    async def test_aggregate_no_posts(self, aggregator):
        """无帖子时返回空结果"""
        with patch.object(aggregator, '_fetch_from_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            result = await aggregator.aggregate_sentiment("AAPL", "US")

        assert result.total_posts == 0
        assert result.overall_sentiment == SentimentLevel.NEUTRAL.value
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_aggregate_with_posts(self, aggregator):
        """有帖子时正常聚合"""
        mock_posts = [
            SentimentPost(source="reddit", title="Bull", content="Going up", sentiment_score=0.5),
            SentimentPost(source="news", title="Growth", content="Strong", sentiment_score=0.3),
        ]

        with patch.object(aggregator, '_fetch_from_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_posts

            result = await aggregator.aggregate_sentiment("AAPL", "US")

        assert result.total_posts > 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_aggregate_cn_market(self, aggregator):
        """中国市场聚合"""
        mock_posts = [
            SentimentPost(source="eastmoney_guba", title="利好", content="涨停", sentiment_score=0.6),
        ]

        with patch.object(aggregator, '_fetch_from_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_posts
            with patch.object(aggregator, '_get_company_name_cn', new_callable=AsyncMock) as mock_name:
                mock_name.return_value = "贵州茅台"

                result = await aggregator.aggregate_sentiment("600519.SH", "CN")

        assert result.market == "CN"

    @pytest.mark.asyncio
    async def test_aggregate_hk_market(self, aggregator):
        """香港市场聚合"""
        mock_posts = [
            SentimentPost(source="xueqiu", title="看好", content="买入", sentiment_score=0.4),
        ]

        with patch.object(aggregator, '_fetch_from_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_posts
            with patch.object(aggregator, '_get_company_name_hk', new_callable=AsyncMock) as mock_name:
                mock_name.return_value = "腾讯"

                result = await aggregator.aggregate_sentiment("0700.HK", "HK")

        assert result.market == "HK"

    @pytest.mark.asyncio
    async def test_aggregate_source_error(self, aggregator):
        """数据源错误处理"""
        with patch.object(aggregator, '_fetch_from_source', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API Error")

            result = await aggregator.aggregate_sentiment("AAPL", "US")

        # 应该返回空结果而不是抛出异常
        assert result.total_posts == 0


# =============================================================================
# 数据源获取测试
# =============================================================================

class TestFetchFromSource:
    """数据源获取测试"""

    @pytest.fixture
    def aggregator(self):
        return SentimentAggregator()

    @pytest.mark.asyncio
    async def test_fetch_news_no_ddgs(self, aggregator):
        """无 DDGS 时返回空"""
        with patch.object(aggregator, '_get_ddgs', return_value=None):
            result = await aggregator._fetch_news("AAPL", "Apple", "US", 7, 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_eastmoney_no_ddgs(self, aggregator):
        """无 DDGS 时返回空"""
        with patch.object(aggregator, '_get_ddgs', return_value=None):
            result = await aggregator._fetch_eastmoney_guba("600519.SH", 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_xueqiu_no_ddgs(self, aggregator):
        """无 DDGS 时返回空"""
        with patch.object(aggregator, '_get_ddgs', return_value=None):
            result = await aggregator._fetch_xueqiu("600519.SH", "CN", 10)

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_reddit_no_ddgs(self, aggregator):
        """无 DDGS 时返回空"""
        with patch.object(aggregator, '_get_ddgs', return_value=None):
            result = await aggregator._fetch_reddit("AAPL", "Apple", 10)

        assert result == []


# =============================================================================
# 公司名称获取测试
# =============================================================================

class TestGetCompanyName:
    """公司名称获取测试"""

    @pytest.fixture
    def aggregator(self):
        return SentimentAggregator()

    @pytest.mark.asyncio
    async def test_get_cn_company_name(self, aggregator):
        """获取 A 股公司名称"""
        name = await aggregator._get_company_name_cn("600519.SH")
        assert name == "600519"

    @pytest.mark.asyncio
    async def test_get_hk_company_name(self, aggregator):
        """获取港股公司名称"""
        name = await aggregator._get_company_name_hk("0700.HK")
        assert name == "0700"


# =============================================================================
# DDGS 初始化测试
# =============================================================================

class TestGetDdgs:
    """DDGS 初始化测试"""

    def test_ddgs_not_available(self):
        """DDGS 不可用"""
        aggregator = SentimentAggregator()

        with patch("services.sentiment_aggregator.DDGS", None):
            result = aggregator._get_ddgs()

        assert result is None

    def test_ddgs_lazy_init(self):
        """DDGS 延迟初始化"""
        aggregator = SentimentAggregator()
        aggregator._ddgs = None

        mock_ddgs_class = MagicMock()
        mock_ddgs_instance = MagicMock()
        mock_ddgs_class.return_value = mock_ddgs_instance

        with patch("services.sentiment_aggregator.DDGS", mock_ddgs_class):
            result = aggregator._get_ddgs()

        assert result == mock_ddgs_instance


# =============================================================================
# 关键词配置测试
# =============================================================================

class TestKeywordConfig:
    """关键词配置测试"""

    def test_bullish_keywords_cn_not_empty(self):
        """中文利好关键词非空"""
        assert len(SentimentAggregator.BULLISH_KEYWORDS_CN) > 0

    def test_bearish_keywords_cn_not_empty(self):
        """中文利空关键词非空"""
        assert len(SentimentAggregator.BEARISH_KEYWORDS_CN) > 0

    def test_bullish_keywords_en_not_empty(self):
        """英文利好关键词非空"""
        assert len(SentimentAggregator.BULLISH_KEYWORDS_EN) > 0

    def test_bearish_keywords_en_not_empty(self):
        """英文利空关键词非空"""
        assert len(SentimentAggregator.BEARISH_KEYWORDS_EN) > 0


# =============================================================================
# 单例测试
# =============================================================================

class TestSentimentAggregatorSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert sentiment_aggregator is not None
        assert isinstance(sentiment_aggregator, SentimentAggregator)
