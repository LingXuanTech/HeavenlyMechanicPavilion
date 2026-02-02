"""
ResponseSynthesizer 单元测试

覆盖:
1. SynthesisContext 数据类方法
2. 缓存机制（生成缓存键、缓存命中/过期）
3. 合成流程（mock LLM）
4. 后处理（diagnostics、uiHints）
5. 降级 UI Hints 生成
"""
import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from services.synthesizer import (
    ResponseSynthesizer,
    SynthesisContext,
    _synthesis_cache,
    _SYNTHESIS_CACHE_TTL,
)


# =============================================================================
# SynthesisContext 测试
# =============================================================================

class TestSynthesisContext:
    """SynthesisContext 数据类测试"""

    def test_default_values(self):
        """测试默认值"""
        ctx = SynthesisContext()
        assert ctx.analysis_level == "L2"
        assert ctx.task_id is None
        assert ctx.elapsed_seconds is None
        assert ctx.analysts_used == []
        assert ctx.planner_decision is None
        assert ctx.data_quality_issues == []
        assert ctx.market == "US"

    def test_custom_values(self):
        """测试自定义值"""
        ctx = SynthesisContext(
            analysis_level="L1",
            task_id="task-123",
            elapsed_seconds=25.5,
            analysts_used=["market", "news"],
            planner_decision="使用快速分析模式",
            market="CN",
        )
        assert ctx.analysis_level == "L1"
        assert ctx.task_id == "task-123"
        assert ctx.elapsed_seconds == 25.5
        assert ctx.analysts_used == ["market", "news"]
        assert ctx.market == "CN"

    def test_get_planner_insight_empty(self):
        """Planner 洞察为空时返回 None"""
        ctx = SynthesisContext()
        assert ctx.get_planner_insight() is None

    def test_get_planner_insight_with_reasoning(self):
        """Planner 洞察包含决策理由"""
        ctx = SynthesisContext(
            planner_reasoning="该股票成交量低，跳过资金流向分析",
            analysts_used=["market", "news", "macro"],
        )
        insight = ctx.get_planner_insight()
        assert "**决策理由**" in insight
        assert "成交量低" in insight
        assert "**最终使用**" in insight
        assert "market" in insight

    def test_get_planner_insight_with_skip_reasons(self):
        """Planner 洞察包含跳过原因"""
        ctx = SynthesisContext(
            planner_decision="自适应选择",
            planner_skip_reasons={
                "fund_flow": "成交量不足",
                "social": "非热门股票",
            },
        )
        insight = ctx.get_planner_insight()
        assert "**跳过的分析师**" in insight
        assert "fund_flow: 成交量不足" in insight
        assert "social: 非热门股票" in insight

    def test_get_planner_insight_with_historical(self):
        """Planner 洞察包含历史洞察"""
        ctx = SynthesisContext(
            planner_decision="使用完整分析",
            planner_historical_insight="历史上该股票在财报季波动较大",
        )
        insight = ctx.get_planner_insight()
        assert "**历史洞察**" in insight
        assert "财报季波动较大" in insight


# =============================================================================
# 缓存机制测试
# =============================================================================

