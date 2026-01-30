"""Scout Agent - 股票发现专家

基于实时搜索发现潜在投资标的的 Agent。

注意：Scout Agent 已增强为 Planner 功能。
- create_scout_agent: 原始 Scout 功能（股票发现）
- create_planner_agent: 新增 Planner 功能（分析师选择）

推荐在图中使用 create_planner_agent 进行自适应分析师选择。
"""

import json
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from services.prompt_manager import prompt_manager
import structlog

# 导入 Planner Agent（向后兼容 + 新功能）
from tradingagents.agents.analysts.planner_agent import (
    create_planner_agent,
    _get_stock_characteristics,
    _get_available_analysts,
)

# 导入 Scout 工具
from tradingagents.agents.utils.scout_tools import (
    search_market_news,
    search_stock_info,
    search_trending_stocks,
    validate_ticker,
)

logger = structlog.get_logger(__name__)


def create_scout_agent(llm):
    """创建 Scout Agent 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        异步节点函数
    """
    # 绑定工具到 LLM
    tools = [search_market_news, search_stock_info, search_trending_stocks, validate_ticker]
    llm_with_tools = llm.bind_tools(tools)

    async def scout_agent_node(state):
        """Scout Agent 节点逻辑"""
        query = state.get("query", "")
        logger.info("Scout agent starting", query=query)

        # 获取 prompt
        prompt_data = prompt_manager.get_prompt("scout_agent", {"query": query})

        # 构建消息
        messages = [
            {"role": "system", "content": prompt_data["system"]},
            {"role": "user", "content": prompt_data["user"]},
        ]

        # 第一轮：让 LLM 决定是否需要搜索
        response = await llm_with_tools.ainvoke(messages)

        # 处理工具调用
        tool_results = []
        if response.tool_calls:
            logger.info("Scout agent making tool calls", tool_count=len(response.tool_calls))

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.debug("Executing tool", tool=tool_name, args=tool_args)

                # 执行工具
                try:
                    if tool_name == "search_market_news":
                        result = search_market_news.invoke(tool_args)
                    elif tool_name == "search_stock_info":
                        result = search_stock_info.invoke(tool_args)
                    elif tool_name == "search_trending_stocks":
                        result = search_trending_stocks.invoke(tool_args)
                    elif tool_name == "validate_ticker":
                        result = validate_ticker.invoke(tool_args)
                    else:
                        result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })
                    logger.info("Tool executed successfully", tool=tool_name)

                except Exception as e:
                    logger.error("Tool execution failed", tool=tool_name, error=str(e))
                    tool_results.append({
                        "tool": tool_name,
                        "error": str(e)
                    })

            # 第二轮：将工具结果反馈给 LLM 生成最终报告
            tool_results_text = "\n\n".join([
                f"### {r['tool']} 结果:\n{r.get('result', r.get('error', 'No result'))}"
                for r in tool_results
            ])

            synthesis_messages = messages + [
                {"role": "assistant", "content": f"我已经搜索了相关信息，以下是搜索结果：\n\n{tool_results_text}"},
                {"role": "user", "content": "请基于以上搜索结果，输出符合要求的 JSON 格式股票发现列表。"},
            ]

            final_response = await llm.ainvoke(synthesis_messages)
            scout_report = final_response.content

        else:
            # LLM 没有调用工具，直接使用其响应
            scout_report = response.content

        # 尝试解析 opportunities
        opportunities = _parse_opportunities(scout_report)

        logger.info("Scout agent completed", opportunities_count=len(opportunities))

        return {
            "scout_report": scout_report,
            "opportunities": opportunities,
        }

    return scout_agent_node


def _parse_opportunities(report: str) -> List[Dict[str, Any]]:
    """从报告中解析股票机会列表

    Args:
        report: Scout Agent 的报告内容

    Returns:
        解析出的机会列表
    """
    try:
        # 尝试直接解析 JSON
        # 先尝试找到 JSON 数组
        import re

        # 查找 JSON 数组
        json_match = re.search(r'\[[\s\S]*?\]', report)
        if json_match:
            opportunities = json.loads(json_match.group())
            if isinstance(opportunities, list):
                return opportunities

        # 尝试解析整个内容
        data = json.loads(report)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "opportunities" in data:
            return data["opportunities"]

    except json.JSONDecodeError:
        logger.debug("Could not parse opportunities as JSON")

    except Exception as e:
        logger.warning("Failed to parse opportunities", error=str(e))

    return []
