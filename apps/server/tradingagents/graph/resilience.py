# TradingAgents/graph/resilience.py

"""Agent 执行弹性模块

提供：
1. 节点超时处理
2. 失败降级机制
3. 重试逻辑
4. 执行监控
"""

import asyncio
import functools
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable, Dict, Optional, TypeVar
import structlog

from tradingagents.agents.utils.agent_states import (
    AnalystType,
    ANALYST_REPORT_FIELDS,
    set_analyst_report,
)

logger = structlog.get_logger(__name__)

# 类型变量
T = TypeVar("T")


class AgentExecutionError(Exception):
    """Agent 执行异常"""

    def __init__(self, agent_name: str, message: str, original_error: Optional[Exception] = None):
        self.agent_name = agent_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"[{agent_name}] {message}")


class NodeExecutionMetrics:
    """节点执行指标"""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.success: bool = False
        self.error: Optional[str] = None
        self.timeout: bool = False
        self.retries: int = 0

    @property
    def duration_ms(self) -> int:
        """执行时长（毫秒）"""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0


class ResilientNodeWrapper:
    """弹性节点包装器

    为单个 Agent 节点提供超时、降级、重试能力。
    """

    # 默认配置
    DEFAULT_TIMEOUT_SECONDS = 60
    DEFAULT_MAX_RETRIES = 1
    DEFAULT_RETRY_DELAY = 2.0

    # 线程池（用于超时控制）
    _executor: Optional[ThreadPoolExecutor] = None

    @classmethod
    def get_executor(cls) -> ThreadPoolExecutor:
        """获取共享线程池"""
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="agent_node_")
        return cls._executor

    def __init__(
        self,
        node_func: Callable,
        node_name: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        fallback_result: Optional[Dict[str, Any]] = None,
    ):
        """初始化弹性节点包装器

        Args:
            node_func: 原始节点函数
            node_name: 节点名称（用于日志和监控）
            timeout_seconds: 超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            fallback_result: 降级时返回的结果
        """
        self.node_func = node_func
        self.node_name = node_name
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.fallback_result = fallback_result or {}

        # 保留原始函数的元数据
        functools.update_wrapper(self, node_func)

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行节点（带超时和降级）"""
        metrics = NodeExecutionMetrics()
        metrics.start_time = time.time()

        for attempt in range(self.max_retries + 1):
            try:
                # 使用线程池执行并设置超时
                future = self.get_executor().submit(self.node_func, state)
                result = future.result(timeout=self.timeout_seconds)

                metrics.end_time = time.time()
                metrics.success = True

                logger.info(
                    "Agent node completed",
                    node=self.node_name,
                    duration_ms=metrics.duration_ms,
                    attempt=attempt + 1,
                )

                return result

            except FuturesTimeoutError:
                metrics.timeout = True
                metrics.retries = attempt
                logger.warning(
                    "Agent node timeout",
                    node=self.node_name,
                    timeout_seconds=self.timeout_seconds,
                    attempt=attempt + 1,
                )

                # 取消未完成的 future
                future.cancel()

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue

                # 最终超时，返回降级结果
                return self._create_fallback_result(state, "timeout")

            except Exception as e:
                metrics.error = str(e)
                metrics.retries = attempt
                logger.error(
                    "Agent node error",
                    node=self.node_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                )

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue

                # 最终失败，返回降级结果
                return self._create_fallback_result(state, str(e))

        # 不应到达此处
        metrics.end_time = time.time()
        return self._create_fallback_result(state, "max_retries_exceeded")

    def _create_fallback_result(self, state: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """创建降级结果

        Args:
            state: 当前状态
            reason: 降级原因

        Returns:
            降级后的状态更新
        """
        logger.warning(
            "Agent node degraded",
            node=self.node_name,
            reason=reason,
        )

        # 合并自定义降级结果
        result = dict(self.fallback_result)

        # 添加降级标记消息
        fallback_message = (
            f"[{self.node_name}] Analysis unavailable due to {reason}. "
            f"Proceeding with limited information."
        )

        # 根据节点类型设置对应的报告字段为降级内容
        report_field = self._get_report_field_for_node()
        if report_field and report_field not in result:
            result[report_field] = fallback_message

        # 确保消息列表存在
        if "messages" not in result:
            result["messages"] = []

        return result

    def _get_report_field_for_node(self) -> Optional[str]:
        """根据节点名称获取对应的报告字段"""
        # 从节点名称提取分析师类型
        node_to_type = {
            "Market Analyst": AnalystType.MARKET,
            "Social Analyst": AnalystType.SOCIAL,
            "News Analyst": AnalystType.NEWS,
            "Fundamentals Analyst": AnalystType.FUNDAMENTALS,
            "Sentiment Analyst": AnalystType.SENTIMENT,
            "Policy Analyst": AnalystType.POLICY,
            "Fund_flow Analyst": AnalystType.FUND_FLOW,
        }
        analyst_type = node_to_type.get(self.node_name)
        if analyst_type:
            return ANALYST_REPORT_FIELDS.get(analyst_type)
        return None


def with_timeout(
    timeout_seconds: float = ResilientNodeWrapper.DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = ResilientNodeWrapper.DEFAULT_MAX_RETRIES,
    fallback_result: Optional[Dict[str, Any]] = None,
):
    """装饰器：为节点函数添加超时和降级能力

    Usage:
        @with_timeout(timeout_seconds=30, max_retries=2)
        def my_analyst_node(state):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            resilient_node = ResilientNodeWrapper(
                node_func=func,
                node_name=func.__name__,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                fallback_result=fallback_result,
            )
            return resilient_node(state)
        return wrapper
    return decorator


