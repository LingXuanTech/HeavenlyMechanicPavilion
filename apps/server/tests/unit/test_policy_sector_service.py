"""
PolicySectorService 单元测试

覆盖:
1. 数据模型创建
2. 行业名称标准化
3. 分数到情绪转换
4. 行业政策获取
5. 个股政策影响评估
6. 政策文本分析
7. 政策事件管理
8. 批量查询
"""
import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from services.policy_sector_service import (
    PolicySectorService,
    PolicySentiment,
    PolicyStance,
    PolicyEvent,
    SectorPolicy,
    StockSectorMapping,
    SW_LEVEL1_SECTORS,
    CONCEPT_SECTORS,
    POLICY_SENSITIVE_SECTORS,
    policy_sector_service,
)


# =============================================================================
# 数据模型测试
# =============================================================================

class TestPolicyModels:
    """政策数据模型测试"""

    def test_policy_sentiment_values(self):
        """PolicySentiment 枚举值"""
        assert PolicySentiment.STRONG_BULLISH.value == "strong_bullish"
        assert PolicySentiment.BULLISH.value == "bullish"
        assert PolicySentiment.NEUTRAL.value == "neutral"
        assert PolicySentiment.BEARISH.value == "bearish"
        assert PolicySentiment.STRONG_BEARISH.value == "strong_bearish"

    def test_policy_stance_values(self):
        """PolicyStance 枚举值"""
        assert PolicyStance.STRONG_SUPPORT.value == "strong_support"
        assert PolicyStance.SUPPORT.value == "support"
        assert PolicyStance.NEUTRAL.value == "neutral"
        assert PolicyStance.REGULATE.value == "regulate"
        assert PolicyStance.RESTRICT.value == "restrict"

    def test_policy_event_creation(self):
        """创建 PolicyEvent"""
        event = PolicyEvent(
            id="event_001",
            title="央行降准50基点",
            source="央行",
            publish_date=date(2026, 2, 2),
            sectors=["银行", "房地产"],
            sentiment=PolicySentiment.BULLISH,
            sentiment_score=30,
            summary="为支持实体经济发展，央行决定降低存款准备金率0.5个百分点",
            keywords=["降准", "流动性", "实体经济"],
            impact_level="high",
        )

        assert event.id == "event_001"
        assert event.source == "央行"
        assert event.sentiment == PolicySentiment.BULLISH
        assert event.sentiment_score == 30
        assert "银行" in event.sectors

    def test_sector_policy_creation(self):
        """创建 SectorPolicy"""
        policy = SectorPolicy(
            sector_code="801180",
            sector_name="房地产",
            policy_stance=PolicyStance.SUPPORT,
            sentiment_score=20,
            sensitivity=95,
            key_policies=["房住不炒", "因城施策"],
            risks=["债务风险"],
            catalysts=["LPR 下调"],
        )

        assert policy.sector_name == "房地产"
        assert policy.policy_stance == PolicyStance.SUPPORT
        assert policy.sensitivity == 95
        assert "房住不炒" in policy.key_policies

    def test_stock_sector_mapping_creation(self):
        """创建 StockSectorMapping"""
        mapping = StockSectorMapping(
            symbol="600519.SH",
            name="贵州茅台",
            primary_sector="食品饮料",
            secondary_sectors=["白酒"],
            sector_weights={"食品饮料": 1.0},
        )

        assert mapping.symbol == "600519.SH"
        assert mapping.primary_sector == "食品饮料"
        assert mapping.sector_weights["食品饮料"] == 1.0


# =============================================================================
# 行业名称标准化测试
# =============================================================================

