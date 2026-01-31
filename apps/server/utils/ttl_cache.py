"""
TTLCache - 统一的内存 TTL 缓存工具

替代各服务中散落的 _cache + _cache_time 双字典模式，
提供线程安全的本地缓存，适用于单实例部署。

用法:
    cache = TTLCache(default_ttl=600)
    cache.set("key", value)
    result = cache.get("key")  # 过期自动返回 None
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, TypeVar

T = TypeVar("T")


class TTLCache:
    """线程安全的内存 TTL 缓存"""

    def __init__(self, default_ttl: int = 300):
        """
        Args:
            default_ttl: 默认过期时间（秒）
        """
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，过期返回 None"""
        with self._lock:
            if key not in self._expiry:
                return None
            if time.monotonic() > self._expiry[key]:
                # 惰性清理
                del self._data[key]
                del self._expiry[key]
                return None
            return self._data.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            self._data[key] = value
            self._expiry[key] = time.monotonic() + (ttl or self._default_ttl)

    def is_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        with self._lock:
            if key not in self._expiry:
                return False
            return time.monotonic() <= self._expiry[key]

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            existed = key in self._data
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return existed

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._data.clear()
            self._expiry.clear()

    def size(self) -> int:
        """返回（可能包含过期项的）缓存条目数"""
        return len(self._data)
