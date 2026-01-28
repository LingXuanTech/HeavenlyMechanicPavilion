"""Scout Agent 工具集

提供股票发现和验证相关的 LangChain 工具。
"""

from typing import Annotated, List
from langchain_core.tools import tool
import structlog
import json

logger = structlog.get_logger(__name__)


@tool
def search_market_news(
    query: Annotated[str, "搜索查询，如 'AI芯片概念股' 或 '新能源汽车'"],
    limit: Annotated[int, "返回结果数量，默认5"] = 5,
) -> str:
    """搜索市场相关新闻和股票信息。

    使用此工具搜索与投资主题相关的最新新闻，帮助发现潜在的投资标的。
    返回包含标题、摘要、来源和日期的新闻列表。
    """
    from tradingagents.dataflows.duckduckgo_search import search_market_news as _search

    logger.info("Scout tool: searching market news", query=query, limit=limit)
    return _search(query, limit=limit)


@tool
def search_stock_info(
    query: Annotated[str, "搜索查询，如 '英伟达股票代码' 或 'Tesla stock'"],
    limit: Annotated[int, "返回结果数量，默认5"] = 5,
) -> str:
    """搜索股票的详细信息。

    使用此工具查找特定公司或股票的信息，包括股票代码、市场等。
    """
    from tradingagents.dataflows.duckduckgo_search import search_stock_info as _search

    logger.info("Scout tool: searching stock info", query=query, limit=limit)
    return _search(query, limit=limit)


@tool
def validate_ticker(
    symbols: Annotated[List[str], "要验证的股票代码列表，如 ['NVDA', '000001.SZ', '0700.HK']"],
) -> str:
    """验证股票代码的有效性。

    检查给定的股票代码是否存在，返回每个代码的验证状态。
    支持美股、A股（.SH/.SZ）和港股（.HK）。
    """
    logger.info("Scout tool: validating tickers", symbols=symbols)

    results = []

    for symbol in symbols:
        try:
            # 使用 MarketRouter 验证
            from services.data_router import MarketRouter
            router = MarketRouter()

            # 尝试获取价格来验证
            price_data = router.get_price(symbol)

            if price_data and price_data.get("current_price"):
                results.append({
                    "symbol": symbol,
                    "valid": True,
                    "name": price_data.get("name", ""),
                    "market": price_data.get("market", ""),
                    "current_price": price_data.get("current_price"),
                })
            else:
                results.append({
                    "symbol": symbol,
                    "valid": False,
                    "reason": "无法获取价格数据"
                })

        except Exception as e:
            logger.warning("Ticker validation failed", symbol=symbol, error=str(e))
            results.append({
                "symbol": symbol,
                "valid": False,
                "reason": str(e)
            })

    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def search_trending_stocks(
    market: Annotated[str, "市场代码：US（美股）、CN（A股）、HK（港股）"] = "CN",
    limit: Annotated[int, "返回结果数量，默认10"] = 10,
) -> str:
    """搜索当前热门股票话题。

    获取指定市场的热门股票新闻和讨论，帮助发现市场热点。
    """
    from tradingagents.dataflows.duckduckgo_search import search_trending_stocks as _search

    logger.info("Scout tool: searching trending stocks", market=market, limit=limit)
    return _search(market=market, limit=limit)