class TestSynthesizerCache:
    """ResponseSynthesizer 缓存机制测试"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """每个测试前清除缓存"""
        _synthesis_cache.clear()
        yield
        _synthesis_cache.clear()

    def test_generate_cache_key_deterministic(self):
        """缓存键应该是确定性的"""
        synth = ResponseSynthesizer()
        reports = {"market": "Report A", "news": "Report B"}

        key1 = synth._generate_cache_key("AAPL", reports)
        key2 = synth._generate_cache_key("AAPL", reports)

        assert key1 == key2
        assert len(key1) == 32  # MD5 hex digest

    def test_generate_cache_key_different_symbol(self):
        """不同股票代码应生成不同的缓存键"""
        synth = ResponseSynthesizer()
        reports = {"market": "Report A"}

        key1 = synth._generate_cache_key("AAPL", reports)
        key2 = synth._generate_cache_key("MSFT", reports)

        assert key1 != key2

    def test_generate_cache_key_different_reports(self):
        """不同报告内容应生成不同的缓存键"""
        synth = ResponseSynthesizer()

        key1 = synth._generate_cache_key("AAPL", {"market": "Report A"})
        key2 = synth._generate_cache_key("AAPL", {"market": "Report B"})

        assert key1 != key2

    def test_generate_cache_key_order_independent(self):
        """报告顺序不应影响缓存键"""
        synth = ResponseSynthesizer()

        key1 = synth._generate_cache_key("AAPL", {"a": "1", "b": "2"})
        key2 = synth._generate_cache_key("AAPL", {"b": "2", "a": "1"})

        assert key1 == key2

    def test_get_cached_result_miss(self):
        """缓存未命中返回 None"""
        synth = ResponseSynthesizer()
        result = synth._get_cached_result("nonexistent_key")
        assert result is None

    def test_set_and_get_cached_result(self):
        """设置和获取缓存"""
        synth = ResponseSynthesizer()
        test_result = {"signal": "Strong Buy", "confidence": 85}

        synth._set_cached_result("test_key", test_result)
        cached = synth._get_cached_result("test_key")

        assert cached == test_result

    def test_cache_expiry(self):
        """缓存过期测试"""
        synth = ResponseSynthesizer()
        test_result = {"signal": "Hold"}

        # 直接操作缓存，设置过期时间戳
        expired_time = datetime.now() - timedelta(seconds=_SYNTHESIS_CACHE_TTL + 1)
        _synthesis_cache["expired_key"] = (test_result, expired_time)

        cached = synth._get_cached_result("expired_key")
        assert cached is None
        assert "expired_key" not in _synthesis_cache  # 过期缓存应被删除


# =============================================================================
# 合成流程测试
# =============================================================================

class TestSynthesizerSynthesize:
    """ResponseSynthesizer.synthesize() 测试"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """每个测试前清除缓存"""
        _synthesis_cache.clear()
        yield
        _synthesis_cache.clear()

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM 响应"""
        return {
            "symbol": "AAPL",
            "timestamp": "14:30:00",
            "signal": "Strong Buy",
            "confidence": 85,
            "reasoning": "Strong technical indicators and positive news",
            "anchor_script": "今天我们分析了苹果公司...",
            "debate": {
                "bull": {"thesis": "看涨观点", "points": []},
                "bear": {"thesis": "看跌观点", "points": []},
                "winner": "Bull",
                "conclusion": "多方胜出",
            },
            "riskAssessment": {
                "score": 4,
                "volatilityStatus": "Moderate",
                "liquidityConcerns": False,
                "maxDrawdownRisk": "10%",
                "verdict": "Approved",
            },
            "technicalIndicators": {"rsi": 65, "macd": "Bullish", "trend": "Bullish"},
            "priceLevels": {"support": 170.0, "resistance": 190.0},
            "tradeSetup": {
                "entryZone": "175-180",
                "targetPrice": 195.0,
                "stopLossPrice": 165.0,
                "rewardToRiskRatio": 2.5,
                "invalidationCondition": "跌破 165",
            },
            "newsAnalysis": [],
            "catalysts": [],
            "uiHints": {
                "alertLevel": "none",
                "highlightSections": ["signal", "trade_setup"],
                "keyMetrics": ["RSI=65", "Confidence=85"],
                "confidenceDisplay": "gauge",
                "debateDisplay": {
                    "showWinnerBadge": True,
                    "emphasisLevel": "prominent",
                    "expandByDefault": False,
                },
                "showPlannerReasoning": False,
                "actionSuggestions": ["考虑分批建仓"],
                "analysisLevel": "L2",
            },
        }

    @pytest.mark.asyncio
    async def test_synthesize_success(self, mock_llm_response):
        """成功合成测试"""
        synth = ResponseSynthesizer()

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(
            content=json.dumps(mock_llm_response)
        )

        with patch(
            "services.ai_config_service.AIConfigService.get_llm",
            return_value=mock_llm,
        ):
            result = await synth.synthesize(
                symbol="AAPL",
                agent_reports={"market": "Market report...", "news": "News report..."},
                context=SynthesisContext(task_id="test-123", elapsed_seconds=30.0),
            )

        assert result["symbol"] == "AAPL"
        assert result["signal"] == "Strong Buy"
        assert result["confidence"] == 85
        assert "diagnostics" in result
        assert result["diagnostics"]["task_id"] == "test-123"
        assert result["diagnostics"]["elapsed_seconds"] == 30.0

    @pytest.mark.asyncio
    async def test_synthesize_cache_hit(self, mock_llm_response):
        """缓存命中测试 - LLM 不应被调用"""
        synth = ResponseSynthesizer()
        reports = {"market": "Report A"}

        # 预填充缓存
        cache_key = synth._generate_cache_key("AAPL", reports)
        synth._set_cached_result(cache_key, mock_llm_response)

        mock_llm = AsyncMock()

        with patch(
            "services.ai_config_service.AIConfigService.get_llm",
            return_value=mock_llm,
        ):
            result = await synth.synthesize(
                symbol="AAPL",
                agent_reports=reports,
            )

        # LLM 不应被调用
        mock_llm.ainvoke.assert_not_called()

        # 应返回缓存结果（带更新的时间戳和 from_cache 标记）
        assert result["diagnostics"]["from_cache"] is True

    @pytest.mark.asyncio
    async def test_synthesize_json_cleanup(self):
        """测试 JSON 代码块清理"""
        synth = ResponseSynthesizer()

        # 模拟 LLM 返回带代码块标记的 JSON
        json_with_markdown = '```json\n{"symbol": "AAPL", "signal": "Hold", "confidence": 50}\n```'

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content=json_with_markdown)

        with patch(
            "services.ai_config_service.AIConfigService.get_llm",
            return_value=mock_llm,
        ):
            with patch('services.synthesizer.AgentAnalysis') as mock_model:
                mock_model.model_validate.return_value = None
                result = await synth.synthesize(
                    symbol="AAPL",
                    agent_reports={"market": "Report"},
                )

        assert result["symbol"] == "AAPL"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_synthesize_invalid_json(self):
        """无效 JSON 返回错误"""
        synth = ResponseSynthesizer()

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="This is not JSON")

        with patch(
            "services.ai_config_service.AIConfigService.get_llm",
            return_value=mock_llm,
        ):
            result = await synth.synthesize(
                symbol="AAPL",
                agent_reports={"market": "Report"},
            )

        assert "error" in result
        assert result["error"] == "Synthesis failed"
        assert "raw_content" in result


