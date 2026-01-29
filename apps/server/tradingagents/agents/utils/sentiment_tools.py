"""舆情分析 LangChain 工具

为 Agent 提供舆情分析能力。
"""

from langchain_core.tools import tool
import structlog

from services.sentiment_aggregator import sentiment_aggregator, SentimentSummary

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """同步运行异步函数"""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


@tool
def get_sentiment_summary(symbol: str, market: str = "US") -> str:
    """获取股票的舆情分析摘要

    Args:
        symbol: 股票代码（如 AAPL、000001.SZ、0700.HK）
        market: 市场（US、CN、HK）

    Returns:
        舆情分析报告
    """
    try:
        summary: SentimentSummary = _run_async(
            sentiment_aggregator.aggregate_sentiment(
                symbol=symbol,
                market=market,
                days_back=7,
                max_posts_per_source=15,
            )
        )

        if summary.error:
            return f"舆情分析失败：{summary.error}"

        # 格式化输出
        lines = [
            f"## {symbol} 舆情分析报告\n",
            f"**分析时间**: {summary.analysis_time}",
            f"**市场**: {summary.market}\n",
            f"### 整体情绪",
            f"- **情绪倾向**: {_translate_sentiment(summary.overall_sentiment)}",
            f"- **情绪分数**: {summary.sentiment_score:.2f}（-1 极度看空，1 极度看多）",
            f"- **置信度**: {summary.confidence}%\n",
            f"### 舆情统计",
            f"- 总帖子数: {summary.total_posts}",
            f"- 看多: {summary.bullish_count} ({summary.bullish_count/summary.total_posts*100:.1f}%)" if summary.total_posts > 0 else "- 看多: 0",
            f"- 看空: {summary.bearish_count} ({summary.bearish_count/summary.total_posts*100:.1f}%)" if summary.total_posts > 0 else "- 看空: 0",
            f"- 中性: {summary.neutral_count}\n",
        ]

        if summary.top_keywords:
            lines.append(f"### 热点关键词")
            lines.append(f"{', '.join(summary.top_keywords)}\n")

        if summary.hot_topics:
            lines.append(f"### 热门话题")
            for i, topic in enumerate(summary.hot_topics[:5], 1):
                lines.append(f"{i}. {topic}")

        lines.append(f"\n### 数据来源统计")
        for source, stats in summary.sources_summary.items():
            if "error" in stats:
                lines.append(f"- {source}: 获取失败")
            else:
                lines.append(f"- {source}: {stats.get('posts_count', 0)} 条 (平均情绪 {stats.get('avg_sentiment', 0):.2f})")

        return "\n".join(lines)

    except Exception as e:
        logger.error("Sentiment tool failed", symbol=symbol, error=str(e))
        return f"舆情分析失败：{str(e)}"


@tool
def get_sentiment_score(symbol: str, market: str = "US") -> str:
    """获取股票的舆情情绪分数

    Args:
        symbol: 股票代码
        market: 市场（US、CN、HK）

    Returns:
        情绪分数和简要分析
    """
    try:
        summary: SentimentSummary = _run_async(
            sentiment_aggregator.aggregate_sentiment(
                symbol=symbol,
                market=market,
                days_back=7,
                max_posts_per_source=10,
            )
        )

        if summary.error:
            return f"无法获取舆情数据：{summary.error}"

        interpretation = _interpret_sentiment(summary.sentiment_score, summary.confidence)

        return f"""
## {symbol} 舆情分数

**情绪分数**: {summary.sentiment_score:.3f}
**情绪等级**: {_translate_sentiment(summary.overall_sentiment)}
**置信度**: {summary.confidence}%
**样本量**: {summary.total_posts} 条

**解读**: {interpretation}
"""

    except Exception as e:
        logger.error("Sentiment score failed", symbol=symbol, error=str(e))
        return f"获取舆情分数失败：{str(e)}"


@tool
def compare_sentiment(symbols: str, market: str = "US") -> str:
    """比较多个股票的舆情情绪

    Args:
        symbols: 逗号分隔的股票代码（如 "AAPL,MSFT,GOOGL"）
        market: 市场

    Returns:
        舆情对比报告
    """
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        results = []

        for symbol in symbol_list[:5]:  # 最多比较 5 个
            summary = _run_async(
                sentiment_aggregator.aggregate_sentiment(
                    symbol=symbol,
                    market=market,
                    days_back=7,
                    max_posts_per_source=10,
                )
            )
            results.append({
                "symbol": symbol,
                "sentiment_score": summary.sentiment_score,
                "sentiment_level": summary.overall_sentiment,
                "confidence": summary.confidence,
                "total_posts": summary.total_posts,
            })

        # 按情绪分数排序
        results.sort(key=lambda x: x["sentiment_score"], reverse=True)

        lines = [f"## 舆情对比分析（{market} 市场）\n"]
        lines.append("| 股票 | 情绪分数 | 情绪等级 | 置信度 | 样本量 |")
        lines.append("|------|----------|----------|--------|--------|")

        for r in results:
            lines.append(
                f"| {r['symbol']} | {r['sentiment_score']:.3f} | "
                f"{_translate_sentiment(r['sentiment_level'])} | {r['confidence']}% | {r['total_posts']} |"
            )

        # 分析结论
        if results:
            best = results[0]
            worst = results[-1]
            lines.append(f"\n### 分析结论")
            lines.append(f"- **最积极**: {best['symbol']}（情绪分数 {best['sentiment_score']:.3f}）")
            lines.append(f"- **最消极**: {worst['symbol']}（情绪分数 {worst['sentiment_score']:.3f}）")

        return "\n".join(lines)

    except Exception as e:
        logger.error("Sentiment comparison failed", error=str(e))
        return f"舆情对比失败：{str(e)}"


def _translate_sentiment(sentiment_level: str) -> str:
    """翻译情绪等级"""
    translations = {
        "very_bullish": "极度看多 🚀",
        "bullish": "看多 📈",
        "neutral": "中性 📊",
        "bearish": "看空 📉",
        "very_bearish": "极度看空 ⚠️",
    }
    return translations.get(sentiment_level, sentiment_level)


def _interpret_sentiment(score: float, confidence: int) -> str:
    """解读情绪分数"""
    if confidence < 30:
        return "样本量不足，数据可靠性较低，建议参考其他指标"

    if score > 0.4:
        return "市场情绪极度乐观，可能存在过热风险，注意追高风险"
    elif score > 0.2:
        return "市场情绪偏向乐观，投资者信心较强"
    elif score > -0.2:
        return "市场情绪中性，多空分歧明显"
    elif score > -0.4:
        return "市场情绪偏向悲观，投资者信心不足"
    else:
        return "市场情绪极度悲观，可能存在恐慌情绪，关注是否超跌反弹"


# 导出工具列表
SENTIMENT_TOOLS = [
    get_sentiment_summary,
    get_sentiment_score,
    compare_sentiment,
]
