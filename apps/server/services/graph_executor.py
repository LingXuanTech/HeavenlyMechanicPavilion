"""
TradingAgents 图执行器

提供统一的图执行和报告收集逻辑，避免代码重复。
"""
import time
import structlog
from typing import Dict, Optional, List, Any, Callable, Awaitable
from datetime import date

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from services.data_router import MarketRouter

logger = structlog.get_logger()


class GraphExecutionResult:
    """图执行结果"""
    def __init__(
        self,
        agent_reports: Dict[str, str],
        elapsed_seconds: float,
        final_state: Optional[Dict[str, Any]] = None,
    ):
        self.agent_reports = agent_reports
        self.elapsed_seconds = elapsed_seconds
        self.final_state = final_state or {}


async def execute_trading_graph(
    symbol: str,
    trade_date: Optional[str] = None,
    analysis_level: str = "L2",
    override_analysts: Optional[List[str]] = None,
    exclude_analysts: Optional[List[str]] = None,
    use_planner: bool = True,
    use_subgraphs: bool = False,
    debug: bool = False,
    historical_reflection: Optional[str] = None,
    on_node_complete: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
) -> GraphExecutionResult:
    """
    执行 TradingAgents 图分析

    Args:
        symbol: 股票代码
        trade_date: 分析日期（默认今天）
        analysis_level: 分析级别 L1/L2
        override_analysts: 覆盖分析师列表
        exclude_analysts: 排除分析师列表
        use_planner: 是否使用 Planner
        use_subgraphs: 是否使用 SubGraph 架构
        debug: 是否开启调试模式
        historical_reflection: 历史反思信息
        on_node_complete: 节点完成回调函数（用于 SSE 推送）

    Returns:
        GraphExecutionResult: 包含 agent_reports 和执行时间
    """
    start_time = time.time()

    if trade_date is None:
        trade_date = date.today().isoformat()

    # 初始化配置
    config = DEFAULT_CONFIG.copy()
    market = MarketRouter.get_market(symbol)

    # 根据分析级别调整配置
    if analysis_level == "L1":
        config["analysis_level"] = "L1"
        config["enable_debate"] = False
        config["enable_risk_debate"] = False
        use_planner = False  # L1 不使用 Planner

    # 初始化图
    ta = TradingAgentsGraph(
        debug=debug,
        config=config,
        market=market,
        use_subgraphs=use_subgraphs,
    )

    # 创建初始状态
    init_state = ta.propagator.create_initial_state(
        symbol,
        trade_date,
        market=market,
        override_analysts=override_analysts,
        exclude_analysts=exclude_analysts,
        use_planner=use_planner,
        historical_reflection=historical_reflection,
    )

    # 执行图
    args = ta.propagator.get_graph_args()
    agent_reports = {}
    final_state = {}

    logger.info(
        "Starting graph execution",
        symbol=symbol,
        analysis_level=analysis_level,
        use_planner=use_planner,
        use_subgraphs=use_subgraphs,
    )

    for chunk in ta.graph.stream(init_state, **args):
        for node_name, node_data in chunk.items():
            # 收集所有 agent 报告
            collect_agent_reports(node_data, agent_reports)
            # 保存最终状态
            final_state = node_data

            # 调用节点完成回调（用于 SSE 推送）
            if on_node_complete:
                await on_node_complete(node_name, node_data)

    elapsed_seconds = round(time.time() - start_time, 2)

    logger.info(
        "Graph execution completed",
        symbol=symbol,
        elapsed_seconds=elapsed_seconds,
        reports_collected=len(agent_reports),
    )

    return GraphExecutionResult(
        agent_reports=agent_reports,
        elapsed_seconds=elapsed_seconds,
        final_state=final_state,
    )


def collect_agent_reports(node_data: Dict[str, Any], agent_reports: Dict[str, str]) -> None:
    """
    从节点数据中收集 agent 报告

    Args:
        node_data: 节点输出数据
        agent_reports: 报告收集字典（会被修改）
    """
    # 分析师报告
    report_keys = [
        "macro_report",
        "market_report",
        "news_report",
        "fundamentals_report",
        "social_report",
        "sentiment_report",
        "policy_report",
        "fund_flow_report",
        "portfolio_report",
        "retail_sentiment_report",  # A股散户情绪
    ]

    for key in report_keys:
        if key in node_data:
            # 去掉 _report 后缀作为 key
            report_name = key.replace("_report", "")
            agent_reports[report_name] = node_data[key]

    # 其他关键状态
    if "investment_plan" in node_data:
        agent_reports["investment_plan"] = node_data["investment_plan"]

    if "final_trade_decision" in node_data:
        agent_reports["final_trade_decision"] = node_data["final_trade_decision"]

    if "investment_debate_state" in node_data:
        agent_reports["debate"] = node_data["investment_debate_state"]

    if "risk_debate_state" in node_data:
        agent_reports["risk_debate"] = node_data["risk_debate_state"]