# =============================================================================
# 后处理测试
# =============================================================================

class TestSynthesizerPostProcess:
    """ResponseSynthesizer._post_process() 测试"""

    def test_post_process_adds_diagnostics(self):
        """后处理添加 diagnostics"""
        synth = ResponseSynthesizer()

        result = {"signal": "Hold"}
        context = SynthesisContext(
            task_id="task-456",
            elapsed_seconds=45.5,
            analysts_used=["market", "news"],
            planner_decision="自适应选择",
            planner_reasoning="基于成交量决策",
        )

        processed = synth._post_process(result, context)

        assert "diagnostics" in processed
        assert processed["diagnostics"]["task_id"] == "task-456"
        assert processed["diagnostics"]["elapsed_seconds"] == 45.5
        assert processed["diagnostics"]["analysts_used"] == ["market", "news"]
        assert processed["diagnostics"]["planner_decision"] == "自适应选择"
        assert processed["diagnostics"]["planner_reasoning"] == "基于成交量决策"

    def test_post_process_supplements_ui_hints(self):
        """后处理补充 uiHints 缺失字段"""
        synth = ResponseSynthesizer()

        result = {
            "signal": "Buy",
            "uiHints": {
                "alertLevel": "info",
            },
        }
        context = SynthesisContext(
            analysis_level="L1",
            data_quality_issues=["price_deviation"],
            historical_cases_count=5,
        )

        processed = synth._post_process(result, context)

        ui_hints = processed["uiHints"]
        assert ui_hints["alertLevel"] == "info"  # 保留原值
        assert ui_hints["analysisLevel"] == "L1"  # 覆盖为正确值
        assert ui_hints["dataQualityIssues"] == ["price_deviation"]
        assert ui_hints["historicalCasesCount"] == 5
        # 确保默认值存在
        assert "highlightSections" in ui_hints
        assert "keyMetrics" in ui_hints
        assert "confidenceDisplay" in ui_hints
        assert "debateDisplay" in ui_hints

    def test_post_process_generates_fallback_ui_hints(self):
        """无 uiHints 时生成降级版本"""
        synth = ResponseSynthesizer()

        result = {"signal": "Hold", "confidence": 60}
        context = SynthesisContext()

        processed = synth._post_process(result, context)

        assert "uiHints" in processed
        assert processed["uiHints"]["alertLevel"] == "none"


# =============================================================================
# 降级 UI Hints 生成测试
# =============================================================================

