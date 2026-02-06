"""Sentiment Agent 工具测试

测试 search_retail_sentiment 和 get_fear_greed_index 的真实数据获取。
"""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestSearchRetailSentiment:
    """测试散户情绪搜索"""

    def test_returns_json_string(self):
        """应返回有效的 JSON 字符串"""
        from tradingagents.dataflows.sentiment_data import search_retail_sentiment

        with patch("tradingagents.dataflows.sentiment_data._get_ddgs") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Test", "body": "Test body", "href": "https://example.com"}
            ]
            mock_ddgs.return_value = mock_instance

            result = search_retail_sentiment("NVDA")
            data = json.loads(result)

            assert "discussions" in data
            assert "query" in data
            assert data["query"] == "NVDA"

    def test_chinese_stock_uses_chinese_queries(self):
        """A股应使用中文搜索查询"""
        from tradingagents.dataflows.sentiment_data import search_retail_sentiment

        with patch("tradingagents.dataflows.sentiment_data._get_ddgs") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance

            search_retail_sentiment("000001.SZ")

            # 验证搜索查询包含中文
            calls = mock_instance.text.call_args_list
            assert len(calls) > 0
            first_query = calls[0][0][0]
            assert "散户" in first_query or "股吧" in first_query

    def test_platform_filter(self):
        """应支持平台筛选"""
        from tradingagents.dataflows.sentiment_data import search_retail_sentiment

        with patch("tradingagents.dataflows.sentiment_data._get_ddgs") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = []
            mock_ddgs.return_value = mock_instance

            result = search_retail_sentiment("AAPL", platform="reddit")
            data = json.loads(result)
            assert data["platform"] == "reddit"

    def test_deduplicates_results(self):
        """应去重搜索结果"""
        from tradingagents.dataflows.sentiment_data import search_retail_sentiment

        with patch("tradingagents.dataflows.sentiment_data._get_ddgs") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Test", "body": "Body", "href": "https://example.com/1"},
                {"title": "Test2", "body": "Body2", "href": "https://example.com/1"},  # 重复
                {"title": "Test3", "body": "Body3", "href": "https://example.com/2"},
            ]
            mock_ddgs.return_value = mock_instance

            result = search_retail_sentiment("AAPL")
            data = json.loads(result)
            assert data["results_count"] <= 2  # 去重后最多 2 个

    def test_handles_search_failure(self):
        """搜索失败应返回错误 JSON"""
        from tradingagents.dataflows.sentiment_data import search_retail_sentiment

        with patch("tradingagents.dataflows.sentiment_data._get_ddgs") as mock_ddgs:
            mock_ddgs.side_effect = Exception("Search failed")

            result = search_retail_sentiment("AAPL")
            data = json.loads(result)
            assert "error" in data

    def test_caching(self):
        """应缓存搜索结果"""
        from tradingagents.dataflows.sentiment_data import (
            search_retail_sentiment,
            _cache,
        )

        # 清除缓存
        _cache.clear()

        with patch("tradingagents.dataflows.sentiment_data._get_ddgs") as mock_ddgs:
            mock_instance = MagicMock()
            mock_instance.text.return_value = [
                {"title": "Test", "body": "Body", "href": "https://example.com"}
            ]
            mock_ddgs.return_value = mock_instance

            # 第一次调用
            search_retail_sentiment("CACHE_TEST")
            # 第二次调用应使用缓存
            search_retail_sentiment("CACHE_TEST")

            # text 只应被调用一次（第二次使用缓存）
            # 注意：由于有两个搜索查询，第一次调用会调用 text 两次
            call_count = mock_instance.text.call_count
            assert call_count == 2  # 两个搜索查询，但只在第一次调用时


class TestGetFearGreedIndex:
    """测试恐惧贪婪指数"""

    def test_returns_json_string(self):
        """应返回有效的 JSON 字符串"""
        from tradingagents.dataflows.sentiment_data import get_fear_greed_index

        # 清除缓存
        from tradingagents.dataflows.sentiment_data import _cache
        _cache.clear()

        with patch("tradingagents.dataflows.sentiment_data._get_cn_sentiment") as mock_cn, \
             patch("tradingagents.dataflows.sentiment_data._get_us_fear_greed") as mock_us:
            mock_cn.return_value = None
            mock_us.return_value = None

            # 使用搜索降级
            with patch("tradingagents.dataflows.sentiment_data._get_fear_greed_via_search") as mock_search:
                mock_search.return_value = {"source": "search_fallback", "results": []}

                result = get_fear_greed_index("US")
                data = json.loads(result)
                assert "market" in data

    def test_cn_market(self):
        """CN 市场应尝试获取 A 股情绪"""
        from tradingagents.dataflows.sentiment_data import get_fear_greed_index, _cache
        _cache.clear()

        with patch("tradingagents.dataflows.sentiment_data._get_cn_sentiment") as mock_cn:
            mock_cn.return_value = {
                "market": "CN",
                "sentiment_score": 65,
                "sentiment_label": "Greed",
                "indicators": [{"name": "涨跌家数比", "value": 2.1}],
            }

            result = get_fear_greed_index("CN")
            data = json.loads(result)
            assert "cn_sentiment" in data
            assert data["cn_sentiment"]["sentiment_score"] == 65

    def test_handles_failure(self):
        """获取失败应返回错误 JSON"""
        from tradingagents.dataflows.sentiment_data import get_fear_greed_index, _cache
        _cache.clear()

        with patch("tradingagents.dataflows.sentiment_data._get_cn_sentiment") as mock_cn, \
             patch("tradingagents.dataflows.sentiment_data._get_us_fear_greed") as mock_us, \
             patch("tradingagents.dataflows.sentiment_data._get_fear_greed_via_search") as mock_search:
            mock_cn.side_effect = Exception("Failed")
            mock_us.side_effect = Exception("Failed")
            mock_search.side_effect = Exception("Failed")

            result = get_fear_greed_index("auto")
            data = json.loads(result)
            assert "error" in data


class TestExtractSource:
    """测试 URL 来源提取"""

    def test_known_sources(self):
        from tradingagents.dataflows.sentiment_data import _extract_source

        assert _extract_source("https://www.reddit.com/r/stocks") == "Reddit"
        assert _extract_source("https://xueqiu.com/123") == "雪球"
        assert _extract_source("https://guba.eastmoney.com/123") == "东方财富股吧"
        assert _extract_source("https://x.com/user") == "Twitter/X"

    def test_unknown_source(self):
        from tradingagents.dataflows.sentiment_data import _extract_source

        assert _extract_source("https://unknown.com") == "Web"
        assert _extract_source("") == "unknown"


class TestScoreToLabel:
    """测试分数转标签"""

    def test_labels(self):
        from tradingagents.dataflows.sentiment_data import _score_to_label

        assert _score_to_label(90) == "Extreme Greed"
        assert _score_to_label(65) == "Greed"
        assert _score_to_label(50) == "Neutral"
        assert _score_to_label(25) == "Fear"
        assert _score_to_label(10) == "Extreme Fear"
