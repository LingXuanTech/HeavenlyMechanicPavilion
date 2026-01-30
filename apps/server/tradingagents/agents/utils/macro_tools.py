"""美股宏观经济分析工具

提供美联储利率、通胀、就业数据等宏观经济分析工具。
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
import structlog

try:
    import pandas as pd
except ImportError:
    pd = None

logger = structlog.get_logger(__name__)


def _get_fred_data(series_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
    """从 FRED API 获取数据"""
    import os
    try:
        from fredapi import Fred
        api_key = os.getenv("FRED_API_KEY")
        if not api_key:
            logger.warning("FRED_API_KEY not set, using mock data")
            return _get_mock_fred_data(series_id)

        fred = Fred(api_key=api_key)
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        data = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
        return [
            {"date": str(date.date()), "value": float(value)}
            for date, value in data.items()
            if not pd.isna(value)
        ]
    except ImportError:
        logger.warning("fredapi not installed, using mock data")
        return _get_mock_fred_data(series_id)
    except Exception as e:
        logger.warning("FRED API failed", series_id=series_id, error=str(e))
        return _get_mock_fred_data(series_id)


def _get_mock_fred_data(series_id: str) -> List[Dict[str, Any]]:
    """返回模拟的 FRED 数据"""
    # 模拟数据用于开发和测试
    mock_data = {
        "FEDFUNDS": [  # 联邦基金利率
            {"date": "2025-12-01", "value": 4.33},
            {"date": "2025-11-01", "value": 4.58},
            {"date": "2025-10-01", "value": 4.83},
            {"date": "2025-09-01", "value": 5.08},
            {"date": "2025-08-01", "value": 5.33},
        ],
        "CPIAUCSL": [  # CPI 消费者价格指数
            {"date": "2025-12-01", "value": 315.2},
            {"date": "2025-11-01", "value": 314.8},
            {"date": "2025-10-01", "value": 314.1},
            {"date": "2025-09-01", "value": 313.5},
            {"date": "2025-08-01", "value": 312.8},
        ],
        "UNRATE": [  # 失业率
            {"date": "2025-12-01", "value": 4.2},
            {"date": "2025-11-01", "value": 4.1},
            {"date": "2025-10-01", "value": 4.1},
            {"date": "2025-09-01", "value": 4.0},
            {"date": "2025-08-01", "value": 4.2},
        ],
        "PAYEMS": [  # 非农就业人数（千人）
            {"date": "2025-12-01", "value": 159200},
            {"date": "2025-11-01", "value": 159050},
            {"date": "2025-10-01", "value": 158800},
            {"date": "2025-09-01", "value": 158550},
            {"date": "2025-08-01", "value": 158250},
        ],
        "T10Y2Y": [  # 10年-2年国债收益率差（收益率曲线）
            {"date": "2025-12-01", "value": 0.25},
            {"date": "2025-11-01", "value": 0.15},
            {"date": "2025-10-01", "value": -0.05},
            {"date": "2025-09-01", "value": -0.15},
            {"date": "2025-08-01", "value": -0.25},
        ],
        "GDP": [  # GDP（十亿美元）
            {"date": "2025-10-01", "value": 29500},
            {"date": "2025-07-01", "value": 29200},
            {"date": "2025-04-01", "value": 28900},
            {"date": "2025-01-01", "value": 28600},
        ],
    }
    return mock_data.get(series_id, [])


@tool
def get_fed_rate_data() -> str:
    """获取美联储联邦基金利率历史数据

    Returns:
        联邦基金利率历史数据和趋势分析
    """
    data = _get_fred_data("FEDFUNDS")

    if not data:
        return "无法获取联邦基金利率数据"

    output_lines = ["## 美联储联邦基金利率\n"]

    # 最新数据
    latest = data[0]
    output_lines.append(f"**当前利率**: {latest['value']:.2f}%（{latest['date']}）\n")

    # 历史趋势
    output_lines.append("### 近期走势")
    for item in data[:6]:
        output_lines.append(f"- {item['date']}: {item['value']:.2f}%")

    # 计算变化
    if len(data) >= 2:
        change = data[0]["value"] - data[1]["value"]
        trend = "上升" if change > 0 else "下降" if change < 0 else "持平"
        output_lines.append(f"\n**最近变化**: {change:+.2f}% ({trend})")

    # 市场影响分析
    current_rate = data[0]["value"]
    if current_rate > 5:
        impact = "⚠️ 高利率环境，对成长股估值压力较大，利好银行股息差"
    elif current_rate > 3:
        impact = "📊 中性利率环境，关注降息预期对市场的刺激"
    else:
        impact = "📈 低利率环境，有利于股票估值扩张"

    output_lines.append(f"\n**市场影响**: {impact}")

    return "\n".join(output_lines)


@tool
def get_inflation_data() -> str:
    """获取美国通胀数据（CPI）

    Returns:
        CPI 通胀数据和分析
    """
    data = _get_fred_data("CPIAUCSL")

    if not data or len(data) < 2:
        return "无法获取 CPI 数据"

    output_lines = ["## 美国消费者价格指数（CPI）\n"]

    # 最新数据
    latest = data[0]
    output_lines.append(f"**最新 CPI**: {latest['value']:.1f}（{latest['date']}）\n")

    # 计算同比变化（粗略估计）
    if len(data) >= 12:
        yoy_change = ((data[0]["value"] / data[11]["value"]) - 1) * 100
        output_lines.append(f"**同比变化**: {yoy_change:.1f}%")

    # 计算环比变化
    if len(data) >= 2:
        mom_change = ((data[0]["value"] / data[1]["value"]) - 1) * 100
        output_lines.append(f"**环比变化**: {mom_change:.2f}%\n")

    # 历史数据
    output_lines.append("### 近期走势")
    for item in data[:6]:
        output_lines.append(f"- {item['date']}: {item['value']:.1f}")

    # 通胀分析
    if len(data) >= 12:
        if yoy_change > 4:
            analysis = "⚠️ 通胀较高，美联储可能维持紧缩政策"
        elif yoy_change > 2:
            analysis = "📊 通胀温和，接近美联储 2% 目标"
        else:
            analysis = "📉 通胀较低，有降息空间"
        output_lines.append(f"\n**通胀分析**: {analysis}")

    return "\n".join(output_lines)


@tool
def get_employment_data() -> str:
    """获取美国就业数据（失业率和非农）

    Returns:
        失业率和非农就业数据及分析
    """
    unemployment = _get_fred_data("UNRATE")
    nonfarm = _get_fred_data("PAYEMS")

    output_lines = ["## 美国就业数据\n"]

    # 失业率
    if unemployment:
        latest_ur = unemployment[0]
        output_lines.append(f"### 失业率")
        output_lines.append(f"**当前失业率**: {latest_ur['value']:.1f}%（{latest_ur['date']}）\n")

        for item in unemployment[:4]:
            output_lines.append(f"- {item['date']}: {item['value']:.1f}%")

        # 失业率分析
        if latest_ur["value"] < 4.0:
            ur_analysis = "劳动力市场紧张，可能推高工资通胀"
        elif latest_ur["value"] < 5.0:
            ur_analysis = "劳动力市场健康，充分就业状态"
        else:
            ur_analysis = "失业率偏高，经济放缓信号"
        output_lines.append(f"\n**失业率分析**: {ur_analysis}\n")

    # 非农就业
    if nonfarm and len(nonfarm) >= 2:
        output_lines.append(f"### 非农就业人数")
        latest_nf = nonfarm[0]
        prev_nf = nonfarm[1]
        change = (latest_nf["value"] - prev_nf["value"])

        output_lines.append(f"**最新非农**: {latest_nf['value']/1000:.1f} 百万人（{latest_nf['date']}）")
        output_lines.append(f"**月度新增**: {change:.0f} 千人\n")

        # 非农分析
        if change > 200:
            nf_analysis = "📈 就业强劲增长，经济扩张信号"
        elif change > 100:
            nf_analysis = "📊 就业温和增长，经济稳健"
        elif change > 0:
            nf_analysis = "📉 就业增长放缓，需关注经济动能"
        else:
            nf_analysis = "⚠️ 就业萎缩，经济衰退风险"
        output_lines.append(f"**非农分析**: {nf_analysis}")

    return "\n".join(output_lines)


@tool
def get_yield_curve_data() -> str:
    """获取美国国债收益率曲线数据

    Returns:
        收益率曲线数据（10年-2年利差）和倒挂分析
    """
    data = _get_fred_data("T10Y2Y")

    if not data:
        return "无法获取收益率曲线数据"

    output_lines = ["## 美国国债收益率曲线（10Y-2Y 利差）\n"]

    latest = data[0]
    output_lines.append(f"**当前利差**: {latest['value']:.2f}%（{latest['date']}）\n")

    # 历史数据
    output_lines.append("### 近期走势")
    for item in data[:6]:
        status = "⚠️倒挂" if item["value"] < 0 else "✅正常"
        output_lines.append(f"- {item['date']}: {item['value']:+.2f}% {status}")

    # 倒挂分析
    if latest["value"] < 0:
        analysis = """