class TestFallbackUIHints:
    """ResponseSynthesizer._generate_fallback_ui_hints() 测试"""

    def test_critical_alert_high_risk(self):
        """高风险评分触发 critical 警示"""
        synth = ResponseSynthesizer()
        result = {"riskAssessment": {"score": 9}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["alertLevel"] == "critical"
        assert "高风险" in hints["alertMessage"]

    def test_critical_alert_strong_sell(self):
        """Strong Sell 信号触发 critical 警示"""
        synth = ResponseSynthesizer()
        result = {"signal": "Strong Sell", "riskAssessment": {"score": 5}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["alertLevel"] == "critical"

    def test_critical_alert_liquidity_concerns(self):
        """流动性问题触发 critical 警示"""
        synth = ResponseSynthesizer()
        result = {"riskAssessment": {"score": 4, "liquidityConcerns": True}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["alertLevel"] == "critical"

    def test_warning_alert_moderate_risk(self):
        """中等风险触发 warning 警示"""
        synth = ResponseSynthesizer()
        result = {"riskAssessment": {"score": 7}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["alertLevel"] == "warning"

    def test_warning_alert_high_volatility(self):
        """高波动触发 warning 警示"""
        synth = ResponseSynthesizer()
        result = {"riskAssessment": {"score": 4, "volatilityStatus": "High"}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["alertLevel"] == "warning"

    def test_info_alert_catalysts(self):
        """有催化剂触发 info 警示"""
        synth = ResponseSynthesizer()
        result = {
            "riskAssessment": {"score": 4},
            "catalysts": [{"name": "Earnings", "date": "2026-02-15"}],
        }
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["alertLevel"] == "info"

    def test_confidence_display_gauge(self):
        """高置信度使用 gauge 显示"""
        synth = ResponseSynthesizer()
        result = {"confidence": 85}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["confidenceDisplay"] == "gauge"

    def test_confidence_display_progress(self):
        """中置信度使用 progress 显示"""
        synth = ResponseSynthesizer()
        result = {"confidence": 55}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["confidenceDisplay"] == "progress"

    def test_confidence_display_badge(self):
        """低置信度使用 badge 显示"""
        synth = ResponseSynthesizer()
        result = {"confidence": 40}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["confidenceDisplay"] == "badge"

    def test_debate_emphasis_prominent(self):
        """非 Neutral 胜者使用 prominent 强调"""
        synth = ResponseSynthesizer()
        result = {"debate": {"winner": "Bull"}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["debateDisplay"]["emphasisLevel"] == "prominent"
        assert hints["debateDisplay"]["showWinnerBadge"] is True

    def test_debate_emphasis_default(self):
        """Neutral 胜者使用 default 强调"""
        synth = ResponseSynthesizer()
        result = {"debate": {"winner": "Neutral"}}
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["debateDisplay"]["emphasisLevel"] == "default"
        assert hints["debateDisplay"]["showWinnerBadge"] is False

    def test_key_metrics_extraction(self):
        """关键指标提取"""
        synth = ResponseSynthesizer()
        result = {
            "confidence": 75,
            "technicalIndicators": {"rsi": 68, "trend": "Bullish"},
        }
        context = SynthesisContext()

        hints = synth._generate_fallback_ui_hints(result, context)

        assert "RSI=68" in hints["keyMetrics"]
        assert "Trend=Bullish" in hints["keyMetrics"]
        assert "Confidence=75" in hints["keyMetrics"]

    def test_market_specific_hints_cn(self):
        """A股市场特定提示"""
        synth = ResponseSynthesizer()
        result = {}
        context = SynthesisContext(market="CN")

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["marketSpecificHints"] is not None
        assert "A股" in hints["marketSpecificHints"][0]

    def test_market_specific_hints_us(self):
        """美股无市场特定提示"""
        synth = ResponseSynthesizer()
        result = {}
        context = SynthesisContext(market="US")

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["marketSpecificHints"] is None

    def test_planner_insight_included(self):
        """Planner 洞察包含在提示中"""
        synth = ResponseSynthesizer()
        result = {}
        context = SynthesisContext(
            planner_reasoning="使用轻量分析",
            analysts_used=["market"],
        )

        hints = synth._generate_fallback_ui_hints(result, context)

        assert hints["showPlannerReasoning"] is True
        assert hints["plannerInsight"] is not None
        assert "轻量分析" in hints["plannerInsight"]


# =============================================================================
# 上下文信息构建测试
# =============================================================================

class TestBuildContextInfo:
    """ResponseSynthesizer._build_context_info() 测试"""

    def test_empty_context(self):
        """空上下文返回空字符串"""
        synth = ResponseSynthesizer()
        context = SynthesisContext()

        info = synth._build_context_info(context)

        assert info == ""

    def test_context_with_analysts(self):
        """包含分析师信息"""
        synth = ResponseSynthesizer()
        context = SynthesisContext(analysts_used=["market", "news"])

        info = synth._build_context_info(context)

        assert "使用的分析师" in info
        assert "market" in info
        assert "news" in info

    def test_context_with_planner_decision(self):
        """包含 Planner 决策"""
        synth = ResponseSynthesizer()
        context = SynthesisContext(planner_decision="快速分析模式")

        info = synth._build_context_info(context)

        assert "Planner 决策" in info
        assert "快速分析模式" in info

    def test_context_with_data_quality_issues(self):
        """包含数据质量问题"""
        synth = ResponseSynthesizer()
        context = SynthesisContext(data_quality_issues=["price_mismatch", "stale_data"])

        info = synth._build_context_info(context)

        assert "数据质量问题" in info
        assert "price_mismatch" in info

    def test_context_with_historical_cases(self):
        """包含历史案例数量"""
        synth = ResponseSynthesizer()
        context = SynthesisContext(historical_cases_count=12)

        info = synth._build_context_info(context)

        assert "相关历史案例数量" in info
        assert "12" in info
