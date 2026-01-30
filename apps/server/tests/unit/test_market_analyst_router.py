"""
MarketAnalystRouter 单元测试

测试市场检测、分析师选择和配置逻辑。
"""

import pytest
from services.market_analyst_router import (
    Market,
    AnalystType,
    MarketAnalystRouter,
    MARKET_ANALYST_PRESETS,
)


class TestMarketDetection:
    """市场检测测试"""

    def test_detect_a_share_sh_suffix(self):
        """测试上海 A股代码检测 (.SH 后缀)"""
        assert MarketAnalystRouter.detect_market("600519.SH") == Market.CN
        assert MarketAnalystRouter.detect_market("601318.SH") == Market.CN

    def test_detect_a_share_sz_suffix(self):
        """测试深圳 A股代码检测 (.SZ 后缀)"""
        assert MarketAnalystRouter.detect_market("000001.SZ") == Market.CN
        assert MarketAnalystRouter.detect_market("300750.SZ") == Market.CN

    def test_detect_a_share_ss_suffix(self):
        """测试 Yahoo Finance 格式 A股代码 (.SS 后缀)"""
        assert MarketAnalystRouter.detect_market("600519.SS") == Market.CN

    def test_detect_a_share_pure_number(self):
        """测试纯数字 6 位 A股代码（无后缀）"""
        # 6/9 开头 -> 上海
        assert MarketAnalystRouter.detect_market("600519") == Market.CN
        # 0/3 开头 -> 深圳
        assert MarketAnalystRouter.detect_market("000001") == Market.CN
        assert MarketAnalystRouter.detect_market("300750") == Market.CN

    def test_detect_hk_stock_suffix(self):
        """测试港股代码检测 (.HK 后缀)"""
        assert MarketAnalystRouter.detect_market("00700.HK") == Market.HK
        assert MarketAnalystRouter.detect_market("09988.HK") == Market.HK

    def test_detect_hk_stock_pure_number(self):
        """测试纯数字 5 位港股代码（无后缀）"""
        assert MarketAnalystRouter.detect_market("00700") == Market.HK
        assert MarketAnalystRouter.detect_market("09988") == Market.HK

    def test_detect_us_stock(self):
        """测试美股代码检测"""
        assert MarketAnalystRouter.detect_market("AAPL") == Market.US
        assert MarketAnalystRouter.detect_market("TSLA") == Market.US
        assert MarketAnalystRouter.detect_market("NVDA") == Market.US

    def test_detect_case_insensitive(self):
        """测试大小写不敏感"""
        assert MarketAnalystRouter.detect_market("600519.sh") == Market.CN
        assert MarketAnalystRouter.detect_market("aapl") == Market.US
        assert MarketAnalystRouter.detect_market("00700.hk") == Market.HK


