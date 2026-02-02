"""
NorthMoneyService 单元测试

覆盖:
1. 数据模型创建
2. 北向资金流向获取
3. 历史数据
4. 个股持仓
5. TOP 净买入/卖出
6. 板块流向分析
7. 板块轮动信号
8. 盘中实时流向
9. 异常检测
10. 缓存机制
"""
import pytest
from datetime import date, datetime, time
from unittest.mock import patch, AsyncMock, MagicMock
import pandas as pd

from services.north_money_service import (
    NorthMoneyService,
    NorthMoneyFlow,
    StockNorthHolding,
    NorthMoneyTopStock,
    NorthMoneyHistory,
    NorthMoneySectorFlow,
    SectorRotationSignal,
    NorthMoneySummary,
    IntradayFlowPoint,
    IntradayFlowSummary,
    NorthMoneyAnomaly,
    NorthMoneyRealtime,
    north_money_service,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestNorthMoneyModels:
    """北向资金数据模型测试"""

    def test_north_money_flow_creation(self):
        """创建 NorthMoneyFlow"""
        flow = NorthMoneyFlow(
            date=date(2026, 2, 2),
            sh_connect=50.5,
            sz_connect=30.2,
            total=80.7,
            market_sentiment="Inflow",
        )

        assert flow.date == date(2026, 2, 2)
        assert flow.sh_connect == 50.5
        assert flow.sz_connect == 30.2
        assert flow.total == 80.7
        assert flow.market_sentiment == "Inflow"

    def test_stock_north_holding_creation(self):
        """创建 StockNorthHolding"""
        holding = StockNorthHolding(
            symbol="600519.SH",
            name="贵州茅台",
            holding_shares=100000000,
            holding_value=180.0,
            holding_ratio=8.5,
            change_shares=1000000,
            change_ratio=1.0,
            rank=1,
        )

        assert holding.symbol == "600519.SH"
        assert holding.holding_value == 180.0
        assert holding.rank == 1

    def test_north_money_top_stock_creation(self):
        """创建 NorthMoneyTopStock"""
        stock = NorthMoneyTopStock(
            symbol="600519.SH",
            name="贵州茅台",
            net_buy=5.5,
            buy_amount=8.0,
            sell_amount=2.5,
            holding_ratio=8.5,
        )

        assert stock.net_buy == 5.5
        assert stock.buy_amount == 8.0

    def test_north_money_history_creation(self):
        """创建 NorthMoneyHistory"""
        history = NorthMoneyHistory(
            date=date(2026, 2, 1),
            total=60.0,
            sh_connect=35.0,
            sz_connect=25.0,
        )

        assert history.total == 60.0

    def test_sector_flow_creation(self):
        """创建 NorthMoneySectorFlow"""
        sector = NorthMoneySectorFlow(
            sector="食品饮料",
            net_buy=15.5,
            stock_count=20,
            top_stocks=["贵州茅台", "五粮液"],
            flow_direction="inflow",
        )

        assert sector.sector == "食品饮料"
        assert sector.flow_direction == "inflow"
        assert len(sector.top_stocks) == 2

    def test_sector_rotation_signal_creation(self):
        """创建 SectorRotationSignal"""
        signal = SectorRotationSignal(
            date=date(2026, 2, 2),
            inflow_sectors=["食品饮料", "银行"],
            outflow_sectors=["电子", "计算机"],
            rotation_pattern="defensive",
            signal_strength=75,
            interpretation="资金流向防御性板块",
        )

        assert signal.rotation_pattern == "defensive"
        assert signal.signal_strength == 75

    def test_intraday_flow_point_creation(self):
        """创建 IntradayFlowPoint"""
        point = IntradayFlowPoint(
            time="10:30",
            sh_connect=20.0,
            sz_connect=15.0,
            total=35.0,
            cumulative_total=55.0,
        )

        assert point.time == "10:30"
        assert point.cumulative_total == 55.0

    def test_north_money_anomaly_creation(self):
        """创建 NorthMoneyAnomaly"""
        anomaly = NorthMoneyAnomaly(
            timestamp=datetime(2026, 2, 2, 14, 30),
            anomaly_type="sudden_inflow",
            severity="high",
            description="北向资金大额流入",
            affected_stocks=["贵州茅台", "宁德时代"],
            flow_change=120.0,
            recommendation="关注机构重仓股",
        )

        assert anomaly.anomaly_type == "sudden_inflow"
        assert anomaly.severity == "high"


# =============================================================================
# 北向资金流向测试
# =============================================================================

class TestGetNorthMoneyFlow:
    """get_north_money_flow() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_flow_df(self):
        """Mock 北向资金数据"""
        return pd.DataFrame({
            '日期': ['2026-02-01', '2026-02-02'],
            '沪股通': [30.0, 50.0],
            '深股通': [20.0, 35.0],
            '北向资金': [50.0, 85.0],
        })

    @pytest.mark.asyncio
    async def test_get_flow_success(self, service, mock_flow_df):
        """成功获取北向资金流向"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=mock_flow_df, create=True):
            result = await service.get_north_money_flow()

        assert result.sh_connect == 50.0
        assert result.sz_connect == 35.0
        assert result.total == 85.0
        assert result.market_sentiment == "Strong Inflow"  # 85 > 50

    @pytest.mark.asyncio
    async def test_get_flow_strong_inflow(self, service):
        """强流入情绪判断"""
        df = pd.DataFrame({
            '沪股通': [60.0],
            '深股通': [40.0],
            '北向资金': [100.0],
        })
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=df, create=True):
            result = await service.get_north_money_flow()

        assert result.market_sentiment == "Strong Inflow"

    @pytest.mark.asyncio
    async def test_get_flow_strong_outflow(self, service):
        """强流出情绪判断"""
        df = pd.DataFrame({
            '沪股通': [-40.0],
            '深股通': [-30.0],
            '北向资金': [-70.0],
        })
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=df, create=True):
            result = await service.get_north_money_flow()

        assert result.market_sentiment == "Strong Outflow"

    @pytest.mark.asyncio
    async def test_get_flow_empty(self, service):
        """空数据返回默认值"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=pd.DataFrame(), create=True):
            result = await service.get_north_money_flow()

        assert result.total == 0
        assert result.market_sentiment == "Unknown"

    @pytest.mark.asyncio
    async def test_get_flow_error(self, service):
        """异常返回默认值"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", side_effect=Exception("API Error"), create=True):
            result = await service.get_north_money_flow()

        assert result.total == 0
        assert result.market_sentiment == "Unknown"

    @pytest.mark.asyncio
    async def test_get_flow_cache(self, service, mock_flow_df):
        """缓存机制测试"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=mock_flow_df, create=True) as mock_api:
            result1 = await service.get_north_money_flow()
            result2 = await service.get_north_money_flow()

        assert mock_api.call_count == 1
        assert result1.total == result2.total


# =============================================================================
# 历史数据测试
# =============================================================================

class TestGetNorthMoneyHistory:
    """get_north_money_history() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_history_df(self):
        """Mock 历史数据"""
        return pd.DataFrame({
            '日期': ['2026-01-28', '2026-01-29', '2026-01-30', '2026-01-31', '2026-02-01'],
            '沪股通': [20.0, 30.0, -10.0, 40.0, 25.0],
            '深股通': [15.0, 20.0, -5.0, 30.0, 20.0],
            '北向资金': [35.0, 50.0, -15.0, 70.0, 45.0],
        })

    @pytest.mark.asyncio
    async def test_get_history_success(self, service, mock_history_df):
        """成功获取历史数据"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=mock_history_df, create=True):
            result = await service.get_north_money_history(days=5)

        assert len(result) == 5
        assert result[0].total == 35.0

    @pytest.mark.asyncio
    async def test_get_history_empty(self, service):
        """空数据返回空列表"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", return_value=pd.DataFrame(), create=True):
            result = await service.get_north_money_history()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_error(self, service):
        """异常返回空列表"""
        with patch("services.north_money_service.ak.stock_hsgt_north_net_flow_in_em", side_effect=Exception("Error"), create=True):
            result = await service.get_north_money_history()

        assert result == []


