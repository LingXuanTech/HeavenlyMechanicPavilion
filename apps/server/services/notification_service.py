"""
推送通知服务

支持多渠道通知(当前实现 Telegram),包含:
- 信号阈值过滤
- 静默时段检查(支持跨午夜)
- 发送日志记录
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import httpx
import structlog
from sqlmodel import Session, select

from config.settings import settings
from db.models import NotificationConfig, NotificationLog, get_engine

logger = structlog.get_logger()

# 信号优先级映射(数值越高越重要)
SIGNAL_PRIORITY = {
    "STRONG_BUY": 5,
    "STRONG_SELL": 5,
    "BUY": 4,
    "SELL": 4,
    "HOLD": 3,
}

# 阈值对应的最低优先级
THRESHOLD_MIN_PRIORITY = {
    "STRONG_BUY": 5,  # 仅 STRONG_BUY / STRONG_SELL
    "BUY": 4,         # BUY/SELL 及以上
    "ALL": 0,          # 所有信号
}

# 信号展示 emoji
SIGNAL_EMOJI = {
    "STRONG_BUY": "🚀",
    "BUY": "📈",
    "HOLD": "⏸️",
    "SELL": "📉",
    "STRONG_SELL": "🔻",
}


class NotificationProvider(ABC):
    """通知渠道抽象基类"""

    @abstractmethod
    async def send(self, channel_user_id: str, title: str, body: str) -> bool:
        """发送通知,返回是否成功"""
        ...


class TelegramProvider(NotificationProvider):
    """Telegram Bot API 推送"""

    def __init__(self, bot_token: str, api_base: str = "https://api.telegram.org"):
        self._bot_token = bot_token
        self._api_base = api_base.rstrip("/")

    async def send(self, channel_user_id: str, title: str, body: str) -> bool:
        url = f"{self._api_base}/bot{self._bot_token}/sendMessage"
        text = f"*{title}*\n\n{body}"
        payload = {
            "chat_id": channel_user_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200 and resp.json().get("ok"):
                    return True
                logger.warning(
                    "Telegram send failed",
                    status=resp.status_code,
                    response=resp.text[:200],
                )
                return False
        except Exception as e:
            logger.error("Telegram send error", error=str(e))
            return False


class NotificationService:
    """推送通知服务(单例)"""

    _instance: Optional["NotificationService"] = None

    def __new__(cls) -> "NotificationService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._providers: dict[str, NotificationProvider] = {}
        self._engine = get_engine()

        # 注册 Telegram provider(如果配置了 token)
        if settings.TELEGRAM_BOT_TOKEN:
            self._providers["telegram"] = TelegramProvider(
                bot_token=settings.TELEGRAM_BOT_TOKEN,
                api_base=settings.TELEGRAM_API_BASE,
            )
            logger.info("Telegram notification provider registered")

        self._initialized = True

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def notify_analysis_complete(
        self,
        symbol: str,
        signal: str,
        confidence: int,
        summary: str,
    ) -> int:
        """
        分析完成后触发通知

        Returns:
            成功发送的通知数量
        """
        with Session(self._engine) as session:
            configs = session.exec(
                select(NotificationConfig).where(NotificationConfig.is_enabled == True)  # noqa: E712
            ).all()

        sent_count = 0
        for config in configs:
            if not self._should_notify(config, signal):
                continue
            if self._is_in_quiet_hours(config):
                logger.debug("Skipped notification (quiet hours)", user_id=config.user_id)
                continue

            provider = self._providers.get(config.channel)
            if not provider:
                logger.warning("No provider for channel", channel=config.channel)
                continue
            if not config.channel_user_id:
                continue

            title, body = self._format_analysis_message(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                summary=summary,
            )

            delivered = await provider.send(config.channel_user_id, title, body)
            self._write_log(config, title, body, signal, symbol, delivered)

            if delivered:
                sent_count += 1

        return sent_count

    async def send_test(self, user_id: int, channel: str, channel_user_id: str) -> bool:
        """发送测试通知"""
        provider = self._providers.get(channel)
        if not provider:
            logger.warning("Test notification: no provider", channel=channel)
            return False

        title = "🔔 测试通知"
        body = "天机阁推送通知配置成功!"
        delivered = await provider.send(channel_user_id, title, body)

        # 记录日志
        with Session(self._engine) as session:
            log = NotificationLog(
                user_id=user_id,
                channel=channel,
                title=title,
                body=body,
                delivered=delivered,
            )
            session.add(log)
            session.commit()

        return delivered

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _should_notify(self, config: NotificationConfig, signal: str) -> bool:
        """检查信号是否达到用户配置的阈值"""
        signal_prio = SIGNAL_PRIORITY.get(signal.upper(), 0)
        threshold_min = THRESHOLD_MIN_PRIORITY.get(config.signal_threshold, 0)
        return signal_prio >= threshold_min

    @staticmethod
    def _is_in_quiet_hours(config: NotificationConfig) -> bool:
        """检查当前是否在静默时段(支持跨午夜,如 22:00-08:00)"""
        if config.quiet_hours_start is None or config.quiet_hours_end is None:
            return False

        current_hour = datetime.now().hour
        start = config.quiet_hours_start
        end = config.quiet_hours_end

        if start <= end:
            # 不跨午夜:如 09:00-18:00
            return start <= current_hour < end
        else:
            # 跨午夜:如 22:00-08:00
            return current_hour >= start or current_hour < end

    @staticmethod
    def _format_analysis_message(
        symbol: str,
        signal: str,
        confidence: int,
        summary: str,
    ) -> tuple[str, str]:
        """构建统一的分析完成通知文案"""
        normalized_signal = signal.upper()
        signal_emoji = SIGNAL_EMOJI.get(normalized_signal, "📊")
        title = f"{signal_emoji} {symbol} 分析完成"

        body_lines = [
            f"📌 股票: `{symbol}`",
            f"🎯 信号: {signal}",
            f"📊 置信度: {confidence}%",
            "",
            summary[:300],
            "",
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ]
        body = "\n".join(body_lines)
        return title, body

    def _write_log(
        self,
        config: NotificationConfig,
        title: str,
        body: str,
        signal: str | None,
        symbol: str | None,
        delivered: bool,
        error: str | None = None,
    ) -> None:
        """写入发送日志"""
        with Session(self._engine) as session:
            log = NotificationLog(
                user_id=config.user_id,
                channel=config.channel,
                title=title,
                body=body,
                signal=signal,
                symbol=symbol,
                delivered=delivered,
                error=error,
            )
            session.add(log)
            session.commit()


# 全局单例
notification_service = NotificationService()
