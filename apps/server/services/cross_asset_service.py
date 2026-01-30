"""跨资产联动分析服务

提供股、债、汇、商品之间的联动分析，包括：
- 资产相关性矩阵
- Risk-On/Risk-Off 模式识别
- 跨资产联动信号
- 市场风险偏好指标
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
import structlog
import asyncio

logger = structlog.get_logger(__name__)


# ============ 数据模型 ============

class AssetPrice(BaseModel):
    """资产价格"""
    symbol: str = Field(description="资产代码")
    name: str = Field(description="资产名称")
    asset_class: str = Field(description="资产类别: equity/bond/fx/commodity/volatility")
    price: float = Field(description="当前价格")
    change_1d: float = Field(default=0, description="日涨跌幅%")
    change_5d: float = Field(default=0, description="5日涨跌幅%")
    change_20d: float = Field(default=0, description="20日涨跌幅%")


class AssetCorrelation(BaseModel):
    """资产相关性"""
    asset1: str = Field(description="资产1")
    asset2: str = Field(description="资产2")
    correlation: float = Field(description="相关系数 -1 到 1")
    period_days: int = Field(description="计算周期（天）")
    interpretation: str = Field(description="解读")


class RiskAppetiteSignal(BaseModel):
    """风险偏好信号"""
    date: date = Field(description="信号日期")
    regime: str = Field(description="市场模式: risk_on/risk_off/neutral")
    score: float = Field(description="风险偏好评分 -100(极度避险) 到 100(极度冒险)")
    confidence: float = Field(description="置信度 0-1")
    supporting_signals: List[str] = Field(description="支持信号")
    contrary_signals: List[str] = Field(description="相反信号")
    interpretation: str = Field(description="解读")


class CrossAssetDivergence(BaseModel):
    """跨资产背离信号"""
    signal_type: str = Field(description="背离类型: stock_bond/stock_fx/commodity_equity")
    description: str = Field(description="背离描述")
    severity: str = Field(description="严重程度: mild/moderate/severe")
    historical_resolution: str = Field(description="历史上类似背离的解决方式")
    trading_implication: str = Field(description="交易含义")


class CrossAssetAnalysisResult(BaseModel):
    """跨资产分析结果"""
    analyzed_at: datetime = Field(default_factory=datetime.now)
    asset_prices: List[AssetPrice] = Field(description="资产价格快照")
    risk_appetite: RiskAppetiteSignal = Field(description="风险偏好信号")
    correlations: List[AssetCorrelation] = Field(description="关键相关性")
    divergences: List[CrossAssetDivergence] = Field(description="背离信号")
    market_narrative: str = Field(description="市场叙事")
    actionable_insights: List[str] = Field(description="可操作建议")


# ============ 核心资产定义 ============

class CoreAssets:
    """核心跟踪资产"""

    # 全球股指
    EQUITY_INDICES = {
        "SPX": {"name": "标普500", "class": "equity", "risk": "risk_on"},
        "NDX": {"name": "纳斯达克100", "class": "equity", "risk": "risk_on"},
        "000001.SH": {"name": "上证指数", "class": "equity", "risk": "risk_on"},
        "399001.SZ": {"name": "深证成指", "class": "equity", "risk": "risk_on"},
        "HSI": {"name": "恒生指数", "class": "equity", "risk": "risk_on"},
    }

    # 债券
    BONDS = {
        "US10Y": {"name": "美国10年期国债收益率", "class": "bond", "risk": "mixed"},
        "US2Y": {"name": "美国2年期国债收益率", "class": "bond", "risk": "mixed"},
        "CN10Y": {"name": "中国10年期国债收益率", "class": "bond", "risk": "mixed"},
    }

    # 汇率
    FX = {
        "DXY": {"name": "美元指数", "class": "fx", "risk": "risk_off"},
        "USDCNY": {"name": "美元/人民币", "class": "fx", "risk": "mixed"},
        "USDJPY": {"name": "美元/日元", "class": "fx", "risk": "risk_on"},
    }

    # 大宗商品
    COMMODITIES = {
        "GOLD": {"name": "黄金", "class": "commodity", "risk": "risk_off"},
        "COPPER": {"name": "铜", "class": "commodity", "risk": "risk_on"},
        "OIL": {"name": "原油", "class": "commodity", "risk": "risk_on"},
    }

    # 波动率
    VOLATILITY = {
        "VIX": {"name": "VIX恐慌指数", "class": "volatility", "risk": "risk_off"},
    }

    @classmethod
    def all_assets(cls) -> Dict[str, Dict]:
        """获取所有资产"""
        return {
            **cls.EQUITY_INDICES,
            **cls.BONDS,
            **cls.FX,
            **cls.COMMODITIES,
            **cls.VOLATILITY,
        }


# ============ 服务类 ============

class CrossAssetService:
    """跨资产联动分析服务"""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 分钟缓存

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

    async def get_asset_prices(self) -> List[AssetPrice]:
        """获取核心资产价格"""
        cache_key = "asset_prices"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        prices = []
        all_assets = CoreAssets.all_assets()

        for symbol, info in all_assets.items():
            try:
                price_data = await self._fetch_asset_price(symbol, info)
                if price_data:
                    prices.append(price_data)
            except Exception as e:
                logger.debug(f"Failed to fetch {symbol}", error=str(e))
                # 使用模拟数据
                prices.append(self._get_mock_price(symbol, info))

        self._set_cache(cache_key, prices)
        return prices

    async def _fetch_asset_price(self, symbol: str, info: Dict) -> Optional[AssetPrice]:
        """从数据源获取资产价格"""
        try:
            import yfinance as yf

            # 转换 symbol 格式
            yf_symbol = self._convert_to_yf_symbol(symbol)
            if not yf_symbol:
                return None

            ticker = yf.Ticker(yf_symbol)
            hist = await asyncio.to_thread(
                ticker.history, period="1mo"
            )

            if hist.empty:
                return None

            current = hist['Close'].iloc[-1]
            prev_1d = hist['Close'].iloc[-2] if len(hist) > 1 else current
            prev_5d = hist['Close'].iloc[-5] if len(hist) > 5 else current
            prev_20d = hist['Close'].iloc[0] if len(hist) >= 20 else current

            return AssetPrice(
                symbol=symbol,
                name=info["name"],
                asset_class=info["class"],
                price=round(current, 2),
                change_1d=round((current / prev_1d - 1) * 100, 2),
                change_5d=round((current / prev_5d - 1) * 100, 2),
                change_20d=round((current / prev_20d - 1) * 100, 2),
            )

        except Exception as e:
            logger.debug(f"yfinance fetch failed for {symbol}", error=str(e))
            return None

    def _convert_to_yf_symbol(self, symbol: str) -> Optional[str]:
        """转换为 yfinance 格式"""
        mapping = {
            "SPX": "^GSPC",
            "NDX": "^NDX",
            "HSI": "^HSI",
            "000001.SH": "000001.SS",
            "399001.SZ": "399001.SZ",
            "US10Y": "^TNX",
            "US2Y": "^IRX",
            "DXY": "DX-Y.NYB",
            "VIX": "^VIX",
            "GOLD": "GC=F",
            "COPPER": "HG=F",
            "OIL": "CL=F",
            "USDCNY": "CNY=X",
            "USDJPY": "JPY=X",
        }
        return mapping.get(symbol)

    def _get_mock_price(self, symbol: str, info: Dict) -> AssetPrice:
        """生成模拟价格数据"""
        mock_prices = {
            "SPX": 5200, "NDX": 18500, "000001.SH": 3100, "399001.SZ": 9500,
            "HSI": 17500, "US10Y": 4.25, "US2Y": 4.60, "CN10Y": 2.30,
            "DXY": 104.5, "USDCNY": 7.25, "USDJPY": 155.0,
            "GOLD": 2350, "COPPER": 4.50, "OIL": 78.0, "VIX": 15.0,
        }
        import random
        base = mock_prices.get(symbol, 100)
        return AssetPrice(
            symbol=symbol,
            name=info["name"],
            asset_class=info["class"],
            price=base,
            change_1d=round(random.uniform(-2, 2), 2),
            change_5d=round(random.uniform(-5, 5), 2),
            change_20d=round(random.uniform(-10, 10), 2),
        )

    async def calculate_risk_appetite(self) -> RiskAppetiteSignal:
        """计算风险偏好信号"""
        cache_key = "risk_appetite"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        prices = await self.get_asset_prices()

        # 构建信号
        risk_on_signals = []
        risk_off_signals = []
        score = 0

        for asset in prices:
            change = asset.change_5d  # 使用5日变化

            if asset.symbol in ["SPX", "NDX", "000001.SH"]:
                # 股指上涨 -> Risk On
                if change > 1:
                    risk_on_signals.append(f"{asset.name} 上涨 {change:.1f}%")
                    score += 15
                elif change < -1:
                    risk_off_signals.append(f"{asset.name} 下跌 {change:.1f}%")
                    score -= 15

            elif asset.symbol == "VIX":
                # VIX 下降 -> Risk On
                if change < -5:
                    risk_on_signals.append(f"VIX 下降 {abs(change):.1f}%，恐慌缓解")
                    score += 20
                elif change > 5:
                    risk_off_signals.append(f"VIX 上升 {change:.1f}%，恐慌加剧")
                    score -= 20

            elif asset.symbol == "GOLD":
                # 黄金上涨 -> Risk Off
                if change > 2:
                    risk_off_signals.append(f"黄金上涨 {change:.1f}%，避险需求上升")
                    score -= 10
                elif change < -2:
                    risk_on_signals.append(f"黄金下跌 {abs(change):.1f}%，避险需求下降")
                    score += 10

            elif asset.symbol == "DXY":
                # 美元走强 -> 混合信号（通常 Risk Off）
                if change > 1:
                    risk_off_signals.append(f"美元走强 {change:.1f}%")
                    score -= 5

            elif asset.symbol == "COPPER":
                # 铜上涨 -> Risk On（经济预期改善）
                if change > 2:
                    risk_on_signals.append(f"铜价上涨 {change:.1f}%，经济预期改善")
                    score += 10
                elif change < -2:
                    risk_off_signals.append(f"铜价下跌 {abs(change):.1f}%，经济预期走弱")
                    score -= 10

            elif asset.symbol == "US10Y":
                # 收益率上升 -> 需要结合原因判断
                if change > 0.1:
                    # 假设是经济向好导致
                    risk_on_signals.append(f"美债收益率上行，经济预期向好")
                    score += 5

        # 确定市场模式
        if score >= 30:
            regime = "risk_on"
            interpretation = "市场风险偏好上升，资金流向风险资产，股市可能继续上涨"
        elif score <= -30:
            regime = "risk_off"
            interpretation = "市场避险情绪浓厚，资金流向避险资产，股市可能承压"
        else:
            regime = "neutral"
            interpretation = "市场情绪中性，缺乏明确方向，建议观望或轻仓操作"

        # 计算置信度
        total_signals = len(risk_on_signals) + len(risk_off_signals)
        if total_signals == 0:
            confidence = 0.3
        else:
            dominant = max(len(risk_on_signals), len(risk_off_signals))
            confidence = min(0.9, 0.5 + (dominant / total_signals) * 0.4)

        signal = RiskAppetiteSignal(
            date=datetime.now().date(),
            regime=regime,
            score=max(-100, min(100, score)),
            confidence=round(confidence, 2),
            supporting_signals=risk_on_signals if score > 0 else risk_off_signals,
            contrary_signals=risk_off_signals if score > 0 else risk_on_signals,
            interpretation=interpretation,
        )

        self._set_cache(cache_key, signal)
        return signal

    async def detect_divergences(self) -> List[CrossAssetDivergence]:
        """检测跨资产背离"""
        prices = await self.get_asset_prices()
        divergences = []

        # 转换为字典便于查找
        price_dict = {p.symbol: p for p in prices}

        # 1. 股债背离：股票涨、债券收益率降（或反过来）
        spx = price_dict.get("SPX")
        us10y = price_dict.get("US10Y")
        if spx and us10y:
            if spx.change_5d > 2 and us10y.change_5d < -0.1:
                divergences.append(CrossAssetDivergence(
                    signal_type="stock_bond",
                    description="股市上涨但债券收益率下降，表明市场对经济前景存在分歧",
                    severity="moderate",
                    historical_resolution="通常以债市向股市靠拢结束（收益率上行）",
                    trading_implication="如果经济数据向好，债券收益率可能补涨，利好银行股",
                ))
            elif spx.change_5d < -2 and us10y.change_5d > 0.1:
                divergences.append(CrossAssetDivergence(
                    signal_type="stock_bond",
                    description="股市下跌但债券收益率上升，表明流动性收紧担忧",
                    severity="moderate",
                    historical_resolution="通常以股市企稳或收益率回落结束",
                    trading_implication="关注美联储政策表态，可能是买入机会",
                ))

        # 2. 股汇背离：A股涨、人民币贬值
        sh = price_dict.get("000001.SH")
        usdcny = price_dict.get("USDCNY")
        if sh and usdcny:
            if sh.change_5d > 2 and usdcny.change_5d > 0.5:
                divergences.append(CrossAssetDivergence(
                    signal_type="stock_fx",
                    description="A股上涨但人民币贬值，可能存在资金外流压力",
                    severity="mild",
                    historical_resolution="通常汇率会在股市稳定后企稳",
                    trading_implication="关注北向资金流向，警惕短期回调风险",
                ))

        # 3. 商品与股票背离：铜跌、股票涨
        copper = price_dict.get("COPPER")
        if spx and copper:
            if spx.change_5d > 2 and copper.change_5d < -3:
                divergences.append(CrossAssetDivergence(
                    signal_type="commodity_equity",
                    description="股市上涨但铜价下跌，经济实际需求可能不如预期",
                    severity="moderate",
                    historical_resolution="关注制造业 PMI 数据验证",
                    trading_implication="股市上涨可能由流动性而非基本面驱动，注意风险",
                ))

        # 4. 黄金与美元背离
        gold = price_dict.get("GOLD")
        dxy = price_dict.get("DXY")
        if gold and dxy:
            if gold.change_5d > 2 and dxy.change_5d > 1:
                divergences.append(CrossAssetDivergence(
                    signal_type="gold_fx",
                    description="黄金和美元同涨，表明全球避险情绪极度升温",
                    severity="severe",
                    historical_resolution="通常出现在地缘政治危机或金融市场剧烈动荡时期",
                    trading_implication="极度避险信号，建议降低风险敞口",
                ))

        return divergences

    def calculate_correlations(self, prices: List[AssetPrice]) -> List[AssetCorrelation]:
        """计算关键资产相关性（简化版，使用短期变化）"""
        correlations = []

        # 关键配对
        pairs = [
            ("SPX", "US10Y", "股债"),
            ("SPX", "VIX", "股波"),
            ("SPX", "GOLD", "股金"),
            ("GOLD", "DXY", "金美"),
            ("000001.SH", "USDCNY", "A股汇率"),
            ("COPPER", "SPX", "铜股"),
        ]

        price_dict = {p.symbol: p for p in prices}

        for sym1, sym2, name in pairs:
            p1 = price_dict.get(sym1)
            p2 = price_dict.get(sym2)
            if not p1 or not p2:
                continue

            # 简化：使用变化方向判断相关性
            c1, c2 = p1.change_5d, p2.change_5d
            if c1 * c2 > 0:
                corr = 0.5 + min(abs(c1), abs(c2)) / 20
            else:
                corr = -0.5 - min(abs(c1), abs(c2)) / 20
            corr = max(-1, min(1, corr))

            if abs(corr) > 0.3:
                if corr > 0:
                    interp = f"{name}正相关，同向波动"
                else:
                    interp = f"{name}负相关，反向波动"

                correlations.append(AssetCorrelation(
                    asset1=sym1,
                    asset2=sym2,
                    correlation=round(corr, 2),
                    period_days=5,
                    interpretation=interp,
                ))

        return correlations

    async def get_full_analysis(self) -> CrossAssetAnalysisResult:
        """获取完整跨资产分析"""
        cache_key = "full_cross_asset"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # 并行获取数据
        prices, risk_appetite, divergences = await asyncio.gather(
            self.get_asset_prices(),
            self.calculate_risk_appetite(),
            self.detect_divergences(),
        )

        correlations = self.calculate_correlations(prices)

        # 生成市场叙事
        narrative = self._generate_narrative(risk_appetite, divergences)

        # 生成可操作建议
        insights = self._generate_insights(risk_appetite, divergences)

        result = CrossAssetAnalysisResult(
            asset_prices=prices,
            risk_appetite=risk_appetite,
            correlations=correlations,
            divergences=divergences,
            market_narrative=narrative,
            actionable_insights=insights,
        )

        self._set_cache(cache_key, result)
        return result

    def _generate_narrative(
        self,
        risk_appetite: RiskAppetiteSignal,
        divergences: List[CrossAssetDivergence]
    ) -> str:
        """生成市场叙事"""
        parts = []

        # 风险偏好叙事
        if risk_appetite.regime == "risk_on":
            parts.append("当前市场处于 Risk-On 模式，投资者风险偏好上升。")
        elif risk_appetite.regime == "risk_off":
            parts.append("当前市场处于 Risk-Off 模式，避险情绪主导。")
        else:
            parts.append("当前市场情绪中性，多空力量相对平衡。")

        # 背离叙事
        if divergences:
            severe = [d for d in divergences if d.severity == "severe"]
            if severe:
                parts.append(f"⚠️ 检测到 {len(severe)} 个严重背离信号，市场可能面临重大转折。")
            else:
                parts.append(f"检测到 {len(divergences)} 个跨资产背离信号，需关注后续演变。")

        return " ".join(parts)

    def _generate_insights(
        self,
        risk_appetite: RiskAppetiteSignal,
        divergences: List[CrossAssetDivergence]
    ) -> List[str]:
        """生成可操作建议"""
        insights = []

        if risk_appetite.regime == "risk_on" and risk_appetite.confidence > 0.6:
            insights.append("✅ 可适当增加股票仓位，关注成长股和周期股")
            insights.append("📉 债券配置可适度降低，关注信用债机会")
        elif risk_appetite.regime == "risk_off" and risk_appetite.confidence > 0.6:
            insights.append("🛡️ 建议降低股票仓位，增配防御性板块")
            insights.append("📈 可增加债券和黄金配置，对冲风险")
        else:
            insights.append("⏸️ 市场方向不明，建议保持中性仓位")
            insights.append("🎯 关注结构性机会，精选个股")

        # 背离相关建议
        for div in divergences[:2]:
            insights.append(f"📊 {div.signal_type} 背离: {div.trading_implication}")

        return insights[:5]


# 单例实例
cross_asset_service = CrossAssetService()
