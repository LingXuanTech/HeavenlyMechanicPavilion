"""LangSmith 可观测性服务

提供 LangSmith 追踪、Token 消耗监控和性能分析能力。
"""

import os
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# 延迟导入
_client = None
_enabled = None


class LangSmithService:
    """LangSmith 可观测性服务（单例）"""

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
        self._client = None
        self._enabled = False
        self._init_langsmith()

    def _init_langsmith(self):
        """初始化 LangSmith 客户端"""
        try:
            from config.settings import settings

            self._enabled = settings.LANGSMITH_ENABLED

            if not self._enabled:
                logger.info("LangSmith tracing disabled")
                return

            if not settings.LANGSMITH_API_KEY:
                logger.warning("LANGSMITH_API_KEY not set, disabling LangSmith")
                self._enabled = False
                return

            # 设置环境变量供 LangSmith SDK 和 LangChain 读取
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT

            # 创建客户端
            try:
                from langsmith import Client
                self._client = Client(
                    api_key=settings.LANGSMITH_API_KEY,
                    api_url=settings.LANGSMITH_ENDPOINT
                )

                # 验证连接
                self._client.list_projects(limit=1)

                logger.info(
                    "LangSmith initialized successfully",
                    project=settings.LANGSMITH_PROJECT,
                    endpoint=settings.LANGSMITH_ENDPOINT,
                )

            except ImportError:
                logger.warning("langsmith package not installed")
                self._enabled = False

            except Exception as e:
                logger.error("Failed to connect to LangSmith", error=str(e))
                self._enabled = False

        except Exception as e:
            logger.error("Failed to initialize LangSmith", error=str(e))
            self._enabled = False

    def is_enabled(self) -> bool:
        """检查 LangSmith 是否启用"""
        return self._enabled

    def get_client(self):
        """获取 LangSmith 客户端"""
        return self._client if self._enabled else None

    def get_status(self) -> dict:
        """获取 LangSmith 状态"""
        try:
            from config.settings import settings
            return {
                "enabled": self._enabled,
                "project": settings.LANGSMITH_PROJECT if self._enabled else None,
                "endpoint": settings.LANGSMITH_ENDPOINT if self._enabled else None,
                "status": "connected" if self._enabled and self._client else "disabled",
            }
        except Exception:
            return {
                "enabled": False,
                "status": "error",
            }

    def refresh(self):
        """刷新 LangSmith 连接"""
        self._initialized = False
        self._client = None
        self._enabled = False
        self._init_langsmith()
        return self.get_status()


# 全局单例
langsmith_service = LangSmithService()