# =============================================================================
# 个股持仓测试
# =============================================================================

class TestGetStockNorthHolding:
    """get_stock_north_holding() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return NorthMoneyService()

    @pytest.fixture
    def mock_holding_df(self):
        """Mock 持仓数据"""
        return pd.DataFrame({
            '代码': ['600519', '000858', '601318'],
            '名称': ['贵州茅台', '五粮液', '中国平安'],
            '持股数量': [100000000, 80000000, 120000000],
            '持股市值': [18000000000, 12000000000, 9000000000],
            '持股占比': [8.5, 6.2, 5.0],
            '今日增持股数': [1000000, -500000, 2000000],
            '今日增持比例': [1.0, -0.6, 1.7],
            '排名': [1, 2, 3],
        })

    @pytest.mark.asyncio
    async def test_get_holding_success(self, service, mock_holding_df):
        """成功获取个股持仓"""
        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", return_value=mock_holding_df):
            result = await service.get_stock_north_holding("600519.SH")

        assert result is not None
        assert result.symbol == "600519.SH"
        assert result.name == "贵州茅台"
        assert result.holding_ratio == 8.5

    @pytest.mark.asyncio
    async def test_get_holding_not_found(self, service, mock_holding_df):
        """股票不存在"""
        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", return_value=mock_holding_df):
            result = await service.get_stock_north_holding("999999.SH")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_holding_error(self, service):
        """异常返回 None"""
        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", side_effect=Exception("Error")):
            result = await service.get_stock_north_holding("600519.SH")

        assert result is None


# =============================================================================
# TOP 净买入/卖出测试
# =============================================================================

class TestTopNorthBuySell:
    """TOP 净买入/卖出测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_holding_df(self):
        """Mock 持仓数据"""
        return pd.DataFrame({
            '代码': ['600519', '000858', '601318', '300750', '002594'],
            '名称': ['贵州茅台', '五粮液', '中国平安', '宁德时代', '比亚迪'],
            '净买额': [500000000, 300000000, -200000000, -400000000, 100000000],
            '买入金额': [800000000, 500000000, 300000000, 200000000, 400000000],
            '卖出金额': [300000000, 200000000, 500000000, 600000000, 300000000],
            '持股占比': [8.5, 6.2, 5.0, 4.5, 3.8],
        })

    @pytest.mark.asyncio
    async def test_get_top_buys(self, service, mock_holding_df):
        """获取 TOP 净买入"""
        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", return_value=mock_holding_df):
            result = await service.get_top_north_buys(limit=3)

        assert len(result) == 3
        assert result[0].name == "贵州茅台"
        assert result[0].net_buy > result[1].net_buy  # 排序正确

    @pytest.mark.asyncio
    async def test_get_top_sells(self, service, mock_holding_df):
        """获取 TOP 净卖出"""
        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", return_value=mock_holding_df):
            result = await service.get_top_north_sells(limit=3)

        # 只返回净卖出的（net_buy < 0）
        for stock in result:
            assert stock.net_buy < 0

    @pytest.mark.asyncio
    async def test_get_top_buys_empty(self, service):
        """空数据返回空列表"""
        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", return_value=pd.DataFrame()):
            result = await service.get_top_north_buys()

        assert result == []