⚠️ **收益率曲线倒挂**
- 历史上，收益率曲线倒挂通常领先经济衰退 6-18 个月
- 短端利率高于长端，反映市场预期未来利率下降
- 建议：防御性配置，关注抗周期板块（公用事业、医疗保健）
"""
    elif latest["value"] < 0.5:
        analysis = """
📊 **收益率曲线平坦**
- 曲线接近平坦，市场对经济前景存在分歧
- 密切关注后续走势，若进一步走平需谨慎
"""
    else:
        analysis = """
📈 **收益率曲线正常**
- 曲线正常向上倾斜，经济扩张预期健康
- 有利于银行等依赖息差的金融机构
"""

    output_lines.append(analysis)

    return "\n".join(output_lines)


@tool
def get_us_macro_summary() -> str:
    """获取美国宏观经济综合概览

    Returns:
        美国宏观经济各项指标的综合分析和投资建议
    """
    # 收集各项数据
    fed_rate = _get_fred_data("FEDFUNDS")
    cpi = _get_fred_data("CPIAUCSL")
    unemployment = _get_fred_data("UNRATE")
    yield_curve = _get_fred_data("T10Y2Y")

    output_lines = ["## 美国宏观经济综合概览\n"]
    output_lines.append(f"**更新日期**: {datetime.now().strftime('%Y-%m-%d')}\n")

    # 关键指标摘要
    output_lines.append("### 关键指标")
    output_lines.append("| 指标 | 最新值 | 趋势 |")
    output_lines.append("|------|--------|------|")

    if fed_rate:
        rate_trend = "↓" if len(fed_rate) > 1 and fed_rate[0]["value"] < fed_rate[1]["value"] else "→" if len(fed_rate) > 1 and fed_rate[0]["value"] == fed_rate[1]["value"] else "↑"
        output_lines.append(f"| 联邦基金利率 | {fed_rate[0]['value']:.2f}% | {rate_trend} |")

    if cpi and len(cpi) >= 12:
        yoy_cpi = ((cpi[0]["value"] / cpi[11]["value"]) - 1) * 100
        cpi_trend = "↓" if yoy_cpi < 3 else "→" if yoy_cpi < 4 else "↑"
        output_lines.append(f"| CPI 同比 | {yoy_cpi:.1f}% | {cpi_trend} |")

    if unemployment:
        ur_trend = "↓" if len(unemployment) > 1 and unemployment[0]["value"] < unemployment[1]["value"] else "→" if len(unemployment) > 1 and unemployment[0]["value"] == unemployment[1]["value"] else "↑"
        output_lines.append(f"| 失业率 | {unemployment[0]['value']:.1f}% | {ur_trend} |")

    if yield_curve:
        yc_trend = "↑" if len(yield_curve) > 1 and yield_curve[0]["value"] > yield_curve[1]["value"] else "→" if len(yield_curve) > 1 and yield_curve[0]["value"] == yield_curve[1]["value"] else "↓"
        yc_status = "倒挂" if yield_curve[0]["value"] < 0 else "正常"
        output_lines.append(f"| 收益率曲线 | {yield_curve[0]['value']:+.2f}% ({yc_status}) | {yc_trend} |")

    output_lines.append("")

    # 综合评估
    output_lines.append("### 综合评估")

    # 计算宏观分数
    score = 0
    reasons = []

    if fed_rate and fed_rate[0]["value"] < 4.5:
        score += 1
        reasons.append("利率处于相对宽松区间")
    elif fed_rate and fed_rate[0]["value"] > 5.5:
        score -= 1
        reasons.append("高利率对估值有压制")

    if cpi and len(cpi) >= 12:
        yoy_cpi = ((cpi[0]["value"] / cpi[11]["value"]) - 1) * 100
        if yoy_cpi < 3:
            score += 1
            reasons.append("通胀温和，政策空间大")
        elif yoy_cpi > 4:
            score -= 1
            reasons.append("通胀偏高，政策可能偏紧")

    if unemployment and unemployment[0]["value"] < 4.5:
        score += 1
        reasons.append("就业市场健康")
    elif unemployment and unemployment[0]["value"] > 5.5:
        score -= 1
        reasons.append("失业率偏高，经济放缓")

    if yield_curve and yield_curve[0]["value"] < 0:
        score -= 2
        reasons.append("收益率曲线倒挂，衰退预警")
    elif yield_curve and yield_curve[0]["value"] > 0.5:
        score += 1
        reasons.append("收益率曲线正常")

    # 输出评估结果
    for reason in reasons:
        output_lines.append(f"- {reason}")

    output_lines.append("")

    # 投资建议
    output_lines.append("### 投资建议")
    if score >= 2:
        output_lines.append("**宏观环境评估**: 📈 **有利**")
        output_lines.append("- 建议：可适度增加风险敞口")
        output_lines.append("- 偏好：成长股、周期股")
        output_lines.append("- 规避：过于保守的配置")
    elif score >= 0:
        output_lines.append("**宏观环境评估**: 📊 **中性**")
        output_lines.append("- 建议：均衡配置")
        output_lines.append("- 偏好：优质蓝筹、股息股")
        output_lines.append("- 规避：高杠杆、高估值")
    else:
        output_lines.append("**宏观环境评估**: ⚠️ **谨慎**")
        output_lines.append("- 建议：防御性配置，控制仓位")
        output_lines.append("- 偏好：公用事业、医疗保健、必需消费")
        output_lines.append("- 规避：周期股、高贝塔股")

    return "\n".join(output_lines)


@tool
def calculate_rate_sensitivity(sector: str) -> str:
    """分析特定行业对利率变化的敏感度

    Args:
        sector: 行业名称（如：technology, financials, real_estate, utilities）

    Returns:
        该行业对利率变化的敏感度分析
    """
    # 行业利率敏感度数据库
    sector_sensitivity = {
        "technology": {
            "sensitivity": "高",
            "direction": "负相关",
            "reason": "高成长股依赖远期现金流，贴现率上升对估值影响大",
            "rate_up_impact": "利空 - 估值收缩",
            "rate_down_impact": "利好 - 估值扩张",
            "subsectors": ["软件", "半导体", "云计算"],
        },
        "financials": {
            "sensitivity": "高",
            "direction": "正相关",
            "reason": "银行依赖净息差，保险公司投资收益受益于高利率",
            "rate_up_impact": "利好 - 净息差扩大",
            "rate_down_impact": "利空 - 净息差收窄",
            "subsectors": ["银行", "保险", "券商"],
        },
        "real_estate": {
            "sensitivity": "极高",
            "direction": "负相关",
            "reason": "房地产高度依赖融资成本，利率上升增加购房和开发成本",
            "rate_up_impact": "重大利空 - 融资成本上升",
            "rate_down_impact": "重大利好 - 融资成本下降",
            "subsectors": ["REITs", "房地产开发", "物业管理"],
        },
        "utilities": {
            "sensitivity": "中",
            "direction": "负相关",
            "reason": "公用事业被视为债券替代品，利率上升降低其吸引力",
            "rate_up_impact": "利空 - 相对吸引力下降",
            "rate_down_impact": "利好 - 股息吸引力上升",
            "subsectors": ["电力", "天然气", "水务"],
        },
        "consumer_discretionary": {
            "sensitivity": "中高",
            "direction": "负相关",
            "reason": "消费贷款成本上升抑制大额消费",
            "rate_up_impact": "利空 - 消费信贷成本上升",
            "rate_down_impact": "利好 - 刺激消费",
            "subsectors": ["汽车", "零售", "酒店旅游"],
        },
        "healthcare": {
            "sensitivity": "低",
            "direction": "中性",
            "reason": "医疗需求刚性，受利率影响较小",
            "rate_up_impact": "影响有限",
            "rate_down_impact": "影响有限",
            "subsectors": ["制药", "医疗器械", "医疗服务"],
        },
        "energy": {
            "sensitivity": "低",
            "direction": "中性",
            "reason": "能源价格主要受供需影响，利率敏感度低",
            "rate_up_impact": "间接影响 - 美元走强可能压制油价",
            "rate_down_impact": "间接影响 - 美元走弱可能支撑油价",
            "subsectors": ["石油天然气", "油服", "新能源"],
        },
    }

    # 标准化行业名称
    sector_lower = sector.lower().replace(" ", "_")
    sector_mapping = {
        "tech": "technology",
        "科技": "technology",
        "金融": "financials",
        "banks": "financials",
        "银行": "financials",
        "地产": "real_estate",
        "房地产": "real_estate",
        "reits": "real_estate",
        "公用事业": "utilities",
        "电力": "utilities",
        "可选消费": "consumer_discretionary",
        "消费": "consumer_discretionary",
        "医疗": "healthcare",
        "医药": "healthcare",
        "能源": "energy",
        "石油": "energy",
    }

    normalized_sector = sector_mapping.get(sector_lower, sector_lower)

    if normalized_sector not in sector_sensitivity:
        return f"未找到 '{sector}' 行业的利率敏感度数据。支持的行业：technology, financials, real_estate, utilities, consumer_discretionary, healthcare, energy"

    info = sector_sensitivity[normalized_sector]

    output_lines = [f"## {sector} 行业利率敏感度分析\n"]
    output_lines.append(f"**敏感度等级**: {info['sensitivity']}")
    output_lines.append(f"**与利率关系**: {info['direction']}")
    output_lines.append(f"\n**原因**: {info['reason']}\n")
    output_lines.append(f"### 利率变化影响")
    output_lines.append(f"- **利率上升**: {info['rate_up_impact']}")
    output_lines.append(f"- **利率下降**: {info['rate_down_impact']}")
    output_lines.append(f"\n**相关子行业**: {', '.join(info['subsectors'])}")

    return "\n".join(output_lines)


# ============ 央行 NLP 分析工具 ============

@tool
def analyze_central_bank_text(text: str) -> str:
    """分析央行报告或讲话的政策倾向

    识别文本的鹰派/鸽派倾向，提取政策信号。

    Args:
        text: 央行报告或讲话文本

    Returns:
        政策情绪分析报告
    """
    try:
        from services.central_bank_nlp_service import central_bank_nlp_service

        # 分析情绪
        sentiment = central_bank_nlp_service.analyze_sentiment(text)

        # 提取政策信号
        signals = central_bank_nlp_service.extract_policy_signals(text)

        # 预测政策变化
        changes = central_bank_nlp_service.predict_policy_change(text)

        # 构建报告
        output_lines = ["## 央行文本分析报告\n"]

        # 情绪分析
        stance_emoji = {"hawkish": "🦅", "dovish": "🕊️", "neutral": "➡️"}
        emoji = stance_emoji.get(sentiment.stance, "❓")

        output_lines.append(f"### {emoji} 政策立场: {sentiment.stance.upper()}")
        output_lines.append(f"- **置信度**: {sentiment.confidence:.0%}")
        output_lines.append(f"- **情绪评分**: {sentiment.score:.3f} (-1=极度鸽派, 1=极度鹰派)\n")

        # 鹰派/鸽派信号
        if sentiment.hawkish_signals:
            output_lines.append("### 鹰派信号")
            for s in sentiment.hawkish_signals[:5]:
                output_lines.append(f"- {s}")
            output_lines.append("")

        if sentiment.dovish_signals:
            output_lines.append("### 鸽派信号")
            for s in sentiment.dovish_signals[:5]:
                output_lines.append(f"- {s}")
            output_lines.append("")

        # 政策信号
        if signals:
            output_lines.append("### 政策信号")
            for signal in signals:
                output_lines.append(f"- 📌 {signal}")
            output_lines.append("")

        # 政策变化预测
        if changes:
            output_lines.append("### 政策变化预测")
            for change in changes:
                output_lines.append(
                    f"- **{change.signal_type}**: "
                    f"概率 {change.probability:.0%}，预期 {change.timeline}"
                )
                output_lines.append(f"  市场影响: {change.market_impact}")
            output_lines.append("")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to analyze central bank text", error=str(e))
        return f"央行文本分析失败: {str(e)}"


@tool
def compare_central_bank_statements(current_text: str, previous_text: str) -> str:
    """对比两次央行声明的变化

    分析政策立场的变化趋势。

    Args:
        current_text: 当前声明文本
        previous_text: 上次声明文本

    Returns:
        变化分析报告
    """
    try:
        from services.central_bank_nlp_service import central_bank_nlp_service

        comparison = central_bank_nlp_service.compare_statements(current_text, previous_text)

        output_lines = ["## 央行声明变化分析\n"]

        # 立场变化
        change_emoji = {
            "更加鹰派": "🔼🦅",
            "更加鸽派": "🔽🕊️",
            "基本不变": "➡️",
        }
        emoji = change_emoji.get(comparison["stance_change"], "❓")

        output_lines.append(f"### {emoji} 立场变化: {comparison['stance_change']}")
        output_lines.append(f"- **当前立场**: {comparison['current_stance']} (评分: {comparison['current_score']:.3f})")
        output_lines.append(f"- **上次立场**: {comparison['previous_stance']} (评分: {comparison['previous_score']:.3f})")
        output_lines.append(f"- **评分变化**: {comparison['score_change']:+.3f}\n")

        # 关键词变化
        if comparison["added_keywords"]:
            output_lines.append("### 新增关键词")
            output_lines.append(f"- {', '.join(comparison['added_keywords'][:10])}")
            output_lines.append("")

        if comparison["removed_keywords"]:
            output_lines.append("### 删除关键词")
            output_lines.append(f"- {', '.join(comparison['removed_keywords'][:10])}")
            output_lines.append("")

        # 解读
        output_lines.append("### 变化解读")
        output_lines.append(comparison["interpretation"])

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to compare statements", error=str(e))
        return f"声明对比分析失败: {str(e)}"


# ============ 跨资产联动分析工具 ============

@tool
def get_cross_asset_analysis() -> str:
    """获取跨资产联动分析

    分析股、债、汇、商品之间的联动关系，包括：
    - 核心资产价格快照
    - Risk-On/Risk-Off 模式识别
    - 跨资产背离信号
    - 市场叙事和可操作建议

    Returns:
        跨资产联动分析报告
    """
    try:
        import asyncio
        from services.cross_asset_service import cross_asset_service

        # 运行异步分析
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(cross_asset_service.get_full_analysis())
        finally:
            loop.close()

        output_lines = ["## 跨资产联动分析\n"]
        output_lines.append(f"**分析时间**: {result.analyzed_at.strftime('%Y-%m-%d %H:%M')}\n")

        # 风险偏好
        risk = result.risk_appetite
        regime_emoji = {"risk_on": "📈", "risk_off": "📉", "neutral": "➡️"}
        output_lines.append(f"### {regime_emoji.get(risk.regime, '❓')} 市场风险偏好: {risk.regime.upper()}")
        output_lines.append(f"- **风险评分**: {risk.score:.0f} (-100 极避险 ~ 100 极冒险)")
        output_lines.append(f"- **置信度**: {risk.confidence:.0%}")
        output_lines.append(f"- **解读**: {risk.interpretation}\n")

        # 支持/相反信号
        if risk.supporting_signals:
            output_lines.append("**支持信号**:")
            for s in risk.supporting_signals[:5]:
                output_lines.append(f"- {s}")
            output_lines.append("")

        if risk.contrary_signals:
            output_lines.append("**相反信号**:")
            for s in risk.contrary_signals[:3]:
                output_lines.append(f"- {s}")
            output_lines.append("")

        # 资产价格摘要
        output_lines.append("### 核心资产价格")
        output_lines.append("| 资产 | 价格 | 日涨跌 | 5日涨跌 |")
        output_lines.append("|------|------|--------|---------|")
        for asset in result.asset_prices[:10]:
            change_1d = f"{asset.change_1d:+.1f}%" if asset.change_1d else "-"
            change_5d = f"{asset.change_5d:+.1f}%" if asset.change_5d else "-"
            output_lines.append(f"| {asset.name} | {asset.price:.2f} | {change_1d} | {change_5d} |")
        output_lines.append("")

        # 背离信号
        if result.divergences:
            output_lines.append("### ⚠️ 跨资产背离信号")
            for div in result.divergences:
                severity_emoji = {"severe": "🔴", "moderate": "🟡", "mild": "🟢"}
                output_lines.append(f"**{severity_emoji.get(div.severity, '⚪')} {div.signal_type}**: {div.description}")
                output_lines.append(f"- 历史解决方式: {div.historical_resolution}")
                output_lines.append(f"- 交易含义: {div.trading_implication}")
                output_lines.append("")

        # 市场叙事
        output_lines.append("### 市场叙事")
        output_lines.append(result.market_narrative + "\n")

        # 可操作建议
        output_lines.append("### 可操作建议")
        for insight in result.actionable_insights:
            output_lines.append(f"- {insight}")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get cross asset analysis", error=str(e))
        return f"跨资产分析失败: {str(e)}"


@tool
def get_risk_appetite_signal() -> str:
    """获取市场风险偏好信号

    基于多资产表现判断当前 Risk-On/Risk-Off 状态。

    Returns:
        风险偏好信号分析
    """
    try:
        import asyncio
        from services.cross_asset_service import cross_asset_service

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(cross_asset_service.calculate_risk_appetite())
        finally:
            loop.close()

        output_lines = ["## 市场风险偏好信号\n"]
        output_lines.append(f"**日期**: {result.date}\n")

        regime_map = {
            "risk_on": ("📈 Risk-On", "风险偏好上升，资金流向风险资产"),
            "risk_off": ("📉 Risk-Off", "避险情绪主导，资金流向避险资产"),
            "neutral": ("➡️ 中性", "多空力量平衡，方向不明"),
        }
        regime_label, regime_desc = regime_map.get(result.regime, ("❓", "未知"))

        output_lines.append(f"### {regime_label}")
        output_lines.append(f"**评分**: {result.score:.0f} / 100")
        output_lines.append(f"**置信度**: {result.confidence:.0%}")
        output_lines.append(f"**特征**: {regime_desc}\n")

        output_lines.append("### 解读")
        output_lines.append(result.interpretation + "\n")

        if result.supporting_signals:
            output_lines.append("### 支持信号")
            for s in result.supporting_signals:
                output_lines.append(f"- ✅ {s}")
            output_lines.append("")

        if result.contrary_signals:
            output_lines.append("### 相反信号")
            for s in result.contrary_signals:
                output_lines.append(f"- ⚠️ {s}")

        return "\n".join(output_lines)

    except Exception as e:
        logger.warning("Failed to get risk appetite signal", error=str(e))
        return f"风险偏好信号获取失败: {str(e)}"


# 导出所有工具
MACRO_TOOLS = [
    get_fed_rate_data,
    get_inflation_data,
    get_employment_data,
    get_yield_curve_data,
    get_us_macro_summary,
    calculate_rate_sensitivity,
    analyze_central_bank_text,
    compare_central_bank_statements,
    get_cross_asset_analysis,
    get_risk_appetite_signal,
]
