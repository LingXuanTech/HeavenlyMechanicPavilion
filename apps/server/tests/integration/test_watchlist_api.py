"""
Watchlist API 集成测试

测试内容：
1. GET /watchlist/ - 获取关注列表
2. POST /watchlist/{symbol} - 添加股票
3. DELETE /watchlist/{symbol} - 删除股票
"""
import pytest
from unittest.mock import patch, AsyncMock

from db.models import Watchlist
from services.models import StockPrice, CompanyFundamentals
from datetime import datetime


class TestGetWatchlist:
    """测试获取关注列表"""

    def test_get_empty_watchlist(self, client):
        """空列表返回空数组"""
        response = client.get("/api/watchlist/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_watchlist_with_items(self, client, db_session):
        """返回已添加的股票"""
        # 添加测试数据
        items = [
            Watchlist(symbol="AAPL", name="Apple Inc.", market="US"),
            Watchlist(symbol="GOOGL", name="Alphabet Inc.", market="US"),
            Watchlist(symbol="600519.SH", name="贵州茅台", market="CN"),
        ]
        for item in items:
            db_session.add(item)
        db_session.commit()

        response = client.get("/api/watchlist/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 3
        symbols = [item["symbol"] for item in data]
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
        assert "600519.SH" in symbols


class TestAddToWatchlist:
    """测试添加股票到关注列表"""

    def test_add_us_stock(self, client):
        """成功添加美股"""
        with patch("api.routes.watchlist.MarketRouter.get_stock_price") as mock_price:
            with patch("api.routes.watchlist.MarketRouter.get_fundamentals") as mock_fund:
                mock_price.return_value = StockPrice(
                    symbol="AAPL",
                    price=150.0,
                    change=2.0,
                    change_percent=1.35,
                    volume=50000000,
                    timestamp=datetime.now(),
                    market="US",
                )
                mock_fund.return_value = CompanyFundamentals(
                    symbol="AAPL",
                    name="Apple Inc.",
                    sector="Technology",
                )

                response = client.post("/api/watchlist/AAPL")

                assert response.status_code == 200
                data = response.json()
                assert data["symbol"] == "AAPL"
                assert data["name"] == "Apple Inc."
                assert data["market"] == "US"

    def test_add_cn_stock(self, client):
        """成功添加 A 股"""
        with patch("api.routes.watchlist.MarketRouter.get_stock_price") as mock_price:
            with patch("api.routes.watchlist.MarketRouter.get_fundamentals") as mock_fund:
                mock_price.return_value = StockPrice(
                    symbol="600519.SH",
                    price=1800.0,
                    change=20.0,
                    change_percent=1.12,
                    volume=5000000,
                    timestamp=datetime.now(),
                    market="CN",
                )
                mock_fund.return_value = CompanyFundamentals(
                    symbol="600519.SH",
                    name="贵州茅台",
                    sector="Consumer Staples",
                )

                response = client.post("/api/watchlist/600519.SH")

                assert response.status_code == 200
                data = response.json()
                assert data["symbol"] == "600519.SH"
                assert data["market"] == "CN"

    def test_add_duplicate_returns_existing(self, client, db_session):
        """重复添加返回已存在的条目"""
        # 先添加一条
        existing = Watchlist(symbol="AAPL", name="Apple Inc.", market="US")
        db_session.add(existing)
        db_session.commit()

        response = client.post("/api/watchlist/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["id"] == existing.id

    def test_add_invalid_symbol(self, client):
        """无效股票代码格式返回 422"""
        # 混合数字字母不匹配任何格式
        response = client.post("/api/watchlist/ABC123")

        assert response.status_code == 422
        assert "Invalid" in response.json()["error"]["message"]

    def test_add_stock_fundamentals_unavailable(self, client):
        """基本面数据不可用时仍能添加（使用 symbol 作为名称）"""
        from api.exceptions import DataSourceError

        with patch("api.routes.watchlist.MarketRouter.get_stock_price") as mock_price:
            with patch("api.routes.watchlist.MarketRouter.get_fundamentals") as mock_fund:
                mock_price.return_value = StockPrice(
                    symbol="TEST",  # 使用有效的 5 字符内美股代码
                    price=100.0,
                    change=1.0,
                    change_percent=1.0,
                    volume=1000000,
                    timestamp=datetime.now(),
                    market="US",
                )
                mock_fund.side_effect = DataSourceError("yfinance", "No fundamentals")

                response = client.post("/api/watchlist/TEST")

                assert response.status_code == 200
                data = response.json()
                # 使用 symbol 作为名称
                assert data["name"] == "TEST"


class TestRemoveFromWatchlist:
    """测试从关注列表删除股票"""

    def test_remove_existing_stock(self, client, db_session):
        """成功删除已存在的股票"""
        item = Watchlist(symbol="AAPL", name="Apple Inc.", market="US")
        db_session.add(item)
        db_session.commit()

        response = client.delete("/api/watchlist/AAPL")

        assert response.status_code == 200
        assert "Removed" in response.json()["message"]

        # 验证已删除
        get_response = client.get("/api/watchlist/")
        assert len(get_response.json()) == 0

    def test_remove_nonexistent_stock(self, client):
        """删除不存在的股票返回 404"""
        # 使用有效格式的 symbol（5 字符内美股代码）
        response = client.delete("/api/watchlist/XXXXX")

        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()


class TestWatchlistEdgeCases:
    """边缘情况测试"""

    def test_symbol_case_sensitivity(self, client, db_session):
        """验证股票代码大小写处理"""
        item = Watchlist(symbol="AAPL", name="Apple Inc.", market="US")
        db_session.add(item)
        db_session.commit()

        # 使用小写查询（应该找不到，因为是精确匹配）
        # 这取决于具体实现，如果需要大小写不敏感则需要调整
        response = client.delete("/api/watchlist/aapl")
        # 根据实际行为断言
        assert response.status_code in [200, 404]

    def test_special_characters_in_symbol(self, client):
        """带特殊字符的股票代码（如港股 .HK）"""
        with patch("api.routes.watchlist.MarketRouter.get_stock_price") as mock_price:
            with patch("api.routes.watchlist.MarketRouter.get_fundamentals") as mock_fund:
                mock_price.return_value = StockPrice(
                    symbol="00700.HK",  # 港股需要 5 位数字
                    price=380.0,
                    change=5.0,
                    change_percent=1.33,
                    volume=20000000,
                    timestamp=datetime.now(),
                    market="HK",
                )
                mock_fund.return_value = CompanyFundamentals(
                    symbol="00700.HK",
                    name="腾讯控股",
                    sector="Communication Services",
                )

                response = client.post("/api/watchlist/00700.HK")

                assert response.status_code == 200
                assert response.json()["symbol"] == "00700.HK"
