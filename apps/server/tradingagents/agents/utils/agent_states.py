from typing import Annotated, Sequence, Dict, List
from datetime import date, timedelta, datetime
from typing_extensions import TypedDict, Optional
from langchain_openai import ChatOpenAI
from tradingagents.agents import *
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, StateGraph, START, MessagesState


# ============ 分析师类型定义 ============

class AnalystType:
    """支持的分析师类型常量"""
    # 核心分析师（所有市场）
    MARKET = "market"           # 市场分析（技术面）
    FUNDAMENTALS = "fundamentals"  # 基本面分析
    NEWS = "news"               # 新闻分析
    SOCIAL = "social"           # 社交媒体分析
    MACRO = "macro"             # 宏观分析

    # A股特色分析师
    SENTIMENT = "sentiment"     # 散户情绪分析
    POLICY = "policy"           # 政策分析
    FUND_FLOW = "fund_flow"     # 资金流向分析

    # 迭代 6 新增分析师
    VISION = "vision"           # 多模态图表分析
    SUPPLY_CHAIN = "supply_chain"  # 产业链分析

    # 所有类型
    ALL = [MARKET, FUNDAMENTALS, NEWS, SOCIAL, MACRO, SENTIMENT, POLICY, FUND_FLOW, VISION, SUPPLY_CHAIN]

    # 核心类型（必须有报告）
    CORE = [MARKET, FUNDAMENTALS, NEWS, SOCIAL]

    # A股专属类型
    CN_ONLY = [SENTIMENT, POLICY, FUND_FLOW]

    # 扩展类型（可选）
    EXTENDED = [VISION, SUPPLY_CHAIN]


# ============ 分析师报告字段映射 ============

# 映射分析师类型到 AgentState 字段名（向后兼容）
ANALYST_REPORT_FIELDS = {
    AnalystType.MARKET: "market_report",
    AnalystType.FUNDAMENTALS: "fundamentals_report",
    AnalystType.NEWS: "news_report",
    AnalystType.SOCIAL: "sentiment_report",  # 注意：social 对应 sentiment_report（历史原因）
    AnalystType.MACRO: "macro_report",       # 新增
    AnalystType.SENTIMENT: "retail_sentiment_report",
    AnalystType.POLICY: "policy_report",
    AnalystType.FUND_FLOW: "china_flow_data",
    AnalystType.VISION: "vision_report",
    AnalystType.SUPPLY_CHAIN: "supply_chain_report",
}


# ============ 团队状态定义 ============

# Researcher team state
class InvestDebateState(TypedDict):
    bull_history: Annotated[
        str, "Bullish Conversation history"
    ]  # Bullish Conversation history
    bear_history: Annotated[
        str, "Bearish Conversation history"
    ]  # Bullish Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    current_response: Annotated[str, "Latest response"]  # Last response
    judge_decision: Annotated[str, "Final judge decision"]  # Last response
    count: Annotated[int, "Length of the current conversation"]  # Conversation length


# Risk management team state
class RiskDebateState(TypedDict):
    risky_history: Annotated[
        str, "Risky Agent's Conversation history"
    ]  # Conversation history
    safe_history: Annotated[
        str, "Safe Agent's Conversation history"
    ]  # Conversation history
    neutral_history: Annotated[
        str, "Neutral Agent's Conversation history"
    ]  # Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    latest_speaker: Annotated[str, "Analyst that spoke last"]
    current_risky_response: Annotated[
        str, "Latest response by the risky analyst"
    ]  # Last response
    current_safe_response: Annotated[
        str, "Latest response by the safe analyst"
    ]  # Last response
    current_neutral_response: Annotated[
        str, "Latest response by the neutral analyst"
    ]  # Last response
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]  # Conversation length


# ============ 主状态定义 ============

