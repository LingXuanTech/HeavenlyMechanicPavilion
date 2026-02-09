"""
测试 API 输入验证

测试 analyze.py 中的输入验证功能
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestSymbolValidation:
    """测试股票代码验证"""

    def test_valid_us_stock(self):
        """测试有效的美股代码"""
        response = client.post("/api/analyze/AAPL")
        # 应该返回 200 或 202（任务已创建）
        assert response.status_code in [200, 202]

    def test_valid_a_stock_sh(self):
        """测试有效的 A股代码（上交所）"""
        response = client.post("/api/analyze/600000.SH")
        assert response.status_code in [200, 202]

    def test_valid_a_stock_sz(self):
        """测试有效的 A股代码（深交所）"""
        response = client.post("/api/analyze/000001.SZ")
        assert response.status_code in [200, 202]

    def test_valid_hk_stock(self):
        """测试有效的港股代码"""
        response = client.post("/api/analyze/00700.HK")
        assert response.status_code in [200, 202]

    def test_invalid_symbol_with_special_chars(self):
        """测试包含特殊字符的无效代码"""
        response = client.post("/api/analyze/ABC@123")
        assert response.status_code == 400
        assert "无效的股票代码格式" in response.json()["detail"]

    def test_invalid_symbol_sql_injection(self):
        """测试 SQL 注入尝试"""
        response = client.post("/api/analyze/' OR 1=1--")
        assert response.status_code == 400
        assert "无效的股票代码格式" in response.json()["detail"]

    def test_invalid_symbol_too_long(self):
        """测试过长的股票代码"""
        response = client.post("/api/analyze/ABCDEFGHIJK")
        assert response.status_code == 400

    def test_invalid_symbol_empty(self):
        """测试空股票代码"""
        response = client.post("/api/analyze/")
        # 应该返回 404（路由不匹配）或 405（方法不允许）
        assert response.status_code in [404, 405]

    def test_invalid_symbol_with_spaces(self):
        """测试包含空格的代码"""
        response = client.post("/api/analyze/ABC 123")
        assert response.status_code == 400

    def test_case_insensitive_validation(self):
        """测试大小写不敏感"""
        # 小写应该也能通过
        response = client.post("/api/analyze/aapl")
        assert response.status_code in [200, 202]

        response = client.post("/api/analyze/600000.sh")
        assert response.status_code in [200, 202]


class TestQuickScanValidation:
    """测试快速扫描端点的验证"""

    def test_valid_symbol_quick_scan(self):
        """测试快速扫描的有效代码"""
        response = client.post("/api/analyze/quick/AAPL")
        assert response.status_code in [200, 202]

    def test_invalid_symbol_quick_scan(self):
        """测试快速扫描的无效代码"""
        response = client.post("/api/analyze/quick/ABC@123")
        assert response.status_code == 400
        assert "无效的股票代码格式" in response.json()["detail"]


class TestTradeDateValidation:
    """测试日期验证"""

    def test_valid_iso_date(self):
        """测试有效的 ISO 日期"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"trade_date": "2024-01-15"}
        )
        assert response.status_code in [200, 202]

    def test_invalid_date_format(self):
        """测试无效的日期格式"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"trade_date": "2024/01/15"}
        )
        assert response.status_code == 422  # Pydantic 验证错误

    def test_invalid_date_string(self):
        """测试无效的日期字符串"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"trade_date": "invalid-date"}
        )
        assert response.status_code == 422

    def test_null_date(self):
        """测试 null 日期（应该使用默认值）"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"trade_date": None}
        )
        assert response.status_code in [200, 202]

    def test_missing_date(self):
        """测试缺失日期（应该使用默认值）"""
        response = client.post("/api/analyze/AAPL")
        assert response.status_code in [200, 202]


class TestAnalysisLevelValidation:
    """测试分析级别验证"""

    def test_valid_l1_level(self):
        """测试有效的 L1 级别"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"analysis_level": "L1"}
        )
        assert response.status_code in [200, 202]

    def test_valid_l2_level(self):
        """测试有效的 L2 级别"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"analysis_level": "L2"}
        )
        assert response.status_code in [200, 202]

    def test_invalid_level(self):
        """测试无效的分析级别"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"analysis_level": "L3"}
        )
        assert response.status_code == 422


class TestPaginationValidation:
    """测试分页参数验证"""

    def test_valid_offset_pagination(self):
        """测试有效的 offset 分页"""
        response = client.get("/api/analyze/history/AAPL?limit=10&offset=0")
        assert response.status_code == 200

    def test_valid_cursor_pagination(self):
        """测试有效的 cursor 分页"""
        response = client.get("/api/analyze/history/AAPL?limit=10&cursor=100")
        assert response.status_code == 200

    def test_invalid_limit_too_large(self):
        """测试过大的 limit"""
        response = client.get("/api/analyze/history/AAPL?limit=1000")
        assert response.status_code == 422  # 超过最大值 100

    def test_invalid_limit_zero(self):
        """测试 limit 为 0"""
        response = client.get("/api/analyze/history/AAPL?limit=0")
        assert response.status_code == 422  # 小于最小值 1

    def test_invalid_offset_negative(self):
        """测试负数 offset"""
        response = client.get("/api/analyze/history/AAPL?offset=-1")
        assert response.status_code == 422

    def test_count_total_parameter(self):
        """测试 count_total 参数"""
        response = client.get("/api/analyze/history/AAPL?count_total=false")
        assert response.status_code == 200

        data = response.json()
        # 当 count_total=false 时，total 应该为 null
        assert data.get("total") is None or data.get("total") == 0


class TestErrorMessages:
    """测试错误消息的清晰度"""

    def test_symbol_error_message_clarity(self):
        """测试股票代码错误消息的清晰度"""
        response = client.post("/api/analyze/INVALID@SYMBOL")
        assert response.status_code == 400

        error_detail = response.json()["detail"]
        # 错误消息应该包含支持的格式
        assert "AAPL" in error_detail
        assert "000001.SZ" in error_detail
        assert "600000.SH" in error_detail
        assert "00700.HK" in error_detail

    def test_date_error_message_clarity(self):
        """测试日期错误消息的清晰度"""
        response = client.post(
            "/api/analyze/AAPL",
            json={"trade_date": "invalid"}
        )
        assert response.status_code == 422

        error_detail = response.json()["detail"]
        # 应该包含验证错误信息
        assert len(error_detail) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
