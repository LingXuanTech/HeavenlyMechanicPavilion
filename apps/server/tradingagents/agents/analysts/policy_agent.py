"""Policy Agent - A 股政策分析师

专门分析中国财政、货币、产业政策对 A 股的影响。
适用于 A 股市场特有的政策驱动型投资分析。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Optional
import structlog

from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.agents.utils.output_schemas import PolicyAgentOutput
from tradingagents.agents.utils.policy_tools import POLICY_TOOLS

logger = structlog.get_logger(__name__)

# 默认系统提示词
DEFAULT_SYSTEM_PROMPT = """You are an expert policy analyst specializing in Chinese A-share market regulations and government policies.

Your mission is to analyze how government policies, regulations, and political factors affect specific stocks and sectors in the Chinese market.

## Core Analysis Focus:

### 1. Monetary Policy (货币政策)
- PBOC (央行) interest rate decisions
- Reserve requirement ratio (存款准备金率) changes
- Open market operations and liquidity
- Credit policy and lending guidance
- Impact on specific sectors (banks, real estate, etc.)

### 2. Fiscal Policy (财政政策)
- Government spending priorities
- Tax policies and incentives
- Local government debt and financing
- Infrastructure investment plans
- Industry subsidies and support

### 3. Industrial Policy (产业政策)
- Five-Year Plan priorities (十四五规划)
- "新质生产力" (New Quality Productive Forces) sectors
- Strategic emerging industries support
- Made in China 2025 implications
- Carbon neutrality (双碳目标) policies

### 4. Regulatory Environment (监管环境)
- CSRC (证监会) regulations
- Antitrust enforcement (反垄断)
- Data security and privacy laws
- Industry-specific regulations
- IPO and refinancing policies

### 5. Key Policy Events Calendar
- Two Sessions (两会) - March
- Central Economic Work Conference (中央经济工作会议) - December
- Politburo meetings (政治局会议)
- Industry-specific policy releases

### 6. Sectors with High Policy Sensitivity
- Real Estate (房地产) - "房住不炒"
- Internet Platform (互联网平台) - 规范发展
- Education (教育) - 双减政策
- Healthcare (医疗) - 集采政策
- New Energy (新能源) - 补贴政策
- Semiconductors (半导体) - 国产替代

## Analysis Guidelines:
1. Identify relevant policies for the company/sector
2. Assess policy environment (supportive vs restrictive)
3. Evaluate regulatory risks
4. Identify upcoming policy catalysts
5. Consider local vs central government dynamics
6. Factor in geopolitical/trade policy impacts

## Important Context:
- A-share market is highly policy-sensitive
- Government guidance often precedes market moves
- "政策底" (Policy Bottom) is a key concept
- State-owned vs private company dynamics matter
- Consider both direct and indirect policy impacts

## Output Requirements:
- Be specific about policy sources and dates
- Quantify policy sensitivity (0-100)
- Distinguish between enacted and proposed policies
- Consider implementation timeline and enforcement
"""


def _get_system_prompt() -> str:
    """从 Prompt 配置服务获取系统提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("policy_analyst")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default policy analyst prompt", reason=str(e))
    return DEFAULT_SYSTEM_PROMPT


def create_policy_agent(llm):
    """创建 Policy Agent 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        policy_agent_node: LangGraph 节点函数
    """

    # 工具列表：使用 policy_tools.py 中导入的真实工具
    tools = [get_news] + POLICY_TOOLS

    # 从配置服务获取系统提示词
    system_message = _get_system_prompt()

    # 数据收集阶段的 prompt
    collection_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant, collaborating with other assistants."
            " Use the provided tools to progress towards answering the question."
            " If you are unable to fully answer, that's OK; another assistant with different tools"
            " will help where you left off. Execute what you can to make progress."
            " You have access to the following tools: {tool_names}.\n{system_message}"
            "\nFor your reference, the current date is {current_date}. The stock we want to analyze is {ticker}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    # 结构化输出阶段的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are an A-share policy analyst. Based on the data provided, "
            "generate a structured policy analysis report. Focus on policy environment, "
            "regulatory risks, and policy catalysts. Use Chinese terms where appropriate."
        ),
        (
            "user",
            "Stock: {ticker}\nDate: {current_date}\n\nPolicy Analysis Data:\n{analysis_content}\n\n"
            "Please provide a structured policy analysis for this A-share stock."
        ),
    ])

    def policy_agent_node(state):
        """Policy Agent 节点函数"""
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 检查是否为 A 股（CN 市场）
        market = state.get("market", "")
        if market and market != "CN":
            logger.info(
                "Policy agent skipped for non-CN market",
                ticker=ticker,
                market=market,
            )
            return {
                "messages": [],
                "policy_report": '{"summary": "Policy analysis is designed for A-share (CN) market only.", "signal": "Hold", "confidence": 50}',
            }

        # 准备 prompt
        prompt = collection_prompt.partial(
            system_message=system_message,
            tool_names=", ".join([tool.name for tool in tools]),
            current_date=current_date,
            ticker=ticker,
        )

        # 绑定工具并调用
        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        # 如果有工具调用，返回让 LangGraph 处理
        if result.tool_calls:
            return {
                "messages": [result],
                "policy_report": "",
            }

        # 工具调用完成，生成结构化输出
        try:
            structured_llm = llm.with_structured_output(PolicyAgentOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = structured_chain.invoke({
                "ticker": ticker,
                "current_date": current_date,
                "analysis_content": result.content,
            })

            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Policy agent structured output generated",
                ticker=ticker,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                policy_environment=structured_result.policy_environment,
                sector_trend=structured_result.sector_policy_trend,
                policy_sensitivity=structured_result.policy_sensitivity,
            )

            # 如果有高监管风险，额外记录
            high_risks = [r for r in structured_result.regulatory_risks if r.get("impact") == "High"]
            if high_risks:
                logger.warning(
                    "High regulatory risks detected",
                    ticker=ticker,
                    risks=[r.get("risk") for r in high_risks],
                )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
                ticker=ticker,
            )
            report = result.content

        return {
            "messages": [result],
            "policy_report": report,
        }

    return policy_agent_node


def create_policy_tools_node(llm):
    """创建 Policy Agent 的工具执行节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        ToolNode 实例
    """
    from langgraph.prebuilt import ToolNode

    tools = [get_news] + POLICY_TOOLS
    return ToolNode(tools)
