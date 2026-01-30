"""Planner Agent - 智能分析师选择器

基于股票特征动态决定激活哪些分析师，实现自适应任务编排。

决策因素：
- 市场类型（CN/HK/US）
- 成交量级别（低成交跳过资金流向）
- 是否财报季（激活 Fundamentals）
- 是否有突发新闻（激活 News/Social）
- 波动率水平（高波动激活更多分析师）
- 历史分层记忆（相似宏观周期/技术形态的成功案例）
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import structlog

from tradingagents.agents.utils.agent_states import AnalystType

logger = structlog.get_logger(__name__)

# Planner 决策的系统提示
PLANNER_SYSTEM_PROMPT = """你是一个智能分析师调度器（Planner）。你的任务是根据股票的特征，决定本次分析需要激活哪些分析师。

## 可用的分析师类型

**核心分析师（所有市场都可用）：**
- market: 技术面分析师 - 分析价格、成交量、技术指标
- news: 新闻分析师 - 分析公司和行业新闻
- fundamentals: 基本面分析师 - 分析财务报表、估值
- social: 社交媒体分析师 - 分析社交媒体情绪

**A股/港股特色分析师：**
- sentiment: 散户情绪分析师 - 分析 FOMO/FUD、股吧情绪
- policy: 政策分析师 - 分析政策影响、监管动态
- fund_flow: 资金流向分析师 - 分析北向资金、龙虎榜

## 决策原则

1. **低成交量股票**（日均成交额 < 1亿）：
   - 跳过 fund_flow（资金流向数据不可靠）
   - 跳过 social（社交讨论量不足）

2. **财报季/重大事件**：
   - 必须包含 fundamentals
   - 建议包含 news

3. **高波动股票**（近期涨跌幅 > 10%）：
   - 建议包含 news 和 social
   - 如果是 A 股，建议包含 fund_flow

4. **市场类型**：
   - US 市场：只用核心分析师
   - HK 市场：核心 + sentiment（可选）
   - CN 市场：核心 + A 股特色分析师

5. **效率优先**：
   - 普通分析：3-4 个分析师
   - 深度分析：5-7 个分析师

6. **历史经验**（如有提供）：
   - 参考相似宏观周期下的成功案例
   - 参考相似技术形态下的成功案例
   - 如果历史案例显示某分析师组合效果好，优先考虑

## 输出格式

请输出 JSON 格式：
```json
{
    "recommended_analysts": ["market", "news", "fundamentals"],
    "reasoning": "简要说明选择原因",
    "skip_reasons": {
        "fund_flow": "成交量过低，资金流向数据不可靠"
    },
    "historical_insight": "（可选）基于历史案例的洞察"
}
```
"""

PLANNER_USER_PROMPT = """请为以下股票选择合适的分析师：

**股票**: {symbol}
**市场**: {market}
**分析日期**: {trade_date}

**股票特征**:
{stock_characteristics}

**可用分析师**: {available_analysts}

{historical_context}

