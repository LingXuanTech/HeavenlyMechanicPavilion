import json
import hashlib
import structlog
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from config.settings import settings
from services.models import AgentAnalysis

logger = structlog.get_logger()

# 合成结果缓存 {hash: (result, timestamp)}
_synthesis_cache: Dict[str, tuple] = {}
_SYNTHESIS_CACHE_TTL = 60 * 60  # 1 小时缓存


class SynthesisContext:
    """合成上下文，包含用于生成 UI Hints 的额外信息"""

    def __init__(
        self,
        analysis_level: str = "L2",
        task_id: Optional[str] = None,
        elapsed_seconds: Optional[float] = None,
        analysts_used: Optional[List[str]] = None,
        planner_decision: Optional[str] = None,
        planner_reasoning: Optional[str] = None,
        planner_skip_reasons: Optional[Dict[str, str]] = None,
        planner_historical_insight: Optional[str] = None,
        data_quality_issues: Optional[List[str]] = None,
        historical_cases_count: Optional[int] = None,
        market: str = "US",
    ):
        self.analysis_level = analysis_level
        self.task_id = task_id
        self.elapsed_seconds = elapsed_seconds
        self.analysts_used = analysts_used or []
        self.planner_decision = planner_decision
        self.planner_reasoning = planner_reasoning
        self.planner_skip_reasons = planner_skip_reasons or {}
        self.planner_historical_insight = planner_historical_insight
        self.data_quality_issues = data_quality_issues or []
        self.historical_cases_count = historical_cases_count
        self.market = market

    def get_planner_insight(self) -> Optional[str]:
        """构建完整的 Planner 洞察文本，用于前端展示"""
        if not self.planner_decision and not self.planner_reasoning:
            return None

        parts = []

        if self.planner_reasoning:
            parts.append(f"**决策理由**: {self.planner_reasoning}")

        if self.planner_skip_reasons:
            skip_lines = [f"- {analyst}: {reason}" for analyst, reason in self.planner_skip_reasons.items()]
            parts.append(f"**跳过的分析师**:\n" + "\n".join(skip_lines))

        if self.planner_historical_insight:
            parts.append(f"**历史洞察**: {self.planner_historical_insight}")

        if self.analysts_used:
            parts.append(f"**最终使用**: {', '.join(self.analysts_used)}")

        return "\n\n".join(parts) if parts else self.planner_decision


