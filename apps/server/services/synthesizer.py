import json
import structlog
from datetime import datetime
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings

logger = structlog.get_logger()

class ResponseSynthesizer:
    def __init__(self):
        self._llm = None
    
    @property
    def llm(self):
        """Lazy initialization of LLM to avoid requiring API keys at import time."""
        if self._llm is None:
            # Use a fast model for synthesis
            if settings.GOOGLE_API_KEY:
                self._llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=settings.GOOGLE_API_KEY)
            elif settings.OPENAI_API_KEY:
                self._llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)
            else:
                raise ValueError("No API key configured. Set GOOGLE_API_KEY or OPENAI_API_KEY.")
        return self._llm

    async def synthesize(self, symbol: str, agent_reports: Dict[str, str]) -> Dict[str, Any]:
        """
        Synthesize multiple agent Markdown reports into a single aligned JSON object.
        """
        logger.info("Synthesizing agent reports", symbol=symbol)
        
        reports_list = []
        for role, report in agent_reports.items():
            reports_list.append(f"### {role} Report:\n{report}")
        
        reports_combined = "\n\n".join(reports_list)
        
        prompt = f"""
        你是一个金融数据合成专家。请将以下多个 Agent 的分析报告合成一个严格符合 JSON 格式的对象。
        
        股票代码: {symbol}
        
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
          "peers": [{{ "name": "竞争对手", "comparison": "对比描述" }}]
        }}
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
            return result
        except json.JSONDecodeError as e:
            logger.error("Failed to parse synthesized JSON", error=str(e), content=content)
            # Fallback or retry logic could go here
            return {"error": "Synthesis failed", "raw_content": content}

synthesizer = ResponseSynthesizer()