class AnalystNodeFactory:
    """分析师节点工厂

    创建带有弹性能力的分析师节点。
    """

    # 各分析师的默认超时配置（秒）
    TIMEOUT_CONFIG = {
        "market": 45,
        "social": 45,
        "news": 60,
        "fundamentals": 60,
        "sentiment": 45,
        "policy": 45,
        "fund_flow": 45,
        "macro": 60,
        "scout": 30,
        "portfolio": 30,
    }

    # 各分析师的降级报告内容
    FALLBACK_REPORTS = {
        "market": "Technical analysis unavailable. Using baseline market assumptions.",
        "social": "Social media sentiment analysis unavailable.",
        "news": "News analysis unavailable. Proceeding without recent news context.",
        "fundamentals": "Fundamental analysis unavailable. Using historical data assumptions.",
        "sentiment": "Retail sentiment analysis unavailable.",
        "policy": "Policy analysis unavailable. Assuming neutral regulatory stance.",
        "fund_flow": "Fund flow analysis unavailable. Assuming neutral capital flow.",
    }

    @classmethod
    def wrap_analyst_node(
        cls,
        node_func: Callable,
        analyst_type: str,
        custom_timeout: Optional[float] = None,
    ) -> ResilientNodeWrapper:
        """包装分析师节点

        Args:
            node_func: 原始节点函数
            analyst_type: 分析师类型（market/social/news/...）
            custom_timeout: 自定义超时时间

        Returns:
            包装后的弹性节点
        """
        timeout = custom_timeout or cls.TIMEOUT_CONFIG.get(analyst_type, 60)
        node_name = f"{analyst_type.capitalize()} Analyst"

        # 使用集中式工具函数构建降级结果
        fallback_result = {"messages": [], "analyst_reports": {}}
        fallback_content = cls.FALLBACK_REPORTS.get(analyst_type, "Analysis unavailable.")

        # 同时更新动态字典和传统字段（向后兼容）
        fallback_result["analyst_reports"][analyst_type] = fallback_content
        report_field = ANALYST_REPORT_FIELDS.get(analyst_type)
        if report_field:
            fallback_result[report_field] = fallback_content

        return ResilientNodeWrapper(
            node_func=node_func,
            node_name=node_name,
            timeout_seconds=timeout,
            max_retries=1,
            fallback_result=fallback_result,
        )


# 全局执行监控（可选扩展）
class ExecutionMonitor:
    """执行监控器

    跟踪所有节点的执行状态和性能指标。
    """

    _instance: Optional["ExecutionMonitor"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {}
            cls._instance._failed_nodes = []
        return cls._instance

    def record_execution(
        self,
        node_name: str,
        duration_ms: int,
        success: bool,
        error: Optional[str] = None,
    ):
        """记录执行"""
        if node_name not in self._metrics:
            self._metrics[node_name] = {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "total_duration_ms": 0,
                "errors": [],
            }

        self._metrics[node_name]["total_executions"] += 1
        self._metrics[node_name]["total_duration_ms"] += duration_ms

        if success:
            self._metrics[node_name]["successful"] += 1
        else:
            self._metrics[node_name]["failed"] += 1
            if error:
                self._metrics[node_name]["errors"].append(error)
                self._failed_nodes.append({"node": node_name, "error": error})

    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "node_metrics": self._metrics,
            "recent_failures": self._failed_nodes[-10:],
        }

    def reset(self):
        """重置监控数据"""
        self._metrics = {}
        self._failed_nodes = []


# 单例监控器
execution_monitor = ExecutionMonitor()