class TestAnalystSelection:
    """分析师选择测试"""

    def test_cn_market_analysts(self):
        """测试 A股市场分析师配置"""
        analysts = MarketAnalystRouter.get_analysts("600519.SH")

        # 必须包含基础分析师
        assert "market" in analysts
        assert "fundamentals" in analysts
        assert "news" in analysts
        assert "social" in analysts

        # 必须包含 A股特有分析师
        assert "sentiment" in analysts
        assert "policy" in analysts
        assert "fund_flow" in analysts

        # 总共 7 个
        assert len(analysts) == 7

    def test_hk_market_analysts(self):
        """测试港股市场分析师配置"""
        analysts = MarketAnalystRouter.get_analysts("00700.HK")

        # 必须包含基础分析师
        assert "market" in analysts
        assert "fundamentals" in analysts
        assert "news" in analysts
        assert "social" in analysts

        # 仅包含 sentiment（港股受 A股情绪影响）
        assert "sentiment" in analysts

        # 不应包含 A股特有
        assert "policy" not in analysts
        assert "fund_flow" not in analysts

        # 总共 5 个
        assert len(analysts) == 5

    def test_us_market_analysts(self):
        """测试美股市场分析师配置"""
        analysts = MarketAnalystRouter.get_analysts("AAPL")

        # 仅基础分析师
        assert "market" in analysts
        assert "fundamentals" in analysts
        assert "news" in analysts
        assert "social" in analysts

        # 不应包含高级分析师
        assert "sentiment" not in analysts
        assert "policy" not in analysts
        assert "fund_flow" not in analysts

        # 总共 4 个
        assert len(analysts) == 4

    def test_override_analysts(self):
        """测试完全覆盖分析师配置"""
        custom = ["market", "news"]
        analysts = MarketAnalystRouter.get_analysts("600519.SH", override_analysts=custom)

        assert analysts == custom

    def test_exclude_analysts(self):
        """测试排除分析师"""
        analysts = MarketAnalystRouter.get_analysts(
            "600519.SH",
            exclude_analysts=["policy", "fund_flow"]
        )

        # 应该排除指定的
        assert "policy" not in analysts
        assert "fund_flow" not in analysts

        # 其他应保留
        assert "market" in analysts
        assert "sentiment" in analysts

    def test_include_analysts(self):
        """测试添加额外分析师"""
        analysts = MarketAnalystRouter.get_analysts(
            "AAPL",
            include_analysts=["sentiment", "policy"]
        )

        # 基础 + 额外添加
        assert "market" in analysts
        assert "sentiment" in analysts
        assert "policy" in analysts

    def test_invalid_analysts_filtered(self):
        """测试无效分析师被过滤"""
        analysts = MarketAnalystRouter.get_analysts(
            "AAPL",
            override_analysts=["market", "invalid_analyst", "news"]
        )

        assert "market" in analysts
        assert "news" in analysts
        assert "invalid_analyst" not in analysts


class TestMarketConfig:
    """市场配置测试"""

    def test_get_market_config_cn(self):
        """测试获取 A股市场配置"""
        config = MarketAnalystRouter.get_market_config("600519.SH")

        assert config["market"] == "CN"
        assert config["symbol"] == "600519.SH"
        assert len(config["analysts"]) == 7
        assert "all_available_analysts" in config

    def test_get_available_analysts(self):
        """测试获取所有可用分析师"""
        available = MarketAnalystRouter.get_available_analysts()

        assert len(available) == len(AnalystType)

        # 检查必要字段
        for analyst in available:
            assert "name" in analyst
            assert "display_name" in analyst
            assert "description" in analyst
            assert "markets" in analyst


class TestAnalystsByMarket:
    """get_analysts_by_market 方法测试"""

    def test_get_by_market_cn(self):
        """测试通过 Market 枚举获取 A股分析师"""
        analysts = MarketAnalystRouter.get_analysts_by_market(Market.CN)
        assert len(analysts) == 7
        assert "policy" in analysts
        assert "fund_flow" in analysts

    def test_get_by_market_hk(self):
        """测试通过 Market 枚举获取港股分析师"""
        analysts = MarketAnalystRouter.get_analysts_by_market(Market.HK)
        assert len(analysts) == 5
        assert "sentiment" in analysts

    def test_get_by_market_us(self):
        """测试通过 Market 枚举获取美股分析师"""
        analysts = MarketAnalystRouter.get_analysts_by_market(Market.US)
        assert len(analysts) == 4

    def test_get_by_market_unknown(self):
        """测试未知市场使用默认配置"""
        analysts = MarketAnalystRouter.get_analysts_by_market(Market.UNKNOWN)
        assert len(analysts) == 4  # 基础分析师


class TestPresets:
    """预设配置测试"""

    def test_all_markets_have_presets(self):
        """测试所有市场类型都有预设配置"""
        for market in Market:
            assert market in MARKET_ANALYST_PRESETS

    def test_presets_have_required_fields(self):
        """测试预设配置包含必要字段"""
        for market, config in MARKET_ANALYST_PRESETS.items():
            assert config.analysts, f"{market} missing analysts"
            assert config.description, f"{market} missing description"