class TestNormalizeSectorName:
    """行业名称标准化测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_normalize_real_estate_aliases(self, service):
        """房地产别名标准化"""
        assert service._normalize_sector_name("地产") == "房地产"
        assert service._normalize_sector_name("楼市") == "房地产"
        assert service._normalize_sector_name("房产") == "房地产"
        assert service._normalize_sector_name("房地产") == "房地产"

    def test_normalize_tech_aliases(self, service):
        """科技/互联网别名标准化"""
        assert service._normalize_sector_name("科技") == "互联网"
        assert service._normalize_sector_name("平台") == "互联网"
        assert service._normalize_sector_name("电商") == "互联网"

    def test_normalize_new_energy_aliases(self, service):
        """新能源别名标准化"""
        assert service._normalize_sector_name("光伏") == "新能源"
        assert service._normalize_sector_name("风电") == "新能源"
        assert service._normalize_sector_name("锂电") == "新能源"
        assert service._normalize_sector_name("储能") == "新能源"

    def test_normalize_semiconductor_aliases(self, service):
        """半导体别名标准化"""
        assert service._normalize_sector_name("芯片") == "半导体"
        assert service._normalize_sector_name("集成电路") == "半导体"
        assert service._normalize_sector_name("IC") == "半导体"

    def test_normalize_pharma_aliases(self, service):
        """医药别名标准化"""
        assert service._normalize_sector_name("制药") == "医药生物"
        assert service._normalize_sector_name("生物医药") == "医药生物"
        assert service._normalize_sector_name("医疗") == "医药生物"
        assert service._normalize_sector_name("药品") == "医药生物"

    def test_normalize_unknown_returns_original(self, service):
        """未知行业返回原值"""
        assert service._normalize_sector_name("未知行业") == "未知行业"
        assert service._normalize_sector_name("测试") == "测试"


# =============================================================================
# 分数到情绪转换测试
# =============================================================================

class TestScoreToSentiment:
    """分数到情绪转换测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_strong_bullish(self, service):
        """强烈利好 (>=50)"""
        assert service._score_to_sentiment(50) == PolicySentiment.STRONG_BULLISH
        assert service._score_to_sentiment(80) == PolicySentiment.STRONG_BULLISH
        assert service._score_to_sentiment(100) == PolicySentiment.STRONG_BULLISH

    def test_bullish(self, service):
        """利好 (20-49)"""
        assert service._score_to_sentiment(20) == PolicySentiment.BULLISH
        assert service._score_to_sentiment(35) == PolicySentiment.BULLISH
        assert service._score_to_sentiment(49) == PolicySentiment.BULLISH

    def test_neutral(self, service):
        """中性 (-20 到 19)"""
        assert service._score_to_sentiment(-20) == PolicySentiment.NEUTRAL
        assert service._score_to_sentiment(0) == PolicySentiment.NEUTRAL
        assert service._score_to_sentiment(19) == PolicySentiment.NEUTRAL

    def test_bearish(self, service):
        """利空 (-50 到 -21)"""
        assert service._score_to_sentiment(-50) == PolicySentiment.BEARISH
        assert service._score_to_sentiment(-35) == PolicySentiment.BEARISH
        assert service._score_to_sentiment(-21) == PolicySentiment.BEARISH

    def test_strong_bearish(self, service):
        """强烈利空 (<-50)"""
        assert service._score_to_sentiment(-51) == PolicySentiment.STRONG_BEARISH
        assert service._score_to_sentiment(-80) == PolicySentiment.STRONG_BEARISH
        assert service._score_to_sentiment(-100) == PolicySentiment.STRONG_BEARISH


# =============================================================================
# 行业政策获取测试
# =============================================================================

