"""
Mock LLM 响应 Fixtures

提供用于测试的标准化 LLM 响应样本。
"""
from typing import Dict, Any


# =============================================================================
# Agent 分析响应样本
# =============================================================================

def get_sample_analyst_response(role: str = "technical") -> str:
    """分析师 Agent 响应样本"""
    responses = {
        "technical": """
## Technical Analysis for AAPL

### Price Action
The stock is currently trading at $150.00, showing a bullish trend with higher highs and higher lows.

### Key Indicators
- **RSI (14)**: 58 - Neutral to slightly bullish
- **MACD**: Bullish crossover, histogram positive
- **Moving Averages**: Price above 20, 50, and 200-day MA

### Support/Resistance
- **Resistance**: $155, $160
- **Support**: $145, $140

### Recommendation
**Buy** with a target of $160 and stop loss at $145.

Confidence: 75%
""",
        "fundamental": """
## Fundamental Analysis for AAPL

### Financial Health
- P/E Ratio: 25.5x (Industry avg: 28x)
- Revenue Growth: 8% YoY
- Profit Margin: 25%

### Valuation
The stock appears fairly valued relative to peers, with strong cash flow generation.

### Competitive Position
Apple maintains a dominant position in the premium smartphone market with strong brand loyalty.

### Recommendation
**Hold** - Fairly valued with limited upside at current levels.

Confidence: 70%
""",
        "news": """
## News Sentiment Analysis for AAPL

### Recent Headlines
1. "Apple Reports Record Q4 Earnings" - Positive
2. "New iPhone Launch Exceeds Expectations" - Positive
3. "Supply Chain Concerns in Asia" - Negative

### Sentiment Score
Overall Sentiment: **Positive** (65% positive, 20% neutral, 15% negative)

### Key Events
- Earnings call scheduled for next week
- Product launch event in March

### Recommendation
News sentiment supports a **Bullish** outlook.

Confidence: 72%
""",
        "social": """
## Social Sentiment Analysis for AAPL

### Reddit Sentiment
- r/wallstreetbets: Bullish mentions up 30%
- r/stocks: Mixed sentiment

### Twitter Metrics
- Mention volume: High
- Sentiment: Slightly positive

### Recommendation
Social sentiment is **Mildly Bullish**.

Confidence: 60%
""",
    }
    return responses.get(role, responses["technical"])


def get_sample_debate_response(side: str = "bull") -> str:
    """辩论 Agent 响应样本"""
    if side == "bull":
        return """
## Bull Case for AAPL

### Key Arguments

1. **Strong Product Pipeline**: iPhone 16 launch exceeded expectations
2. **Services Growth**: Services revenue growing at 15% YoY
3. **AI Integration**: Apple Intelligence gaining traction
4. **Cash Position**: $160B cash enables shareholder returns

### Technical Support
- Price above all major moving averages
- RSI shows room for further upside

### Target Price
$175 (16% upside)

### Conviction Level
HIGH - 82%
"""
    else:
        return """
## Bear Case for AAPL

### Key Concerns

1. **China Risk**: Declining market share in China
2. **Valuation**: P/E premium to historical average
3. **Innovation Slowdown**: Limited differentiation in recent products
4. **Regulatory Headwinds**: App Store scrutiny globally

### Technical Concerns
- RSI approaching overbought territory
- Volume declining on recent rally

### Target Price
$130 (13% downside)

### Conviction Level
MEDIUM - 65%
"""


