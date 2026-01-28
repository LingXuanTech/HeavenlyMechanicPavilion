"""
API 性能指标收集

收集 HTTP 请求延迟、状态码统计、吞吐量等指标
提供轻量级的 /metrics 端点（无需 Prometheus 依赖）
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional
import structlog

logger = structlog.get_logger()


@dataclass
class RequestMetrics:
    """单次请求指标"""
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PathMetrics:
    """路径级别聚合指标"""
    total_requests: int = 0
    total_errors: int = 0  # 5xx
    total_client_errors: int = 0  # 4xx
    total_success: int = 0  # 2xx
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0

    def add_request(self, status_code: int, duration_ms: float):
        self.total_requests += 1
        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)

        if 200 <= status_code < 300:
            self.total_success += 1
        elif 400 <= status_code < 500:
            self.total_client_errors += 1
        elif status_code >= 500:
            self.total_errors += 1

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.total_requests if self.total_requests > 0 else 0.0

    @property
    def error_rate(self) -> float:
        return self.total_errors / self.total_requests * 100 if self.total_requests > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.total_success / self.total_requests * 100 if self.total_requests > 0 else 0.0


class APIMetricsService:
    """API 指标收集服务（单例）"""

    def __init__(self, history_limit: int = 1000, window_minutes: int = 60):
        self.history_limit = history_limit
        self.window_minutes = window_minutes
        self._lock = Lock()
        self._start_time = datetime.now()

        # 按路径聚合指标
        self._path_metrics: dict[str, PathMetrics] = defaultdict(PathMetrics)

        # 最近 N 条请求历史（用于分析）
        self._recent_requests: list[RequestMetrics] = []

        # 滑动窗口统计（最近 N 分钟）
        self._window_requests: list[RequestMetrics] = []

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float
    ):
        """记录一次请求指标"""
        # 规范化路径（移除查询字符串和动态参数）
        normalized_path = self._normalize_path(path)
        key = f"{method} {normalized_path}"

        metrics = RequestMetrics(
            method=method,
            path=normalized_path,
            status_code=status_code,
            duration_ms=duration_ms
        )

        with self._lock:
            # 更新路径聚合指标
            self._path_metrics[key].add_request(status_code, duration_ms)

            # 添加到历史记录
            self._recent_requests.append(metrics)
            if len(self._recent_requests) > self.history_limit:
                self._recent_requests.pop(0)

            # 添加到滑动窗口
            self._window_requests.append(metrics)
            self._cleanup_window()

    def _normalize_path(self, path: str) -> str:
        """规范化路径（将动态参数替换为占位符）"""
        # 移除查询字符串
        path = path.split('?')[0]

        # 常见模式替换
        parts = path.split('/')
        normalized = []
        for part in parts:
            # 任务 ID 格式: task_XXX_XXXX
            if part.startswith('task_'):
                normalized.append('{task_id}')
            # UUID 格式
            elif len(part) == 36 and '-' in part:
                normalized.append('{uuid}')
            # 纯数字
            elif part.isdigit():
                normalized.append('{id}')
            # 股票代码（含数字和字母组合）
            elif len(part) > 0 and any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
                # 可能是股票代码如 AAPL, 600519.SH
                if '.' in part or part.isupper():
                    normalized.append('{symbol}')
                else:
                    normalized.append(part)
            else:
                normalized.append(part)

        return '/'.join(normalized)

    def _cleanup_window(self):
        """清理过期的滑动窗口数据"""
        cutoff = datetime.now() - timedelta(minutes=self.window_minutes)
        self._window_requests = [
            r for r in self._window_requests if r.timestamp > cutoff
        ]

    def get_metrics(self) -> dict:
        """获取所有指标"""
        with self._lock:
            self._cleanup_window()

            # 计算全局指标
            total_requests = sum(m.total_requests for m in self._path_metrics.values())
            total_errors = sum(m.total_errors for m in self._path_metrics.values())
            total_duration = sum(m.total_duration_ms for m in self._path_metrics.values())

            # 窗口内指标
            window_requests = len(self._window_requests)
            window_errors = sum(1 for r in self._window_requests if r.status_code >= 500)
            window_duration = sum(r.duration_ms for r in self._window_requests)

            # 按路径统计
            path_stats = {}
            for key, metrics in self._path_metrics.items():
                path_stats[key] = {
                    "requests": metrics.total_requests,
                    "success": metrics.total_success,
                    "client_errors": metrics.total_client_errors,
                    "errors": metrics.total_errors,
                    "success_rate_pct": round(metrics.success_rate, 2),
                    "error_rate_pct": round(metrics.error_rate, 2),
                    "avg_duration_ms": round(metrics.avg_duration_ms, 2),
                    "min_duration_ms": round(metrics.min_duration_ms, 2) if metrics.min_duration_ms != float('inf') else 0,
                    "max_duration_ms": round(metrics.max_duration_ms, 2),
                }

            return {
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
                "global": {
                    "total_requests": total_requests,
                    "total_errors": total_errors,
                    "avg_duration_ms": round(total_duration / total_requests, 2) if total_requests > 0 else 0,
                    "error_rate_pct": round(total_errors / total_requests * 100, 2) if total_requests > 0 else 0,
                },
                "window": {
                    "window_minutes": self.window_minutes,
                    "requests": window_requests,
                    "errors": window_errors,
                    "avg_duration_ms": round(window_duration / window_requests, 2) if window_requests > 0 else 0,
                    "requests_per_minute": round(window_requests / self.window_minutes, 2),
                },
                "by_path": path_stats,
            }

    def get_slow_requests(self, threshold_ms: float = 1000.0, limit: int = 10) -> list:
        """获取慢请求列表"""
        with self._lock:
            slow = [
                {
                    "method": r.method,
                    "path": r.path,
                    "status_code": r.status_code,
                    "duration_ms": round(r.duration_ms, 2),
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self._recent_requests
                if r.duration_ms >= threshold_ms
            ]
            return sorted(slow, key=lambda x: x["duration_ms"], reverse=True)[:limit]

    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._path_metrics.clear()
            self._recent_requests.clear()
            self._window_requests.clear()
            self._start_time = datetime.now()
        logger.info("API metrics reset")


# 全局单例
api_metrics = APIMetricsService()
