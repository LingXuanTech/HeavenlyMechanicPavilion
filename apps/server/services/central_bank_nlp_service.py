"""央行文本语义分析服务

提供央行报告和讲话的 NLP 分析，包括：
- 鹰派/鸽派倾向识别
- 关键政策信号提取
- 政策变化预测
- 多央行对比分析
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
import structlog
import re
from collections import Counter

logger = structlog.get_logger(__name__)


# ============ 数据模型 ============

class PolicySentiment(BaseModel):
    """政策情绪分析结果"""
    stance: str = Field(description="政策立场: hawkish/dovish/neutral")
    confidence: float = Field(description="置信度 0-1")
    score: float = Field(description="情绪评分 -1(极度鸽派) 到 1(极度鹰派)")
    hawkish_signals: List[str] = Field(description="鹰派信号")
    dovish_signals: List[str] = Field(description="鸽派信号")


class PolicyKeyword(BaseModel):
    """政策关键词"""
    keyword: str = Field(description="关键词")
    count: int = Field(description="出现次数")
    sentiment: str = Field(description="情绪倾向: hawkish/dovish/neutral")
    importance: str = Field(description="重要性: high/medium/low")


class CentralBankStatement(BaseModel):
    """央行声明分析"""
    source: str = Field(description="来源: PBOC/FED/ECB/BOJ")
    date: date = Field(description="发布日期")
    title: str = Field(description="标题")
    sentiment: PolicySentiment = Field(description="情绪分析")
    key_phrases: List[str] = Field(description="关键表述")
    policy_signals: List[str] = Field(description="政策信号")
    market_implications: List[str] = Field(description="市场含义")


class PolicyChangeSignal(BaseModel):
    """政策变化信号"""
    signal_type: str = Field(description="信号类型: rate_hike/rate_cut/qe/qt/forward_guidance")
    probability: float = Field(description="变化概率 0-1")
    timeline: str = Field(description="预期时间线")
    evidence: List[str] = Field(description="支持证据")
    market_impact: str = Field(description="预期市场影响")


class CentralBankAnalysisResult(BaseModel):
    """央行分析结果"""
    analyzed_at: datetime = Field(default_factory=datetime.now)
    statements: List[CentralBankStatement] = Field(description="声明分析")
    overall_stance: str = Field(description="整体立场")
    stance_change: str = Field(description="立场变化: tightening/easing/unchanged")
    policy_outlook: str = Field(description="政策展望")
    change_signals: List[PolicyChangeSignal] = Field(description="变化信号")
    keywords_analysis: List[PolicyKeyword] = Field(description="关键词分析")


# ============ 关键词库 ============

class CentralBankKeywords:
    """央行政策关键词库"""

    # 鹰派关键词（倾向加息/紧缩）
    HAWKISH_KEYWORDS = {
        # 中文 - PBOC
        "收紧": 3, "紧缩": 3, "加息": 3, "上调": 2, "通胀压力": 3,
        "过热": 3, "稳健偏紧": 2, "去杠杆": 2, "防风险": 2,
        "物价上涨": 2, "房价过快": 2, "资产泡沫": 3, "稳杠杆": 1,
        "货币供应量过快": 2, "信贷过快增长": 2, "汇率稳定": 1,

        # 英文 - FED
        "tightening": 3, "hawkish": 3, "rate hike": 3, "inflation": 2,
        "overheating": 3, "restrictive": 2, "tapering": 3,
        "normalize": 2, "price stability": 2, "strong labor": 2,
        "wage pressure": 2, "elevated inflation": 3, "remove accommodation": 3,
        "quantitative tightening": 3, "qt": 2, "balance sheet reduction": 2,
    }

    # 鸽派关键词（倾向降息/宽松）
    DOVISH_KEYWORDS = {
        # 中文 - PBOC
        "宽松": 3, "降息": 3, "降准": 3, "下调": 2, "稳增长": 2,
        "支持实体经济": 2, "流动性合理充裕": 2, "逆周期调节": 2,
        "适度宽松": 3, "降低融资成本": 2, "扩大内需": 2,
        "经济下行压力": 2, "就业压力": 2, "通缩风险": 3,
        "结构性货币政策": 1, "定向降准": 2, "再贷款": 1,

        # 英文 - FED
        "easing": 3, "dovish": 3, "rate cut": 3, "accommodative": 2,
        "support growth": 2, "patient": 2, "flexible": 1,
        "downside risks": 2, "below target": 2, "transitory": 1,
        "employment": 2, "maximum employment": 2, "soft landing": 1,
        "quantitative easing": 3, "qe": 2, "asset purchases": 2,
    }

    # 中性关键词
    NEUTRAL_KEYWORDS = {
        # 中文
        "稳健": 1, "适度": 1, "灵活": 1, "精准": 1, "平稳": 1,
        "观察": 1, "评估": 1, "数据依赖": 1, "相机抉择": 1,

        # 英文
        "balanced": 1, "data-dependent": 1, "gradual": 1,
        "appropriate": 1, "monitor": 1, "assess": 1, "moderate": 1,
    }

    # 政策信号关键词
    POLICY_SIGNALS = {
        # 利率相关
        "利率": "interest_rate", "基准利率": "benchmark_rate",
        "LPR": "lpr", "MLF": "mlf", "逆回购": "reverse_repo",
        "interest rate": "interest_rate", "fed funds": "fed_funds",

        # 流动性相关
        "准备金率": "rrr", "存款准备金": "rrr", "流动性": "liquidity",
        "reserve": "rrr", "liquidity": "liquidity",

        # 资产购买
        "资产购买": "asset_purchase", "国债购买": "bond_purchase",
        "asset purchase": "asset_purchase", "bond buying": "bond_purchase",

        # 前瞻指引
        "前瞻指引": "forward_guidance", "政策路径": "policy_path",
        "forward guidance": "forward_guidance", "outlook": "outlook",
    }


# ============ 服务类 ============

class CentralBankNLPService:
    """央行文本 NLP 分析服务"""

    def __init__(self):
        self.keywords = CentralBankKeywords()
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # 1 小时缓存

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self._cache_ttl

    def _set_cache(self, key: str, value: Any):
        self._cache[key] = value
        self._cache_time[key] = datetime.now()

    def _get_cache(self, key: str) -> Optional[Any]:
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None

    def analyze_sentiment(self, text: str) -> PolicySentiment:
        """分析文本的政策情绪

        Args:
            text: 央行报告或讲话文本

        Returns:
            政策情绪分析结果
        """
        text_lower = text.lower()

        # 统计鹰派/鸽派关键词
        hawkish_score = 0
        dovish_score = 0
        hawkish_signals = []
        dovish_signals = []

        for keyword, weight in self.keywords.HAWKISH_KEYWORDS.items():
            count = len(re.findall(re.escape(keyword.lower()), text_lower))
            if count > 0:
                hawkish_score += count * weight
                hawkish_signals.append(f"{keyword} (x{count})")

        for keyword, weight in self.keywords.DOVISH_KEYWORDS.items():
            count = len(re.findall(re.escape(keyword.lower()), text_lower))
            if count > 0:
                dovish_score += count * weight
                dovish_signals.append(f"{keyword} (x{count})")

        # 计算情绪评分 (-1 到 1)
        total_score = hawkish_score + dovish_score
        if total_score == 0:
            score = 0
            stance = "neutral"
            confidence = 0.3
        else:
            score = (hawkish_score - dovish_score) / total_score
            if score > 0.3:
                stance = "hawkish"
            elif score < -0.3:
                stance = "dovish"
            else:
                stance = "neutral"
            confidence = min(0.95, total_score / 50)

        return PolicySentiment(
            stance=stance,
            confidence=round(confidence, 2),
            score=round(score, 3),
            hawkish_signals=hawkish_signals[:10],
            dovish_signals=dovish_signals[:10],
        )

    def extract_keywords(self, text: str) -> List[PolicyKeyword]:
        """提取政策关键词

        Args:
            text: 文本内容

        Returns:
            关键词列表
        """
        text_lower = text.lower()
        keywords = []

        # 检查所有关键词
        all_keywords = {
            **{k: ("hawkish", w) for k, w in self.keywords.HAWKISH_KEYWORDS.items()},
            **{k: ("dovish", w) for k, w in self.keywords.DOVISH_KEYWORDS.items()},
            **{k: ("neutral", w) for k, w in self.keywords.NEUTRAL_KEYWORDS.items()},
        }

        for keyword, (sentiment, weight) in all_keywords.items():
            count = len(re.findall(re.escape(keyword.lower()), text_lower))
            if count > 0:
                importance = "high" if weight >= 3 else ("medium" if weight >= 2 else "low")
                keywords.append(PolicyKeyword(
                    keyword=keyword,
                    count=count,
                    sentiment=sentiment,
                    importance=importance,
                ))

        # 按出现次数和重要性排序
        importance_order = {"high": 0, "medium": 1, "low": 2}
        keywords.sort(key=lambda x: (importance_order[x.importance], -x.count))
        return keywords[:20]

    def extract_policy_signals(self, text: str) -> List[str]:
        """提取政策信号

        Args:
            text: 文本内容

        Returns:
            政策信号列表
        """
        text_lower = text.lower()
        signals = []

        # 利率相关信号
        if re.search(r'(加息|上调|提高).*(利率|LPR|MLF)', text) or \
           re.search(r'rate.*(hike|increase|raise)', text_lower):
            signals.append("加息预期上升")

        if re.search(r'(降息|下调|降低).*(利率|LPR|MLF)', text) or \
           re.search(r'rate.*(cut|decrease|lower)', text_lower):
            signals.append("降息预期上升")

        # 准备金率信号
        if re.search(r'(下调|降低).*准备金率', text):
            signals.append("降准预期")
        if re.search(r'(上调|提高).*准备金率', text):
            signals.append("上调准备金率预期")

        # 流动性信号
        if re.search(r'流动性.*(充裕|宽松|合理)', text) or \
           re.search(r'(ample|abundant).*(liquidity)', text_lower):
            signals.append("流动性维持宽松")
        if re.search(r'流动性.*(紧张|收紧)', text) or \
           re.search(r'(tight|tighten).*(liquidity)', text_lower):
            signals.append("流动性可能收紧")

        # 通胀相关
        if re.search(r'通胀.*(压力|上行|风险)', text) or \
           re.search(r'inflation.*(pressure|risk|elevated)', text_lower):
            signals.append("通胀担忧上升")
        if re.search(r'通胀.*(可控|温和|回落)', text) or \
           re.search(r'inflation.*(moderate|declining|transitory)', text_lower):
            signals.append("通胀担忧缓解")

        # 经济增长
        if re.search(r'经济.*(下行|放缓|压力)', text) or \
           re.search(r'(economic|growth).*(slow|weak|downside)', text_lower):
            signals.append("经济增长担忧")
        if re.search(r'经济.*(复苏|企稳|向好)', text) or \
           re.search(r'(economic|growth).*(recover|solid|strong)', text_lower):
            signals.append("经济增长信心")

        # 前瞻指引
        if re.search(r'(保持|维持).*(耐心|观察)', text) or \
           re.search(r'(patient|wait|monitor)', text_lower):
            signals.append("政策保持观望")
        if re.search(r'(准备|考虑).*(行动|调整)', text) or \
           re.search(r'(ready|prepared).*(act|adjust)', text_lower):
            signals.append("政策调整在即")

        return signals[:10]

    def analyze_statement(
        self,
        text: str,
        source: str = "PBOC",
        title: str = "",
        statement_date: date = None
    ) -> CentralBankStatement:
        """分析央行声明

        Args:
            text: 声明文本
            source: 来源（PBOC/FED/ECB/BOJ）
            title: 标题
            statement_date: 日期

        Returns:
            声明分析结果
        """
        sentiment = self.analyze_sentiment(text)
        policy_signals = self.extract_policy_signals(text)

        # 生成市场含义
        market_implications = []
        if sentiment.stance == "hawkish":
            market_implications.extend([
                "债券收益率可能上行",
                "股市可能承压，尤其是成长股",
                "银行股可能受益于利差扩大",
            ])
        elif sentiment.stance == "dovish":
            market_implications.extend([
                "债券收益率可能下行",
                "股市可能受益于流动性宽松",
                "房地产等利率敏感板块可能受益",
            ])
        else:
            market_implications.append("市场可能维持震荡格局")

        # 提取关键表述（简化实现：取前几句）
        sentences = re.split(r'[。.!！?？]', text)
        key_phrases = [s.strip() for s in sentences if len(s.strip()) > 20][:5]

        return CentralBankStatement(
            source=source,
            date=statement_date or datetime.now().date(),
            title=title or "央行政策声明",
            sentiment=sentiment,
            key_phrases=key_phrases,
            policy_signals=policy_signals,
            market_implications=market_implications,
        )

    def predict_policy_change(self, text: str) -> List[PolicyChangeSignal]:
        """预测政策变化

        Args:
            text: 文本内容

        Returns:
            政策变化信号列表
        """
        sentiment = self.analyze_sentiment(text)
        signals = []

        # 加息信号
        if sentiment.stance == "hawkish" and sentiment.confidence > 0.5:
            signals.append(PolicyChangeSignal(
                signal_type="rate_hike",
                probability=min(0.8, sentiment.confidence),
                timeline="1-3 个月内",
                evidence=sentiment.hawkish_signals[:3],
                market_impact="利率上行压力，成长股估值承压",
            ))

        # 降息信号
        if sentiment.stance == "dovish" and sentiment.confidence > 0.5:
            signals.append(PolicyChangeSignal(
                signal_type="rate_cut",
                probability=min(0.8, sentiment.confidence),
                timeline="1-3 个月内",
                evidence=sentiment.dovish_signals[:3],
                market_impact="流动性宽松，股债双牛可能",
            ))

        # 根据具体信号添加
        text_lower = text.lower()
        if re.search(r'(缩表|减少.*资产|balance sheet reduction|qt)', text_lower):
            signals.append(PolicyChangeSignal(
                signal_type="qt",
                probability=0.6,
                timeline="3-6 个月内",
                evidence=["提及资产负债表缩减"],
                market_impact="流动性收紧，市场波动可能加大",
            ))

        if re.search(r'(扩表|增加.*资产|asset purchase|qe)', text_lower):
            signals.append(PolicyChangeSignal(
                signal_type="qe",
                probability=0.6,
                timeline="1-3 个月内",
                evidence=["提及资产购买"],
                market_impact="流动性注入，风险资产受益",
            ))

        return signals

    def compare_statements(
        self,
        current_text: str,
        previous_text: str
    ) -> Dict[str, Any]:
        """对比两次声明的变化

        Args:
            current_text: 当前声明
            previous_text: 上次声明

        Returns:
            变化分析
        """
        current = self.analyze_sentiment(current_text)
        previous = self.analyze_sentiment(previous_text)

        score_change = current.score - previous.score
        if score_change > 0.2:
            stance_change = "更加鹰派"
        elif score_change < -0.2:
            stance_change = "更加鸽派"
        else:
            stance_change = "基本不变"

        # 分析新增和删除的关键词
        current_kw = set(kw.keyword for kw in self.extract_keywords(current_text))
        previous_kw = set(kw.keyword for kw in self.extract_keywords(previous_text))

        added_keywords = list(current_kw - previous_kw)
        removed_keywords = list(previous_kw - current_kw)

        return {
            "stance_change": stance_change,
            "score_change": round(score_change, 3),
            "current_stance": current.stance,
            "previous_stance": previous.stance,
            "current_score": current.score,
            "previous_score": previous.score,
            "added_keywords": added_keywords[:10],
            "removed_keywords": removed_keywords[:10],
            "interpretation": self._interpret_change(score_change, added_keywords, removed_keywords),
        }

    def _interpret_change(
        self,
        score_change: float,
        added: List[str],
        removed: List[str]
    ) -> str:
        """解读声明变化"""
        if abs(score_change) < 0.1:
            return "央行政策立场基本维持不变，市场预期平稳。"

        if score_change > 0:
            base = "央行立场转向鹰派"
            if any(k in ["加息", "收紧", "通胀压力", "rate hike"] for k in added):
                return f"{base}，新增加息相关表述，关注货币政策收紧风险。"
            return f"{base}，但尚未释放明确加息信号。"
        else:
            base = "央行立场转向鸽派"
            if any(k in ["降息", "宽松", "降准", "rate cut"] for k in added):
                return f"{base}，新增宽松相关表述，降息/降准概率上升。"
            return f"{base}，但尚未释放明确降息信号。"

    def get_full_analysis(
        self,
        text: str,
        source: str = "PBOC",
        title: str = "",
        previous_text: str = None
    ) -> CentralBankAnalysisResult:
        """获取完整的央行分析

        Args:
            text: 当前声明文本
            source: 来源
            title: 标题
            previous_text: 上次声明（可选，用于对比）

        Returns:
            完整分析结果
        """
        statement = self.analyze_statement(text, source, title)
        change_signals = self.predict_policy_change(text)
        keywords = self.extract_keywords(text)

        # 确定整体立场
        overall_stance = statement.sentiment.stance
        if statement.sentiment.score > 0.5:
            overall_stance = "明显鹰派"
        elif statement.sentiment.score < -0.5:
            overall_stance = "明显鸽派"

        # 确定立场变化
        if previous_text:
            comparison = self.compare_statements(text, previous_text)
            stance_change = comparison["stance_change"]
        else:
            stance_change = "unchanged"

        # 政策展望
        if statement.sentiment.stance == "hawkish":
            outlook = "货币政策可能维持偏紧，关注通胀数据和就业市场变化。"
        elif statement.sentiment.stance == "dovish":
            outlook = "货币政策可能进一步宽松，关注经济数据和流动性状况。"
        else:
            outlook = "货币政策处于观望期，数据依赖特征明显。"

        return CentralBankAnalysisResult(
            statements=[statement],
            overall_stance=overall_stance,
            stance_change=stance_change,
            policy_outlook=outlook,
            change_signals=change_signals,
            keywords_analysis=keywords,
        )


# 单例实例
central_bank_nlp_service = CentralBankNLPService()
