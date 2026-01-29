"""舆情聚合服务

聚合多个社交媒体和论坛的舆情数据。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import structlog

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = structlog.get_logger(__name__)


class SentimentSource(str, Enum):
    """舆情数据源"""
    # 中国市场
    EASTMONEY_GUBA = "eastmoney_guba"  # 东财股吧
    XUEQIU = "xueqiu"                   # 雪球
    WEIBO = "weibo"                     # 微博财经

    # 美股市场
    REDDIT = "reddit"                   # Reddit
    TWITTER = "twitter"                 # Twitter/X
    STOCKTWITS = "stocktwits"           # StockTwits

    # 通用
    NEWS = "news"                       # 新闻
    SEARCH = "search"                   # 搜索引擎


class SentimentLevel(str, Enum):
    """情绪等级"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class SentimentPost:
    """单条舆情帖子"""
    source: str
    title: str
    content: str
    url: Optional[str] = None
    author: Optional[str] = None
    publish_time: Optional[str] = None
    likes: int = 0
    comments: int = 0
    sentiment_score: float = 0  # -1 到 1
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SentimentSummary:
    """舆情汇总"""
    symbol: str
    market: str
    analysis_time: str
    overall_sentiment: str
    sentiment_score: float  # -1 到 1
    confidence: int  # 0-100
    total_posts: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    top_keywords: List[str]
    hot_topics: List[str]
    sources_summary: Dict[str, Dict[str, Any]]
    sample_posts: List[SentimentPost]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["sample_posts"] = [p.to_dict() for p in self.sample_posts]
        return result


