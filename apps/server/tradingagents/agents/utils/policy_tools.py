"""政策分析工具模块

提供 A 股政策分析相关的工具函数：
- 政策新闻搜索
- 监管日历
- 行业政策状态
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
import structlog

logger = structlog.get_logger(__name__)


def _search_with_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """使用 DuckDuckGo 搜索"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": r.get("href", ""),
                }
                for r in results
            ]
    except Exception as e:
        logger.warning("DuckDuckGo search failed", query=query, error=str(e))
        return []


@tool
def search_policy_news(query: str, source: str = "all") -> str:
    """搜索 A 股政策相关新闻

    Args:
        query: 搜索关键词（行业、公司名或政策关键词）
        source: 来源筛选 (gov/央行/证监会/发改委/all)

    Returns:
        政策相关新闻和文件摘要
    """
    # 构建搜索查询
    source_keywords = {
        "gov": "中国政府 国务院",
        "央行": "中国人民银行 央行",
        "证监会": "证监会 CSRC",
        "发改委": "发改委 国家发展改革委员会",
        "all": "",
    }

    source_term = source_keywords.get(source, "")
    search_query = f"{query} {source_term} 政策 site:gov.cn OR site:pbc.gov.cn OR site:csrc.gov.cn"

    results = _search_with_duckduckgo(search_query, max_results=8)

    if not results:
        # 尝试更宽泛的搜索
        search_query = f"{query} 政策 监管 最新"
        results = _search_with_duckduckgo(search_query, max_results=5)

    if not results:
        return f"未找到与 '{query}' 相关的政策新闻。"

    # 格式化结果
    output_lines = [f"## {query} 相关政策新闻\n"]
    for i, r in enumerate(results, 1):
        output_lines.append(f"### {i}. {r['title']}")
        output_lines.append(f"{r['body']}")
        output_lines.append(f"来源: {r['href']}\n")

    return "\n".join(output_lines)


@tool
def get_regulatory_calendar() -> str:
    """获取 A 股监管日历

    Returns:
        近期重要监管事件和政策发布时间表
    """
    today = datetime.now()
    year = today.year
    month = today.month

    # 固定的重要会议日历
    calendar_events = [
        # 两会
        {"name": "全国两会（两会）", "month": 3, "day_range": "3-15", "importance": "极高",
         "description": "全国人大和政协会议，发布政府工作报告，确定全年经济目标"},
        # 中央经济工作会议
        {"name": "中央经济工作会议", "month": 12, "day_range": "中旬", "importance": "极高",
         "description": "总结全年经济工作，部署来年经济政策基调"},
        # 政治局会议
        {"name": "中央政治局会议（季度）", "month": None, "day_range": "每季度末", "importance": "高",
         "description": "分析经济形势，部署下一阶段工作，4/7/10/12月"},
        # 国常会
        {"name": "国务院常务会议", "month": None, "day_range": "每周三", "importance": "中高",
         "description": "讨论经济政策、产业发展等议题"},
        # MLF
        {"name": "MLF 操作", "month": None, "day_range": "每月15日左右", "importance": "高",
         "description": "央行中期借贷便利操作，影响市场利率"},
        # LPR
        {"name": "LPR 报价", "month": None, "day_range": "每月20日", "importance": "高",
         "description": "贷款市场报价利率，影响房贷和企业贷款成本"},
        # 财报季
        {"name": "季报披露期（Q1）", "month": 4, "day_range": "1-30", "importance": "中",
         "description": "A 股一季报披露期"},
        {"name": "中报披露期", "month": 8, "day_range": "1-31", "importance": "中",
         "description": "A 股中报披露期"},
        {"name": "三季报披露期", "month": 10, "day_range": "1-31", "importance": "中",
         "description": "A 股三季报披露期"},
        {"name": "年报披露期", "month": 4, "day_range": "1-30", "importance": "高",
         "description": "A 股年报披露期，关注业绩雷"},
    ]

    output_lines = ["## A 股监管日历\n"]
    output_lines.append(f"当前日期: {today.strftime('%Y年%m月%d日')}\n")

    # 近期事件
    output_lines.append("### 近期重要事件\n")

    for event in calendar_events:
        if event["month"] is None:
            # 周期性事件
            output_lines.append(f"- **{event['name']}** ({event['day_range']})")
            output_lines.append(f"  重要性: {event['importance']} | {event['description']}")
        elif event["month"] == month or event["month"] == (month % 12) + 1:
            # 当月或下月事件
            output_lines.append(f"- **{event['name']}** ({year}年{event['month']}月{event['day_range']}日)")
            output_lines.append(f"  重要性: {event['importance']} | {event['description']}")

    # 政治局会议月份
    politburo_months = [4, 7, 10, 12]
    if month in politburo_months or (month + 1) in politburo_months:
        next_politburo = month if month in politburo_months else month + 1
        output_lines.append(f"\n⚠️ **{next_politburo}月有中央政治局会议，关注政策信号**")

    return "\n".join(output_lines)


