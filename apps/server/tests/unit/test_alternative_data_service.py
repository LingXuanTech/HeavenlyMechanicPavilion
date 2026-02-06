"""另类数据服务测试"""

import json
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


class TestAHPremiumService:
    """测试 AH 溢价服务"""

    def test_get_ah_premium_list_with_mock(self):
        """应返回 AH 溢价排行"""
        from services.alternative_data_service import ah_premium_service, _cache
        _cache.clear()

        mock_df = pd.DataFrame({
            "A股代码": ["600036", "601318"],
            "H股代码": ["03968", "02318"],
            "名称": ["招商银行", "中国平安"],
            "A股价格": [35.0, 50.0],
            "H股价格": [40.0, 55.0],
            "比价(A/H)": [1.1, 1.15],
        })

        with patch("services.alternative_data_service.ak") as mock_ak:
            mock_ak.stock_zh_ah_spot_em.return_value = mock_df

            result = ah_premium_service.get_ah_premium_list(limit=10)
            assert "stocks" in result
            assert "stats" in result
            assert len(result["stocks"]) == 2

    def test_get_ah_premium_list_empty(self):
        """空数据应返回空列表"""
        from services.alternative_data_service import ah_premium_service, _cache
        _cache.clear()

        with patch("services.alternative_data_service.ak") as mock_ak:
            mock_ak.stock_zh_ah_spot_em.return_value = pd.DataFrame()

            result = ah_premium_service.get_ah_premium_list()
            assert result.get("stocks") == [] or "error" in result

    def test_calculate_stats(self):
        """应正确计算统计数据"""
        from services.alternative_data_service import ah_premium_service

        stocks = [
            {"premium_pct": 50.0},
            {"premium_pct": 30.0},
            {"premium_pct": -10.0},
            {"premium_pct": 20.0},
        ]

        stats = ah_premium_service._calculate_stats(stocks)
        assert stats["avg_premium_pct"] == 22.5
        assert stats["max_premium_pct"] == 50.0
        assert stats["min_premium_pct"] == -10.0
        assert stats["discount_count"] == 1
        assert stats["premium_count"] == 3

    def test_generate_arbitrage_signal_high_premium(self):
        """高溢价应生成卖出信号"""
        from services.alternative_data_service import ah_premium_service

        current = {"premium_pct": 120, "premium_rate": 2.2}
        signal = ah_premium_service._generate_arbitrage_signal(current, [])
        assert "SELL" in signal["signal"]

    def test_generate_arbitrage_signal_discount(self):
        """折价应生成买入信号"""
        from services.alternative_data_service import ah_premium_service

        current = {"premium_pct": -25, "premium_rate": 0.75}
        signal = ah_premium_service._generate_arbitrage_signal(current, [])
        assert "BUY" in signal["signal"]

    def test_generate_arbitrage_signal_with_history(self):
        """有历史数据时应基于分位数判断"""
        from services.alternative_data_service import ah_premium_service

        current = {"premium_pct": 50, "premium_rate": 1.5}
        history = [{"date": f"2024-01-{i:02d}", "ratio": 1.0 + i * 0.01} for i in range(1, 61)]

        signal = ah_premium_service._generate_arbitrage_signal(current, history)
        assert "signal" in signal
        assert "percentile" in signal


class TestPatentService:
    """测试专利监控服务"""

    def test_get_patent_analysis(self):
        """应返回专利分析结果"""
        from services.alternative_data_service import patent_service, _cache
        _cache.clear()

        with patch.object(patent_service, "_search_patents") as mock_patents, \
             patch.object(patent_service, "_search_tech_trends") as mock_trends, \
             patch.object(patent_service, "_get_company_name", return_value="Test Corp"):
            mock_patents.return_value = [{"title": "Patent 1", "body": "Desc", "url": "http://example.com"}]
            mock_trends.return_value = [{"title": "Trend 1", "body": "Desc", "url": "http://example.com"}]

            result = patent_service.get_patent_analysis("AAPL")
            assert "patent_news" in result
            assert "tech_trends" in result
            assert len(result["patent_news"]) == 1

    def test_search_patents_handles_failure(self):
        """搜索失败应返回空列表"""
        from services.alternative_data_service import patent_service

        with patch("services.alternative_data_service.DDGS") as mock_ddgs_cls:
            mock_ddgs_cls.side_effect = ImportError("not installed")

            result = patent_service._search_patents("Test Corp")
            assert result == []
