"""
JiejinService 单元测试

覆盖:
1. 数据模型创建
2. 解禁压力评估
3. 近期解禁获取
4. 解禁日历
5. 个股解禁计划
6. 高压力股票筛选
7. 解禁概览
8. 解禁预警
9. 缓存机制
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, AsyncMock, MagicMock
import pandas as pd

from services.jiejin_service import (
    JiejinService,
    JiejinStock,
    JiejinCalendar,
    StockJiejinPlan,
    JiejinSummary,
    jiejin_service,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestJiejinModels:
    """解禁数据模型测试"""

    def test_jiejin_stock_creation(self):
        """创建 JiejinStock"""
        stock = JiejinStock(
            symbol="600519.SH",
            name="贵州茅台",
            jiejin_date=date(2026, 3, 1),
            jiejin_shares=1000.0,
            jiejin_market_value=18.0,
            jiejin_ratio=2.5,
            jiejin_type="定增解禁",
            pressure_level="中",
        )

        assert stock.symbol == "600519.SH"
        assert stock.jiejin_shares == 1000.0
        assert stock.jiejin_market_value == 18.0
        assert stock.pressure_level == "中"

    def test_jiejin_stock_with_optional_fields(self):
        """创建带可选字段的 JiejinStock"""
        stock = JiejinStock(
            symbol="000001.SZ",
            name="平安银行",
            jiejin_date=date(2026, 3, 15),
            jiejin_shares=5000.0,
            jiejin_market_value=60.0,
            jiejin_ratio=12.0,
            jiejin_type="首发解禁",
            current_price=12.5,
            total_market_value=200.0,
            pressure_level="高",
        )

        assert stock.current_price == 12.5
        assert stock.total_market_value == 200.0
        assert stock.pressure_level == "高"

    def test_jiejin_calendar_creation(self):
        """创建 JiejinCalendar"""
        stocks = [
            JiejinStock(
                symbol="600519.SH",
                name="贵州茅台",
                jiejin_date=date(2026, 3, 1),
                jiejin_shares=1000.0,
                jiejin_market_value=18.0,
                jiejin_ratio=2.5,
                jiejin_type="定增解禁",
                pressure_level="中",
            ),
        ]

        calendar = JiejinCalendar(
            date=date(2026, 3, 1),
            stock_count=1,
            total_shares=0.1,  # 亿股
            total_market_value=18.0,
            stocks=stocks,
        )

        assert calendar.stock_count == 1
        assert len(calendar.stocks) == 1

    def test_stock_jiejin_plan_creation(self):
        """创建 StockJiejinPlan"""
        plan = StockJiejinPlan(
            symbol="600519.SH",
            name="贵州茅台",
            upcoming_jiejin=[],
            past_jiejin=[],
            total_locked_shares=5000.0,
            total_locked_ratio=3.5,
        )

        assert plan.symbol == "600519.SH"
        assert plan.total_locked_ratio == 3.5

    def test_jiejin_summary_creation(self):
        """创建 JiejinSummary"""
        summary = JiejinSummary(
            date_range="2026-02-02 ~ 2026-03-04",
            total_stocks=50,
            total_market_value=500.0,
            daily_average=16.67,
            high_pressure_stocks=[],
            calendar=[],
        )

        assert summary.total_stocks == 50
        assert summary.daily_average == 16.67


# =============================================================================
# 解禁压力评估测试
# =============================================================================

class TestEvaluatePressure:
    """解禁压力评估测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return JiejinService()

    def test_high_pressure_by_ratio(self, service):
        """高压力：解禁比例 > 10%"""
        assert service._evaluate_pressure(jiejin_ratio=15.0, jiejin_market_value=5.0) == "高"
        assert service._evaluate_pressure(jiejin_ratio=10.1, jiejin_market_value=1.0) == "高"

    def test_high_pressure_by_market_value(self, service):
        """高压力：解禁市值 > 50 亿"""
        assert service._evaluate_pressure(jiejin_ratio=2.0, jiejin_market_value=55.0) == "高"
        assert service._evaluate_pressure(jiejin_ratio=1.0, jiejin_market_value=100.0) == "高"

    def test_medium_pressure_by_ratio(self, service):
        """中压力：解禁比例 > 5%"""
        assert service._evaluate_pressure(jiejin_ratio=7.0, jiejin_market_value=5.0) == "中"
        assert service._evaluate_pressure(jiejin_ratio=5.1, jiejin_market_value=1.0) == "中"

    def test_medium_pressure_by_market_value(self, service):
        """中压力：解禁市值 > 10 亿"""
        assert service._evaluate_pressure(jiejin_ratio=2.0, jiejin_market_value=15.0) == "中"
        assert service._evaluate_pressure(jiejin_ratio=1.0, jiejin_market_value=10.1) == "中"

    def test_low_pressure(self, service):
        """低压力"""
        assert service._evaluate_pressure(jiejin_ratio=3.0, jiejin_market_value=5.0) == "低"
        assert service._evaluate_pressure(jiejin_ratio=1.0, jiejin_market_value=1.0) == "低"


