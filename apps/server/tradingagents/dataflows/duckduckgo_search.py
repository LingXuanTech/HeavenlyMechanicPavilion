"""DuckDuckGo 搜索数据源实现

提供基于 DuckDuckGo 的市场新闻和股票信息搜索能力。
"""

import json
import time
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

# 延迟导入以避免启动时的依赖问题
_ddgs = None


def _get_ddgs():
    """延迟加载 DDGS 客户端"""
    global _ddgs
    if _ddgs is None:
        try:
            from duckduckgo_search import DDGS
            _ddgs = DDGS()
        except ImportError:
            logger.error("duckduckgo-search not installed. Run: pip install duckduckgo-search")
            raise
    return _ddgs


def search_market_news(query: str, limit: int = 5, timeout: int = 10) -> str:
    """搜索市场相关新闻

    Args:
        query: 搜索查询（如 "AI芯片概念股" 或 "NVIDIA earnings"）
        limit: 返回结果数量限制
        timeout: 请求超时时间（秒）

    Returns:
        JSON 格式的搜索结果字符串
    """
    try:
        ddgs = _get_ddgs()

        # 构建搜索查询，添加股票/市场相关关键词
        search_query = f"{query} stock market finance"

        logger.info("Searching market news", query=search_query, limit=limit)
        start_time = time.time()

        # 执行新闻搜索
        results = list(ddgs.news(search_query, max_results=limit * 2, timelimit="w"))

        elapsed = time.time() - start_time
        logger.info("Search completed", results_count=len(results), elapsed_ms=int(elapsed * 1000))

        # 格式化结果
        formatted_results = []
        for result in results[:limit]:
            formatted_results.append({
                "title": result.get("title", ""),
                "body": result.get("body", ""),
                "source": result.get("source", ""),
                "date": result.get("date", ""),
                "url": result.get("url", ""),
            })

        return json.dumps(formatted_results, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("DuckDuckGo news search failed", error=str(e), query=query)
        return json.dumps({"error": str(e), "results": []}, ensure_ascii=False)


def search_stock_info(query: str, limit: int = 5, timeout: int = 10) -> str:
    """搜索股票相关信息（通用搜索）

    Args:
        query: 搜索查询
        limit: 返回结果数量限制
        timeout: 请求超时时间（秒）

    Returns:
        JSON 格式的搜索结果字符串
    """
    try:
        ddgs = _get_ddgs()

        # 构建搜索查询
        search_query = f"{query} stock ticker symbol"

        logger.info("Searching stock info", query=search_query, limit=limit)
        start_time = time.time()

        # 执行通用搜索
        results = list(ddgs.text(search_query, max_results=limit * 2, timelimit="m"))

        elapsed = time.time() - start_time
        logger.info("Search completed", results_count=len(results), elapsed_ms=int(elapsed * 1000))

        # 格式化结果
        formatted_results = []
        for result in results[:limit]:
            formatted_results.append({
                "title": result.get("title", ""),
                "body": result.get("body", ""),
                "href": result.get("href", ""),
            })

        return json.dumps(formatted_results, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("DuckDuckGo text search failed", error=str(e), query=query)
        return json.dumps({"error": str(e), "results": []}, ensure_ascii=False)


def search_trending_stocks(market: str = "US", limit: int = 10) -> str:
    """搜索热门股票话题

    Args:
        market: 市场代码 (US/CN/HK)
        limit: 返回结果数量限制

    Returns:
        JSON 格式的搜索结果字符串
    """
    try:
        ddgs = _get_ddgs()

        # 根据市场构建查询
        market_queries = {
            "US": "trending stocks today US market",
            "CN": "A股 热门股票 今日",
            "HK": "港股 热门股票 今日",
        }
        search_query = market_queries.get(market.upper(), market_queries["US"])

        logger.info("Searching trending stocks", market=market, query=search_query)
        start_time = time.time()

        results = list(ddgs.news(search_query, max_results=limit, timelimit="d"))

        elapsed = time.time() - start_time
        logger.info("Search completed", results_count=len(results), elapsed_ms=int(elapsed * 1000))

        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.get("title", ""),
                "body": result.get("body", ""),
                "source": result.get("source", ""),
                "date": result.get("date", ""),
                "url": result.get("url", ""),
            })

        return json.dumps(formatted_results, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("DuckDuckGo trending search failed", error=str(e), market=market)
        return json.dumps({"error": str(e), "results": []}, ensure_ascii=False)