class SentimentAggregator:
    """舆情聚合器

    功能：
    1. 从多个来源收集舆情数据
    2. 分析情绪倾向
    3. 提取热点话题
    """

    # 情绪关键词
    BULLISH_KEYWORDS_CN = [
        "利好", "上涨", "涨停", "突破", "新高", "买入", "看多", "加仓",
        "利润", "增长", "超预期", "龙头", "强势", "牛市", "爆发",
    ]
    BEARISH_KEYWORDS_CN = [
        "利空", "下跌", "跌停", "破位", "新低", "卖出", "看空", "减仓",
        "亏损", "下滑", "不及预期", "风险", "弱势", "熊市", "暴跌",
    ]

    BULLISH_KEYWORDS_EN = [
        "bullish", "buy", "long", "moon", "rocket", "breakout", "new high",
        "beat", "growth", "strong", "upgrade", "outperform",
    ]
    BEARISH_KEYWORDS_EN = [
        "bearish", "sell", "short", "crash", "dump", "breakdown", "new low",
        "miss", "decline", "weak", "downgrade", "underperform",
    ]

    def __init__(self):
        self._ddgs = None

    def _get_ddgs(self):
        """延迟初始化 DuckDuckGo 搜索"""
        if DDGS is None:
            return None
        if self._ddgs is None:
            self._ddgs = DDGS()
        return self._ddgs

    async def aggregate_sentiment(
        self,
        symbol: str,
        market: str = "US",
        days_back: int = 7,
        max_posts_per_source: int = 20,
    ) -> SentimentSummary:
        """聚合舆情数据

        Args:
            symbol: 股票代码
            market: 市场（US, CN, HK）
            days_back: 回溯天数
            max_posts_per_source: 每个来源最大帖子数

        Returns:
            舆情汇总
        """
        all_posts: List[SentimentPost] = []
        sources_summary: Dict[str, Dict[str, Any]] = {}

        # 根据市场选择数据源
        if market == "CN":
            sources = [SentimentSource.EASTMONEY_GUBA, SentimentSource.XUEQIU, SentimentSource.NEWS]
            company_name = await self._get_company_name_cn(symbol)
        elif market == "HK":
            sources = [SentimentSource.XUEQIU, SentimentSource.NEWS]
            company_name = await self._get_company_name_hk(symbol)
        else:  # US
            sources = [SentimentSource.REDDIT, SentimentSource.NEWS]
            company_name = symbol  # 美股直接用代码

        # 并行收集各来源数据
        tasks = []
        for source in sources:
            task = self._fetch_from_source(
                source=source,
                symbol=symbol,
                company_name=company_name,
                market=market,
                days_back=days_back,
                max_posts=max_posts_per_source,
            )
            tasks.append((source, task))

        for source, task in tasks:
            try:
                posts = await task
                all_posts.extend(posts)

                # 统计来源摘要
                source_bullish = sum(1 for p in posts if p.sentiment_score > 0.2)
                source_bearish = sum(1 for p in posts if p.sentiment_score < -0.2)
                sources_summary[source.value] = {
                    "posts_count": len(posts),
                    "bullish_count": source_bullish,
                    "bearish_count": source_bearish,
                    "avg_sentiment": sum(p.sentiment_score for p in posts) / len(posts) if posts else 0,
                }
            except Exception as e:
                logger.warning(f"Failed to fetch from {source.value}", error=str(e))
                sources_summary[source.value] = {"error": str(e)}

        if not all_posts:
            return SentimentSummary(
                symbol=symbol,
                market=market,
                analysis_time=datetime.now().isoformat(),
                overall_sentiment=SentimentLevel.NEUTRAL.value,
                sentiment_score=0,
                confidence=0,
                total_posts=0,
                bullish_count=0,
                bearish_count=0,
                neutral_count=0,
                top_keywords=[],
                hot_topics=[],
                sources_summary=sources_summary,
                sample_posts=[],
                error="No posts collected from any source",
            )

        # 分析情绪
        return self._analyze_sentiment(
            symbol=symbol,
            market=market,
            posts=all_posts,
            sources_summary=sources_summary,
        )

    async def _fetch_from_source(
        self,
        source: SentimentSource,
        symbol: str,
        company_name: str,
        market: str,
        days_back: int,
        max_posts: int,
    ) -> List[SentimentPost]:
        """从指定来源获取数据"""
        if source == SentimentSource.NEWS:
            return await self._fetch_news(symbol, company_name, market, days_back, max_posts)
        elif source == SentimentSource.EASTMONEY_GUBA:
            return await self._fetch_eastmoney_guba(symbol, max_posts)
        elif source == SentimentSource.XUEQIU:
            return await self._fetch_xueqiu(symbol, market, max_posts)
        elif source == SentimentSource.REDDIT:
            return await self._fetch_reddit(symbol, company_name, max_posts)
        else:
            return []

    async def _fetch_news(
        self,
        symbol: str,
        company_name: str,
        market: str,
        days_back: int,
        max_posts: int,
    ) -> List[SentimentPost]:
        """通过搜索获取新闻"""
        ddgs = self._get_ddgs()
        if ddgs is None:
            return []

        posts = []
        try:
            # 构建搜索词
            if market == "CN":
                query = f"{company_name} 股票 新闻"
            elif market == "HK":
                query = f"{company_name} 港股 新闻"
            else:
                query = f"{symbol} stock news"

            results = list(ddgs.news(query, max_results=max_posts, timelimit=f"w{min(days_back // 7 + 1, 4)}"))

            for item in results[:max_posts]:
                title = item.get("title", "")
                body = item.get("body", "")
                sentiment_score = self._calculate_sentiment_score(
                    title + " " + body,
                    is_chinese=(market in ["CN", "HK"]),
                )

                posts.append(SentimentPost(
                    source=SentimentSource.NEWS.value,
                    title=title,
                    content=body[:500],
                    url=item.get("url"),
                    publish_time=item.get("date"),
                    sentiment_score=sentiment_score,
                    keywords=self._extract_keywords(title + " " + body, market),
                ))

        except Exception as e:
            logger.warning("News search failed", error=str(e))

        return posts

    async def _fetch_eastmoney_guba(self, symbol: str, max_posts: int) -> List[SentimentPost]:
        """获取东财股吧数据（通过搜索模拟）"""
        ddgs = self._get_ddgs()
        if ddgs is None:
            return []

        posts = []
        try:
            # 提取股票代码数字部分
            code = symbol.replace(".SZ", "").replace(".SH", "")
            query = f"site:guba.eastmoney.com {code}"

            results = list(ddgs.text(query, max_results=max_posts))

            for item in results[:max_posts]:
                title = item.get("title", "")
                body = item.get("body", "")
                sentiment_score = self._calculate_sentiment_score(title + " " + body, is_chinese=True)

                posts.append(SentimentPost(
                    source=SentimentSource.EASTMONEY_GUBA.value,
                    title=title,
                    content=body[:500],
                    url=item.get("href"),
                    sentiment_score=sentiment_score,
                    keywords=self._extract_keywords(title + " " + body, "CN"),
                ))

        except Exception as e:
            logger.warning("Eastmoney guba fetch failed", error=str(e))

        return posts

    async def _fetch_xueqiu(self, symbol: str, market: str, max_posts: int) -> List[SentimentPost]:
        """获取雪球数据（通过搜索模拟）"""
        ddgs = self._get_ddgs()
        if ddgs is None:
            return []

        posts = []
        try:
            # 转换为雪球格式
            if market == "CN":
                xq_symbol = "SZ" + symbol.replace(".SZ", "") if ".SZ" in symbol else "SH" + symbol.replace(".SH", "")
            elif market == "HK":
                xq_symbol = symbol.replace(".HK", "")
            else:
                xq_symbol = symbol

            query = f"site:xueqiu.com {xq_symbol}"
            results = list(ddgs.text(query, max_results=max_posts))

            for item in results[:max_posts]:
                title = item.get("title", "")
                body = item.get("body", "")
                sentiment_score = self._calculate_sentiment_score(title + " " + body, is_chinese=True)

                posts.append(SentimentPost(
                    source=SentimentSource.XUEQIU.value,
                    title=title,
                    content=body[:500],
                    url=item.get("href"),
                    sentiment_score=sentiment_score,
                    keywords=self._extract_keywords(title + " " + body, market),
                ))

        except Exception as e:
            logger.warning("Xueqiu fetch failed", error=str(e))

        return posts

    async def _fetch_reddit(self, symbol: str, company_name: str, max_posts: int) -> List[SentimentPost]:
        """获取 Reddit 数据（通过搜索模拟）"""
        ddgs = self._get_ddgs()
        if ddgs is None:
            return []

        posts = []
        try:
            query = f"site:reddit.com {symbol} OR {company_name} stock"
            results = list(ddgs.text(query, max_results=max_posts))

            for item in results[:max_posts]:
                title = item.get("title", "")
                body = item.get("body", "")
                sentiment_score = self._calculate_sentiment_score(title + " " + body, is_chinese=False)

                posts.append(SentimentPost(
                    source=SentimentSource.REDDIT.value,
                    title=title,
                    content=body[:500],
                    url=item.get("href"),
                    sentiment_score=sentiment_score,
                    keywords=self._extract_keywords(title + " " + body, "US"),
                ))

        except Exception as e:
            logger.warning("Reddit fetch failed", error=str(e))

        return posts

    def _calculate_sentiment_score(self, text: str, is_chinese: bool = False) -> float:
        """计算情绪分数（-1 到 1）"""
        if not text:
            return 0

        text_lower = text.lower()

        if is_chinese:
            bullish_keywords = self.BULLISH_KEYWORDS_CN
            bearish_keywords = self.BEARISH_KEYWORDS_CN
        else:
            bullish_keywords = self.BULLISH_KEYWORDS_EN
            bearish_keywords = self.BEARISH_KEYWORDS_EN

        bullish_count = sum(1 for kw in bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return 0

        return (bullish_count - bearish_count) / total

    def _extract_keywords(self, text: str, market: str, max_keywords: int = 5) -> List[str]:
        """提取关键词"""
        if not text:
            return []

        if market in ["CN", "HK"]:
            all_keywords = self.BULLISH_KEYWORDS_CN + self.BEARISH_KEYWORDS_CN
        else:
            all_keywords = self.BULLISH_KEYWORDS_EN + self.BEARISH_KEYWORDS_EN

        found = [kw for kw in all_keywords if kw in text.lower()]
        return found[:max_keywords]

    def _analyze_sentiment(
        self,
        symbol: str,
        market: str,
        posts: List[SentimentPost],
        sources_summary: Dict[str, Dict[str, Any]],
    ) -> SentimentSummary:
        """分析舆情汇总"""
        # 统计情绪分布
        bullish_count = sum(1 for p in posts if p.sentiment_score > 0.2)
        bearish_count = sum(1 for p in posts if p.sentiment_score < -0.2)
        neutral_count = len(posts) - bullish_count - bearish_count

        # 计算总体情绪分数
        avg_sentiment = sum(p.sentiment_score for p in posts) / len(posts) if posts else 0

        # 确定情绪等级
        if avg_sentiment > 0.4:
            overall_sentiment = SentimentLevel.VERY_BULLISH.value
        elif avg_sentiment > 0.15:
            overall_sentiment = SentimentLevel.BULLISH.value
        elif avg_sentiment > -0.15:
            overall_sentiment = SentimentLevel.NEUTRAL.value
        elif avg_sentiment > -0.4:
            overall_sentiment = SentimentLevel.BEARISH.value
        else:
            overall_sentiment = SentimentLevel.VERY_BEARISH.value

        # 计算置信度（基于帖子数量和一致性）
        consistency = abs(bullish_count - bearish_count) / len(posts) if posts else 0
        volume_factor = min(len(posts) / 50, 1)  # 50条帖子以上满分
        confidence = int((consistency * 0.6 + volume_factor * 0.4) * 100)

        # 提取热点关键词
        all_keywords = []
        for p in posts:
            all_keywords.extend(p.keywords)
        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
        top_keywords = sorted(keyword_counts.keys(), key=lambda k: keyword_counts[k], reverse=True)[:10]

        # 提取热点话题（高互动帖子的标题）
        hot_posts = sorted(posts, key=lambda p: p.likes + p.comments, reverse=True)[:5]
        hot_topics = [p.title[:50] for p in hot_posts if p.title]

        # 选取样本帖子
        sample_posts = sorted(posts, key=lambda p: abs(p.sentiment_score), reverse=True)[:10]

        return SentimentSummary(
            symbol=symbol,
            market=market,
            analysis_time=datetime.now().isoformat(),
            overall_sentiment=overall_sentiment,
            sentiment_score=round(avg_sentiment, 3),
            confidence=confidence,
            total_posts=len(posts),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            top_keywords=top_keywords,
            hot_topics=hot_topics,
            sources_summary=sources_summary,
            sample_posts=sample_posts,
        )

    async def _get_company_name_cn(self, symbol: str) -> str:
        """获取 A 股公司名称"""
        # 简单映射或通过 API 获取
        # 这里简化处理，返回股票代码
        return symbol.replace(".SZ", "").replace(".SH", "")

    async def _get_company_name_hk(self, symbol: str) -> str:
        """获取港股公司名称"""
        return symbol.replace(".HK", "")


# 单例实例
sentiment_aggregator = SentimentAggregator()
