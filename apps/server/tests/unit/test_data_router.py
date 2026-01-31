"""
MarketRouter 单元测试

测试内容：
1. 市场识别逻辑 (get_market)
2. 数据源优先级选择
3. 价格获取与降级机制
4. 缓存行为
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from services.data_router import MarketRouter, _price_cache
from api.exceptions import DataSourceError


class TestMarketIdentification:
    """测试市场识别逻辑"""

    @pytest.mark.parametrize("symbol,expected_market", [
        # A股 - 上交所
        ("600519.SH", "CN"),
        ("601318.sh", "CN"),  # 小写测试
        # A股 - 深交所
        ("000001.SZ", "CN"),
        ("300750.sz", "CN"),
        # 港股
        ("0700.HK", "HK"),
        ("9988.hk", "HK"),
        # 美股
        ("AAPL", "US"),
        ("GOOGL", "US"),
        ("TSLA", "US"),
        # 无后缀默认美股
        ("MSFT", "US"),
        ("AMZN", "US"),
    ])
    def test_get_market_identification(self, symbol: str, expected_market: str):
        """验证各类股票代码能正确识别市场"""
        assert MarketRouter.get_market(symbol) == expected_market

    def test_get_providers_for_market(self):
        """验证各市场的数据源优先级"""
        assert MarketRouter._get_providers_for_market("CN") == ["akshare", "yfinance"]
        assert MarketRouter._get_providers_for_market("HK") == ["yfinance", "akshare"]
        assert MarketRouter._get_providers_for_market("US") == ["yfinance", "alpha_vantage"]
        # 未知市场降级到 yfinance
        assert MarketRouter._get_providers_for_market("UNKNOWN") == ["yfinance"]


class TestPriceCache:
    """测试价格缓存行为"""

    def test_cache_set_and_get(self, sample_stock_price, clear_price_cache):
        """测试缓存设置和获取"""
        MarketRouter._set_cached_price("AAPL", sample_stock_price)
        cached = MarketRouter._get_cached_price("AAPL")
        assert cached is not None
        assert cached.price == sample_stock_price.price

    def test_cache_expiry(self, sample_stock_price, clear_price_cache):
        """测试缓存过期"""
        MarketRouter._set_cached_price("AAPL", sample_stock_price)

        # 模拟缓存过期
        _price_cache["AAPL"] = (sample_stock_price, datetime.now() - timedelta(seconds=120))

        cached = MarketRouter._get_cached_price("AAPL")
        assert cached is None

    def test_cache_miss(self, clear_price_cache):
        """测试缓存未命中"""
        cached = MarketRouter._get_cached_price("NONEXISTENT")
        assert cached is None


class TestYFinanceProvider:
    """测试 yfinance 数据源"""

    @pytest.mark.asyncio
    async def test_get_price_yfinance_success(self, mock_yfinance):
        """yfinance 成功获取价格"""
        price = await MarketRouter._get_price_yfinance("AAPL", "US")

        assert price.symbol == "AAPL"
        assert price.price == 150.0
        assert price.market == "US"
        mock_yfinance.Ticker.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_price_yfinance_no_data(self):
        """yfinance 无数据时抛出错误"""
        with patch("services.data_router.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.fast_info = {"last_price": None}
            mock_yf.Ticker.return_value = mock_ticker

            with pytest.raises(DataSourceError) as exc_info:
                await MarketRouter._get_price_yfinance("INVALID", "US")

            assert exc_info.value.source == "yfinance"

    @pytest.mark.asyncio
    async def test_get_price_yfinance_exception(self):
        """yfinance 异常时正确包装错误"""
        with patch("services.data_router.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")

            with pytest.raises(DataSourceError) as exc_info:
                await MarketRouter._get_price_yfinance("AAPL", "US")

            assert "Network error" in str(exc_info.value)


class TestAkShareProvider:
    """测试 AkShare 数据源"""

    @pytest.mark.asyncio
    async def test_get_price_akshare_success(self, mock_akshare):
        """AkShare 成功获取 A 股价格"""
        price = await MarketRouter._get_price_akshare("600519.SH")

        assert price.symbol == "600519.SH"
        assert price.price == 1800.0
        assert price.market == "CN"

    @pytest.mark.asyncio
    async def test_get_price_akshare_not_found(self):
        """AkShare 股票代码不存在时抛出错误"""
        with patch("services.data_router.ak") as mock_ak:
            mock_ak.stock_zh_a_spot_em.return_value = pd.DataFrame({
                "代码": ["600519"],
                "最新价": [1800.0],
                "涨跌额": [20.0],
                "涨跌幅": [1.12],
                "成交量": [5000000],
            })

            with pytest.raises(DataSourceError) as exc_info:
                await MarketRouter._get_price_akshare("999999.SH")

            assert exc_info.value.source == "akshare"
            assert "not found" in str(exc_info.value).lower()


class TestAlphaVantageProvider:
    """测试 Alpha Vantage 数据源"""

    @pytest.mark.asyncio
    async def test_get_price_alpha_vantage_no_api_key(self):
        """Alpha Vantage 无 API Key 时抛出错误"""
        with patch("services.data_router.settings") as mock_settings:
            mock_settings.ALPHA_VANTAGE_API_KEY = None

            with pytest.raises(DataSourceError) as exc_info:
                await MarketRouter._get_price_alpha_vantage("AAPL")

            assert "API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_price_alpha_vantage_success(self):
        """Alpha Vantage 成功获取价格"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Global Quote": {
                "05. price": "150.00",
                "08. previous close": "148.00",
                "10. change percent": "1.35%",
                "06. volume": "50000000",
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("services.data_router.settings") as mock_settings:
            mock_settings.ALPHA_VANTAGE_API_KEY = "test-key"

            with patch("services.data_router.get_http_client", return_value=mock_client):
                price = await MarketRouter._get_price_alpha_vantage("AAPL")

                assert price.symbol == "AAPL"
                assert price.price == 150.0
                assert price.market == "US"


class TestFallbackMechanism:
    """测试数据源降级机制"""

    @pytest.mark.asyncio
    async def test_us_stock_fallback_to_alpha_vantage(self, clear_price_cache):
        """美股 yfinance 失败后降级到 Alpha Vantage"""
        with patch.object(MarketRouter, "_get_price_yfinance", side_effect=DataSourceError("yfinance", "Failed")):
            with patch.object(MarketRouter, "_get_price_alpha_vantage") as mock_av:
                from services.models import StockPrice
                mock_av.return_value = StockPrice(
                    symbol="AAPL",
                    price=150.0,
                    change=2.0,
                    change_percent=1.35,
                    volume=1000000,
                    timestamp=datetime.now(),
                    market="US",
                )

                price = await MarketRouter.get_stock_price("AAPL")

                assert price.symbol == "AAPL"
                mock_av.assert_called_once()

    @pytest.mark.asyncio
    async def test_cn_stock_fallback_to_yfinance(self, clear_price_cache):
        """A股 AkShare 失败后降级到 yfinance"""
        with patch.object(MarketRouter, "_get_price_akshare", side_effect=DataSourceError("akshare", "Failed")):
            with patch.object(MarketRouter, "_get_price_yfinance") as mock_yf:
                from services.models import StockPrice
                mock_yf.return_value = StockPrice(
                    symbol="600519.SH",
                    price=1800.0,
                    change=20.0,
                    change_percent=1.12,
                    volume=5000000,
                    timestamp=datetime.now(),
                    market="CN",
                )

                price = await MarketRouter.get_stock_price("600519.SH")

                assert price.symbol == "600519.SH"
                mock_yf.assert_called_once_with("600519.SH", "CN")

    @pytest.mark.asyncio
    async def test_all_providers_fail_uses_cache(self, sample_stock_price, clear_price_cache):
        """所有数据源失败时使用缓存"""
        # 先设置缓存
        MarketRouter._set_cached_price("AAPL", sample_stock_price)

        with patch.object(MarketRouter, "_get_price_yfinance", side_effect=DataSourceError("yfinance", "Failed")):
            with patch.object(MarketRouter, "_get_price_alpha_vantage", side_effect=DataSourceError("alpha_vantage", "Failed")):
                price = await MarketRouter.get_stock_price("AAPL")

                assert price.price == sample_stock_price.price

    @pytest.mark.asyncio
    async def test_all_providers_fail_no_cache_raises(self, clear_price_cache):
        """所有数据源失败且无缓存时抛出错误"""
        with patch.object(MarketRouter, "_get_price_yfinance", side_effect=DataSourceError("yfinance", "Failed")):
            with patch.object(MarketRouter, "_get_price_alpha_vantage", side_effect=DataSourceError("alpha_vantage", "Failed")):
                with pytest.raises(DataSourceError):
                    await MarketRouter.get_stock_price("AAPL")


class TestHistoryData:
    """测试历史 K 线数据获取"""

    @pytest.mark.asyncio
    async def test_get_history_cn_stock_akshare(self, mock_akshare):
        """A股优先使用 AkShare 获取历史数据"""
        klines = await MarketRouter.get_history("600519.SH")

        assert len(klines) > 0
        assert klines[0].close == 1800.0

    @pytest.mark.asyncio
    async def test_get_history_us_stock_yfinance(self, mock_yfinance):
        """美股使用 yfinance 获取历史数据"""
        import pandas as pd

        # Mock history 方法
        hist_data = pd.DataFrame({
            "Open": [148.0, 149.0, 150.0],
            "High": [151.0, 152.0, 153.0],
            "Low": [147.0, 148.0, 149.0],
            "Close": [150.0, 151.0, 152.0],
            "Volume": [1000000, 1100000, 1200000],
        }, index=pd.date_range(end=datetime.now(), periods=3))

        mock_yfinance.Ticker.return_value.history.return_value = hist_data

        klines = await MarketRouter.get_history("AAPL")

        assert len(klines) == 3
        mock_yfinance.Ticker.assert_called_with("AAPL")


class TestFundamentals:
    """测试基本面数据获取"""

    @pytest.mark.asyncio
    async def test_get_fundamentals(self, mock_yfinance):
        """获取公司基本面数据"""
        fundamentals = await MarketRouter.get_fundamentals("AAPL")

        assert fundamentals.symbol == "AAPL"
        assert fundamentals.name == "Apple Inc."
        assert fundamentals.sector == "Technology"
        assert fundamentals.pe_ratio == 25.5