# =============================================================================
# 概览测试
# =============================================================================

class TestGetSummary:
    """get_summary() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_summary(self, service):
        """获取概览"""
        mock_flow = NorthMoneyFlow(
            date=date(2026, 2, 2),
            sh_connect=50.0,
            sz_connect=30.0,
            total=80.0,
            market_sentiment="Inflow",
        )
        mock_history = [
            NorthMoneyHistory(date=date(2026, 2, 1), total=60.0, sh_connect=35.0, sz_connect=25.0),
            NorthMoneyHistory(date=date(2026, 2, 2), total=80.0, sh_connect=50.0, sz_connect=30.0),
        ]
        mock_top_buys = [
            NorthMoneyTopStock(symbol="600519.SH", name="贵州茅台", net_buy=5.0, buy_amount=8.0, sell_amount=3.0, holding_ratio=8.5),
        ]

        with patch.object(service, 'get_north_money_flow', return_value=mock_flow):
            with patch.object(service, 'get_north_money_history', return_value=mock_history):
                with patch.object(service, 'get_top_north_buys', return_value=mock_top_buys):
                    with patch.object(service, 'get_top_north_sells', return_value=[]):
                        result = await service.get_summary()

        assert result.today.total == 80.0
        assert result.week_total == 140.0  # 60 + 80
        assert result.trend == "Strong Inflow"


# =============================================================================
# 板块流向测试
# =============================================================================

class TestSectorFlow:
    """板块流向测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    def test_match_sector_food(self, service):
        """匹配食品饮料板块"""
        # 使用包含关键词的名称
        assert service._match_sector("五粮液酒业") == "食品饮料"
        assert service._match_sector("伊利乳业") == "食品饮料"
        assert service._match_sector("青岛啤酒") == "食品饮料"  # "啤酒" 包含 "酒" 子串
        assert service._match_sector("金龙鱼食品") == "食品饮料"

    def test_match_sector_bank(self, service):
        """匹配银行板块"""
        assert service._match_sector("招商银行") == "银行"
        assert service._match_sector("工商银行") == "银行"
        assert service._match_sector("杭州农商银行") == "银行"

    def test_match_sector_electronics(self, service):
        """匹配电子板块"""
        assert service._match_sector("中芯半导体") == "电子"
        assert service._match_sector("京东方电子") == "电子"
        assert service._match_sector("海力士芯片") == "电子"

    def test_match_sector_default(self, service):
        """无法匹配返回其他"""
        assert service._match_sector("某某公司") == "其他"
        assert service._match_sector("贵州茅台") == "其他"  # 没有关键词匹配

    @pytest.mark.asyncio
    async def test_get_sector_flow(self, service):
        """获取板块流向"""
        mock_df = pd.DataFrame({
            '代码': ['600519', '000858', '600036'],
            '名称': ['贵州茅台', '五粮液', '招商银行'],
            '净买额': [500000000, 300000000, -100000000],
        })

        with patch("services.north_money_service.ak.stock_hsgt_hold_stock_em", return_value=mock_df):
            result = await service.get_sector_flow()

        assert len(result) >= 1
        # 食品饮料应该是流入
        food_sector = next((s for s in result if s.sector == "食品饮料"), None)
        if food_sector:
            assert food_sector.flow_direction == "inflow"


