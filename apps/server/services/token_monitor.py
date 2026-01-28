"""Token 消耗监控服务

追踪 LLM 调用的 Token 消耗，提供成本分析能力。
"""

from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import structlog

logger = structlog.get_logger(__name__)


# 常见模型的 Token 价格（美元/1K tokens）
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "o4-mini": {"input": 0.003, "output": 0.012},  # 估算
    # Anthropic
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    # Google
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004},
    # DeepSeek
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
}


class TokenMonitor:
    """Token 消耗监控服务（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._reset_stats()

    def _reset_stats(self):
        """重置统计数据"""
        self._usage_by_model: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "calls": 0,
                "cost_usd": 0.0,
                "last_call": None,
            }
        )
        self._session_start = datetime.now()
        self._total_calls = 0

    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Optional[float] = None,
    ):
        """记录一次 LLM 调用的 Token 消耗

        Args:
            model: 模型名称
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            cost_usd: 可选的成本（美元），如果不提供则自动计算
        """
        # 标准化模型名称
        model_key = self._normalize_model_name(model)

        # 计算成本
        if cost_usd is None:
            cost_usd = self._calculate_cost(model_key, input_tokens, output_tokens)

        # 更新统计
        stats = self._usage_by_model[model_key]
        stats["input_tokens"] += input_tokens
        stats["output_tokens"] += output_tokens
        stats["total_tokens"] += (input_tokens + output_tokens)
        stats["calls"] += 1
        stats["cost_usd"] += cost_usd
        stats["last_call"] = datetime.now().isoformat()

        self._total_calls += 1

        logger.debug(
            "Token usage recorded",
            model=model_key,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=round(cost_usd, 6),
            cumulative_total=stats["total_tokens"],
        )

    def _normalize_model_name(self, model: str) -> str:
        """标准化模型名称"""
        if not model:
            return "unknown"
        # 移除前缀和版本号
        model = model.lower().strip()
        for prefix in ["models/", "openai/", "anthropic/", "google/"]:
            if model.startswith(prefix):
                model = model[len(prefix):]
        return model

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """计算 Token 成本"""
        # 查找匹配的定价
        pricing = None
        for model_name, price in MODEL_PRICING.items():
            if model_name in model or model in model_name:
                pricing = price
                break

        if pricing is None:
            # 使用默认定价（基于 GPT-4o-mini）
            pricing = {"input": 0.00015, "output": 0.0006}

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def get_usage_summary(self) -> Dict[str, Any]:
        """获取 Token 使用摘要"""
        total_tokens = sum(m["total_tokens"] for m in self._usage_by_model.values())
        total_cost = sum(m["cost_usd"] for m in self._usage_by_model.values())

        return {
            "timestamp": datetime.now().isoformat(),
            "session_start": self._session_start.isoformat(),
            "total_calls": self._total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "by_model": dict(self._usage_by_model),
            "models_used": list(self._usage_by_model.keys()),
        }

    def get_model_stats(self, model: str) -> Optional[Dict[str, Any]]:
        """获取特定模型的统计"""
        model_key = self._normalize_model_name(model)
        if model_key in self._usage_by_model:
            return dict(self._usage_by_model[model_key])
        return None

    def reset(self):
        """重置所有统计数据"""
        self._reset_stats()
        logger.info("Token monitor stats reset")
        return {"status": "reset", "timestamp": datetime.now().isoformat()}


# 全局单例
token_monitor = TokenMonitor()
