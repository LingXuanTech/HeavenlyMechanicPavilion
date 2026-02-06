"""情绪数据适配器

为 Sentiment Agent 提供散户情绪搜索和恐惧贪婪指数数据。
支持 A股（AkShare）和美股（CNN Fear & Greed）数据源。
"""

import json
import time
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# ============ 简单内存缓存 ============

_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 1800  # 30 分钟


def _get_cache(key: str) -> Optional[str]:
    """获取缓存数据"""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < _CACHE_TTL:
            logger.debug("Cache hit", key=key)
            return entry["data"]
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data: str) -> None:
    """设置缓存数据"""
    _cache[key] = {"data": data, "timestamp": time.time()}


def _cache_key(*args) -> str:
    """生成缓存键"""
    raw = "|".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()


# ============ DuckDuckGo 搜索复用 ============

def _get_ddgs():
    """延迟加载 DDGS 客户端"""
    try:
        from duckduckgo_search import DDGS
        return DDGS()
    except ImportError:
        logger.error("duckduckgo-search not installed")
        raise


# ============ 散户情绪搜索 ============

def search_retail_sentiment(query: str, platform: str = "all", limit: int = 8) -> str:
    """搜索散户情绪数据

    通过 DuckDuckGo 搜索散户讨论平台的内容，获取情绪数据。

    Args:
        query: 搜索关键词（股票代码或公司名）
        platform: 平台筛选 (reddit/twitter/stocktwits/xueqiu/all)
        limit: 返回结果数量

    Returns:
        JSON 格式的散户情绪搜索结果
    """
    cache_k = _cache_key("retail_sentiment", query, platform)
    cached = _get_cache(cache_k)
    if cached:
        return cached

    try:
        ddgs = _get_ddgs()

        # 根据平台构建搜索查询
        platform_keywords = {
            "reddit": "site:reddit.com",
            "twitter": "site:twitter.com OR site:x.com",
            "stocktwits": "site:stocktwits.com",
            "xueqiu": "site:xueqiu.com 雪球",
            "all": "",
        }

        platform_suffix = platform_keywords.get(platform.lower(), "")

        # 构建多语言搜索查询
        # 判断是否为中文股票（A股/港股）
        is_chinese = any(s in query for s in [".SH", ".SZ", ".HK", "沪", "深", "港"])

        if is_chinese:
            search_queries = [
                f"{query} 散户 讨论 情绪 {platform_suffix}".strip(),
                f"{query} 股吧 评论 看多 看空".strip(),
            ]
        else:
            search_queries = [
                f"{query} retail investor sentiment discussion {platform_suffix}".strip(),
                f"{query} reddit wallstreetbets stocks opinion".strip(),
            ]

        logger.info("Searching retail sentiment", query=query, platform=platform)
        start_time = time.time()

        all_results = []
        for sq in search_queries:
            try:
                results = list(ddgs.text(sq, max_results=limit, timelimit="w"))
                all_results.extend(results)
            except Exception as e:
                logger.warning("Search query failed", query=sq, error=str(e))

        elapsed = time.time() - start_time
        logger.info("Sentiment search completed",
                     results_count=len(all_results),
                     elapsed_ms=int(elapsed * 1000))

        # 格式化结果
        formatted = []
        seen_urls = set()
        for r in all_results:
            url = r.get("href", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            formatted.append({
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "url": url,
                "source": _extract_source(url),
            })

        # 添加情绪分析提示
        result = json.dumps({
            "query": query,
            "platform": platform,
            "results_count": len(formatted),
            "search_time_ms": int(elapsed * 1000),
            "discussions": formatted[:limit],
            "analysis_hint": (
                "Based on the above discussions, analyze: "
                "1) Overall retail sentiment (bullish/bearish/neutral), "
                "2) FOMO indicators (chasing behavior, unrealistic targets), "
                "3) FUD indicators (panic selling, doom narratives), "
                "4) Key discussion themes"
            ),
        }, ensure_ascii=False, indent=2)

        _set_cache(cache_k, result)
        return result

    except Exception as e:
        logger.error("Retail sentiment search failed", error=str(e), query=query)
        return json.dumps({
            "error": str(e),
            "query": query,
            "discussions": [],
            "analysis_hint": "Search failed. Use available news data to infer retail sentiment.",
        }, ensure_ascii=False)


def _extract_source(url: str) -> str:
    """从 URL 提取来源平台名"""
    if not url:
        return "unknown"
    url_lower = url.lower()
    source_map = {
        "reddit.com": "Reddit",
        "twitter.com": "Twitter/X",
        "x.com": "Twitter/X",
        "stocktwits.com": "StockTwits",
        "xueqiu.com": "雪球",
        "eastmoney.com": "东方财富",
        "guba.eastmoney.com": "东方财富股吧",
        "toutiao.com": "今日头条",
        "weibo.com": "微博",
        "zhihu.com": "知乎",
    }
    for domain, name in source_map.items():
        if domain in url_lower:
            return name
    return "Web"


# ============ 恐惧贪婪指数 ============

def get_fear_greed_index(market: str = "auto") -> str:
    """获取恐惧贪婪指数

    A股：使用 AkShare 获取市场情绪指标
    美股：使用 CNN Fear & Greed Index 公开数据

    Args:
        market: 市场类型 (CN/US/auto)

    Returns:
        JSON 格式的恐惧贪婪指数数据
    """
    cache_k = _cache_key("fear_greed", market)
    cached = _get_cache(cache_k)
    if cached:
        return cached

    result_data = {
        "market": market,
        "timestamp": datetime.now().isoformat(),
        "indicators": [],
    }

    try:
        if market.upper() in ("CN", "AUTO"):
            cn_data = _get_cn_sentiment()
            if cn_data:
                result_data["cn_sentiment"] = cn_data
                result_data["indicators"].extend(cn_data.get("indicators", []))

        if market.upper() in ("US", "AUTO"):
            us_data = _get_us_fear_greed()
            if us_data:
                result_data["us_fear_greed"] = us_data
                result_data["indicators"].extend(us_data.get("indicators", []))

        # 如果没有获取到任何数据，使用搜索作为降级
        if not result_data["indicators"]:
            fallback = _get_fear_greed_via_search(market)
            result_data["fallback_search"] = fallback
            result_data["note"] = "Real-time index unavailable, using search-based estimation"

        result = json.dumps(result_data, ensure_ascii=False, indent=2)
        _set_cache(cache_k, result)
        return result

    except Exception as e:
        logger.error("Fear & Greed index fetch failed", error=str(e), market=market)
        return json.dumps({
            "error": str(e),
            "market": market,
            "indicators": [],
            "note": "Failed to fetch Fear & Greed data. Use news sentiment as proxy.",
        }, ensure_ascii=False)


def _get_cn_sentiment() -> Optional[Dict[str, Any]]:
    """获取 A 股市场情绪指标（AkShare）"""
    try:
        import akshare as ak

        indicators = []

        # 1. 融资融券余额（市场杠杆情绪）
        try:
            margin_data = ak.stock_margin_sz_sh_summary()
            if margin_data is not None and not margin_data.empty:
                latest = margin_data.iloc[-1]
                rzye = float(latest.get("融资余额(元)", 0))
                indicators.append({
                    "name": "融资余额",
                    "value": rzye,
                    "formatted": f"{rzye / 1e8:.2f} 亿元",
                    "interpretation": "融资余额上升表示市场杠杆情绪偏多",
                })
        except Exception as e:
            logger.debug("Failed to get margin data", error=str(e))

        # 2. 涨跌家数比（市场广度）
        try:
            # 使用 A 股实时行情获取涨跌统计
            spot_data = ak.stock_zh_a_spot_em()
            if spot_data is not None and not spot_data.empty:
                up_count = len(spot_data[spot_data["涨跌幅"] > 0])
                down_count = len(spot_data[spot_data["涨跌幅"] < 0])
                flat_count = len(spot_data[spot_data["涨跌幅"] == 0])
                total = len(spot_data)
                ratio = up_count / max(down_count, 1)

                indicators.append({
                    "name": "涨跌家数比",
                    "value": round(ratio, 2),
                    "up": up_count,
                    "down": down_count,
                    "flat": flat_count,
                    "total": total,
                    "interpretation": (
                        "极度贪婪" if ratio > 3 else
                        "贪婪" if ratio > 2 else
                        "中性" if ratio > 0.8 else
                        "恐惧" if ratio > 0.5 else
                        "极度恐惧"
                    ),
                })

                # 涨停跌停统计
                limit_up = len(spot_data[spot_data["涨跌幅"] >= 9.9])
                limit_down = len(spot_data[spot_data["涨跌幅"] <= -9.9])
                indicators.append({
                    "name": "涨停跌停",
                    "limit_up": limit_up,
                    "limit_down": limit_down,
                    "interpretation": f"涨停 {limit_up} 家，跌停 {limit_down} 家",
                })
        except Exception as e:
            logger.debug("Failed to get A-share spot data", error=str(e))

        # 3. 成交量（市场活跃度）
        try:
            index_data = ak.stock_zh_index_daily(symbol="sh000001")
            if index_data is not None and not index_data.empty:
                recent = index_data.tail(20)
                avg_vol = recent["volume"].mean()
                latest_vol = recent.iloc[-1]["volume"]
                vol_ratio = latest_vol / max(avg_vol, 1)

                indicators.append({
                    "name": "量比(20日)",
                    "value": round(vol_ratio, 2),
                    "interpretation": (
                        "极度活跃（贪婪）" if vol_ratio > 2 else
                        "活跃" if vol_ratio > 1.3 else
                        "正常" if vol_ratio > 0.7 else
                        "低迷（恐惧）"
                    ),
                })
        except Exception as e:
            logger.debug("Failed to get index volume data", error=str(e))

        if indicators:
            # 计算综合情绪分数
            sentiment_score = _calculate_cn_sentiment_score(indicators)
            return {
                "market": "CN",
                "sentiment_score": sentiment_score,
                "sentiment_label": _score_to_label(sentiment_score),
                "indicators": indicators,
            }

    except ImportError:
        logger.warning("AkShare not installed, skipping CN sentiment")
    except Exception as e:
        logger.error("CN sentiment fetch failed", error=str(e))

    return None


def _calculate_cn_sentiment_score(indicators: list) -> int:
    """根据 A 股指标计算综合情绪分数 (0-100)"""
    scores = []

    for ind in indicators:
        name = ind.get("name", "")
        if name == "涨跌家数比":
            ratio = ind.get("value", 1.0)
            # ratio 0.3 -> 10, 1.0 -> 50, 3.0 -> 90
            score = min(max(int(ratio * 30), 0), 100)
            scores.append(score)
        elif name == "量比(20日)":
            vol_ratio = ind.get("value", 1.0)
            score = min(max(int(vol_ratio * 40), 0), 100)
            scores.append(score)

    if scores:
        return int(sum(scores) / len(scores))
    return 50  # 默认中性


def _score_to_label(score: int) -> str:
    """分数转标签"""
    if score >= 80:
        return "Extreme Greed"
    elif score >= 60:
        return "Greed"
    elif score >= 40:
        return "Neutral"
    elif score >= 20:
        return "Fear"
    else:
        return "Extreme Fear"


def _get_us_fear_greed() -> Optional[Dict[str, Any]]:
    """获取美股 CNN Fear & Greed Index"""
    try:
        import httpx

        # CNN Fear & Greed API (公开端点)
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {"User-Agent": "Mozilla/5.0"}

        with httpx.Client(timeout=10, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            fg = data.get("fear_and_greed", {})
            score = fg.get("score", 50)
            rating = fg.get("rating", "Neutral")

            indicators = [{
                "name": "CNN Fear & Greed Index",
                "value": round(score),
                "rating": rating,
                "interpretation": f"CNN 恐惧贪婪指数: {round(score)} ({rating})",
            }]

            # 提取子指标
            for key in ["market_momentum", "stock_price_strength",
                        "stock_price_breadth", "put_call_options",
                        "market_volatility", "junk_bond_demand",
                        "safe_haven_demand"]:
                sub = data.get(key, {})
                if sub:
                    indicators.append({
                        "name": key.replace("_", " ").title(),
                        "value": round(sub.get("score", 0)),
                        "rating": sub.get("rating", ""),
                    })

            return {
                "market": "US",
                "sentiment_score": round(score),
                "sentiment_label": rating,
                "indicators": indicators,
            }

        logger.warning("CNN Fear & Greed API returned non-200", status=response.status_code)

    except ImportError:
        logger.debug("httpx not available for CNN Fear & Greed")
    except Exception as e:
        logger.warning("US Fear & Greed fetch failed", error=str(e))

    return None


def _get_fear_greed_via_search(market: str) -> Dict[str, Any]:
    """通过搜索获取恐惧贪婪指数（降级方案）"""
    try:
        ddgs = _get_ddgs()

        if market.upper() in ("CN", "AUTO"):
            query = "A股 市场情绪 恐惧贪婪 今日"
        else:
            query = "fear greed index today stock market"

        results = list(ddgs.text(query, max_results=5, timelimit="d"))

        return {
            "source": "search_fallback",
            "results": [
                {
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "url": r.get("href", ""),
                }
                for r in results
            ],
        }

    except Exception as e:
        logger.warning("Fear & Greed search fallback failed", error=str(e))
        return {"source": "search_fallback", "error": str(e), "results": []}