class TestGetSectorPolicy:
    """行业政策获取测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_get_sector_policy_existing(self, service):
        """获取已配置的行业政策"""
        policy = service.get_sector_policy("房地产")

        assert policy is not None
        assert policy.sector_name == "房地产"
        assert policy.sensitivity == 95
        assert policy.policy_stance == PolicyStance.SUPPORT

    def test_get_sector_policy_via_alias(self, service):
        """通过别名获取行业政策"""
        policy = service.get_sector_policy("地产")

        assert policy is not None
        assert policy.sector_name == "房地产"

    def test_get_sector_policy_nonexistent(self, service):
        """获取不存在的行业政策返回 None"""
        policy = service.get_sector_policy("不存在的行业")

        assert policy is None

    def test_get_sector_policy_semiconductor(self, service):
        """获取半导体政策"""
        policy = service.get_sector_policy("半导体")

        assert policy is not None
        assert policy.policy_stance == PolicyStance.STRONG_SUPPORT
        assert policy.sentiment_score == 50
        assert policy.sensitivity == 90

    def test_get_sector_policy_education(self, service):
        """获取教育政策（利空行业）"""
        policy = service.get_sector_policy("教育")

        assert policy is not None
        assert policy.policy_stance == PolicyStance.RESTRICT
        assert policy.sentiment_score == -50
        assert policy.sensitivity == 98


# =============================================================================
# 申万行业映射测试
# =============================================================================

class TestMapToSWSector:
    """申万行业映射测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_map_direct_match(self, service):
        """直接匹配申万行业"""
        assert service._map_to_sw_sector("银行") == "银行"
        assert service._map_to_sw_sector("房地产") == "房地产"
        assert service._map_to_sw_sector("电子") == "电子"

    def test_map_via_alias(self, service):
        """通过别名匹配"""
        assert service._map_to_sw_sector("煤炭") == "采掘"
        assert service._map_to_sw_sector("白酒") == "食品饮料"
        assert service._map_to_sw_sector("芯片") == "电子"
        assert service._map_to_sw_sector("券商") == "非银金融"

    def test_map_empty_returns_comprehensive(self, service):
        """空值返回综合"""
        assert service._map_to_sw_sector("") == "综合"
        assert service._map_to_sw_sector(None) == "综合"

    def test_map_unknown_returns_comprehensive(self, service):
        """未知行业返回综合"""
        assert service._map_to_sw_sector("未知") == "综合"


# =============================================================================
# 个股政策影响测试
# =============================================================================

class TestGetStockPolicyImpact:
    """个股政策影响评估测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_get_impact_no_mapping(self, service):
        """无行业映射返回 unknown"""
        with patch.object(service, 'get_stock_sectors', return_value=None):
            result = service.get_stock_policy_impact("000000.SZ")

        assert result["policy_impact"] == "unknown"
        assert "无法获取" in result["message"]

    def test_get_impact_with_mapping(self, service):
        """有行业映射返回政策影响"""
        mapping = StockSectorMapping(
            symbol="600519.SH",
            name="贵州茅台",
            primary_sector="食品饮料",
            secondary_sectors=[],
            sector_weights={"食品饮料": 1.0},
        )

        with patch.object(service, 'get_stock_sectors', return_value=mapping):
            result = service.get_stock_policy_impact("600519.SH")

        assert result["symbol"] == "600519.SH"
        assert result["name"] == "贵州茅台"
        assert result["primary_sector"] == "食品饮料"
        # 食品饮料不在 POLICY_SENSITIVE_SECTORS 中，所以返回中性
        assert result["policy_impact"] == "neutral"

    def test_get_impact_real_estate(self, service):
        """房地产行业政策影响"""
        mapping = StockSectorMapping(
            symbol="000002.SZ",
            name="万科A",
            primary_sector="房地产",
            secondary_sectors=[],
            sector_weights={"房地产": 1.0},
        )

        with patch.object(service, 'get_stock_sectors', return_value=mapping):
            result = service.get_stock_policy_impact("000002.SZ")

        assert result["policy_impact"] == "bullish"  # 房地产 sentiment_score=20
        assert result["sentiment_score"] == 20
        assert len(result["key_policies"]) > 0

    def test_get_impact_with_secondary_sectors(self, service):
        """包含关联行业的政策影响"""
        mapping = StockSectorMapping(
            symbol="300750.SZ",
            name="宁德时代",
            primary_sector="新能源",
            secondary_sectors=["半导体"],
            sector_weights={"新能源": 1.0},
        )

        with patch.object(service, 'get_stock_sectors', return_value=mapping):
            result = service.get_stock_policy_impact("300750.SZ")

        # 新能源 60 + 半导体 50 * 0.3 = 75 / 1.3 = 57.69 -> strong_bullish
        assert result["policy_impact"] == "strong_bullish"
        assert len(result["sector_impacts"]) == 2


# =============================================================================
# 政策文本分析测试
# =============================================================================

class TestAnalyzePolicyText:
    """政策文本分析测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_analyze_bullish_text(self, service):
        """分析利好文本"""
        text = "国务院支持新能源汽车发展，加快充电基础设施建设，鼓励企业创新"

        sentiment, score, sectors = service.analyze_policy_text(text)

        assert sentiment in [PolicySentiment.BULLISH, PolicySentiment.STRONG_BULLISH]
        assert score > 0
        # 可能识别出汽车相关行业
        assert isinstance(sectors, list)

    def test_analyze_bearish_text(self, service):
        """分析利空文本"""
        text = "监管部门将严厉打击违规行为，禁止相关业务，整治市场乱象"

        sentiment, score, sectors = service.analyze_policy_text(text)

        assert sentiment in [PolicySentiment.BEARISH, PolicySentiment.STRONG_BEARISH]
        assert score < 0

    def test_analyze_neutral_text(self, service):
        """分析中性文本"""
        text = "今日天气晴朗，适合户外活动"

        sentiment, score, sectors = service.analyze_policy_text(text)

        assert sentiment == PolicySentiment.NEUTRAL
        assert -20 <= score < 20

    def test_analyze_text_identifies_sectors(self, service):
        """识别文本中的行业"""
        text = "央行降准支持银行向房地产企业放贷"

        sentiment, score, sectors = service.analyze_policy_text(text)

        assert "银行" in sectors or "房地产" in sectors

    def test_analyze_score_capped(self, service):
        """分数被限制在 -100 到 100"""
        # 大量利好关键词
        text = "支持 鼓励 促进 补贴 减税 降息 降准 扩大 推动 优化 " * 10

        sentiment, score, sectors = service.analyze_policy_text(text)

        assert score <= 100

    def test_analyze_mixed_text(self, service):
        """分析混合情绪文本"""
        text = "政府支持新能源发展，但同时加强规范监管，限制部分违规企业"

        sentiment, score, sectors = service.analyze_policy_text(text)

        # 利好利空混合，分数取决于关键词权重
        assert isinstance(score, int)