# =============================================================================
# 近期解禁获取测试
# =============================================================================

class TestGetUpcomingJiejin:
    """get_upcoming_jiejin() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例（清除缓存）"""
        svc = JiejinService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_jiejin_df(self):
        """Mock 解禁数据"""
        today = date.today()
        return pd.DataFrame({
            '股票代码': ['600519', '000001', '300750'],
            '股票简称': ['贵州茅台', '平安银行', '宁德时代'],
            '解禁日期': [
                (today + timedelta(days=5)).strftime('%Y-%m-%d'),
                (today + timedelta(days=10)).strftime('%Y-%m-%d'),
                (today + timedelta(days=15)).strftime('%Y-%m-%d'),
            ],
            '解禁数量': [1000, 5000, 3000],
            '解禁市值': [180000000, 600000000, 900000000],  # 万元
            '解禁比例': [2.5, 12.0, 8.0],
            '限售股类型': ['定增解禁', '首发解禁', '定增解禁'],
        })

    @pytest.mark.asyncio
    async def test_get_upcoming_success(self, service, mock_jiejin_df):
        """成功获取近期解禁"""
        with patch("services.jiejin_service.ak.stock_restricted_release_queue_sina", return_value=mock_jiejin_df):
            result = await service.get_upcoming_jiejin(days=30)

        assert len(result) == 3
        assert all(isinstance(s, JiejinStock) for s in result)

    @pytest.mark.asyncio
    async def test_get_upcoming_filtered_by_date(self, service, mock_jiejin_df):
        """按日期范围筛选"""
        with patch("services.jiejin_service.ak.stock_restricted_release_queue_sina", return_value=mock_jiejin_df):
            result = await service.get_upcoming_jiejin(days=7)

        # 只有 5 天后的一个在范围内
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_upcoming_empty(self, service):
        """空数据返回空列表"""
        with patch("services.jiejin_service.ak.stock_restricted_release_queue_sina", return_value=pd.DataFrame()):
            result = await service.get_upcoming_jiejin()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_upcoming_error(self, service):
        """异常返回空列表"""
        with patch("services.jiejin_service.ak.stock_restricted_release_queue_sina", side_effect=Exception("API Error")):
            result = await service.get_upcoming_jiejin()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_upcoming_cache(self, service, mock_jiejin_df):
        """缓存机制测试"""
        with patch("services.jiejin_service.ak.stock_restricted_release_queue_sina", return_value=mock_jiejin_df) as mock_api:
            result1 = await service.get_upcoming_jiejin(days=30)
            result2 = await service.get_upcoming_jiejin(days=30)

        # API 只应调用一次
        assert mock_api.call_count == 1
        assert len(result1) == len(result2)

    @pytest.mark.asyncio
    async def test_get_upcoming_symbol_format(self, service, mock_jiejin_df):
        """股票代码格式化"""
        with patch("services.jiejin_service.ak.stock_restricted_release_queue_sina", return_value=mock_jiejin_df):
            result = await service.get_upcoming_jiejin(days=30)

        # 600 开头应该是 .SH
        sh_stock = next((s for s in result if s.symbol.endswith(".SH")), None)
        assert sh_stock is not None
        assert sh_stock.symbol.startswith("6")

        # 000/300 开头应该是 .SZ
        sz_stocks = [s for s in result if s.symbol.endswith(".SZ")]
        assert len(sz_stocks) == 2