@tool
def get_sector_policy_status(sector: str) -> str:
    """获取行业政策状态

    Args:
        sector: 行业名称（如：新能源、房地产、互联网、半导体、医药）

    Returns:
        该行业当前的政策导向和监管态度
    """
    # 预定义的行业政策状态（可从数据库或配置文件加载）
    sector_policies = {
        "房地产": {
            "policy_stance": "宽松",
            "direction": "支持合理需求",
            "key_policies": [
                "房住不炒 - 长期基调不变",
                "因城施策 - 各地放松限购限贷",
                "保交楼 - 确保已售项目交付",
                "三支箭 - 融资渠道支持",
                "城中村改造 - 新一轮刺激政策",
            ],
            "risks": ["部分房企债务风险", "销售持续低迷"],
            "sensitivity": 95,
        },
        "互联网": {
            "policy_stance": "常态化监管",
            "direction": "规范发展",
            "key_policies": [
                "平台经济规范发展 - 监管趋于常态化",
                "数据安全法 - 数据出境审查",
                "反垄断 - 并购审查趋严",
                "算法推荐管理 - 内容合规要求",
            ],
            "risks": ["反垄断罚款", "数据合规成本"],
            "sensitivity": 80,
        },
        "新能源": {
            "policy_stance": "强力支持",
            "direction": "战略性新兴产业",
            "key_policies": [
                "双碳目标 - 2030碳达峰/2060碳中和",
                "新能源汽车补贴 - 延续至2027年",
                "光伏/风电平价 - 装机量持续增长",
                "储能发展 - 配储政策推进",
                "绿电交易 - 市场化机制完善",
            ],
            "risks": ["补贴退坡", "产能过剩竞争加剧"],
            "sensitivity": 70,
        },
        "半导体": {
            "policy_stance": "战略支持",
            "direction": "国产替代",
            "key_policies": [
                "大基金三期 - 持续注资",
                "集成电路产业扶持 - 税收优惠",
                "EDA/设备国产化 - 突破卡脖子",
                "人才培养 - 集成电路专业扩招",
            ],
            "risks": ["美国制裁升级", "技术突破难度大"],
            "sensitivity": 90,
        },
        "医药": {
            "policy_stance": "分化监管",
            "direction": "创新支持+仿制集采",
            "key_policies": [
                "集中带量采购 - 仿制药价格持续下行",
                "创新药优先审评 - 加速上市",
                "医保谈判 - 以价换量",
                "中医药发展 - 政策支持",
            ],
            "risks": ["集采降价压力", "医保控费"],
            "sensitivity": 85,
        },
        "金融": {
            "policy_stance": "稳健审慎",
            "direction": "防风险+服务实体",
            "key_policies": [
                "降准降息 - 支持实体经济",
                "房贷利率下调 - 刺激需求",
                "资本市场改革 - 注册制全面实施",
                "金融开放 - 外资准入放宽",
            ],
            "risks": ["息差收窄", "房地产风险敞口"],
            "sensitivity": 75,
        },
        "教育": {
            "policy_stance": "严格监管",
            "direction": "公益属性",
            "key_policies": [
                "双减政策 - K12 学科培训转型",
                "职业教育 - 政策鼓励",
                "民办教育 - 分类管理",
            ],
            "risks": ["政策不确定性高", "商业模式受限"],
            "sensitivity": 98,
        },
    }

    # 标准化行业名称
    sector_mapping = {
        "地产": "房地产", "楼市": "房地产", "房产": "房地产",
        "科技": "互联网", "平台": "互联网", "电商": "互联网",
        "光伏": "新能源", "风电": "新能源", "锂电": "新能源", "新能车": "新能源", "电动车": "新能源",
        "芯片": "半导体", "集成电路": "半导体", "IC": "半导体",
        "制药": "医药", "生物医药": "医药", "医疗": "医药", "药品": "医药",
        "银行": "金融", "券商": "金融", "保险": "金融",
        "培训": "教育", "在线教育": "教育",
    }

    normalized_sector = sector_mapping.get(sector, sector)

    if normalized_sector in sector_policies:
        policy = sector_policies[normalized_sector]
        output_lines = [f"## {normalized_sector}行业政策状态\n"]
        output_lines.append(f"**政策立场**: {policy['policy_stance']}")
        output_lines.append(f"**政策方向**: {policy['direction']}")
        output_lines.append(f"**政策敏感度**: {policy['sensitivity']}/100\n")

        output_lines.append("### 核心政策")
        for p in policy["key_policies"]:
            output_lines.append(f"- {p}")

        output_lines.append("\n### 主要风险")
        for r in policy["risks"]:
            output_lines.append(f"- ⚠️ {r}")

        return "\n".join(output_lines)
    else:
        # 尝试搜索
        search_results = _search_with_duckduckgo(f"{sector} 行业政策 监管 最新", max_results=5)
        if search_results:
            output_lines = [f"## {sector}行业政策搜索结果\n"]
            for r in search_results:
                output_lines.append(f"- **{r['title']}**: {r['body'][:100]}...")
            return "\n".join(output_lines)

        return f"未找到 '{sector}' 行业的政策信息。支持的行业包括：房地产、互联网、新能源、半导体、医药、金融、教育"


@tool
def search_industry_planning(industry: str) -> str:
    """搜索行业五年规划和发展目标

    Args:
        industry: 行业名称

    Returns:
        行业规划和发展目标信息
    """
    search_query = f"{industry} 十四五规划 发展目标 政策"
    results = _search_with_duckduckgo(search_query, max_results=5)

    if not results:
        return f"未找到 '{industry}' 的五年规划信息。"

    output_lines = [f"## {industry} 行业规划\n"]
    for i, r in enumerate(results, 1):
        output_lines.append(f"{i}. **{r['title']}**")
        output_lines.append(f"   {r['body']}\n")

    return "\n".join(output_lines)


# 导出所有工具
POLICY_TOOLS = [
    search_policy_news,
    get_regulatory_calendar,
    get_sector_policy_status,
    search_industry_planning,
]