def get_sample_risk_assessment() -> str:
    """风险评估 Agent 响应样本"""
    return """
## Risk Assessment for AAPL

### Risk Score: 4/10 (Low-Medium)

### Risk Factors

| Factor | Score | Weight | Weighted Score |
|--------|-------|--------|----------------|
| Market Risk | 5 | 0.3 | 1.5 |
| Company Specific | 3 | 0.3 | 0.9 |
| Sector Risk | 4 | 0.2 | 0.8 |
| Macro Risk | 4 | 0.2 | 0.8 |

### Key Risks
1. **Concentration Risk**: iPhone accounts for 50%+ of revenue
2. **Supply Chain**: Dependence on Asian manufacturing
3. **Currency**: Strong USD impacts international sales

### Mitigation
- Diversified services revenue
- Strong balance sheet
- Pricing power

### Recommendation
Proceed with trade. Risk level acceptable for position sizing up to 5% of portfolio.
"""


def get_sample_final_decision() -> str:
    """最终决策 Agent 响应样本"""
    return """
## Final Trading Decision for AAPL

### Signal: STRONG BUY

### Confidence: 78%

### Summary
After analyzing technical, fundamental, news, and social indicators, along with the bull/bear debate, the evidence supports a bullish outlook for AAPL.

### Key Drivers
1. Technical momentum remains strong
2. Fundamentals support current valuation
3. News sentiment is positive
4. Bull case more compelling than bear case

### Trade Setup
- **Entry**: $150.00 (current price)
- **Target 1**: $160.00 (6.7% upside)
- **Target 2**: $170.00 (13.3% upside)
- **Stop Loss**: $142.00 (5.3% downside)
- **Risk/Reward**: 2.5:1

### Position Sizing
Recommended allocation: 3-5% of portfolio

### Timeframe
Medium-term (3-6 months)
"""


# =============================================================================
# 合成器响应样本（JSON 格式）
# =============================================================================

def get_sample_synthesized_analysis() -> Dict[str, Any]:
    """合成后的分析结果 JSON 样本"""
    return {
        "symbol": "AAPL",
        "date": "2026-01-28",
        "signal": "Strong Buy",
        "confidence": 78,
        "entry_price": 150.0,
        "target_price": 160.0,
        "stop_loss": 142.0,
        "risk_reward_ratio": 2.5,
        "summary": "Technical momentum and fundamental strength support bullish outlook.",
        "analysts": {
            "technical": {
                "signal": "Buy",
                "confidence": 75,
                "key_points": ["Price above MAs", "RSI neutral", "MACD bullish"],
            },
            "fundamental": {
                "signal": "Hold",
                "confidence": 70,
                "key_points": ["Fair valuation", "Strong cash flow", "8% revenue growth"],
            },
            "news": {
                "signal": "Bullish",
                "confidence": 72,
                "key_points": ["Positive earnings", "Strong product launch"],
            },
            "social": {
                "signal": "Mildly Bullish",
                "confidence": 60,
                "key_points": ["Reddit bullish", "Twitter positive"],
            },
        },
        "debate": {
            "winner": "Bull",
            "bull_conviction": 82,
            "bear_conviction": 65,
            "key_arguments": {
                "bull": ["Strong pipeline", "Services growth", "AI integration"],
                "bear": ["China risk", "Valuation premium", "Regulatory headwinds"],
            },
        },
        "risk": {
            "score": 4,
            "max_score": 10,
            "level": "Low-Medium",
            "factors": ["Concentration risk", "Supply chain", "Currency"],
            "recommendation": "Proceed with position sizing up to 5%",
        },
    }


def get_sample_anchor_script() -> str:
    """主播稿样本"""
    return """
大家好，欢迎收看今日股市分析。

今天我们来分析苹果公司的股票 AAPL。

从技术面来看，股价目前位于 150 美元，保持在所有主要均线上方，MACD 显示看涨信号。

基本面方面，市盈率 25.5 倍，与行业平均水平相当，服务业务收入增长强劲。

综合多方分析师意见和多空辩论，我们给出"强烈买入"信号，置信度 78%。

建议入场价 150 美元，目标价 160 美元，止损价 142 美元。

风险评估显示整体风险较低，建议仓位控制在 3-5%。

以上就是今天的分析，投资有风险，入市需谨慎。
"""