class AgentState(MessagesState):
    """主 Agent 状态

    使用动态字典 `analyst_reports` 存储所有分析师报告。
    同时保留原有字段以向后兼容现有代码。

    使用 `set_analyst_report()` 和 `get_analyst_report()` 操作报告。
    """
    company_of_interest: Annotated[str, "Company that we are interested in trading"]
    trade_date: Annotated[str, "What date we are trading at"]
    market: Annotated[str, "Market of the stock: US, HK, or CN"]

    sender: Annotated[str, "Agent that sent this message"]

    # Historical reflection context (from memory service)
    historical_reflection: Annotated[str, "Historical analysis patterns and lessons for this stock"]

    # ============ 动态分析师报告存储 ============
    # 新增：使用字典统一管理所有分析师报告
    analyst_reports: Annotated[Dict[str, str], "Dynamic storage for all analyst reports keyed by analyst type"]

    # ============ 向后兼容的静态字段 ============
    # 这些字段保留以兼容现有代码，新代码应使用 analyst_reports

    # research step
    market_report: Annotated[str, "Report from the Market Analyst"]
    sentiment_report: Annotated[str, "Report from the Social Media Analyst"]
    news_report: Annotated[
        str, "Report from the News Researcher of current world affairs"
    ]
    fundamentals_report: Annotated[str, "Report from the Fundamentals Researcher"]

    # New A-share focused reports
    retail_sentiment_report: Annotated[str, "Report from the Retail Sentiment Analyst (FOMO/FUD analysis)"]
    policy_report: Annotated[str, "Report from the Policy Analyst (A-share regulatory analysis)"]

    # A 股资金流向数据（北向资金 + 龙虎榜）
    china_flow_data: Annotated[str, "A-share fund flow data: north money + LHB analysis"]

    # 迭代 6 新增报告字段
    vision_report: Annotated[str, "Report from the Vision Analyst (chart/image analysis)"]
    supply_chain_report: Annotated[str, "Report from the Supply Chain Analyst (industry chain analysis)"]

    # ============ Planner 相关字段 ============
    # Planner/Scout Agent 输出
    macro_report: Annotated[str, "Report from the Macro Analyst"]
    portfolio_report: Annotated[str, "Portfolio risk analysis report"]
    scout_report: Annotated[str, "Report from the Scout/Planner Agent"]
    opportunities: Annotated[List[str], "Discovered stock opportunities from Scout"]
    recommended_analysts: Annotated[List[str], "Planner recommended analysts for this analysis"]

    # researcher team discussion step
    investment_debate_state: Annotated[
        InvestDebateState, "Current state of the debate on if to invest or not"
    ]
    investment_plan: Annotated[str, "Plan generated by the Analyst"]

    trader_investment_plan: Annotated[str, "Plan generated by the Trader"]

    # risk management team discussion step
    risk_debate_state: Annotated[
        RiskDebateState, "Current state of the debate on evaluating risk"
    ]
    final_trade_decision: Annotated[str, "Final decision made by the Risk Analysts"]


# ============ 状态操作工具函数 ============

def get_analyst_report(state: AgentState, analyst_type: str) -> str:
    """从状态中获取指定分析师的报告

    优先从 analyst_reports 字典读取，
    如果不存在则回退到传统字段。

    Args:
        state: AgentState 实例
        analyst_type: 分析师类型（使用 AnalystType 常量）

    Returns:
        分析报告内容，如果不存在返回空字符串
    """
    # 首先尝试从动态字典获取
    reports = state.get("analyst_reports", {})
    if analyst_type in reports and reports[analyst_type]:
        return reports[analyst_type]

    # 回退到传统字段
    field_name = ANALYST_REPORT_FIELDS.get(analyst_type)
    if field_name:
        return state.get(field_name, "")

    return ""


def set_analyst_report(analyst_type: str, report: str) -> Dict:
    """生成用于更新分析师报告的状态更新字典

    同时更新 analyst_reports 字典和传统字段，确保向后兼容。

    Args:
        analyst_type: 分析师类型（使用 AnalystType 常量）
        report: 报告内容

    Returns:
        可用于状态更新的字典

    Example:
        return set_analyst_report(AnalystType.MARKET, "Market analysis...")
    """
    update = {
        "analyst_reports": {analyst_type: report}
    }

    # 同时更新传统字段以向后兼容
    field_name = ANALYST_REPORT_FIELDS.get(analyst_type)
    if field_name:
        update[field_name] = report

    return update


def get_all_reports(state: AgentState) -> Dict[str, str]:
    """获取所有分析师报告

    合并 analyst_reports 字典和传统字段中的报告。

    Args:
        state: AgentState 实例

    Returns:
        所有报告的字典 {analyst_type: report}
    """
    reports = {}

    # 从动态字典获取
    dynamic_reports = state.get("analyst_reports", {})
    reports.update(dynamic_reports)

    # 从传统字段补充（如果动态字典中没有）
    for analyst_type, field_name in ANALYST_REPORT_FIELDS.items():
        if analyst_type not in reports or not reports[analyst_type]:
            value = state.get(field_name, "")
            if value:
                reports[analyst_type] = value

    return reports


def get_missing_reports(state: AgentState, required: list = None) -> list:
    """获取缺失的必需报告

    Args:
        state: AgentState 实例
        required: 必需的分析师类型列表，默认为 AnalystType.CORE

    Returns:
        缺失的分析师类型列表
    """
    if required is None:
        required = AnalystType.CORE

    all_reports = get_all_reports(state)
    missing = []

    for analyst_type in required:
        report = all_reports.get(analyst_type, "")
        if not report or "unavailable" in report.lower():
            missing.append(analyst_type)

    return missing