# =============================================================================
# 解禁日历测试
# =============================================================================

class TestGetJiejinCalendar:
    """get_jiejin_calendar() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = JiejinService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_calendar(self, service):
        """获取解禁日历"""
        today = date.today()
        mock_stocks = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=today + timedelta(days=5),
                jiejin_shares=1000, jiejin_market_value=18.0,
                jiejin_ratio=2.5, jiejin_type="定增解禁", pressure_level="中",
            ),
            JiejinStock(
                symbol="000001.SZ", name="平安银行",
                jiejin_date=today + timedelta(days=5),
                jiejin_shares=5000, jiejin_market_value=60.0,
                jiejin_ratio=12.0, jiejin_type="首发解禁", pressure_level="高",
            ),
            JiejinStock(
                symbol="300750.SZ", name="宁德时代",
                jiejin_date=today + timedelta(days=10),
                jiejin_shares=3000, jiejin_market_value=90.0,
                jiejin_ratio=8.0, jiejin_type="定增解禁", pressure_level="中",
            ),
        ]

        with patch.object(service, 'get_upcoming_jiejin', return_value=mock_stocks):
            result = await service.get_jiejin_calendar(days=30)

        assert len(result) == 2  # 两个不同日期
        # 第一个日期有两只股票
        first_day = result[0]
        assert first_day.stock_count == 2
        assert first_day.total_market_value == 78.0  # 18 + 60

    @pytest.mark.asyncio
    async def test_get_calendar_empty(self, service):
        """无数据返回空列表"""
        with patch.object(service, 'get_upcoming_jiejin', return_value=[]):
            result = await service.get_jiejin_calendar()

        assert result == []


# =============================================================================
# 个股解禁计划测试
# =============================================================================

class TestGetStockJiejinPlan:
    """get_stock_jiejin_plan() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = JiejinService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_detail_df(self):
        """Mock 个股解禁详情"""
        today = date.today()
        return pd.DataFrame({
            '股票简称': ['贵州茅台', '贵州茅台', '贵州茅台'],
            '解禁日期': [
                (today - timedelta(days=30)).strftime('%Y-%m-%d'),  # 历史
                (today + timedelta(days=30)).strftime('%Y-%m-%d'),  # 未来
                (today + timedelta(days=60)).strftime('%Y-%m-%d'),  # 未来
            ],
            '解禁数量': [500, 1000, 800],
            '解禁市值': [90000000, 180000000, 144000000],  # 万元
            '占总股本比例': [1.0, 2.5, 2.0],
            '限售股类型': ['定增解禁', '定增解禁', '首发解禁'],
        })

    @pytest.mark.asyncio
    async def test_get_plan_success(self, service, mock_detail_df):
        """成功获取个股解禁计划"""
        with patch("services.jiejin_service.ak.stock_restricted_release_detail_em", return_value=mock_detail_df):
            result = await service.get_stock_jiejin_plan("600519.SH")

        assert result is not None
        assert result.symbol == "600519.SH"
        assert len(result.upcoming_jiejin) == 2
        assert len(result.past_jiejin) == 1
        assert result.total_locked_shares == 1800  # 1000 + 800

    @pytest.mark.asyncio
    async def test_get_plan_empty(self, service):
        """无数据返回 None"""
        with patch("services.jiejin_service.ak.stock_restricted_release_detail_em", return_value=pd.DataFrame()):
            result = await service.get_stock_jiejin_plan("600519.SH")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_plan_error(self, service):
        """异常返回 None"""
        with patch("services.jiejin_service.ak.stock_restricted_release_detail_em", side_effect=Exception("Error")):
            result = await service.get_stock_jiejin_plan("600519.SH")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_plan_cache(self, service, mock_detail_df):
        """缓存机制测试"""
        with patch("services.jiejin_service.ak.stock_restricted_release_detail_em", return_value=mock_detail_df) as mock_api:
            result1 = await service.get_stock_jiejin_plan("600519.SH")
            result2 = await service.get_stock_jiejin_plan("600519.SH")

        assert mock_api.call_count == 1
        assert result1.total_locked_shares == result2.total_locked_shares