请输出你的分析师选择决策（JSON 格式）。
"""


def create_planner_agent(llm, default_analysts: Optional[List[str]] = None):
    """创建 Planner Agent 节点

    Args:
        llm: LangChain LLM 实例
        default_analysts: 默认分析师列表（当 Planner 无法决策时使用）

    Returns:
        节点函数
    """
    if default_analysts is None:
        default_analysts = [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS]

    def planner_agent_node(state):
        """Planner Agent 节点逻辑"""
        symbol = state.get("company_of_interest", "")
        market = state.get("market", "US")
        trade_date = state.get("trade_date", "")

        logger.info("Planner agent starting", symbol=symbol, market=market)

        # 获取股票特征（从之前的数据获取或使用默认值）
        stock_characteristics = _get_stock_characteristics(state, symbol, market)

        # 确定可用分析师
        available_analysts = _get_available_analysts(market)

        # 获取历史分层记忆洞察
        historical_context = _get_historical_memory_context()

        # 构建 prompt
        user_content = PLANNER_USER_PROMPT.format(
            symbol=symbol,
            market=market,
            trade_date=trade_date,
            stock_characteristics=json.dumps(stock_characteristics, ensure_ascii=False, indent=2),
            available_analysts=", ".join(available_analysts),
            historical_context=historical_context,
        )

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response = llm.invoke(messages)
            decision = _parse_planner_decision(response.content, available_analysts)

            recommended = decision.get("recommended_analysts", default_analysts)
            reasoning = decision.get("reasoning", "Default selection")

            logger.info(
                "Planner decision made",
                symbol=symbol,
                recommended_analysts=recommended,
                reasoning=reasoning,
            )

            return {
                "recommended_analysts": recommended,
                "scout_report": json.dumps(decision, ensure_ascii=False, indent=2),
            }

        except Exception as e:
            logger.error("Planner agent failed, using defaults", error=str(e))
            return {
                "recommended_analysts": default_analysts,
                "scout_report": f"Planner failed: {str(e)}. Using default analysts.",
            }

    return planner_agent_node


def _get_stock_characteristics(state: Dict, symbol: str, market: str) -> Dict[str, Any]:
    """获取股票特征用于 Planner 决策

    Args:
        state: 当前状态
        symbol: 股票代码
        market: 市场类型

    Returns:
        股票特征字典
    """
    # 尝试从数据服务获取真实数据
    characteristics = {
        "symbol": symbol,
        "market": market,
        "volume_level": "normal",  # low / normal / high
        "volatility": "normal",    # low / normal / high
        "is_earnings_season": False,
        "has_recent_news": True,
        "sector": "unknown",
    }

    try:
        from services.data_router import market_router

        # 尝试获取价格数据来判断成交量和波动率
        price_data = market_router.get_stock_price(symbol)
        if price_data:
            volume = price_data.get("volume", 0)
            # 简单的成交量分级（可以根据实际情况调整）
            if volume < 10_000_000:  # 1000万股以下
                characteristics["volume_level"] = "low"
            elif volume > 100_000_000:  # 1亿股以上
                characteristics["volume_level"] = "high"

            # 简单的波动率判断
            change_pct = abs(price_data.get("change_percent", 0))
            if change_pct > 5:
                characteristics["volatility"] = "high"
            elif change_pct < 1:
                characteristics["volatility"] = "low"

    except Exception as e:
        logger.debug("Could not fetch stock characteristics", error=str(e))

    # 检查是否是财报季（简单判断：1月、4月、7月、10月）
    try:
        current_month = datetime.now().month
        if current_month in [1, 4, 7, 10]:
            characteristics["is_earnings_season"] = True
    except:
        pass

    return characteristics


def _get_available_analysts(market: str) -> List[str]:
    """根据市场类型获取可用分析师列表

    Args:
        market: 市场类型 (US/HK/CN)

    Returns:
        可用分析师列表
    """
    core = [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS, AnalystType.SOCIAL]

    if market == "CN":
        return core + [AnalystType.SENTIMENT, AnalystType.POLICY, AnalystType.FUND_FLOW]
    elif market == "HK":
        return core + [AnalystType.SENTIMENT]
    else:
        return core


def _parse_planner_decision(response: str, available: List[str]) -> Dict[str, Any]:
    """解析 Planner 的决策输出

    Args:
        response: LLM 响应内容
        available: 可用分析师列表

    Returns:
        解析后的决策字典
    """
    import re

    try:
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            decision = json.loads(json_match.group())

            # 验证推荐的分析师都在可用列表中
            recommended = decision.get("recommended_analysts", [])
            validated = [a for a in recommended if a in available]

            # 确保至少有 market 分析师
            if AnalystType.MARKET not in validated:
                validated.insert(0, AnalystType.MARKET)

            decision["recommended_analysts"] = validated
            return decision

    except json.JSONDecodeError:
        logger.debug("Could not parse Planner response as JSON")

    # 降级：返回默认决策
    return {
        "recommended_analysts": [AnalystType.MARKET, AnalystType.NEWS, AnalystType.FUNDAMENTALS],
        "reasoning": "Failed to parse LLM response, using defaults",
    }


def _get_historical_memory_context() -> str:
    """获取分层记忆的历史洞察上下文

    从 LayeredMemoryService 缓存中提取当前宏观周期下的历史成功案例，
    供 Planner 决策参考。

    Returns:
        格式化的历史上下文字符串（无数据时返回空字符串）
    """
    try:
        from services.memory_service import layered_memory

        # 获取分层统计
        stats = layered_memory.get_layered_stats()
        macro_count = stats.get("macro_cycles", {}).get("count", 0)
        pattern_count = stats.get("pattern_cases", {}).get("count", 0)

        if macro_count == 0 and pattern_count == 0:
            return ""

        # 构建上下文
        lines = ["**历史案例参考**:"]

        # 宏观周期统计
        if macro_count > 0:
            # 尝试获取当前周期的相关案例
            try:
                from services.macro_service import _macro_cache
                cached = _macro_cache.get("macro_overview")
                if cached:
                    overview, _ = cached
                    current_cycle = _infer_current_cycle(overview)
                    if current_cycle != "neutral":
                        lines.append(f"- 当前宏观周期: {current_cycle}")
                        lines.append(f"- 该周期下历史案例数: {macro_count}")
            except Exception:
                pass

        # 形态统计
        if pattern_count > 0:
            lines.append(f"- 历史技术形态案例数: {pattern_count}")

        # 简要洞察
        if len(lines) > 1:
            lines.append("")
            lines.append("（分析时可参考相似历史案例的成功经验）")
            return "\n".join(lines)

        return ""

    except Exception as e:
        logger.debug("Could not fetch historical memory context", error=str(e))
        return ""


def _infer_current_cycle(overview) -> str:
    """根据宏观概览推断当前周期（与 memory_service 逻辑一致）"""
    if overview.fed_rate and overview.fed_rate.trend == "down":
        return "rate_cut"
    if overview.fed_rate and overview.fed_rate.trend == "up":
        return "rate_hike"
    if overview.gdp_growth and overview.gdp_growth.value < 0:
        return "recession"
    if overview.vix and overview.vix.value > 25:
        return "bear_market"
    if overview.vix and overview.vix.value < 15 and overview.sentiment == "Bullish":
        return "bull_market"
    return "neutral"


# 向后兼容：保留 create_scout_agent 别名
create_scout_agent = create_planner_agent
