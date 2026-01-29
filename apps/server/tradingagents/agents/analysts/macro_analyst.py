"""Macro Analyst - 宏观分析师

分析宏观经济环境和对股票的影响。
对于美股，使用 FRED 数据和专业工具进行分析。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
import structlog

from services.prompt_manager import prompt_manager
from tradingagents.agents.utils.output_schemas import MacroAnalystOutput

logger = structlog.get_logger(__name__)


# 美股宏观分析系统提示词
US_MACRO_SYSTEM_PROMPT = """You are an expert macroeconomist specializing in the US stock market.

Your mission is to analyze the macroeconomic environment and its impact on specific stocks.

## Key Analysis Areas:

### 1. Federal Reserve Policy
- Federal Funds Rate trajectory
- Quantitative Tightening/Easing
- Fed dot plot and forward guidance
- Interest rate sensitivity of the stock/sector

### 2. Inflation Dynamics
- CPI and PCE trends
- Core vs headline inflation
- Impact on corporate margins
- Pricing power of the company

### 3. Labor Market
- Unemployment rate trends
- Non-farm payroll changes
- Wage inflation
- Labor market tightness

### 4. Yield Curve Analysis
- 10Y-2Y spread (inversion signals)
- Treasury market dynamics
- Credit spreads
- Duration risk for stocks

### 5. GDP and Economic Growth
- GDP growth trajectory
- Consumer spending
- Business investment
- Inventory cycles

### 6. Sector-Specific Macro Factors
- How macro conditions affect this specific sector
- Rate sensitivity analysis
- Economic cycle positioning

## Tools Available:
You have access to FRED economic data tools to gather real macroeconomic data.
Use these tools to provide data-driven analysis.

