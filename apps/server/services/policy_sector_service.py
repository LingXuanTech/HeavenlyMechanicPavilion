"""
政策-行业板块映射服务

提供：
1. A股行业板块分类与映射
2. 个股-行业关联
3. 政策情绪量化评分
4. 政策事件追踪与历史记录
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import structlog
import re

logger = structlog.get_logger(__name__)


class PolicySentiment(str, Enum):
    """政策情绪分类"""
    STRONG_BULLISH = "strong_bullish"   # 重大利好
    BULLISH = "bullish"                 # 利好
    NEUTRAL = "neutral"                 # 中性
    BEARISH = "bearish"                 # 利空
    STRONG_BEARISH = "strong_bearish"   # 重大利空


class PolicyStance(str, Enum):
    """政策立场"""
    STRONG_SUPPORT = "strong_support"   # 强力支持
    SUPPORT = "support"                 # 支持
    NEUTRAL = "neutral"                 # 中性/观望
    REGULATE = "regulate"               # 规范监管
    RESTRICT = "restrict"               # 限制打压


@dataclass
class PolicyEvent:
    """政策事件"""
    id: str
    title: str
    source: str                         # 发布机构（央行/证监会/发改委/国务院等）
    publish_date: date
    sectors: List[str]                  # 影响的行业板块
    sentiment: PolicySentiment          # 政策情绪
    sentiment_score: int                # 情绪分数 (-100 到 +100)
    summary: str                        # 政策摘要
    keywords: List[str]                 # 关键词
    url: Optional[str] = None
    impact_level: str = "medium"        # high/medium/low


@dataclass
class SectorPolicy:
    """行业政策状态"""
    sector_code: str                    # 行业代码
    sector_name: str                    # 行业名称
    policy_stance: PolicyStance         # 当前政策立场
    sentiment_score: int                # 综合情绪分数 (-100 到 +100)
    sensitivity: int                    # 政策敏感度 (0-100)
    key_policies: List[str]             # 核心政策列表
    risks: List[str]                    # 主要风险
    catalysts: List[str]                # 潜在催化剂
    recent_events: List[PolicyEvent] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class StockSectorMapping:
    """股票-行业映射"""
    symbol: str
    name: str
    primary_sector: str                 # 主行业
    secondary_sectors: List[str]        # 关联行业
    sector_weights: Dict[str, float]    # 行业权重


# ============ 行业板块定义 ============

# 申万一级行业分类（28个）
SW_LEVEL1_SECTORS = {
    "农林牧渔": {"code": "801010", "aliases": ["农业", "畜牧", "养殖", "种植"]},
    "采掘": {"code": "801020", "aliases": ["煤炭", "石油", "矿业", "能源"]},
    "化工": {"code": "801030", "aliases": ["化学", "石化", "农化"]},
    "钢铁": {"code": "801040", "aliases": ["钢材", "冶金"]},
    "有色金属": {"code": "801050", "aliases": ["有色", "铜", "铝", "锂", "稀土"]},
    "电子": {"code": "801080", "aliases": ["半导体", "芯片", "元器件", "面板"]},
    "家用电器": {"code": "801110", "aliases": ["家电", "白电", "小家电"]},
    "食品饮料": {"code": "801120", "aliases": ["白酒", "饮料", "食品", "乳制品"]},
    "纺织服装": {"code": "801130", "aliases": ["服装", "纺织", "鞋帽"]},
    "轻工制造": {"code": "801140", "aliases": ["造纸", "包装", "家居"]},
    "医药生物": {"code": "801150", "aliases": ["医药", "生物", "医疗", "制药", "疫苗"]},
    "公用事业": {"code": "801160", "aliases": ["电力", "水务", "燃气", "环保"]},
    "交通运输": {"code": "801170", "aliases": ["航运", "物流", "铁路", "航空", "港口"]},
    "房地产": {"code": "801180", "aliases": ["地产", "房产", "楼市", "开发商"]},
    "商业贸易": {"code": "801200", "aliases": ["零售", "百货", "超市", "电商"]},
    "休闲服务": {"code": "801210", "aliases": ["旅游", "酒店", "餐饮", "免税"]},
    "综合": {"code": "801230", "aliases": ["多元化"]},
    "建筑材料": {"code": "801710", "aliases": ["水泥", "玻璃", "建材"]},
    "建筑装饰": {"code": "801720", "aliases": ["建筑", "装饰", "工程"]},
    "电气设备": {"code": "801730", "aliases": ["新能源", "光伏", "风电", "储能", "电池"]},
    "国防军工": {"code": "801740", "aliases": ["军工", "航天", "国防"]},
    "计算机": {"code": "801750", "aliases": ["软件", "IT", "信创", "云计算"]},
    "传媒": {"code": "801760", "aliases": ["游戏", "影视", "广告", "出版"]},
    "通信": {"code": "801770", "aliases": ["电信", "5G", "通讯", "运营商"]},
    "银行": {"code": "801780", "aliases": ["商业银行", "城商行", "农商行"]},
    "非银金融": {"code": "801790", "aliases": ["证券", "券商", "保险", "信托"]},
    "汽车": {"code": "801880", "aliases": ["整车", "汽配", "新能源车", "电动车"]},
    "机械设备": {"code": "801890", "aliases": ["工程机械", "机床", "自动化"]},
}

# 概念板块（热门主题）
CONCEPT_SECTORS = {
    "人工智能": {"aliases": ["AI", "大模型", "ChatGPT", "算力"], "related_sw": ["计算机", "电子", "通信"]},
    "新能源车": {"aliases": ["电动车", "智能驾驶", "自动驾驶"], "related_sw": ["汽车", "电气设备", "电子"]},
    "光伏": {"aliases": ["太阳能", "硅料", "硅片", "组件"], "related_sw": ["电气设备"]},
    "锂电池": {"aliases": ["动力电池", "储能", "正极", "负极"], "related_sw": ["电气设备", "有色金属"]},
    "半导体": {"aliases": ["芯片", "集成电路", "晶圆", "封测"], "related_sw": ["电子"]},
    "国产替代": {"aliases": ["自主可控", "信创", "国产化"], "related_sw": ["计算机", "电子"]},
    "医美": {"aliases": ["医疗美容", "玻尿酸", "肉毒素"], "related_sw": ["医药生物"]},
    "白酒": {"aliases": ["高端白酒", "次高端白酒"], "related_sw": ["食品饮料"]},
    "房地产链": {"aliases": ["地产链", "建材", "家居"], "related_sw": ["房地产", "建筑材料", "家用电器"]},
    "中特估": {"aliases": ["央企改革", "国企改革", "央企估值"], "related_sw": ["银行", "非银金融", "建筑装饰"]},
    "数字经济": {"aliases": ["数字化", "数据要素", "数字货币"], "related_sw": ["计算机", "通信"]},
}

# 政策敏感行业配置（增强版）
POLICY_SENSITIVE_SECTORS: Dict[str, SectorPolicy] = {
    "房地产": SectorPolicy(
        sector_code="801180",
        sector_name="房地产",
        policy_stance=PolicyStance.SUPPORT,
        sentiment_score=20,
        sensitivity=95,
        key_policies=[
            "房住不炒 - 长期基调",
            "因城施策 - 各地放松限购限贷",
            "保交楼 - 确保已售项目交付",
            "三支箭 - 融资渠道支持",
            "城中村改造 - 新一轮刺激",
            "白名单制度 - 融资协调机制",
        ],
        risks=["部分房企债务风险", "销售持续低迷", "土地财政压力"],
        catalysts=["LPR 下调", "限购放松", "城中村政策加码"],
    ),
    "互联网": SectorPolicy(
        sector_code="801750",
        sector_name="互联网",
        policy_stance=PolicyStance.REGULATE,
        sentiment_score=10,
        sensitivity=80,
        key_policies=[
            "平台经济规范发展 - 常态化监管",
            "数据安全法 - 数据出境审查",
            "反垄断 - 并购审查趋严",
            "算法推荐管理 - 内容合规",
            "未成年人保护 - 游戏/直播限制",
        ],
        risks=["反垄断罚款", "数据合规成本", "业务模式调整"],
        catalysts=["监管态度缓和", "出海政策支持"],
    ),
    "新能源": SectorPolicy(
        sector_code="801730",
        sector_name="新能源",
        policy_stance=PolicyStance.STRONG_SUPPORT,
        sentiment_score=60,
        sensitivity=70,
        key_policies=[
            "双碳目标 - 2030碳达峰/2060碳中和",
            "新能源汽车补贴 - 延续至2027年",
            "光伏/风电平价 - 装机量高增",
            "储能发展 - 配储政策推进",
            "绿电交易 - 市场化机制",
            "新型电力系统 - 电网投资",
        ],
        risks=["补贴退坡", "产能过剩", "海外贸易壁垒"],
        catalysts=["碳交易扩容", "储能政策", "海外订单"],
    ),
    "半导体": SectorPolicy(
        sector_code="801080",
        sector_name="半导体",
        policy_stance=PolicyStance.STRONG_SUPPORT,
        sentiment_score=50,
        sensitivity=90,
        key_policies=[
            "大基金三期 - 持续注资",
            "集成电路产业扶持 - 税收优惠",
            "EDA/设备国产化 - 突破卡脖子",
            "人才培养 - 专业扩招",
            "科创板支持 - 融资绿色通道",
        ],
        risks=["美国制裁升级", "技术突破难度", "周期下行"],
        catalysts=["国产替代订单", "技术突破", "政策加码"],
    ),
    "医药生物": SectorPolicy(
        sector_code="801150",
        sector_name="医药生物",
        policy_stance=PolicyStance.NEUTRAL,
        sentiment_score=0,
        sensitivity=85,
        key_policies=[
            "集中带量采购 - 仿制药价格下行",
            "创新药优先审评 - 加速上市",
            "医保谈判 - 以价换量",
            "中医药发展 - 政策支持",
            "医疗反腐 - 短期扰动",
        ],
        risks=["集采降价压力", "医保控费", "医疗反腐影响"],
        catalysts=["创新药获批", "集采出清", "出海突破"],
    ),
    "银行": SectorPolicy(
        sector_code="801780",
        sector_name="银行",
        policy_stance=PolicyStance.SUPPORT,
        sentiment_score=15,
        sensitivity=75,
        key_policies=[
            "降准降息 - 支持实体经济",
            "房贷利率下调 - 刺激需求",
            "中小银行改革 - 风险化解",
            "金融开放 - 外资准入放宽",
            "数字人民币 - 推广应用",
        ],
        risks=["息差收窄", "房地产风险敞口", "资产质量压力"],
        catalysts=["息差企稳", "不良出清", "估值修复"],
    ),
    "教育": SectorPolicy(
        sector_code="801210",
        sector_name="教育",
        policy_stance=PolicyStance.RESTRICT,
        sentiment_score=-50,
        sensitivity=98,
        key_policies=[
            "双减政策 - K12学科培训转型",
            "职业教育 - 政策鼓励",
            "民办教育 - 分类管理",
            "学前教育 - 普惠化",
        ],
        risks=["政策不确定性", "商业模式受限", "估值重构"],
        catalysts=["职业教育机会", "政策边际放松"],
    ),
    "军工": SectorPolicy(
        sector_code="801740",
        sector_name="军工",
        policy_stance=PolicyStance.STRONG_SUPPORT,
        sentiment_score=55,
        sensitivity=65,
        key_policies=[
            "国防预算增长 - 持续增加",
            "装备现代化 - 十四五重点",
            "军民融合 - 深度发展",
            "航空航天 - 战略支持",
        ],
        risks=["订单波动", "保密限制信息披露"],
        catalysts=["军改落地", "装备列装", "地缘事件"],
    ),
    "汽车": SectorPolicy(
        sector_code="801880",
        sector_name="汽车",
        policy_stance=PolicyStance.SUPPORT,
        sentiment_score=30,
        sensitivity=70,
        key_policies=[
            "新能源汽车购置税减免 - 延续",
            "汽车下乡 - 刺激消费",
            "以旧换新 - 政策补贴",
            "智能网联 - 示范区建设",
            "充电基础设施 - 加速布局",
        ],
        risks=["价格战压力", "产能过剩", "出口壁垒"],
        catalysts=["销量超预期", "出海突破", "智能化升级"],
    ),
}


class PolicySectorService:
    """政策-行业板块映射服务"""

    def __init__(self):
        """初始化服务"""
        self._sector_cache: Dict[str, SectorPolicy] = POLICY_SENSITIVE_SECTORS.copy()
        self._stock_sector_cache: Dict[str, StockSectorMapping] = {}
        self._policy_events: List[PolicyEvent] = []
        logger.info("PolicySectorService initialized", sectors=len(self._sector_cache))

    # ============ 行业映射 ============

    def get_stock_sectors(self, symbol: str) -> Optional[StockSectorMapping]:
        """获取股票的行业归属

        Args:
            symbol: 股票代码

        Returns:
            StockSectorMapping 或 None
        """
        # 检查缓存
        if symbol in self._stock_sector_cache:
            return self._stock_sector_cache[symbol]

        # 尝试从 AkShare 获取
        mapping = self._fetch_stock_sector(symbol)
        if mapping:
            self._stock_sector_cache[symbol] = mapping

        return mapping

    def _fetch_stock_sector(self, symbol: str) -> Optional[StockSectorMapping]:
        """从数据源获取股票行业信息"""
        try:
            import akshare as ak

            # 清理 symbol 格式
            clean_symbol = symbol.split(".")[0]

            # 获取个股所属板块
            df = ak.stock_individual_info_em(symbol=clean_symbol)

            # 解析行业信息
            info_dict = dict(zip(df["item"], df["value"]))
            industry = info_dict.get("行业", "")
            name = info_dict.get("股票简称", "")

            # 映射到申万行业
            primary_sector = self._map_to_sw_sector(industry)
            secondary = self._get_related_concepts(industry, name)

            return StockSectorMapping(
                symbol=symbol,
                name=name,
                primary_sector=primary_sector,
                secondary_sectors=secondary,
                sector_weights={primary_sector: 1.0},
            )
        except Exception as e:
            logger.warning("Failed to fetch stock sector", symbol=symbol, error=str(e))
            return None

    def _map_to_sw_sector(self, industry: str) -> str:
        """将行业名称映射到申万一级行业"""
        if not industry:
            return "综合"

        # 直接匹配
        if industry in SW_LEVEL1_SECTORS:
            return industry

        # 别名匹配
        for sector, info in SW_LEVEL1_SECTORS.items():
            for alias in info.get("aliases", []):
                if alias in industry:
                    return sector

        return "综合"

    def _get_related_concepts(self, industry: str, name: str) -> List[str]:
        """获取关联的概念板块"""
        related = []
        search_text = f"{industry} {name}".lower()

        for concept, info in CONCEPT_SECTORS.items():
            for alias in info.get("aliases", []):
                if alias.lower() in search_text:
                    related.append(concept)
                    break

        return related

    # ============ 政策情绪量化 ============

    def get_sector_policy(self, sector: str) -> Optional[SectorPolicy]:
        """获取行业政策状态

        Args:
            sector: 行业名称

        Returns:
            SectorPolicy 或 None
        """
        # 标准化行业名称
        normalized = self._normalize_sector_name(sector)

        if normalized in self._sector_cache:
            return self._sector_cache[normalized]

        return None

    def get_stock_policy_impact(self, symbol: str) -> Dict:
        """获取个股受政策影响的综合评估

        Args:
            symbol: 股票代码

        Returns:
            政策影响评估结果
        """
        mapping = self.get_stock_sectors(symbol)
        if not mapping:
            return {
                "symbol": symbol,
                "policy_impact": "unknown",
                "sentiment_score": 0,
                "message": "无法获取股票行业信息",
            }

        # 获取主行业政策
        primary_policy = self.get_sector_policy(mapping.primary_sector)

        # 计算综合政策情绪
        total_score = 0
        total_weight = 0
        sector_impacts = []

        if primary_policy:
            weight = mapping.sector_weights.get(mapping.primary_sector, 1.0)
            total_score += primary_policy.sentiment_score * weight
            total_weight += weight
            sector_impacts.append({
                "sector": mapping.primary_sector,
                "stance": primary_policy.policy_stance.value,
                "sentiment_score": primary_policy.sentiment_score,
                "sensitivity": primary_policy.sensitivity,
                "weight": weight,
            })

        # 计算关联行业影响
        for sec in mapping.secondary_sectors:
            sec_policy = self.get_sector_policy(sec)
            if sec_policy:
                weight = 0.3  # 关联行业权重较低
                total_score += sec_policy.sentiment_score * weight
                total_weight += weight
                sector_impacts.append({
                    "sector": sec,
                    "stance": sec_policy.policy_stance.value,
                    "sentiment_score": sec_policy.sentiment_score,
                    "sensitivity": sec_policy.sensitivity,
                    "weight": weight,
                })

        # 计算加权平均
        final_score = int(total_score / total_weight) if total_weight > 0 else 0
        sentiment = self._score_to_sentiment(final_score)

        return {
            "symbol": symbol,
            "name": mapping.name,
            "primary_sector": mapping.primary_sector,
            "secondary_sectors": mapping.secondary_sectors,
            "policy_impact": sentiment.value,
            "sentiment_score": final_score,
            "sector_impacts": sector_impacts,
            "key_policies": primary_policy.key_policies if primary_policy else [],
            "risks": primary_policy.risks if primary_policy else [],
            "catalysts": primary_policy.catalysts if primary_policy else [],
        }

    def _score_to_sentiment(self, score: int) -> PolicySentiment:
        """将分数转换为情绪分类"""
        if score >= 50:
            return PolicySentiment.STRONG_BULLISH
        elif score >= 20:
            return PolicySentiment.BULLISH
        elif score >= -20:
            return PolicySentiment.NEUTRAL
        elif score >= -50:
            return PolicySentiment.BEARISH
        else:
            return PolicySentiment.STRONG_BEARISH

    def _normalize_sector_name(self, sector: str) -> str:
        """标准化行业名称"""
        # 别名映射表
        alias_map = {
            "地产": "房地产", "楼市": "房地产", "房产": "房地产",
            "科技": "互联网", "平台": "互联网", "电商": "互联网",
            "光伏": "新能源", "风电": "新能源", "锂电": "新能源", "储能": "新能源",
            "芯片": "半导体", "集成电路": "半导体", "IC": "半导体",
            "制药": "医药生物", "生物医药": "医药生物", "医疗": "医药生物", "药品": "医药生物",
            "商业银行": "银行", "城商行": "银行", "农商行": "银行",
            "培训": "教育", "在线教育": "教育",
            "航天": "军工", "国防": "军工",
            "整车": "汽车", "新能源车": "汽车", "电动车": "汽车",
        }

        return alias_map.get(sector, sector)

    # ============ 政策事件追踪 ============

    def add_policy_event(self, event: PolicyEvent):
        """添加政策事件

        Args:
            event: 政策事件
        """
        self._policy_events.append(event)

        # 更新相关行业的 recent_events
        for sector in event.sectors:
            if sector in self._sector_cache:
                policy = self._sector_cache[sector]
                policy.recent_events.append(event)
                # 保留最近 10 条
                policy.recent_events = policy.recent_events[-10:]
                policy.last_updated = datetime.now()

        logger.info(
            "Policy event added",
            title=event.title,
            sectors=event.sectors,
            sentiment=event.sentiment.value,
        )

    def get_recent_policy_events(
        self,
        sector: Optional[str] = None,
        days: int = 30,
        limit: int = 20,
    ) -> List[PolicyEvent]:
        """获取近期政策事件

        Args:
            sector: 行业筛选（可选）
            days: 天数范围
            limit: 返回数量限制

        Returns:
            政策事件列表
        """
        cutoff = date.today() - timedelta(days=days)
        events = [e for e in self._policy_events if e.publish_date >= cutoff]

        if sector:
            normalized = self._normalize_sector_name(sector)
            events = [e for e in events if normalized in e.sectors]

        # 按日期降序
        events.sort(key=lambda x: x.publish_date, reverse=True)

        return events[:limit]

    def analyze_policy_text(self, text: str) -> Tuple[PolicySentiment, int, List[str]]:
        """分析政策文本的情绪

        Args:
            text: 政策文本内容

        Returns:
            (情绪分类, 情绪分数, 关联行业)
        """
        # 利好关键词
        bullish_keywords = {
            "支持": 10, "鼓励": 10, "促进": 8, "加快": 8, "加强": 5,
            "补贴": 15, "减税": 15, "降息": 12, "降准": 12,
            "扩大": 8, "推动": 8, "优化": 5, "完善": 5,
            "战略性": 10, "重点": 8, "优先": 8,
            "放松": 12, "放开": 12, "取消限制": 15,
        }

        # 利空关键词
        bearish_keywords = {
            "限制": -10, "禁止": -15, "整治": -12, "整顿": -10,
            "打击": -15, "处罚": -12, "罚款": -10,
            "收紧": -10, "从严": -10, "规范": -5,
            "反垄断": -8, "反不正当竞争": -8,
            "暂停": -12, "叫停": -15, "取消资格": -15,
            "风险": -5, "违规": -8,
        }

        # 计算分数
        score = 0
        for keyword, value in bullish_keywords.items():
            if keyword in text:
                score += value

        for keyword, value in bearish_keywords.items():
            if keyword in text:
                score += value

        # 限制范围
        score = max(-100, min(100, score))

        # 转换为情绪
        sentiment = self._score_to_sentiment(score)

        # 识别关联行业
        related_sectors = []
        text_lower = text.lower()
        for sector, info in SW_LEVEL1_SECTORS.items():
            if sector in text:
                related_sectors.append(sector)
            else:
                for alias in info.get("aliases", []):
                    if alias in text:
                        related_sectors.append(sector)
                        break

        return sentiment, score, related_sectors

    # ============ 批量查询 ============

    def get_all_sector_policies(self) -> Dict[str, SectorPolicy]:
        """获取所有行业政策状态"""
        return self._sector_cache.copy()

    def get_sectors_by_sentiment(self, sentiment: PolicySentiment) -> List[str]:
        """获取指定情绪的行业列表"""
        result = []
        for sector, policy in self._sector_cache.items():
            current_sentiment = self._score_to_sentiment(policy.sentiment_score)
            if current_sentiment == sentiment:
                result.append(sector)
        return result

    def get_high_sensitivity_sectors(self, threshold: int = 80) -> List[Tuple[str, int]]:
        """获取高政策敏感度行业

        Args:
            threshold: 敏感度阈值

        Returns:
            [(行业名, 敏感度分数), ...]
        """
        result = [
            (sector, policy.sensitivity)
            for sector, policy in self._sector_cache.items()
            if policy.sensitivity >= threshold
        ]
        return sorted(result, key=lambda x: x[1], reverse=True)


# 单例实例
policy_sector_service = PolicySectorService()