# =============================================================================
# 高压力股票筛选测试
# =============================================================================

class TestGetHighPressureStocks:
    """get_high_pressure_stocks() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return JiejinService()

    @pytest.mark.asyncio
    async def test_get_high_pressure(self, service):
        """获取高压力股票"""
        mock_stocks = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=date.today() + timedelta(days=5),
                jiejin_shares=1000, jiejin_market_value=18.0,
                jiejin_ratio=2.5, jiejin_type="定增解禁", pressure_level="低",
            ),
            JiejinStock(
                symbol="000001.SZ", name="平安银行",
                jiejin_date=date.today() + timedelta(days=5),
                jiejin_shares=5000, jiejin_market_value=60.0,
                jiejin_ratio=12.0, jiejin_type="首发解禁", pressure_level="高",
            ),
        ]

        with patch.object(service, 'get_upcoming_jiejin', return_value=mock_stocks):
            result = await service.get_high_pressure_stocks(days=7)

        assert len(result) == 1
        assert result[0].symbol == "000001.SZ"
        assert result[0].pressure_level == "高"


# =============================================================================
# 解禁概览测试
# =============================================================================

class TestGetSummary:
    """get_summary() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return JiejinService()

    @pytest.mark.asyncio
    async def test_get_summary(self, service):
        """获取解禁概览"""
        today = date.today()
        mock_stocks = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=today + timedelta(days=5),
                jiejin_shares=1000, jiejin_market_value=18.0,
                jiejin_ratio=2.5, jiejin_type="定增解禁", pressure_level="低",
            ),
            JiejinStock(
                symbol="000001.SZ", name="平安银行",
                jiejin_date=today + timedelta(days=10),
                jiejin_shares=5000, jiejin_market_value=60.0,
                jiejin_ratio=12.0, jiejin_type="首发解禁", pressure_level="高",
            ),
        ]
        mock_calendar = [
            JiejinCalendar(
                date=today + timedelta(days=5),
                stock_count=1, total_shares=0.1, total_market_value=18.0, stocks=[mock_stocks[0]],
            ),
            JiejinCalendar(
                date=today + timedelta(days=10),
                stock_count=1, total_shares=0.5, total_market_value=60.0, stocks=[mock_stocks[1]],
            ),
        ]

        with patch.object(service, 'get_upcoming_jiejin', return_value=mock_stocks):
            with patch.object(service, 'get_jiejin_calendar', return_value=mock_calendar):
                result = await service.get_summary(days=30)

        assert result.total_stocks == 2
        assert result.total_market_value == 78.0  # 18 + 60
        assert result.daily_average == 78.0 / 30
        assert len(result.high_pressure_stocks) == 1


# =============================================================================
# 解禁预警测试
# =============================================================================

