"""
MacroDataService 单元测试

覆盖:
1. 数据模型创建
2. 情绪计算
3. 概要生成
4. FRED 数据获取
5. VIX/DXY 获取
6. 宏观概览
7. 缓存机制
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from services.macro_service import (
    MacroDataService,
    MacroIndicator,
    MacroOverview,
    MacroImpact,
    MacroAnalysisResult,
    _macro_cache,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestMacroModels:
    """宏观数据模型测试"""

    def test_macro_indicator_creation(self):
        """创建 MacroIndicator"""
        indicator = MacroIndicator(
            name="联邦基金利率",
            value=5.25,
            previous_value=5.00,
            change=0.25,
            change_percent=5.0,
            unit="%",
            date="2026-02-01",
            source="FRED",
            trend="up",
        )

        assert indicator.name == "联邦基金利率"
        assert indicator.value == 5.25
        assert indicator.trend == "up"

    def test_macro_indicator_minimal(self):
        """创建最小 MacroIndicator"""
        indicator = MacroIndicator(
            name="Test",
            value=100.0,
            date="2026-02-01",
            source="Test",
        )

        assert indicator.previous_value is None
        assert indicator.change is None
        assert indicator.trend == "stable"

    def test_macro_overview_creation(self):
        """创建 MacroOverview"""
        overview = MacroOverview(
            fed_rate=MacroIndicator(
                name="联邦基金利率",
                value=5.25,
                date="2026-02-01",
                source="FRED",
            ),
            sentiment="Neutral",
            summary="当前宏观环境：联邦基金利率 5.25%",
            last_updated="2026-02-02T10:00:00",
        )

        assert overview.fed_rate.value == 5.25
        assert overview.sentiment == "Neutral"

    def test_macro_impact_creation(self):
        """创建 MacroImpact"""
        impact = MacroImpact(
            indicator="VIX",
            impact_level="High",
            direction="Bearish",
            reasoning="高 VIX 表明市场恐慌",
        )

        assert impact.impact_level == "High"
        assert impact.direction == "Bearish"

    def test_macro_analysis_result_creation(self):
        """创建 MacroAnalysisResult"""
        result = MacroAnalysisResult(
            overview=MacroOverview(),
            impacts=[],
            market_outlook="谨慎乐观",
            risk_factors=["通胀压力"],
            opportunities=["科技板块"],
        )

        assert result.market_outlook == "谨慎乐观"
        assert "通胀压力" in result.risk_factors


# =============================================================================
# 情绪计算测试
# =============================================================================

class TestCalculateSentiment:
    """情绪计算测试"""

    def test_bullish_sentiment_low_rate_high_gdp(self):
        """低利率 + 高 GDP = 利好"""
        overview = MacroOverview(
            fed_rate=MacroIndicator(name="FR", value=2.5, date="", source=""),
            gdp_growth=MacroIndicator(name="GDP", value=3.0, date="", source=""),
            unemployment=MacroIndicator(name="UE", value=3.5, date="", source=""),
            vix=MacroIndicator(name="VIX", value=12.0, date="", source=""),
        )

        sentiment = MacroDataService._calculate_sentiment(overview)

        assert sentiment == "Bullish"

    def test_bearish_sentiment_high_rate_negative_gdp(self):
        """高利率 + 负 GDP = 利空"""
        overview = MacroOverview(
            fed_rate=MacroIndicator(name="FR", value=6.0, date="", source=""),
            gdp_growth=MacroIndicator(name="GDP", value=-1.0, date="", source=""),
            unemployment=MacroIndicator(name="UE", value=7.0, date="", source=""),
            vix=MacroIndicator(name="VIX", value=30.0, date="", source=""),
        )

        sentiment = MacroDataService._calculate_sentiment(overview)

        assert sentiment == "Bearish"

    def test_neutral_sentiment_mixed_signals(self):
        """混合信号 = 中性"""
        overview = MacroOverview(
            fed_rate=MacroIndicator(name="FR", value=4.0, date="", source=""),  # 中等
            gdp_growth=MacroIndicator(name="GDP", value=1.5, date="", source=""),  # 中等
            unemployment=MacroIndicator(name="UE", value=5.0, date="", source=""),  # 中等
            vix=MacroIndicator(name="VIX", value=20.0, date="", source=""),  # 中等
        )

        sentiment = MacroDataService._calculate_sentiment(overview)

        assert sentiment == "Neutral"

    def test_sentiment_with_missing_indicators(self):
        """部分指标缺失"""
        overview = MacroOverview(
            fed_rate=MacroIndicator(name="FR", value=2.0, date="", source=""),
            # 其他为 None
        )

        sentiment = MacroDataService._calculate_sentiment(overview)

        # 只有一个利好信号，不足以判断为 Bullish
        assert sentiment == "Neutral"


# =============================================================================
# 概要生成测试
# =============================================================================

class TestGenerateSummary:
    """概要生成测试"""

    def test_summary_with_all_indicators(self):
        """包含所有指标的概要"""
        overview = MacroOverview(
            fed_rate=MacroIndicator(name="FR", value=5.25, date="", source=""),
            gdp_growth=MacroIndicator(name="GDP", value=2.5, date="", source=""),
            vix=MacroIndicator(name="VIX", value=18.0, date="", source=""),
        )

        summary = MacroDataService._generate_summary(overview)

        assert "联邦基金利率 5.25%" in summary
        assert "GDP增长 2.5%" in summary
        assert "VIX" in summary

    def test_summary_vix_levels(self):
        """VIX 级别描述"""
        # 低 VIX
        overview_low = MacroOverview(
            vix=MacroIndicator(name="VIX", value=12.0, date="", source=""),
        )
        summary_low = MacroDataService._generate_summary(overview_low)
        assert "低" in summary_low

        # 高 VIX
        overview_high = MacroOverview(
            vix=MacroIndicator(name="VIX", value=30.0, date="", source=""),
        )
        summary_high = MacroDataService._generate_summary(overview_high)
        assert "高" in summary_high

        # 中等 VIX
        overview_mid = MacroOverview(
            vix=MacroIndicator(name="VIX", value=18.0, date="", source=""),
        )
        summary_mid = MacroDataService._generate_summary(overview_mid)
        assert "中等" in summary_mid

    def test_summary_no_data(self):
        """无数据时的概要"""
        overview = MacroOverview()

        summary = MacroDataService._generate_summary(overview)

        assert "暂不可用" in summary


# =============================================================================
# FRED 数据获取测试
# =============================================================================

class TestFetchFredData:
    """FRED API 数据获取测试"""

    @pytest.mark.asyncio
    async def test_fetch_fred_no_api_key(self):
        """无 API Key 返回 None"""
        with patch("services.macro_service.settings") as mock_settings:
            mock_settings.FRED_API_KEY = None

            result = await MacroDataService._fetch_fred_data("FEDFUNDS")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_fred_success(self):
        """成功获取 FRED 数据"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [
                {"date": "2026-02-01", "value": "5.25"},
                {"date": "2026-01-01", "value": "5.00"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("services.macro_service.settings") as mock_settings:
            mock_settings.FRED_API_KEY = "test_api_key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.get.return_value = mock_response
                mock_client.return_value.__aenter__.return_value = mock_client_instance

                result = await MacroDataService._fetch_fred_data("FEDFUNDS")

        assert result is not None
        assert len(result) == 2
        assert result[0]["value"] == "5.25"

    @pytest.mark.asyncio
    async def test_fetch_fred_error(self):
        """FRED API 请求失败"""
        with patch("services.macro_service.settings") as mock_settings:
            mock_settings.FRED_API_KEY = "test_api_key"

            with patch("httpx.AsyncClient") as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.get.side_effect = Exception("Network error")
                mock_client.return_value.__aenter__.return_value = mock_client_instance

                result = await MacroDataService._fetch_fred_data("FEDFUNDS")

        assert result is None


# =============================================================================
# FRED 指标解析测试
# =============================================================================

class TestFetchFredIndicator:
    """FRED 指标解析测试"""

    @pytest.mark.asyncio
    async def test_fetch_indicator_success(self):
        """成功解析 FRED 指标"""
        mock_data = [
            {"date": "2026-02-01", "value": "5.25"},
            {"date": "2026-01-01", "value": "5.00"},
        ]

        with patch.object(MacroDataService, '_fetch_fred_data', return_value=mock_data):
            result = await MacroDataService._fetch_fred_indicator("fed_rate", "FEDFUNDS")

        assert result is not None
        assert result.value == 5.25
        assert result.previous_value == 5.00
        assert result.change == 0.25
        assert result.trend == "up"
        assert result.name == "联邦基金利率"
        assert result.unit == "%"

    @pytest.mark.asyncio
    async def test_fetch_indicator_no_data(self):
        """无数据返回 None"""
        with patch.object(MacroDataService, '_fetch_fred_data', return_value=None):
            result = await MacroDataService._fetch_fred_indicator("fed_rate", "FEDFUNDS")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_indicator_trend_down(self):
        """下降趋势"""
        mock_data = [
            {"date": "2026-02-01", "value": "4.75"},
            {"date": "2026-01-01", "value": "5.00"},
        ]

        with patch.object(MacroDataService, '_fetch_fred_data', return_value=mock_data):
            result = await MacroDataService._fetch_fred_indicator("fed_rate", "FEDFUNDS")

        assert result.trend == "down"

    @pytest.mark.asyncio
    async def test_fetch_indicator_missing_value(self):
        """处理缺失值"""
        mock_data = [
            {"date": "2026-02-01", "value": "."},  # FRED 用 "." 表示缺失
        ]

        with patch.object(MacroDataService, '_fetch_fred_data', return_value=mock_data):
            result = await MacroDataService._fetch_fred_indicator("fed_rate", "FEDFUNDS")

        assert result is not None
        assert result.value == 0


# =============================================================================
# VIX/DXY 获取测试
# =============================================================================

class TestFetchVixDxy:
    """VIX/DXY 获取测试"""

    @pytest.mark.asyncio
    async def test_fetch_vix_success(self):
        """成功获取 VIX"""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {
            "last_price": 18.5,
            "previous_close": 17.0,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await MacroDataService._fetch_vix()

        assert result is not None
        assert result.value == 18.5
        assert result.previous_value == 17.0
        assert result.trend == "up"  # 18.5 > 17.0 * 1.05

    @pytest.mark.asyncio
    async def test_fetch_vix_down_trend(self):
        """VIX 下降趋势"""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {
            "last_price": 15.0,
            "previous_close": 20.0,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await MacroDataService._fetch_vix()

        assert result.trend == "down"

    @pytest.mark.asyncio
    async def test_fetch_vix_error(self):
        """VIX 获取失败"""
        with patch("yfinance.Ticker", side_effect=Exception("API Error")):
            result = await MacroDataService._fetch_vix()

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_dxy_success(self):
        """成功获取 DXY"""
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {
            "last_price": 103.5,
            "previous_close": 103.0,
        }

        with patch("yfinance.Ticker", return_value=mock_ticker):
            result = await MacroDataService._fetch_dxy()

        assert result is not None
        assert result.value == 103.5
        assert result.name == "DXY (美元指数)"


# =============================================================================
# 宏观概览测试
# =============================================================================

class TestGetMacroOverview:
    """get_macro_overview() 测试"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """每个测试前清除缓存"""
        _macro_cache.clear()

    @pytest.mark.asyncio
    async def test_get_overview_from_cache(self):
        """从缓存获取概览"""
        cached_overview = MacroOverview(
            sentiment="Bullish",
            summary="Cached",
            last_updated="2026-02-02T10:00:00",
        )
        _macro_cache.set("macro_overview", cached_overview)

        result = await MacroDataService.get_macro_overview()

        assert result.summary == "Cached"

    @pytest.mark.asyncio
    async def test_get_overview_fresh(self):
        """获取新鲜数据"""
        mock_indicator = MacroIndicator(
            name="Test", value=5.0, date="2026-02-01", source="Test"
        )

        with patch.object(MacroDataService, '_fetch_fred_indicator', return_value=mock_indicator):
            with patch.object(MacroDataService, '_fetch_vix', return_value=mock_indicator):
                with patch.object(MacroDataService, '_fetch_dxy', return_value=mock_indicator):
                    result = await MacroDataService.get_macro_overview()

        assert result is not None
        assert result.last_updated != ""


# =============================================================================
# 缓存测试
# =============================================================================

class TestClearCache:
    """缓存清除测试"""

    def test_clear_cache(self):
        """清除缓存"""
        _macro_cache.set("test_key", "test_value")

        MacroDataService.clear_cache()

        assert _macro_cache.get("test_key") is None
