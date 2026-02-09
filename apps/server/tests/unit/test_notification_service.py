"""
测试 notification_service 模块

测试推送通知服务的核心功能
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from services.notification_service import (
    NotificationService,
    TelegramProvider,
    SIGNAL_PRIORITY,
    THRESHOLD_MIN_PRIORITY,
)


class TestSignalPriority:
    """测试信号优先级映射"""

    def test_signal_priority_values(self):
        """测试信号优先级数值"""
        assert SIGNAL_PRIORITY["STRONG_BUY"] == 5
        assert SIGNAL_PRIORITY["STRONG_SELL"] == 5
        assert SIGNAL_PRIORITY["BUY"] == 4
        assert SIGNAL_PRIORITY["SELL"] == 4
        assert SIGNAL_PRIORITY["HOLD"] == 3

    def test_threshold_min_priority(self):
        """测试阈值最低优先级"""
        assert THRESHOLD_MIN_PRIORITY["STRONG_BUY"] == 5
        assert THRESHOLD_MIN_PRIORITY["BUY"] == 4
        assert THRESHOLD_MIN_PRIORITY["ALL"] == 0


@pytest.mark.asyncio
class TestTelegramProvider:
    """测试 Telegram 推送提供商"""

    async def test_send_success(self):
        """测试成功发送消息"""
        provider = TelegramProvider(bot_token="test_token")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.send(
                channel_user_id="123456",
                title="测试标题",
                body="测试内容",
            )

            assert result is True
            mock_client.post.assert_called_once()

            # 验证请求参数
            call_args = mock_client.post.call_args
            assert "sendMessage" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["chat_id"] == "123456"
            assert "测试标题" in payload["text"]
            assert "测试内容" in payload["text"]
            assert payload["parse_mode"] == "Markdown"

    async def test_send_failure(self):
        """测试发送失败"""
        provider = TelegramProvider(bot_token="test_token")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"ok": False}
            mock_response.text = "Bad Request"
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.send(
                channel_user_id="123456",
                title="测试",
                body="内容",
            )

            assert result is False

    async def test_send_network_error(self):
        """测试网络错误"""
        provider = TelegramProvider(bot_token="test_token")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await provider.send(
                channel_user_id="123456",
                title="测试",
                body="内容",
            )

            assert result is False

    async def test_custom_api_base(self):
        """测试自定义 API 基础 URL"""
        custom_base = "https://custom.telegram.org"
        provider = TelegramProvider(
            bot_token="test_token",
            api_base=custom_base,
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await provider.send("123", "标题", "内容")

            call_args = mock_client.post.call_args
            assert custom_base in call_args[0][0]


class TestNotificationService:
    """测试通知服务"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        service1 = NotificationService()
        service2 = NotificationService()

        assert service1 is service2

    def test_should_notify_strong_buy_threshold(self):
        """测试 STRONG_BUY 阈值过滤"""
        service = NotificationService()

        # 创建配置 mock
        config = Mock()
        config.signal_threshold = "STRONG_BUY"

        # STRONG_BUY 应该通过
        assert service._should_notify(config, "STRONG_BUY") is True
        assert service._should_notify(config, "STRONG_SELL") is True

        # BUY/SELL/HOLD 不应该通过
        assert service._should_notify(config, "BUY") is False
        assert service._should_notify(config, "SELL") is False
        assert service._should_notify(config, "HOLD") is False

    def test_should_notify_buy_threshold(self):
        """测试 BUY 阈值过滤"""
        service = NotificationService()

        config = Mock()
        config.signal_threshold = "BUY"

        # STRONG_BUY/BUY/SELL/STRONG_SELL 应该通过
        assert service._should_notify(config, "STRONG_BUY") is True
        assert service._should_notify(config, "BUY") is True
        assert service._should_notify(config, "SELL") is True
        assert service._should_notify(config, "STRONG_SELL") is True

        # HOLD 不应该通过
        assert service._should_notify(config, "HOLD") is False

    def test_should_notify_all_threshold(self):
        """测试 ALL 阈值（所有信号）"""
        service = NotificationService()

        config = Mock()
        config.signal_threshold = "ALL"

        # 所有信号都应该通过
        assert service._should_notify(config, "STRONG_BUY") is True
        assert service._should_notify(config, "BUY") is True
        assert service._should_notify(config, "HOLD") is True
        assert service._should_notify(config, "SELL") is True
        assert service._should_notify(config, "STRONG_SELL") is True

    def test_is_in_quiet_hours_no_quiet_hours(self):
        """测试无静默时段"""
        service = NotificationService()

        config = Mock()
        config.quiet_hours_start = None
        config.quiet_hours_end = None

        assert service._is_in_quiet_hours(config) is False

    def test_is_in_quiet_hours_normal_range(self):
        """测试正常静默时段（不跨午夜）"""
        service = NotificationService()

        config = Mock()
        config.quiet_hours_start = 9  # 09:00
        config.quiet_hours_end = 18   # 18:00

        # Mock 当前时间
        with patch("services.notification_service.datetime") as mock_datetime:
            # 10:00 - 在静默时段内
            mock_datetime.now.return_value = Mock(hour=10)
            assert service._is_in_quiet_hours(config) is True

            # 08:00 - 不在静默时段
            mock_datetime.now.return_value = Mock(hour=8)
            assert service._is_in_quiet_hours(config) is False

            # 19:00 - 不在静默时段
            mock_datetime.now.return_value = Mock(hour=19)
            assert service._is_in_quiet_hours(config) is False

    def test_is_in_quiet_hours_cross_midnight(self):
        """测试跨午夜静默时段"""
        service = NotificationService()

        config = Mock()
        config.quiet_hours_start = 22  # 22:00
        config.quiet_hours_end = 8     # 08:00

        with patch("services.notification_service.datetime") as mock_datetime:
            # 23:00 - 在静默时段内
            mock_datetime.now.return_value = Mock(hour=23)
            assert service._is_in_quiet_hours(config) is True

            # 02:00 - 在静默时段内
            mock_datetime.now.return_value = Mock(hour=2)
            assert service._is_in_quiet_hours(config) is True

            # 10:00 - 不在静默时段
            mock_datetime.now.return_value = Mock(hour=10)
            assert service._is_in_quiet_hours(config) is False

    @pytest.mark.asyncio
    async def test_send_test_notification(self):
        """测试发送测试通知"""
        service = NotificationService()

        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.send.return_value = True
        service._providers["telegram"] = mock_provider

        # Mock 数据库
        with patch("services.notification_service.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session

            result = await service.send_test(
                user_id=1,
                channel="telegram",
                channel_user_id="123456",
            )

            assert result is True
            mock_provider.send.assert_called_once()

            # 验证日志记录
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_no_provider(self):
        """测试发送测试通知时提供商不存在"""
        service = NotificationService()
        service._providers = {}  # 清空提供商

        result = await service.send_test(
            user_id=1,
            channel="nonexistent",
            channel_user_id="123456",
        )

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