class TestCheckJiejinWarning:
    """check_stock_jiejin_warning() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return JiejinService()

    @pytest.mark.asyncio
    async def test_warning_no_plan(self, service):
        """无解禁计划返回 None"""
        with patch.object(service, 'get_stock_jiejin_plan', return_value=None):
            result = await service.check_stock_jiejin_warning("600519.SH")

        assert result is None

    @pytest.mark.asyncio
    async def test_warning_no_upcoming(self, service):
        """无即将解禁返回 None"""
        plan = StockJiejinPlan(
            symbol="600519.SH", name="贵州茅台",
            upcoming_jiejin=[], past_jiejin=[],
            total_locked_shares=0, total_locked_ratio=0,
        )

        with patch.object(service, 'get_stock_jiejin_plan', return_value=plan):
            result = await service.check_stock_jiejin_warning("600519.SH")

        assert result is None

    @pytest.mark.asyncio
    async def test_warning_level_severe(self, service):
        """严重预警级别"""
        today = date.today()
        upcoming = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=today + timedelta(days=10),
                jiejin_shares=10000, jiejin_market_value=120.0,  # > 100 亿
                jiejin_ratio=25.0,  # > 20%
                jiejin_type="定增解禁", pressure_level="高",
            ),
        ]
        plan = StockJiejinPlan(
            symbol="600519.SH", name="贵州茅台",
            upcoming_jiejin=upcoming, past_jiejin=[],
            total_locked_shares=10000, total_locked_ratio=25.0,
        )

        with patch.object(service, 'get_stock_jiejin_plan', return_value=plan):
            result = await service.check_stock_jiejin_warning("600519.SH", days=30)

        assert result["warning_level"] == "严重"

    @pytest.mark.asyncio
    async def test_warning_level_warning(self, service):
        """警告级别"""
        today = date.today()
        upcoming = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=today + timedelta(days=10),
                jiejin_shares=5000, jiejin_market_value=55.0,  # > 50 亿
                jiejin_ratio=12.0,  # > 10%
                jiejin_type="定增解禁", pressure_level="高",
            ),
        ]
        plan = StockJiejinPlan(
            symbol="600519.SH", name="贵州茅台",
            upcoming_jiejin=upcoming, past_jiejin=[],
            total_locked_shares=5000, total_locked_ratio=12.0,
        )

        with patch.object(service, 'get_stock_jiejin_plan', return_value=plan):
            result = await service.check_stock_jiejin_warning("600519.SH", days=30)

        assert result["warning_level"] == "警告"

    @pytest.mark.asyncio
    async def test_warning_level_notice(self, service):
        """提示级别"""
        today = date.today()
        upcoming = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=today + timedelta(days=10),
                jiejin_shares=500, jiejin_market_value=9.0,  # < 10 亿
                jiejin_ratio=2.0,  # < 10%
                jiejin_type="定增解禁", pressure_level="低",
            ),
        ]
        plan = StockJiejinPlan(
            symbol="600519.SH", name="贵州茅台",
            upcoming_jiejin=upcoming, past_jiejin=[],
            total_locked_shares=500, total_locked_ratio=2.0,
        )

        with patch.object(service, 'get_stock_jiejin_plan', return_value=plan):
            result = await service.check_stock_jiejin_warning("600519.SH", days=30)

        assert result["warning_level"] == "提示"

    @pytest.mark.asyncio
    async def test_warning_outside_window(self, service):
        """解禁日在窗口外返回 None"""
        today = date.today()
        upcoming = [
            JiejinStock(
                symbol="600519.SH", name="贵州茅台",
                jiejin_date=today + timedelta(days=60),  # 60 天后
                jiejin_shares=5000, jiejin_market_value=90.0,
                jiejin_ratio=12.0,
                jiejin_type="定增解禁", pressure_level="高",
            ),
        ]
        plan = StockJiejinPlan(
            symbol="600519.SH", name="贵州茅台",
            upcoming_jiejin=upcoming, past_jiejin=[],
            total_locked_shares=5000, total_locked_ratio=12.0,
        )

        with patch.object(service, 'get_stock_jiejin_plan', return_value=plan):
            result = await service.check_stock_jiejin_warning("600519.SH", days=30)

        assert result is None


# =============================================================================
# 单例测试
# =============================================================================

class TestJiejinServiceSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert jiejin_service is not None
        assert isinstance(jiejin_service, JiejinService)
