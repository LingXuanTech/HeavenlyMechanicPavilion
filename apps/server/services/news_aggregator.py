"""新闻聚合服务 - 多源金融新闻聚合"""
import asyncio
import hashlib
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from pydantic import BaseModel
from enum import Enum

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import finnhub
    FINNHUB_AVAILABLE = True
except ImportError:
    FINNHUB_AVAILABLE = False
    finnhub = None

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

from config.settings import settings

logger = structlog.get_logger()


class NewsCategory(str, Enum):
    """新闻类别"""
    MARKET = "market"       # 市场动态
    STOCK = "stock"         # 个股新闻
    MACRO = "macro"         # 宏观经济
    POLICY = "policy"       # 政策法规
    EARNINGS = "earnings"   # 财报业绩
    IPO = "ipo"             # IPO/新股
    FOREX = "forex"         # 外汇
    CRYPTO = "crypto"       # 加密货币
    GENERAL = "general"     # 综合


class NewsSentiment(str, Enum):
    """新闻情感"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class NewsItem(BaseModel):
    """新闻条目"""
    id: str
    title: str
    summary: Optional[str] = None
    url: str
    source: str
    category: NewsCategory = NewsCategory.GENERAL
    sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    symbols: List[str] = []  # 相关股票代码
    published_at: datetime
    fetched_at: datetime


class NewsAggregateResult(BaseModel):
    """新闻聚合结果"""
    news: List[NewsItem]
    total: int
    sources: List[str]
    updated_at: datetime


# RSS 新闻源配置
RSS_FEEDS = {
    # 中文财经
    "sina_finance": {
        "url": "https://finance.sina.com.cn/roll/index.d.html?cid=56588&page=1",
        "name": "新浪财经",
        "category": NewsCategory.MARKET,
        "enabled": False,  # 需要爬虫，暂时禁用
    },
    "wallstreetcn": {
        "url": "https://wallstreetcn.com/rss/news",
        "name": "华尔街见闻",
        "category": NewsCategory.MARKET,
        "enabled": True,
    },

    # 英文财经
    "yahoo_finance": {
        "url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
        "name": "Yahoo Finance",
        "category": NewsCategory.MARKET,
        "enabled": True,
    },
    "cnbc": {
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "name": "CNBC",
        "category": NewsCategory.MARKET,
        "enabled": True,
    },
    "reuters_business": {
        "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "name": "Reuters Business",
        "category": NewsCategory.MARKET,
        "enabled": True,
    },
}


class NewsAggregatorService:
    """
    新闻聚合服务

    功能：
    1. 从多个 RSS 源聚合新闻
    2. 从 Finnhub API 获取市场新闻
    3. 新闻去重和排序
    4. 按股票/类别筛选
    """

    _instance = None
    _news_cache: Dict[str, NewsItem] = {}
    _cache_time: Optional[datetime] = None
    _cache_ttl = timedelta(minutes=5)
    _seen_ids: Set[str] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        if not self._initialized:
            self._initialized = True
            self._finnhub_client = None

            # 初始化 Finnhub 客户端
            if FINNHUB_AVAILABLE and settings.FINNHUB_API_KEY:
                try:
                    self._finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
                    logger.info("Finnhub client initialized")
                except Exception as e:
                    logger.warning("Failed to initialize Finnhub client", error=str(e))

            logger.info("NewsAggregatorService initialized")

    def _generate_news_id(self, title: str, url: str) -> str:
        """生成新闻唯一 ID"""
        content = f"{title}|{url}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache_time or not self._news_cache:
            return False
        return datetime.now() - self._cache_time < self._cache_ttl

    async def _fetch_rss_feeds(self) -> List[NewsItem]:
        """从 RSS 源获取新闻"""
        if not FEEDPARSER_AVAILABLE:
            logger.warning("feedparser not available")
            return []

        news_items = []
        now = datetime.now()

        for feed_id, feed_config in RSS_FEEDS.items():
            if not feed_config.get("enabled", True):
                continue

            try:
                feed = feedparser.parse(feed_config["url"])

                for entry in feed.entries[:20]:  # 每个源取前 20 条
                    try:
                        # 解析发布时间
                        published_at = now
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published_at = datetime(*entry.published_parsed[:6])
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            published_at = datetime(*entry.updated_parsed[:6])

                        news_id = self._generate_news_id(entry.title, entry.link)

                        # 跳过已存在的新闻
                        if news_id in self._seen_ids:
                            continue

                        news_item = NewsItem(
                            id=news_id,
                            title=entry.title,
                            summary=entry.get('summary', '')[:500] if entry.get('summary') else None,
                            url=entry.link,
                            source=feed_config["name"],
                            category=feed_config.get("category", NewsCategory.GENERAL),
                            published_at=published_at,
                            fetched_at=now
                        )

                        news_items.append(news_item)
                        self._seen_ids.add(news_id)

                    except Exception as e:
                        logger.warning(f"Failed to parse RSS entry", feed=feed_id, error=str(e))

                logger.debug(f"Fetched RSS feed", feed=feed_id, count=len(feed.entries))

            except Exception as e:
                logger.warning(f"Failed to fetch RSS feed", feed=feed_id, error=str(e))

        return news_items

    async def _fetch_finnhub_news(self, category: str = "general") -> List[NewsItem]:
        """从 Finnhub 获取新闻"""
        if not self._finnhub_client:
            return []

        news_items = []
        now = datetime.now()

        try:
            # 获取市场新闻
            news = self._finnhub_client.general_news(category, min_id=0)

            for item in news[:30]:  # 取前 30 条
                try:
                    news_id = self._generate_news_id(item['headline'], item['url'])

                    if news_id in self._seen_ids:
                        continue

                    # 解析时间戳
                    published_at = datetime.fromtimestamp(item['datetime'])

                    # 解析情感
                    sentiment = NewsSentiment.NEUTRAL
                    if 'sentiment' in item:
                        if item['sentiment'] > 0.2:
                            sentiment = NewsSentiment.POSITIVE
                        elif item['sentiment'] < -0.2:
                            sentiment = NewsSentiment.NEGATIVE

                    news_item = NewsItem(
                        id=news_id,
                        title=item['headline'],
                        summary=item.get('summary', '')[:500] if item.get('summary') else None,
                        url=item['url'],
                        source=item.get('source', 'Finnhub'),
                        category=NewsCategory.MARKET,
                        sentiment=sentiment,
                        symbols=item.get('related', '').split(',') if item.get('related') else [],
                        published_at=published_at,
                        fetched_at=now
                    )

                    news_items.append(news_item)
                    self._seen_ids.add(news_id)

                except Exception as e:
                    logger.warning("Failed to parse Finnhub news item", error=str(e))

            logger.debug("Fetched Finnhub news", count=len(news_items))

        except Exception as e:
            logger.error("Failed to fetch Finnhub news", error=str(e))

        return news_items

    async def _fetch_stock_news(self, symbol: str) -> List[NewsItem]:
        """获取特定股票的新闻"""
        if not self._finnhub_client:
            return []

        news_items = []
        now = datetime.now()

        try:
            # 获取最近 7 天的新闻
            from_date = (now - timedelta(days=7)).strftime('%Y-%m-%d')
            to_date = now.strftime('%Y-%m-%d')

            news = self._finnhub_client.company_news(symbol, _from=from_date, to=to_date)

            for item in news[:20]:
                try:
                    news_id = self._generate_news_id(item['headline'], item['url'])

                    if news_id in self._seen_ids:
                        continue

                    published_at = datetime.fromtimestamp(item['datetime'])

                    news_item = NewsItem(
                        id=news_id,
                        title=item['headline'],
                        summary=item.get('summary', '')[:500] if item.get('summary') else None,
                        url=item['url'],
                        source=item.get('source', 'Finnhub'),
                        category=NewsCategory.STOCK,
                        symbols=[symbol],
                        published_at=published_at,
                        fetched_at=now
                    )

                    news_items.append(news_item)
                    self._seen_ids.add(news_id)

                except Exception as e:
                    logger.warning("Failed to parse stock news item", symbol=symbol, error=str(e))

        except Exception as e:
            logger.error("Failed to fetch stock news", symbol=symbol, error=str(e))

        return news_items

    async def get_all_news(self, force_refresh: bool = False) -> List[NewsItem]:
        """
        获取所有新闻

        Args:
            force_refresh: 强制刷新缓存

        Returns:
            新闻列表（按时间倒序）
        """
        if not force_refresh and self._is_cache_valid():
            return sorted(
                self._news_cache.values(),
                key=lambda x: x.published_at,
                reverse=True
            )

        # 并行获取各源新闻
        rss_task = asyncio.create_task(self._fetch_rss_feeds())
        finnhub_task = asyncio.create_task(self._fetch_finnhub_news())

        rss_news, finnhub_news = await asyncio.gather(rss_task, finnhub_task)

        all_news = rss_news + finnhub_news

        # 更新缓存
        for news in all_news:
            self._news_cache[news.id] = news

        self._cache_time = datetime.now()

        # 清理过期新闻（超过 3 天）
        cutoff = datetime.now() - timedelta(days=3)
        self._news_cache = {
            k: v for k, v in self._news_cache.items()
            if v.published_at > cutoff
        }

        logger.info("News aggregated", total=len(self._news_cache))

        return sorted(
            self._news_cache.values(),
            key=lambda x: x.published_at,
            reverse=True
        )

    async def get_news_by_category(self, category: NewsCategory) -> List[NewsItem]:
        """按类别获取新闻"""
        all_news = await self.get_all_news()
        return [n for n in all_news if n.category == category]

    async def get_news_by_symbol(self, symbol: str) -> List[NewsItem]:
        """获取特定股票的新闻"""
        # 先从缓存中查找
        all_news = await self.get_all_news()
        cached_news = [n for n in all_news if symbol in n.symbols]

        # 如果缓存中没有足够的相关新闻，单独获取
        if len(cached_news) < 5:
            stock_news = await self._fetch_stock_news(symbol)
            for news in stock_news:
                self._news_cache[news.id] = news
            cached_news = [n for n in self._news_cache.values() if symbol in n.symbols]

        return sorted(cached_news, key=lambda x: x.published_at, reverse=True)

    async def get_flash_news(self, limit: int = 10) -> List[NewsItem]:
        """获取快讯（最新的 N 条新闻）"""
        all_news = await self.get_all_news()
        return all_news[:limit]

    async def aggregate(self, force_refresh: bool = False) -> NewsAggregateResult:
        """聚合所有新闻并返回结果"""
        news = await self.get_all_news(force_refresh)
        sources = list(set(n.source for n in news))

        return NewsAggregateResult(
            news=news,
            total=len(news),
            sources=sources,
            updated_at=datetime.now()
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        return {
            "status": "available",
            "feedparser_available": FEEDPARSER_AVAILABLE,
            "finnhub_available": FINNHUB_AVAILABLE and self._finnhub_client is not None,
            "cached_news": len(self._news_cache),
            "cache_valid": self._is_cache_valid(),
            "last_update": self._cache_time.isoformat() if self._cache_time else None,
            "enabled_feeds": [k for k, v in RSS_FEEDS.items() if v.get("enabled", True)]
        }


# 全局单例
news_aggregator = NewsAggregatorService()
