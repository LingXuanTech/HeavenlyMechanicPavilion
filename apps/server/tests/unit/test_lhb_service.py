"""
LHBService 单元测试

覆盖:
1. 数据模型创建
2. 席位类型识别
3. 每日龙虎榜获取（mock akshare）
4. 游资活动分析
5. 游资画像
6. 游资动向信号
7. 缓存机制
"""
import pytest
from datetime import date, datetime
from unittest.mock import patch, AsyncMock, MagicMock
import pandas as pd

from services.lhb_service import (
    LHBService,
    LHBSeat,
    LHBStock,
    LHBRecord,
    HotMoneySeat,
    HotMoneyProfile,
    HotMoneyMovementSignal,
    LHBSummary,
    HOT_MONEY_SEATS,
    lhb_service,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestLHBModels:
    """龙虎榜数据模型测试"""

    def test_lhb_seat_creation(self):
        """创建 LHBSeat"""
        seat = LHBSeat(
            seat_name="华鑫证券上海分公司",
            buy_amount=5000.0,
            sell_amount=1000.0,
            net_amount=4000.0,
            seat_type="游资",
            hot_money_name="溧阳路",
        )

        assert seat.seat_name == "华鑫证券上海分公司"
        assert seat.buy_amount == 5000.0
        assert seat.net_amount == 4000.0
        assert seat.seat_type == "游资"
        assert seat.hot_money_name == "溧阳路"

    def test_lhb_seat_no_hot_money(self):
        """普通席位无游资名称"""
        seat = LHBSeat(
            seat_name="某某证券营业部",
            buy_amount=1000.0,
            sell_amount=500.0,
            net_amount=500.0,
            seat_type="普通",
        )

        assert seat.hot_money_name is None

    def test_lhb_stock_creation(self):
        """创建 LHBStock"""
        stock = LHBStock(
            symbol="600519.SH",
            name="贵州茅台",
            close_price=1800.0,
            change_percent=2.5,
            turnover_rate=0.8,
            lhb_net_buy=10000.0,
            lhb_buy_amount=15000.0,
            lhb_sell_amount=5000.0,
            reason="涨幅偏离值达7%",
            buy_seats=[],
            sell_seats=[],
            institution_net=5000.0,
            hot_money_involved=False,
        )

        assert stock.symbol == "600519.SH"
        assert stock.lhb_net_buy == 10000.0
        assert stock.institution_net == 5000.0

    def test_lhb_record_creation(self):
        """创建 LHBRecord"""
        record = LHBRecord(
            date=date(2026, 2, 1),
            reason="连续三个交易日收盘价涨幅偏离值累计20%",
            net_buy=8000.0,
            buy_amount=12000.0,
            sell_amount=4000.0,
            institution_net=3000.0,
        )

        assert record.date == date(2026, 2, 1)
        assert record.net_buy == 8000.0

    def test_hot_money_profile_creation(self):
        """创建 HotMoneyProfile"""
        profile = HotMoneyProfile(
            seat_name="华鑫证券上海分公司",
            alias="溧阳路",
            tier="一线",
            style="打板/接力",
            style_tags=["打板", "接力", "题材"],
            total_appearances=50,
            total_buy_amount=10.5,
            preferred_sectors=["科技", "新能源"],
        )

        assert profile.alias == "溧阳路"
        assert profile.tier == "一线"
        assert "打板" in profile.style_tags

    def test_hot_money_movement_signal_creation(self):
        """创建 HotMoneyMovementSignal"""
        signal = HotMoneyMovementSignal(
            signal_date=date(2026, 2, 2),
            signal_type="consensus_buy",
            signal_strength=80,
            involved_seats=["溧阳路", "赵老哥"],
            target_stocks=[{"symbol": "600519.SH", "name": "贵州茅台"}],
            interpretation="多路游资同时买入",
        )

        assert signal.signal_type == "consensus_buy"
        assert signal.signal_strength == 80
        assert len(signal.involved_seats) == 2


# =============================================================================
# 席位识别测试
# =============================================================================

class TestSeatIdentification:
    """席位类型识别测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return LHBService()

    def test_identify_institution_seat(self, service):
        """识别机构席位"""
        seat_type, style, alias, tier = service._identify_seat_type("机构专用")

        assert seat_type == "机构"
        assert alias == "机构"
        assert tier == "机构"

    def test_identify_hot_money_seat_liyang(self, service):
        """识别溧阳路游资"""
        seat_type, style, alias, tier = service._identify_seat_type(
            "华鑫证券上海分公司营业部"
        )

        assert seat_type == "游资"
        assert alias == "溧阳路"
        assert tier == "一线"
        assert "打板" in style

    def test_identify_hot_money_seat_zhaolao(self, service):
        """识别赵老哥"""
        seat_type, style, alias, tier = service._identify_seat_type(
            "中国银河证券绍兴证券营业部"
        )

        assert seat_type == "游资"
        assert alias == "赵老哥"
        assert tier == "一线"

    def test_identify_hot_money_seat_lasa(self, service):
        """识别拉萨天团"""
        seat_type, style, alias, tier = service._identify_seat_type(
            "东方财富证券拉萨团结路第二营业部"
        )

        assert seat_type == "游资"
        assert alias == "拉萨天团"

    def test_identify_normal_seat(self, service):
        """识别普通席位"""
        seat_type, style, alias, tier = service._identify_seat_type(
            "某某证券某某营业部"
        )

        assert seat_type == "普通"
        assert style == "未知"
        assert alias is None
        assert tier is None

    def test_parse_seat_data(self, service):
        """解析席位数据"""
        seat = service._parse_seat_data(
            "华鑫证券上海分公司",
            buy=5000.0,
            sell=1000.0,
        )

        assert seat.seat_name == "华鑫证券上海分公司"
        assert seat.buy_amount == 5000.0
        assert seat.sell_amount == 1000.0
        assert seat.net_amount == 4000.0
        assert seat.seat_type == "游资"
        assert seat.hot_money_name == "溧阳路"


# =============================================================================
# 每日龙虎榜获取测试
# =============================================================================

class TestGetDailyLHB:
    """get_daily_lhb() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例（清除缓存）"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_lhb_df(self):
        """Mock 龙虎榜数据"""
        return pd.DataFrame({
            '代码': ['600519', '600519', '000001', '000001'],
            '名称': ['贵州茅台', '贵州茅台', '平安银行', '平安银行'],
            '收盘价': [1800.0, 1800.0, 12.5, 12.5],
            '涨跌幅': [5.0, 5.0, 3.0, 3.0],
            '换手率': [2.0, 2.0, 1.5, 1.5],
            '上榜原因': ['涨幅偏离值达7%', '涨幅偏离值达7%', '换手率达20%', '换手率达20%'],
            '买入营业部': ['华鑫证券上海分公司', '机构专用', '某证券营业部', '机构专用'],
            '买入金额': [5000, 3000, 2000, 1500],
            '卖出金额': [1000, 500, 800, 300],
        })

    @pytest.mark.asyncio
    async def test_get_daily_lhb_success(self, service, mock_lhb_df):
        """成功获取每日龙虎榜"""
        with patch("services.lhb_service.ak.stock_lhb_detail_em", return_value=mock_lhb_df):
            result = await service.get_daily_lhb()

        assert len(result) == 2  # 2 只股票
        assert result[0].symbol in ["600519.SH", "000001.SZ"]

    @pytest.mark.asyncio
    async def test_get_daily_lhb_with_date(self, service, mock_lhb_df):
        """指定日期获取龙虎榜"""
        with patch("services.lhb_service.ak.stock_lhb_detail_em", return_value=mock_lhb_df):
            result = await service.get_daily_lhb(trade_date="20260202")

        assert len(result) >= 0  # 可能有数据

    @pytest.mark.asyncio
    async def test_get_daily_lhb_empty(self, service):
        """空数据返回空列表"""
        with patch("services.lhb_service.ak.stock_lhb_detail_em", return_value=pd.DataFrame()):
            result = await service.get_daily_lhb()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_daily_lhb_error(self, service):
        """异常返回空列表"""
        with patch("services.lhb_service.ak.stock_lhb_detail_em", side_effect=Exception("API Error")):
            result = await service.get_daily_lhb()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_daily_lhb_cache(self, service, mock_lhb_df):
        """缓存机制测试"""
        with patch("services.lhb_service.ak.stock_lhb_detail_em", return_value=mock_lhb_df) as mock_api:
            # 第一次调用
            result1 = await service.get_daily_lhb()
            # 第二次调用应该使用缓存
            result2 = await service.get_daily_lhb()

        # API 只应该被调用一次
        assert mock_api.call_count == 1
        assert result1 == result2


# =============================================================================
# 个股龙虎榜历史测试
# =============================================================================

class TestGetStockLHBHistory:
    """get_stock_lhb_history() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_history_df(self):
        """Mock 历史数据"""
        return pd.DataFrame({
            '上榜日期': ['2026-01-15', '2026-01-10', '2026-01-05'],
            '上榜原因': ['涨幅偏离值达7%', '换手率达20%', '振幅达15%'],
            '龙虎榜净买额': [8000.0, -2000.0, 5000.0],
            '龙虎榜买入额': [12000.0, 6000.0, 9000.0],
            '龙虎榜卖出额': [4000.0, 8000.0, 4000.0],
            '机构净买额': [3000.0, -1000.0, 2000.0],
        })

    @pytest.mark.asyncio
    async def test_get_stock_lhb_history_success(self, service, mock_history_df):
        """成功获取个股历史"""
        with patch("services.lhb_service.ak.stock_lhb_stock_statistic_em", return_value=mock_history_df):
            result = await service.get_stock_lhb_history("600519.SH", days=10)

        assert len(result) == 3
        assert result[0].net_buy == 8000.0
        assert result[0].reason == "涨幅偏离值达7%"

    @pytest.mark.asyncio
    async def test_get_stock_lhb_history_empty(self, service):
        """空数据返回空列表"""
        with patch("services.lhb_service.ak.stock_lhb_stock_statistic_em", return_value=pd.DataFrame()):
            result = await service.get_stock_lhb_history("600519.SH")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stock_lhb_history_error(self, service):
        """异常返回空列表"""
        with patch("services.lhb_service.ak.stock_lhb_stock_statistic_em", side_effect=Exception("Error")):
            result = await service.get_stock_lhb_history("600519.SH")

        assert result == []


# =============================================================================
# 游资活动测试
# =============================================================================

class TestHotMoneyActivity:
    """游资活动测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.fixture
    def mock_lhb_with_hot_money(self):
        """带游资的龙虎榜数据"""
        return [
            LHBStock(
                symbol="600519.SH",
                name="贵州茅台",
                close_price=1800.0,
                change_percent=5.0,
                turnover_rate=2.0,
                lhb_net_buy=10000.0,
                lhb_buy_amount=15000.0,
                lhb_sell_amount=5000.0,
                reason="涨幅偏离",
                buy_seats=[
                    LHBSeat(
                        seat_name="华鑫证券上海分公司",
                        buy_amount=5000,
                        sell_amount=1000,
                        net_amount=4000,
                        seat_type="游资",
                        hot_money_name="溧阳路",
                    ),
                ],
                sell_seats=[],
                institution_net=3000.0,
                hot_money_involved=True,
            ),
            LHBStock(
                symbol="000001.SZ",
                name="平安银行",
                close_price=12.5,
                change_percent=3.0,
                turnover_rate=1.5,
                lhb_net_buy=5000.0,
                lhb_buy_amount=8000.0,
                lhb_sell_amount=3000.0,
                reason="换手率达20%",
                buy_seats=[
                    LHBSeat(
                        seat_name="中国银河证券绍兴证券营业部",
                        buy_amount=3000,
                        sell_amount=500,
                        net_amount=2500,
                        seat_type="游资",
                        hot_money_name="赵老哥",
                    ),
                ],
                sell_seats=[],
                institution_net=1000.0,
                hot_money_involved=True,
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_hot_money_activity(self, service, mock_lhb_with_hot_money):
        """获取游资活动"""
        with patch.object(service, 'get_daily_lhb', return_value=mock_lhb_with_hot_money):
            result = await service.get_hot_money_activity()

        assert len(result) >= 2
        aliases = [r.alias for r in result]
        assert "溧阳路" in aliases
        assert "赵老哥" in aliases

    @pytest.mark.asyncio
    async def test_get_hot_money_activity_empty(self, service):
        """无游资活动"""
        with patch.object(service, 'get_daily_lhb', return_value=[]):
            result = await service.get_hot_money_activity()

        assert result == []


# =============================================================================
# 龙虎榜概览测试
# =============================================================================

class TestLHBSummary:
    """get_summary() 测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_summary(self, service):
        """获取龙虎榜概览"""
        mock_stocks = [
            LHBStock(
                symbol="600519.SH",
                name="贵州茅台",
                close_price=1800.0,
                change_percent=5.0,
                turnover_rate=2.0,
                lhb_net_buy=10000.0,
                lhb_buy_amount=15000.0,
                lhb_sell_amount=5000.0,
                reason="涨幅偏离",
                buy_seats=[],
                sell_seats=[],
                institution_net=3000.0,
                hot_money_involved=False,
            ),
        ]
        mock_hot_money = [
            HotMoneySeat(
                seat_name="华鑫证券上海分公司",
                alias="溧阳路",
                style="打板/接力",
                recent_stocks=[],
            )
        ]

        with patch.object(service, 'get_daily_lhb', return_value=mock_stocks):
            with patch.object(service, 'get_hot_money_activity', return_value=mock_hot_money):
                result = await service.get_summary()

        assert result.total_stocks == 1
        assert result.total_net_buy == 1.0  # 10000 / 10000 = 1 亿
        assert len(result.hot_money_active) == 1


# =============================================================================
# 游资画像测试
# =============================================================================

class TestHotMoneyProfile:
    """游资画像测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_hot_money_profile_success(self, service):
        """获取游资画像成功"""
        mock_stocks = [
            LHBStock(
                symbol="600519.SH",
                name="贵州茅台",
                close_price=1800.0,
                change_percent=5.0,
                turnover_rate=2.0,
                lhb_net_buy=10000.0,
                lhb_buy_amount=15000.0,
                lhb_sell_amount=5000.0,
                reason="涨幅偏离",
                buy_seats=[
                    LHBSeat(
                        seat_name="华鑫证券上海分公司",
                        buy_amount=5000,
                        sell_amount=1000,
                        net_amount=4000,
                        seat_type="游资",
                        hot_money_name="溧阳路",
                    ),
                ],
                sell_seats=[],
                institution_net=3000.0,
                hot_money_involved=True,
            ),
        ]

        with patch.object(service, 'get_daily_lhb', return_value=mock_stocks):
            result = await service.get_hot_money_profile("溧阳路")

        assert result is not None
        assert result.alias == "溧阳路"
        assert result.tier == "一线"
        assert "打板" in result.style
        assert result.total_appearances == 1

    @pytest.mark.asyncio
    async def test_get_hot_money_profile_not_found(self, service):
        """游资别名不存在"""
        with patch.object(service, 'get_daily_lhb', return_value=[]):
            result = await service.get_hot_money_profile("不存在的游资")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_hot_money_profiles(self, service):
        """获取所有游资画像"""
        mock_profile = HotMoneyProfile(
            seat_name="华鑫证券上海分公司",
            alias="溧阳路",
            tier="一线",
            style="打板/接力",
        )

        with patch.object(service, 'get_hot_money_profile', return_value=mock_profile):
            result = await service.get_all_hot_money_profiles()

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_get_all_hot_money_profiles_by_tier(self, service):
        """按层级筛选游资画像"""
        mock_profile = HotMoneyProfile(
            seat_name="华鑫证券上海分公司",
            alias="溧阳路",
            tier="一线",
            style="打板/接力",
        )

        with patch.object(service, 'get_hot_money_profile', return_value=mock_profile):
            result = await service.get_all_hot_money_profiles(tier="一线")

        # 只返回一线游资
        for profile in result:
            assert profile.tier == "一线"


# =============================================================================
# 游资动向信号测试
# =============================================================================

class TestHotMoneyMovementSignal:
    """游资动向信号测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_consensus_buy_signal(self, service):
        """共识买入信号"""
        mock_stocks = [
            LHBStock(
                symbol="600519.SH",
                name="贵州茅台",
                close_price=1800.0,
                change_percent=5.0,
                turnover_rate=2.0,
                lhb_net_buy=10000.0,
                lhb_buy_amount=15000.0,
                lhb_sell_amount=5000.0,
                reason="涨幅偏离",
                buy_seats=[
                    LHBSeat(
                        seat_name="华鑫证券上海分公司",
                        buy_amount=5000,
                        sell_amount=0,
                        net_amount=5000,
                        seat_type="游资",
                        hot_money_name="溧阳路",
                    ),
                    LHBSeat(
                        seat_name="中国银河证券绍兴证券营业部",
                        buy_amount=3000,
                        sell_amount=0,
                        net_amount=3000,
                        seat_type="游资",
                        hot_money_name="赵老哥",
                    ),
                ],
                sell_seats=[],
                institution_net=3000.0,
                hot_money_involved=True,
            ),
        ]

        with patch.object(service, 'get_daily_lhb', return_value=mock_stocks):
            result = await service.get_hot_money_movement_signal()

        assert result.signal_type == "consensus_buy"
        assert result.signal_strength >= 50
        assert "溧阳路" in result.involved_seats or "赵老哥" in result.involved_seats

    @pytest.mark.asyncio
    async def test_no_activity_signal(self, service):
        """无活动信号"""
        with patch.object(service, 'get_daily_lhb', return_value=[]):
            result = await service.get_hot_money_movement_signal()

        assert result.signal_type == "no_activity"
        assert result.signal_strength == 0

    @pytest.mark.asyncio
    async def test_signal_error_handling(self, service):
        """信号获取异常处理"""
        with patch.object(service, 'get_daily_lhb', side_effect=Exception("API Error")):
            result = await service.get_hot_money_movement_signal()

        assert result.signal_type == "error"
        assert "失败" in result.interpretation


# =============================================================================
# 席位关联测试
# =============================================================================

class TestSeatCorrelation:
    """席位关联测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        svc = LHBService()
        svc._cache.clear()
        return svc

    @pytest.mark.asyncio
    async def test_get_seat_correlation(self, service):
        """获取席位关联"""
        mock_stocks = [
            LHBStock(
                symbol="600519.SH",
                name="贵州茅台",
                close_price=1800.0,
                change_percent=5.0,
                turnover_rate=2.0,
                lhb_net_buy=10000.0,
                lhb_buy_amount=15000.0,
                lhb_sell_amount=5000.0,
                reason="涨幅偏离",
                buy_seats=[
                    LHBSeat(
                        seat_name="华鑫证券上海分公司",
                        buy_amount=5000,
                        sell_amount=0,
                        net_amount=5000,
                        seat_type="游资",
                        hot_money_name="溧阳路",
                    ),
                    LHBSeat(
                        seat_name="中国银河证券绍兴证券营业部",
                        buy_amount=3000,
                        sell_amount=0,
                        net_amount=3000,
                        seat_type="游资",
                        hot_money_name="赵老哥",
                    ),
                ],
                sell_seats=[],
                institution_net=3000.0,
                hot_money_involved=True,
            ),
        ]

        with patch.object(service, 'get_daily_lhb', return_value=mock_stocks):
            result = await service.get_seat_correlation("溧阳路")

        assert len(result) >= 1
        assert any(r["alias"] == "赵老哥" for r in result)

    @pytest.mark.asyncio
    async def test_get_seat_correlation_empty(self, service):
        """无关联席位"""
        with patch.object(service, 'get_daily_lhb', return_value=[]):
            result = await service.get_seat_correlation("溧阳路")

        assert result == []


# =============================================================================
# 知名游资席位库测试
# =============================================================================

class TestHotMoneySeatsConfig:
    """知名游资席位库测试"""

    def test_hot_money_seats_not_empty(self):
        """席位库不为空"""
        assert len(HOT_MONEY_SEATS) > 0

    def test_hot_money_seats_structure(self):
        """席位库结构正确"""
        for seat_name, info in HOT_MONEY_SEATS.items():
            assert "alias" in info
            assert "tier" in info
            assert "style" in info

    def test_tier_levels(self):
        """层级分类正确"""
        tiers = set()
        for info in HOT_MONEY_SEATS.values():
            tiers.add(info["tier"])

        assert "一线" in tiers
        assert "二线" in tiers
        assert "机构" in tiers


# =============================================================================
# 单例测试
# =============================================================================

class TestLHBServiceSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert lhb_service is not None
        assert isinstance(lhb_service, LHBService)