# =============================================================================
# 政策事件管理测试
# =============================================================================

class TestPolicyEventManagement:
    """政策事件管理测试"""

    @pytest.fixture
    def service(self):
        """创建新的服务实例"""
        return PolicySectorService()

    def test_add_policy_event(self, service):
        """添加政策事件"""
        event = PolicyEvent(
            id="test_001",
            title="测试政策",
            source="测试来源",
            publish_date=date.today(),
            sectors=["房地产"],
            sentiment=PolicySentiment.BULLISH,
            sentiment_score=25,
            summary="测试摘要",
            keywords=["测试"],
        )

        service.add_policy_event(event)

        # 验证事件被添加
        assert len(service._policy_events) >= 1
        assert any(e.id == "test_001" for e in service._policy_events)

    def test_add_event_updates_sector(self, service):
        """添加事件更新行业的 recent_events"""
        event = PolicyEvent(
            id="test_002",
            title="房地产政策",
            source="住建部",
            publish_date=date.today(),
            sectors=["房地产"],
            sentiment=PolicySentiment.BULLISH,
            sentiment_score=30,
            summary="放松限购",
            keywords=["限购", "放松"],
        )

        initial_count = len(service._sector_cache["房地产"].recent_events)
        service.add_policy_event(event)

        assert len(service._sector_cache["房地产"].recent_events) == initial_count + 1

    def test_get_recent_events(self, service):
        """获取近期政策事件"""
        # 添加一些事件
        for i in range(3):
            event = PolicyEvent(
                id=f"recent_{i}",
                title=f"政策 {i}",
                source="测试",
                publish_date=date.today(),
                sectors=["银行"],
                sentiment=PolicySentiment.NEUTRAL,
                sentiment_score=0,
                summary=f"摘要 {i}",
                keywords=[],
            )
            service.add_policy_event(event)

        events = service.get_recent_policy_events(days=30, limit=10)

        assert len(events) >= 3

    def test_get_recent_events_filtered_by_sector(self, service):
        """按行业筛选政策事件"""
        # 添加银行事件
        bank_event = PolicyEvent(
            id="bank_event",
            title="银行政策",
            source="央行",
            publish_date=date.today(),
            sectors=["银行"],
            sentiment=PolicySentiment.BULLISH,
            sentiment_score=20,
            summary="银行相关",
            keywords=[],
        )
        service.add_policy_event(bank_event)

        # 添加房地产事件
        real_estate_event = PolicyEvent(
            id="re_event",
            title="房产政策",
            source="住建部",
            publish_date=date.today(),
            sectors=["房地产"],
            sentiment=PolicySentiment.BULLISH,
            sentiment_score=25,
            summary="房产相关",
            keywords=[],
        )
        service.add_policy_event(real_estate_event)

        bank_events = service.get_recent_policy_events(sector="银行")
        re_events = service.get_recent_policy_events(sector="房地产")

        assert all("银行" in e.sectors for e in bank_events)
        assert all("房地产" in e.sectors for e in re_events)