class ResponseSynthesizer:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """通过 ai_config_service 统一获取 LLM"""
        from services.ai_config_service import ai_config_service
        return ai_config_service.get_llm("synthesis")

    def _generate_cache_key(self, symbol: str, agent_reports: Dict[str, str]) -> str:
        """生成报告内容的哈希作为缓存键"""
        # 按键排序确保一致性
        sorted_reports = json.dumps(agent_reports, sort_keys=True, ensure_ascii=False)
        content = f"{symbol}:{sorted_reports}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的合成结果"""
        cached = _synthesis_cache.get(cache_key)
        if cached:
            result, timestamp = cached
            if (datetime.now() - timestamp).total_seconds() < _SYNTHESIS_CACHE_TTL:
                logger.info("Synthesis cache hit", cache_key=cache_key[:8])
                return result
            # 过期缓存，删除
            del _synthesis_cache[cache_key]
        return None

    def _set_cached_result(self, cache_key: str, result: Dict[str, Any]):
        """设置合成结果缓存"""
        _synthesis_cache[cache_key] = (result, datetime.now())
        logger.debug("Synthesis result cached", cache_key=cache_key[:8])

    async def synthesize(
        self,
        symbol: str,
        agent_reports: Dict[str, str],
        context: Optional[SynthesisContext] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize multiple agent Markdown reports into a single aligned JSON object.

        Args:
            symbol: Stock symbol
            agent_reports: Dictionary of agent role -> report content
            context: Optional synthesis context with analysis metadata

        Returns:
            Synthesized JSON object with analysis results and UI hints
        """
        if context is None:
            context = SynthesisContext()

        # 检查缓存（基于报告内容哈希）
        cache_key = self._generate_cache_key(symbol, agent_reports)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            # 更新时间戳和诊断信息
            cached_result = cached_result.copy()
            cached_result["timestamp"] = datetime.now().strftime('%H:%M:%S')
            if "diagnostics" not in cached_result:
                cached_result["diagnostics"] = {}
            cached_result["diagnostics"]["from_cache"] = True
            return cached_result

        logger.info(
            "Synthesizing agent reports",
            symbol=symbol,
            analysis_level=context.analysis_level,
            analysts_count=len(agent_reports),
        )

        reports_list = []
        for role, report in agent_reports.items():
            reports_list.append(f"### {role} Report:\n{report}")

        reports_combined = "\n\n".join(reports_list)

        # 构建上下文信息供 LLM 参考
        context_info = self._build_context_info(context)

        prompt = f"""
        你是一个金融数据合成专家。请将以下多个 Agent 的分析报告合成一个严格符合 JSON 格式的对象。

        股票代码: {symbol}
        分析级别: {context.analysis_level}
        市场: {context.market}

        {context_info}

        报告内容:
        {reports_combined}

        请输出以下结构的 JSON (不要包含 Markdown 代码块标记，只输出纯 JSON):
        {{
          "symbol": "{symbol}",
          "timestamp": "{datetime.now().strftime('%H:%M:%S')}",
          "signal": "Strong Buy/Buy/Hold/Sell/Strong Sell",
          "confidence": 0-100,
          "reasoning": "核心理由总结",
          "anchor_script": "一段专业、亲切的主播口播稿，适合 TTS 朗读，不要包含 Markdown 格式",
          "debate": {{
            "bull": {{ "thesis": "多头核心观点", "points": [{{ "argument": "论点", "evidence": "证据", "weight": "High/Medium/Low" }}] }},
            "bear": {{ "thesis": "空头核心观点", "points": [{{ "argument": "论点", "evidence": "证据", "weight": "High/Medium/Low" }}] }},
            "winner": "Bull/Bear/Neutral",
            "conclusion": "辩论总结"
          }},
          "riskAssessment": {{
            "score": 1-10,
            "volatilityStatus": "Low/Moderate/High/Extreme",
            "liquidityConcerns": false,
            "maxDrawdownRisk": "百分比",
            "verdict": "Approved/Caution/Rejected"
          }},
          "technicalIndicators": {{ "rsi": 50, "macd": "描述", "trend": "Bullish/Bearish/Neutral" }},
          "priceLevels": {{ "support": 0.0, "resistance": 0.0 }},
          "tradeSetup": {{
            "entryZone": "价格区间",
            "targetPrice": 0.0,
            "stopLossPrice": 0.0,
            "rewardToRiskRatio": 0.0,
            "invalidationCondition": "失效条件"
          }},
          "newsAnalysis": [{{ "headline": "标题", "sentiment": "Positive/Negative/Neutral", "summary": "摘要" }}],
          "catalysts": [{{ "name": "催化剂名称", "date": "日期", "impact": "Positive/Negative/Neutral" }}],
          "peers": [{{ "name": "竞争对手", "comparison": "对比描述" }}],
          "chinaMarket": {{
            "retailSentiment": {{
              "fomoLevel": "High/Medium/Low/None",
              "fudLevel": "High/Medium/Low/None",
              "overallMood": "Greedy/Neutral/Fearful",
              "keyIndicators": ["散户情绪指标列表"]
            }},
            "policyAnalysis": {{
              "recentPolicies": ["最新政策列表"],
              "impact": "Positive/Neutral/Negative",
              "riskFactors": ["政策风险因素"],
              "opportunities": ["政策带来的机遇"]
            }}
          }},
          "uiHints": {{
            "alertLevel": "none/info/warning/critical",
            "alertMessage": "警示信息（如有）",
            "highlightSections": ["signal", "risk", "debate", "trade_setup", "news", "planner"],
            "keyMetrics": ["最重要的 3-5 个指标，如 RSI=70, PE=25"],
            "confidenceDisplay": "gauge/progress/badge/number",
            "debateDisplay": {{
              "showWinnerBadge": true,
              "emphasisLevel": "default/prominent/subtle/highlight",
              "expandByDefault": false
            }},
            "showPlannerReasoning": true,
            "plannerInsight": "Planner 选择分析师的理由（如有）",
            "actionSuggestions": ["根据分析给出的行动建议"],
            "analysisLevel": "{context.analysis_level}",
            "marketSpecificHints": ["市场特定提示（如A股政策敏感期）"]
          }}
        }}

        **UI Hints 生成规则:**
        1. alertLevel 规则:
           - critical: 风险评分 >= 8，或存在流动性问题，或信号为 Strong Sell
           - warning: 风险评分 6-7，或波动性为 High/Extreme，或存在数据质量问题
           - info: 有重要催化剂或新闻事件
           - none: 正常情况
        2. highlightSections: 根据分析重点选择 2-3 个需要突出的区域
        3. keyMetrics: 提取最关键的 3-5 个指标（格式: "指标名=值"）
        4. confidenceDisplay:
           - gauge: 置信度 >= 70（高确定性，适合仪表盘展示）
           - progress: 置信度 50-69（中等确定性）
           - badge: 置信度 < 50（低确定性，仅显示标签）
           - number: 默认数字展示
        5. debateDisplay.emphasisLevel:
           - prominent: 辩论结果明确（winner 非 Neutral），建议突出显示
           - highlight: 辩论激烈（多空分歧大），值得关注
           - subtle: 分析结果一边倒，辩论不重要
           - default: 默认展示
        6. actionSuggestions: 基于分析结果给出 1-3 条具体建议

        注意：
        - 如果没有 A股相关的散户情绪或政策分析报告，chinaMarket 字段可以设为 null 或省略
        - uiHints 必须输出，不可省略
        """
        
        response = await self.llm.ainvoke(prompt)
        content = response.content.strip()

        # Clean up potential markdown blocks
        if content.startswith("```json"):
            content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
        elif content.startswith("```"):
            content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
        content = content.strip()

        try:
            result = json.loads(content)

            # 后处理：添加 diagnostics 和补充 uiHints 字段
            result = self._post_process(result, context)

            # Pydantic 结构验证（宽松模式：记录告警但不阻塞）
            try:
                AgentAnalysis.model_validate(result)
            except Exception as validation_err:
                logger.warning(
                    "AgentAnalysis validation warning (non-blocking)",
                    symbol=symbol,
                    error=str(validation_err),
                )

            # 缓存成功的合成结果
            self._set_cached_result(cache_key, result)

            return result
        except json.JSONDecodeError as e:
            logger.error("Failed to parse synthesized JSON", error=str(e), content=content)
            # Fallback or retry logic could go here
            return {"error": "Synthesis failed", "raw_content": content}

    def _build_context_info(self, context: SynthesisContext) -> str:
        """构建上下文信息字符串，供 LLM 参考生成 UI Hints"""
        info_parts = []

        if context.analysts_used:
            info_parts.append(f"使用的分析师: {', '.join(context.analysts_used)}")

        if context.planner_decision:
            info_parts.append(f"Planner 决策: {context.planner_decision}")

        if context.data_quality_issues:
            info_parts.append(f"数据质量问题: {', '.join(context.data_quality_issues)}")

        if context.historical_cases_count is not None:
            info_parts.append(f"相关历史案例数量: {context.historical_cases_count}")

        if not info_parts:
            return ""

        return "**上下文信息:**\n" + "\n".join(f"- {p}" for p in info_parts)

    def _post_process(
        self,
        result: Dict[str, Any],
        context: SynthesisContext,
    ) -> Dict[str, Any]:
        """后处理合成结果，添加 diagnostics 和补充 uiHints 字段"""

        # 添加 diagnostics
        diagnostics = {}
        if context.task_id:
            diagnostics["task_id"] = context.task_id
        if context.elapsed_seconds is not None:
            diagnostics["elapsed_seconds"] = round(context.elapsed_seconds, 2)
        if context.analysts_used:
            diagnostics["analysts_used"] = context.analysts_used
        if context.planner_decision:
            diagnostics["planner_decision"] = context.planner_decision
        if context.planner_reasoning:
            diagnostics["planner_reasoning"] = context.planner_reasoning
        if context.planner_skip_reasons:
            diagnostics["planner_skip_reasons"] = context.planner_skip_reasons

        if diagnostics:
            result["diagnostics"] = diagnostics

        # 确保 uiHints 存在并补充缺失字段
        if "uiHints" not in result:
            result["uiHints"] = self._generate_fallback_ui_hints(result, context)
        else:
            # 补充系统级字段（LLM 可能遗漏）
            ui_hints = result["uiHints"]

            # 数据质量问题（来自 DataValidator，优先级高于 LLM 生成）
            if context.data_quality_issues:
                ui_hints["dataQualityIssues"] = context.data_quality_issues

            # 历史案例数量
            if context.historical_cases_count is not None:
                ui_hints["historicalCasesCount"] = context.historical_cases_count

            # 确保 analysisLevel 正确
            ui_hints["analysisLevel"] = context.analysis_level

            # Planner 决策透明度 - 使用完整洞察
            planner_insight = context.get_planner_insight()
            ui_hints.setdefault("showPlannerReasoning", bool(planner_insight))
            if planner_insight:
                ui_hints["plannerInsight"] = planner_insight

            # 确保关键字段存在
            ui_hints.setdefault("alertLevel", "none")
            ui_hints.setdefault("highlightSections", ["signal"])
            ui_hints.setdefault("keyMetrics", [])
            ui_hints.setdefault("confidenceDisplay", "number")
            ui_hints.setdefault("debateDisplay", {
                "showWinnerBadge": True,
                "emphasisLevel": "default",
                "expandByDefault": False,
            })
            ui_hints.setdefault("actionSuggestions", [])

        return result

    def _generate_fallback_ui_hints(
        self,
        result: Dict[str, Any],
        context: SynthesisContext,
    ) -> Dict[str, Any]:
        """当 LLM 未生成 uiHints 时的降级方案"""

        # 基于 riskAssessment 推断 alertLevel
        risk = result.get("riskAssessment", {})
        risk_score = risk.get("score", 5)
        signal = result.get("signal", "Hold")

        if risk_score >= 8 or signal == "Strong Sell" or risk.get("liquidityConcerns"):
            alert_level = "critical"
            alert_message = "高风险警示：请谨慎评估"
        elif risk_score >= 6 or risk.get("volatilityStatus") in ["High", "Extreme"]:
            alert_level = "warning"
            alert_message = "中等风险提示"
        elif result.get("catalysts"):
            alert_level = "info"
            alert_message = "有重要事件关注"
        else:
            alert_level = "none"
            alert_message = None

        # 基于 confidence 推断显示方式
        confidence = result.get("confidence", 50)
        if confidence >= 70:
            confidence_display = "gauge"
        elif confidence >= 50:
            confidence_display = "progress"
        else:
            confidence_display = "badge"

        # 基于 debate.winner 推断辩论显示
        debate = result.get("debate", {})
        winner = debate.get("winner", "Neutral")
        if winner != "Neutral":
            debate_emphasis = "prominent"
        else:
            debate_emphasis = "default"

        # 提取关键指标
        key_metrics = []
        tech = result.get("technicalIndicators", {})
        if "rsi" in tech:
            key_metrics.append(f"RSI={tech['rsi']}")
        if "trend" in tech:
            key_metrics.append(f"Trend={tech['trend']}")
        key_metrics.append(f"Confidence={confidence}")

        # 获取完整 Planner 洞察
        planner_insight = context.get_planner_insight()

        return {
            "alertLevel": alert_level,
            "alertMessage": alert_message,
            "highlightSections": ["signal", "risk"],
            "keyMetrics": key_metrics,
            "dataQualityIssues": context.data_quality_issues or None,
            "confidenceDisplay": confidence_display,
            "debateDisplay": {
                "showWinnerBadge": winner != "Neutral",
                "emphasisLevel": debate_emphasis,
                "expandByDefault": False,
            },
            "showPlannerReasoning": bool(planner_insight),
            "plannerInsight": planner_insight,
            "actionSuggestions": [],
            "historicalCasesCount": context.historical_cases_count,
            "analysisLevel": context.analysis_level,
            "marketSpecificHints": (
                ["A股市场：注意政策风险"] if context.market == "CN" else None
            ),
        }


synthesizer = ResponseSynthesizer()