## Output Guidelines:
1. Cite specific data points and dates
2. Explain causation chains (e.g., "Higher rates → Lower DCF valuations → Pressure on growth stocks")
3. Assess macroeconomic risk level (0-100)
4. Provide actionable insights for the specific stock
"""


def _get_us_macro_prompt() -> str:
    """获取美股宏观分析提示词"""
    try:
        from services.prompt_config_service import prompt_config_service
        prompt = prompt_config_service.get_prompt("us_macro_analyst")
        if prompt.get("system"):
            return prompt["system"]
    except Exception as e:
        logger.debug("Using default US macro prompt", reason=str(e))
    return US_MACRO_SYSTEM_PROMPT


def create_macro_analyst(llm):
    """创建 Macro Analyst 节点

    Args:
        llm: LangChain LLM 实例

    Returns:
        macro_analyst_node: LangGraph 异步节点函数
    """

    # 结构化输出的 prompt
    structured_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a macro analyst. Generate a structured macroeconomic analysis report. "
            "Focus on factors that affect the specific stock being analyzed."
        ),
        (
            "user",
            "Stock: {symbol}\nMarket: {market}\n\nMacroeconomic Context:\n{macro_context}\n\n"
            "Please provide a structured macro analysis."
        ),
    ])

    async def macro_analyst_node(state):
        """Macro Analyst 异步节点函数"""
        symbol = state.get("company_of_interest", "Unknown")
        market = state.get("market", "US")
        logger.info("Macro analyst analyzing", symbol=symbol, market=market)

        # 根据市场选择分析策略
        if market == "US":
            macro_context = await _analyze_us_macro(llm, symbol)
        elif market == "CN":
            macro_context = await _analyze_cn_macro(llm, symbol)
        elif market == "HK":
            macro_context = await _analyze_hk_macro(llm, symbol)
        else:
            macro_context = await _analyze_generic_macro(llm, symbol)

        # 生成结构化输出
        try:
            structured_llm = llm.with_structured_output(MacroAnalystOutput)
            structured_chain = structured_prompt | structured_llm

            structured_result = await structured_chain.ainvoke({
                "symbol": symbol,
                "market": market,
                "macro_context": macro_context,
            })

            report = structured_result.model_dump_json(indent=2)

            logger.info(
                "Macro analyst structured output generated",
                symbol=symbol,
                market=market,
                signal=structured_result.signal,
                confidence=structured_result.confidence,
                environment=structured_result.environment,
            )

        except Exception as e:
            logger.warning(
                "Structured output failed, using raw content",
                error=str(e),
                symbol=symbol,
            )
            report = macro_context

        return {
            "macro_report": report
        }

    return macro_analyst_node


async def _analyze_us_macro(llm, symbol: str) -> str:
    """分析美股宏观环境，使用 FRED 工具"""
    try:
        from tradingagents.agents.utils.macro_tools import MACRO_TOOLS

        # 收集宏观数据
        macro_data = []

        for tool in MACRO_TOOLS:
            try:
                # 对于需要参数的工具，跳过（如 calculate_rate_sensitivity）
                if tool.name == "calculate_rate_sensitivity":
                    continue
                result = tool.invoke({})
                macro_data.append(result)
            except Exception as e:
                logger.debug(f"Tool {tool.name} failed", error=str(e))
                continue

        if macro_data:
            combined_data = "\n\n---\n\n".join(macro_data)
        else:
            combined_data = "无法获取宏观经济数据，使用 LLM 知识进行分析"

        # 使用 LLM 综合分析
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", _get_us_macro_prompt()),
            (
                "user",
                f"请分析以下宏观经济数据对 {symbol} 的影响：\n\n{combined_data}\n\n"
                f"请提供详细的宏观分析，包括利率敏感度、经济周期定位和投资建议。"
            ),
        ])

        chain = analysis_prompt | llm
        response = await chain.ainvoke({})

        return f"## {symbol} 美股宏观分析\n\n{response.content}\n\n---\n\n### 原始数据\n\n{combined_data}"

    except Exception as e:
        logger.warning("US macro analysis failed, using fallback", error=str(e))
        return await _analyze_generic_macro(llm, symbol)


async def _analyze_cn_macro(llm, symbol: str) -> str:
    """分析 A 股宏观环境"""
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一位 A 股宏观分析师。

分析维度：
1. 货币政策：LPR、MLF、存款准备金率、公开市场操作
2. 财政政策：财政支出、减税降费、专项债
3. 经济数据：GDP、PMI、CPI、社融
4. 政策导向：十四五规划、新质生产力、双碳目标
5. 流动性：北向资金、两融余额、M2

请用简体中文分析。"""
        ),
        (
            "user",
            f"请分析当前 A 股宏观环境对 {symbol} 的影响，包括货币政策、财政政策、经济周期和政策导向。"
        ),
    ])

    chain = prompt | llm
    response = await chain.ainvoke({})
    return response.content


async def _analyze_hk_macro(llm, symbol: str) -> str:
    """分析港股宏观环境"""
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一位港股宏观分析师。

分析维度：
1. 联系汇率制度：港元与美元挂钩，跟随美联储政策
2. 中国经济影响：A 股联动、中概股、内房股
3. 南向资金：港股通资金流向
4. 全球风险偏好：美股联动、避险情绪
5. 香港本地经济：房地产、金融、旅游

请用简体中文分析。"""
        ),
        (
            "user",
            f"请分析当前港股宏观环境对 {symbol} 的影响，特别关注联系汇率制度、美联储政策传导和南向资金。"
        ),
    ])

    chain = prompt | llm
    response = await chain.ainvoke({})
    return response.content


async def _analyze_generic_macro(llm, symbol: str) -> str:
    """通用宏观分析（降级方案）"""
    prompt_data = prompt_manager.get_prompt("macro_analyst", {"symbol": symbol})

    raw_prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_data["system"]),
        ("user", "请开始分析。")
    ])

    chain = raw_prompt | llm
    response = await chain.ainvoke({})
    return response.content