# =============================================================================
# 批量查询测试
# =============================================================================

class TestBatchQueries:
    """批量查询测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PolicySectorService()

    def test_get_all_sector_policies(self, service):
        """获取所有行业政策"""
        policies = service.get_all_sector_policies()

        assert len(policies) > 0
        assert "房地产" in policies
        assert "半导体" in policies
        assert all(isinstance(p, SectorPolicy) for p in policies.values())

    def test_get_sectors_by_sentiment_bullish(self, service):
        """获取利好行业"""
        bullish_sectors = service.get_sectors_by_sentiment(PolicySentiment.BULLISH)

        # 房地产 sentiment_score=20，属于 BULLISH
        assert "房地产" in bullish_sectors
        # 银行 sentiment_score=15，也属于 BULLISH (但 15 < 20 是 NEUTRAL)
        # 需要检查实际值

    def test_get_sectors_by_sentiment_strong_bullish(self, service):
        """获取强烈利好行业"""
        strong_bullish = service.get_sectors_by_sentiment(PolicySentiment.STRONG_BULLISH)

        # 新能源 60, 军工 55, 半导体 50 都是 strong_bullish
        assert "新能源" in strong_bullish
        assert "军工" in strong_bullish
        assert "半导体" in strong_bullish

    def test_get_sectors_by_sentiment_bearish(self, service):
        """获取利空行业"""
        bearish_sectors = service.get_sectors_by_sentiment(PolicySentiment.BEARISH)

        # 教育 -50 是 BEARISH 边界
        assert "教育" in bearish_sectors

    def test_get_high_sensitivity_sectors(self, service):
        """获取高敏感度行业"""
        high_sens = service.get_high_sensitivity_sectors(threshold=80)

        # 教育 98, 房地产 95, 半导体 90 都 >= 80
        sector_names = [s[0] for s in high_sens]
        assert "教育" in sector_names
        assert "房地产" in sector_names
        assert "半导体" in sector_names

        # 验证按敏感度降序排列
        sensitivities = [s[1] for s in high_sens]
        assert sensitivities == sorted(sensitivities, reverse=True)

    def test_get_high_sensitivity_custom_threshold(self, service):
        """自定义敏感度阈值"""
        high_sens_90 = service.get_high_sensitivity_sectors(threshold=90)
        high_sens_70 = service.get_high_sensitivity_sectors(threshold=70)

        # 阈值越低，返回的行业越多
        assert len(high_sens_70) >= len(high_sens_90)


# =============================================================================
# 配置数据验证测试
# =============================================================================

class TestConfigData:
    """配置数据验证测试"""

    def test_sw_sectors_not_empty(self):
        """申万行业列表不为空"""
        assert len(SW_LEVEL1_SECTORS) > 0
        assert len(SW_LEVEL1_SECTORS) == 28  # 申万一级 28 个行业

    def test_sw_sectors_have_code(self):
        """申万行业都有代码"""
        for sector, info in SW_LEVEL1_SECTORS.items():
            assert "code" in info
            assert info["code"].startswith("80")

    def test_concept_sectors_have_related_sw(self):
        """概念板块都有关联申万行业"""
        for concept, info in CONCEPT_SECTORS.items():
            assert "related_sw" in info
            assert len(info["related_sw"]) > 0

    def test_policy_sensitive_sectors_structure(self):
        """政策敏感行业结构正确"""
        for sector, policy in POLICY_SENSITIVE_SECTORS.items():
            assert isinstance(policy, SectorPolicy)
            assert policy.sector_name == sector
            assert -100 <= policy.sentiment_score <= 100
            assert 0 <= policy.sensitivity <= 100


# =============================================================================
# 单例测试
# =============================================================================

class TestPolicySectorServiceSingleton:
    """单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert policy_sector_service is not None
        assert isinstance(policy_sector_service, PolicySectorService)