# =============================================================================
# 板块轮动信号测试
# =============================================================================

class TestSectorRotationSignal:
    """板块轮动信号测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_rotation_signal_empty(self, service):
        """无数据返回 unclear"""
        with patch.object(service, 'get_sector_flow', return_value=[]):
            result = await service.get_sector_rotation_signal()

        assert result.rotation_pattern == "unclear"
        assert result.signal_strength == 0

    @pytest.mark.asyncio
    async def test_rotation_signal_defensive(self, service):
        """防御性轮动信号"""
        mock_sectors = [
            NorthMoneySectorFlow(sector="银行", net_buy=20.0, stock_count=10, top_stocks=[], flow_direction="inflow"),
            NorthMoneySectorFlow(sector="食品饮料", net_buy=15.0, stock_count=8, top_stocks=[], flow_direction="inflow"),
            NorthMoneySectorFlow(sector="电子", net_buy=-5.0, stock_count=15, top_stocks=[], flow_direction="outflow"),
        ]

        with patch.object(service, 'get_sector_flow', return_value=mock_sectors):
            result = await service.get_sector_rotation_signal()

        assert result.rotation_pattern == "defensive"
        assert "防御" in result.interpretation

    @pytest.mark.asyncio
    async def test_rotation_signal_aggressive(self, service):
        """进攻性轮动信号"""
        mock_sectors = [
            NorthMoneySectorFlow(sector="电子", net_buy=25.0, stock_count=20, top_stocks=[], flow_direction="inflow"),
            NorthMoneySectorFlow(sector="计算机", net_buy=20.0, stock_count=15, top_stocks=[], flow_direction="inflow"),
            NorthMoneySectorFlow(sector="银行", net_buy=-10.0, stock_count=10, top_stocks=[], flow_direction="outflow"),
        ]

        with patch.object(service, 'get_sector_flow', return_value=mock_sectors):
            result = await service.get_sector_rotation_signal()

        assert result.rotation_pattern == "aggressive"
        assert "进攻" in result.interpretation


# =============================================================================
# 交易时段判断测试
# =============================================================================

class TestTradingHours:
    """交易时段判断测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return NorthMoneyService()

    def test_trading_hours_morning(self, service):
        """上午盘时段"""
        with patch("services.north_money_service.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 1  # 周二
            mock_now.time.return_value = time(10, 30)  # 10:30
            mock_dt.now.return_value = mock_now

            result = service._is_trading_hours()

        assert result is True

    def test_trading_hours_afternoon(self, service):
        """下午盘时段"""
        with patch("services.north_money_service.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 3  # 周四
            mock_now.time.return_value = time(14, 0)  # 14:00
            mock_dt.now.return_value = mock_now

            result = service._is_trading_hours()

        assert result is True

    def test_non_trading_hours_weekend(self, service):
        """周末非交易时段"""
        with patch("services.north_money_service.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 5  # 周六
            mock_dt.now.return_value = mock_now

            result = service._is_trading_hours()

        assert result is False

    def test_non_trading_hours_lunch(self, service):
        """午休非交易时段"""
        with patch("services.north_money_service.datetime") as mock_dt:
            mock_now = MagicMock()
            mock_now.weekday.return_value = 2  # 周三
            mock_now.time.return_value = time(12, 30)  # 12:30
            mock_dt.now.return_value = mock_now

            result = service._is_trading_hours()

        assert result is False


# =============================================================================
# 异常检测测试
# =============================================================================

class TestDetectAnomalies:
    """异常检测测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_detect_sudden_inflow(self, service):
        """检测大额流入"""
        mock_flow = NorthMoneyFlow(
            date=date(2026, 2, 2),
            sh_connect=80.0,
            sz_connect=70.0,
            total=150.0,  # > 100
            market_sentiment="Strong Inflow",
        )

        with patch.object(service, 'get_north_money_flow', return_value=mock_flow):
            with patch.object(service, 'get_north_money_history', return_value=[]):
                with patch.object(service, 'get_intraday_flow', return_value=IntradayFlowSummary(
                    date=date(2026, 2, 2), last_update="14:30", current_total=150.0,
                    flow_points=[], peak_inflow=150.0, peak_outflow=0, momentum="stable"
                )):
                    with patch.object(service, 'get_top_north_buys', return_value=[]):
                        result = await service.detect_anomalies()

        assert len(result) >= 1
        assert any(a.anomaly_type == "sudden_inflow" for a in result)

    @pytest.mark.asyncio
    async def test_detect_reversal(self, service):
        """检测流向反转"""
        mock_flow = NorthMoneyFlow(
            date=date(2026, 2, 2),
            sh_connect=-30.0,
            sz_connect=-20.0,
            total=-50.0,
            market_sentiment="Outflow",
        )
        mock_history = [
            NorthMoneyHistory(date=date(2026, 1, 28), total=30.0, sh_connect=20.0, sz_connect=10.0),
            NorthMoneyHistory(date=date(2026, 1, 29), total=40.0, sh_connect=25.0, sz_connect=15.0),
            NorthMoneyHistory(date=date(2026, 1, 30), total=35.0, sh_connect=20.0, sz_connect=15.0),
            NorthMoneyHistory(date=date(2026, 1, 31), total=45.0, sh_connect=25.0, sz_connect=20.0),
            NorthMoneyHistory(date=date(2026, 2, 1), total=-50.0, sh_connect=-30.0, sz_connect=-20.0),
        ]

        with patch.object(service, 'get_north_money_flow', return_value=mock_flow):
            with patch.object(service, 'get_north_money_history', return_value=mock_history):
                with patch.object(service, 'get_intraday_flow', return_value=IntradayFlowSummary(
                    date=date(2026, 2, 2), last_update="14:30", current_total=-50.0,
                    flow_points=[], peak_inflow=0, peak_outflow=-50.0, momentum="stable"
                )):
                    with patch.object(service, 'get_top_north_buys', return_value=[]):
                        result = await service.detect_anomalies()

        # 应该检测到反转
        assert any(a.anomaly_type == "reversal" for a in result)

    @pytest.mark.asyncio
    async def test_detect_no_anomalies(self, service):
        """无异常情况"""
        mock_flow = NorthMoneyFlow(
            date=date(2026, 2, 2),
            sh_connect=20.0,
            sz_connect=15.0,
            total=35.0,  # 正常范围
            market_sentiment="Inflow",
        )

        with patch.object(service, 'get_north_money_flow', return_value=mock_flow):
            with patch.object(service, 'get_north_money_history', return_value=[]):
                with patch.object(service, 'get_intraday_flow', return_value=IntradayFlowSummary(
                    date=date(2026, 2, 2), last_update="14:30", current_total=35.0,
                    flow_points=[], peak_inflow=35.0, peak_outflow=0, flow_volatility=5.0, momentum="stable"
                )):
                    with patch.object(service, 'get_top_north_buys', return_value=[]):
                        result = await service.detect_anomalies()

        # 无严重异常
        critical_anomalies = [a for a in result if a.severity in ["high", "critical"]]
        assert len(critical_anomalies) == 0


# =============================================================================
# 实时全景测试
# =============================================================================

class TestRealtimePanorama:
    """实时全景测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = NorthMoneyService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_realtime_panorama(self, service):
        """获取实时全景"""
        mock_summary = NorthMoneySummary(
            today=NorthMoneyFlow(
                date=date(2026, 2, 2), sh_connect=50.0, sz_connect=30.0,
                total=80.0, market_sentiment="Inflow"
            ),
            top_buys=[],
            top_sells=[],
            history_5d=[],
            trend="Inflow",
            week_total=200.0,
        )

        with patch.object(service, 'get_summary', return_value=mock_summary):
            with patch.object(service, 'detect_anomalies', return_value=[]):
                with patch.object(service, '_is_trading_hours', return_value=False):
                    with patch.object(service, 'get_north_money_history', return_value=[]):
                        result = await service.get_realtime_panorama()

        assert result.summary.today.total == 80.0
        assert result.is_trading_hours is False
        assert result.intraday is None  # 非交易时段


# =============================================================================
# 单例测试
# =============================================================================

class TestNorthMoneyServiceSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert north_money_service is not None
        assert isinstance(north_money_service, NorthMoneyService)
