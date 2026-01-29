"""
Prompt 配置服务

统一管理 Agent Prompt，支持：
- 动态配置：无需重启即可调整 Agent 行为
- 版本管理：记录 prompt 变更历史，支持回滚
- 热加载：从数据库实时获取最新 prompt
- A/B 测试：同一 Agent 可有多版本 prompt
- YAML 导入导出：方便批量编辑和版本控制
"""
import json
import yaml
import structlog
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlmodel import Session, select

from db.models import AgentPrompt, PromptVersion, AgentCategory, engine
from config.settings import settings

logger = structlog.get_logger()


# 默认 Prompt 配置（用于初始化）
DEFAULT_PROMPTS: List[Dict[str, Any]] = [
    # ============ 分析师 ============
    {
        "agent_key": "market_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "市场分析师",
        "description": "使用技术指标分析股票市场趋势",
        "system_prompt": """You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicators** for a given market condition or trading strategy.

Categories and indicators:
- Moving Averages: close_50_sma, close_200_sma, close_10_ema
- MACD Related: macd, macds, macdh
- Momentum: rsi
- Volatility: boll, boll_ub, boll_lb, atr
- Volume: vwma

Instructions:
1. Call get_stock_data to retrieve the stock CSV data
2. Use get_indicators with specific indicator names
3. Analyze the data and provide detailed insights
4. Select indicators that provide diverse and complementary information

Output language: 简体中文""",
        "user_prompt_template": "请分析 {ticker} 在 {date} 的技术指标数据。",
        "available_variables": ["ticker", "date", "data"],
    },
    {
        "agent_key": "news_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "新闻分析师",
        "description": "分析市场新闻和舆情对股票的影响",
        "system_prompt": """你是一位专业的新闻分析师。你的任务是：
1. 搜集与股票相关的最新新闻
2. 分析新闻对股价的潜在影响
3. 评估市场情绪（乐观/悲观/中性）
4. 识别重要的催化剂事件

请使用工具获取新闻数据，然后提供结构化分析。
输出语言：简体中文""",
        "user_prompt_template": "请分析 {ticker} 的最新新闻和市场情绪。",
        "available_variables": ["ticker", "date"],
    },
    {
        "agent_key": "fundamentals_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "基本面分析师",
        "description": "分析公司财务数据和基本面",
        "system_prompt": """你是一位专业的基本面分析师。你的任务是：
1. 分析公司的财务报表（资产负债表、现金流量表、利润表）
2. 评估公司的盈利能力、偿债能力和成长性
3. 计算关键财务比率（PE、PB、ROE 等）
4. 与同行业公司进行比较

请使用工具获取财务数据，然后提供结构化分析。
输出语言：简体中文""",
        "user_prompt_template": "请分析 {ticker} 的基本面数据。",
        "available_variables": ["ticker", "date"],
    },
    {
        "agent_key": "social_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "社交媒体分析师",
        "description": "分析社交媒体上的股票讨论热度",
        "system_prompt": """你是一位社交媒体分析师。你的任务是：
1. 分析社交媒体上关于股票的讨论
2. 评估散户情绪和关注度
3. 识别热门话题和潜在炒作
4. 警惕可能的 pump and dump 行为

请使用工具获取社交媒体数据，然后提供结构化分析。
输出语言：简体中文""",
        "user_prompt_template": "请分析 {ticker} 在社交媒体上的讨论情况。",
        "available_variables": ["ticker", "date"],
    },
    {
        "agent_key": "sentiment_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "散户情绪分析师",
        "description": "A股散户情绪分析，检测 FOMO/FUD",
        "system_prompt": """你是一位专业的 A股散户情绪分析师。你的任务是：
1. 分析东方财富、雪球等平台的散户评论
2. 检测 FOMO（错失恐惧）信号：追高情绪、盲目乐观
3. 检测 FUD（恐惧不确定怀疑）信号：恐慌抛售、过度悲观
4. 评估整体散户情绪（贪婪/中性/恐惧）
5. 结合龙虎榜数据判断主力动向

输出格式：
- FOMO 等级：高/中/低/无
- FUD 等级：高/中/低/无
- 整体情绪：贪婪/中性/恐惧
- 关键信号列表

输出语言：简体中文""",
        "user_prompt_template": "请分析 {ticker} 的散户情绪，市场：{market}。",
        "available_variables": ["ticker", "date", "market"],
    },
    {
        "agent_key": "policy_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "政策分析师",
        "description": "A股政策分析，关注监管和产业政策",
        "system_prompt": """你是一位专业的 A股政策分析师。你的任务是：
1. 分析最新的监管政策和产业政策
2. 评估政策对特定行业/个股的影响
3. 识别政策利好和利空因素
4. 关注北向资金、减持公告等重要信息
5. 预判政策走向和市场反应

输出格式：
- 最新政策列表
- 影响评估：利好/中性/利空
- 风险因素
- 机遇分析

输出语言：简体中文""",
        "user_prompt_template": "请分析影响 {ticker} 的最新政策，市场：{market}。",
        "available_variables": ["ticker", "date", "market"],
    },
    {
        "agent_key": "macro_analyst",
        "category": AgentCategory.ANALYST,
        "display_name": "宏观分析师",
        "description": "分析宏观经济环境对股票的影响",
        "system_prompt": """你是一位宏观经济学家。你的任务是：
1. 分析当前的宏观经济环境（利率、通胀、GDP 等）
2. 评估地缘政治风险
3. 分析行业周期位置
4. 预判宏观趋势对股票的影响

输出语言：简体中文""",
        "user_prompt_template": "请分析宏观经济环境对 {ticker} 所属行业的影响。",
        "available_variables": ["ticker", "date", "market"],
    },
    # ============ 研究员 ============
    {
        "agent_key": "bull_researcher",
        "category": AgentCategory.RESEARCHER,
        "display_name": "多头研究员",
        "description": "从多头视角分析股票投资价值",
        "system_prompt": """你是一位坚定的多头研究员。你的任务是：
1. 深入挖掘支持买入的核心逻辑
2. 寻找被市场低估的价值点
3. 识别潜在的上涨催化剂
4. 用事实和数据支持你的观点

辩论规则：
- 你将与空头研究员进行对抗性辩论
- 每轮发言需要回应对方观点
- 提供有力的反驳和新论据

输出语言：简体中文""",
        "user_prompt_template": "请从多头角度分析 {ticker}，回应对方观点：{opponent_argument}",
        "available_variables": ["ticker", "date", "opponent_argument", "market_report", "news_report", "fundamentals_report"],
    },
    {
        "agent_key": "bear_researcher",
        "category": AgentCategory.RESEARCHER,
        "display_name": "空头研究员",
        "description": "从空头视角分析股票风险",
        "system_prompt": """你是一位冷静的空头研究员。你的任务是：
1. 识别潜在的风险和下行压力
2. 寻找被市场忽视的利空因素
3. 分析估值泡沫和过热信号
4. 用事实和数据支持你的观点

辩论规则：
- 你将与多头研究员进行对抗性辩论
- 每轮发言需要回应对方观点
- 提供有力的反驳和新论据

输出语言：简体中文""",
        "user_prompt_template": "请从空头角度分析 {ticker}，回应对方观点：{opponent_argument}",
        "available_variables": ["ticker", "date", "opponent_argument", "market_report", "news_report", "fundamentals_report"],
    },
    # ============ 管理层 ============
    {
        "agent_key": "research_manager",
        "category": AgentCategory.MANAGER,
        "display_name": "研究经理",
        "description": "综合多空观点做出投资决策",
        "system_prompt": """你是一位经验丰富的研究经理。你的任务是：
1. 综合多头和空头研究员的观点
2. 评估双方论据的质量和可信度
3. 权衡风险和收益
4. 做出最终的投资建议

你需要输出：
- 胜出方：Bull/Bear/Neutral
- 决策理由
- 投资建议

输出语言：简体中文""",
        "user_prompt_template": "请综合以下辩论内容做出决策：\n\n多头观点：{bull_argument}\n\n空头观点：{bear_argument}",
        "available_variables": ["ticker", "bull_argument", "bear_argument"],
    },
    {
        "agent_key": "risk_manager",
        "category": AgentCategory.MANAGER,
        "display_name": "风险经理",
        "description": "综合三方风险评估做出最终决策",
        "system_prompt": """你是一位严谨的风险经理。你拥有一票否决权。你的任务是：
1. 综合激进派、保守派和中立派的风险评估
2. 评估波动率、流动性和最大回撤风险
3. 确定风险等级（1-10）
4. 做出最终裁决：Approved/Caution/Rejected

输出语言：简体中文""",
        "user_prompt_template": "请综合以下风险评估做出决策：\n\n激进派：{aggressive}\n\n保守派：{conservative}\n\n中立派：{neutral}",
        "available_variables": ["ticker", "aggressive", "conservative", "neutral"],
    },
    # ============ 风险辩论 ============
    {
        "agent_key": "aggressive_debator",
        "category": AgentCategory.RISK,
        "display_name": "激进派分析师",
        "description": "风险辩论中的激进派",
        "system_prompt": """你是风险辩论中的激进派。你的任务是：
1. 强调潜在的高回报机会
2. 认为适度风险是可接受的
3. 关注上行空间而非下行风险
4. 建议更积极的仓位配置

输出语言：简体中文""",
        "user_prompt_template": "请从激进派角度评估 {ticker} 的风险收益比。",
        "available_variables": ["ticker", "investment_plan"],
    },
    {
        "agent_key": "conservative_debator",
        "category": AgentCategory.RISK,
        "display_name": "保守派分析师",
        "description": "风险辩论中的保守派",
        "system_prompt": """你是风险辩论中的保守派。你的任务是：
1. 强调资本保护的重要性
2. 关注潜在的下行风险
3. 建议设置严格的止损
4. 建议更谨慎的仓位配置

输出语言：简体中文""",
        "user_prompt_template": "请从保守派角度评估 {ticker} 的风险收益比。",
        "available_variables": ["ticker", "investment_plan"],
    },
    {
        "agent_key": "neutral_debator",
        "category": AgentCategory.RISK,
        "display_name": "中立派分析师",
        "description": "风险辩论中的中立派",
        "system_prompt": """你是风险辩论中的中立派。你的任务是：
1. 平衡考虑风险和收益
2. 提供客观的风险评估
3. 建议合理的仓位配置
4. 综合激进派和保守派的观点

输出语言：简体中文""",
        "user_prompt_template": "请从中立角度评估 {ticker} 的风险收益比，综合激进派和保守派观点。",
        "available_variables": ["ticker", "investment_plan", "aggressive_view", "conservative_view"],
    },
    # ============ 交易员 ============
    {
        "agent_key": "trader",
        "category": AgentCategory.TRADER,
        "display_name": "交易员",
        "description": "制定具体的交易计划",
        "system_prompt": """你是一位专业的交易员。你的任务是：
1. 根据研究经理的投资建议制定交易计划
2. 确定入场点位、止损位和目标位
3. 计算风险收益比
4. 设定失效条件

输出格式：
- 交易方向：买入/卖出/观望
- 入场区间
- 止损价格
- 目标价格
- 风险收益比
- 失效条件

输出语言：简体中文""",
        "user_prompt_template": "根据以下分析制定 {ticker} 的交易计划：\n{analysis_summary}",
        "available_variables": ["ticker", "analysis_summary", "current_price"],
    },
    # ============ 合成器 ============
    {
        "agent_key": "response_synthesizer",
        "category": AgentCategory.SYNTHESIZER,
        "display_name": "响应合成器",
        "description": "将 Agent 报告合成为 JSON",
        "system_prompt": """你是一个金融数据合成专家。请将多个 Agent 的分析报告合成一个严格符合 JSON 格式的对象。

输出语言：简体中文
重要：不要输出 Markdown 代码块，直接输出纯 JSON。""",
        "user_prompt_template": "股票代码: {symbol}\n\n报告内容:\n{reports}",
        "available_variables": ["symbol", "reports"],
    },
]


class PromptConfigService:
    """
    Prompt 配置服务 - 统一管理 Agent Prompt

    功能：
    1. 从数据库加载 Prompt 配置
    2. 支持变量注入
    3. 版本管理和回滚
    4. YAML 导入导出
    5. 热加载（每次请求检查更新）
    """

    _instance = None
    _prompts_cache: Dict[str, AgentPrompt] = {}
    _last_refresh: Optional[datetime] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._prompts_cache:
            self._ensure_default_prompts()
            self.refresh_cache()

    def _ensure_default_prompts(self):
        """确保默认 Prompt 存在"""
        with Session(engine) as session:
            existing = session.exec(select(AgentPrompt)).first()
            if existing:
                return

            logger.info("Creating default agent prompts")

            for prompt_data in DEFAULT_PROMPTS:
                prompt = AgentPrompt(
                    agent_key=prompt_data["agent_key"],
                    category=prompt_data["category"],
                    display_name=prompt_data["display_name"],
                    description=prompt_data["description"],
                    system_prompt=prompt_data["system_prompt"],
                    user_prompt_template=prompt_data["user_prompt_template"],
                    available_variables=json.dumps(prompt_data["available_variables"]),
                    version=1,
                    is_active=True,
                )
                session.add(prompt)

            session.commit()
            logger.info("Default prompts created", count=len(DEFAULT_PROMPTS))

    def refresh_cache(self):
        """刷新 Prompt 缓存"""
        with Session(engine) as session:
            prompts = session.exec(
                select(AgentPrompt).where(AgentPrompt.is_active == True)
            ).all()

            self._prompts_cache = {p.agent_key: p for p in prompts}
            self._last_refresh = datetime.now()

            logger.info("Prompt cache refreshed", count=len(self._prompts_cache))

    def get_prompt(
        self,
        agent_key: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        获取 Agent Prompt

        Args:
            agent_key: Agent 标识，如 "market_analyst"
            variables: 变量字典，用于填充模板

        Returns:
            {"system": "...", "user": "..."} 或空字典
        """
        # 确保缓存已加载
        if not self._prompts_cache:
            self.refresh_cache()

        prompt = self._prompts_cache.get(agent_key)
        if not prompt:
            logger.warning("Prompt not found", agent_key=agent_key)
            return {"system": "", "user": ""}

        system_prompt = prompt.system_prompt
        user_prompt = prompt.user_prompt_template

        # 变量注入
        if variables:
            try:
                system_prompt = system_prompt.format(**variables)
                user_prompt = user_prompt.format(**variables)
            except KeyError as e:
                logger.warning(
                    "Missing variable in prompt template",
                    agent_key=agent_key,
                    missing=str(e)
                )

        return {
            "system": system_prompt,
            "user": user_prompt,
        }

    def get_system_prompt(
        self,
        agent_key: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> str:
        """仅获取 system prompt"""
        return self.get_prompt(agent_key, variables).get("system", "")

    # =========================================================================
    # CRUD 操作
    # =========================================================================

    async def list_prompts(
        self,
        category: Optional[AgentCategory] = None
    ) -> List[Dict[str, Any]]:
        """列出所有 Prompt"""
        with Session(engine) as session:
            query = select(AgentPrompt)
            if category:
                query = query.where(AgentPrompt.category == category)

            prompts = session.exec(query.order_by(AgentPrompt.category, AgentPrompt.agent_key)).all()

            return [
                {
                    "id": p.id,
                    "agent_key": p.agent_key,
                    "category": p.category.value,
                    "display_name": p.display_name,
                    "description": p.description,
                    "system_prompt": p.system_prompt,
                    "user_prompt_template": p.user_prompt_template,
                    "available_variables": json.loads(p.available_variables),
                    "version": p.version,
                    "is_active": p.is_active,
                    "updated_at": p.updated_at.isoformat(),
                }
                for p in prompts
            ]

    async def get_prompt_detail(self, prompt_id: int) -> Optional[Dict[str, Any]]:
        """获取 Prompt 详情"""
        with Session(engine) as session:
            prompt = session.get(AgentPrompt, prompt_id)
            if not prompt:
                return None

            # 获取版本历史
            versions = session.exec(
                select(PromptVersion)
                .where(PromptVersion.prompt_id == prompt_id)
                .order_by(PromptVersion.version.desc())
            ).all()

            return {
                "id": prompt.id,
                "agent_key": prompt.agent_key,
                "category": prompt.category.value,
                "display_name": prompt.display_name,
                "description": prompt.description,
                "system_prompt": prompt.system_prompt,
                "user_prompt_template": prompt.user_prompt_template,
                "available_variables": json.loads(prompt.available_variables),
                "version": prompt.version,
                "is_active": prompt.is_active,
                "created_at": prompt.created_at.isoformat(),
                "updated_at": prompt.updated_at.isoformat(),
                "version_history": [
                    {
                        "version": v.version,
                        "change_note": v.change_note,
                        "created_at": v.created_at.isoformat(),
                        "created_by": v.created_by,
                    }
                    for v in versions[:10]  # 最近 10 个版本
                ],
            }

    async def update_prompt(
        self,
        prompt_id: int,
        data: Dict[str, Any],
        change_note: str = "",
        created_by: str = "user"
    ) -> Optional[Dict[str, Any]]:
        """更新 Prompt（自动保存版本历史）"""
        with Session(engine) as session:
            prompt = session.get(AgentPrompt, prompt_id)
            if not prompt:
                return None

            # 保存旧版本到历史
            version_record = PromptVersion(
                prompt_id=prompt.id,
                version=prompt.version,
                system_prompt=prompt.system_prompt,
                user_prompt_template=prompt.user_prompt_template,
                change_note=change_note or f"Updated to version {prompt.version + 1}",
                created_by=created_by,
            )
            session.add(version_record)

            # 更新 Prompt
            if "system_prompt" in data:
                prompt.system_prompt = data["system_prompt"]
            if "user_prompt_template" in data:
                prompt.user_prompt_template = data["user_prompt_template"]
            if "display_name" in data:
                prompt.display_name = data["display_name"]
            if "description" in data:
                prompt.description = data["description"]
            if "available_variables" in data:
                prompt.available_variables = json.dumps(data["available_variables"])

            prompt.version += 1
            prompt.updated_at = datetime.now()

            session.commit()

            # 刷新缓存
            self.refresh_cache()

            return {
                "id": prompt.id,
                "agent_key": prompt.agent_key,
                "version": prompt.version,
                "updated": True,
            }

    async def rollback_prompt(
        self,
        prompt_id: int,
        target_version: int
    ) -> Optional[Dict[str, Any]]:
        """回滚 Prompt 到指定版本"""
        with Session(engine) as session:
            prompt = session.get(AgentPrompt, prompt_id)
            if not prompt:
                return None

            # 查找目标版本
            version_record = session.exec(
                select(PromptVersion)
                .where(
                    PromptVersion.prompt_id == prompt_id,
                    PromptVersion.version == target_version
                )
            ).first()

            if not version_record:
                return {"error": f"Version {target_version} not found"}

            # 保存当前版本到历史
            current_version = PromptVersion(
                prompt_id=prompt.id,
                version=prompt.version,
                system_prompt=prompt.system_prompt,
                user_prompt_template=prompt.user_prompt_template,
                change_note=f"Before rollback to version {target_version}",
                created_by="system",
            )
            session.add(current_version)

            # 回滚
            prompt.system_prompt = version_record.system_prompt
            prompt.user_prompt_template = version_record.user_prompt_template
            prompt.version += 1
            prompt.updated_at = datetime.now()

            session.commit()

            self.refresh_cache()

            return {
                "id": prompt.id,
                "agent_key": prompt.agent_key,
                "rolled_back_to": target_version,
                "new_version": prompt.version,
            }

    # =========================================================================
    # YAML 导入导出
    # =========================================================================

    async def export_to_yaml(self) -> str:
        """导出所有 Prompt 到 YAML 格式"""
        prompts = await self.list_prompts()

        # 按类别分组
        grouped = {}
        for p in prompts:
            category = p["category"]
            if category not in grouped:
                grouped[category] = []
            grouped[category].append({
                "agent_key": p["agent_key"],
                "display_name": p["display_name"],
                "description": p["description"],
                "system_prompt": p["system_prompt"],
                "user_prompt_template": p["user_prompt_template"],
                "available_variables": p["available_variables"],
            })

        return yaml.dump(grouped, allow_unicode=True, default_flow_style=False, sort_keys=False)

    async def import_from_yaml(
        self,
        yaml_content: str,
        created_by: str = "import"
    ) -> Dict[str, Any]:
        """从 YAML 导入 Prompt（更新已存在的，创建新的）"""
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return {"success": False, "error": f"Invalid YAML: {str(e)}"}

        created = 0
        updated = 0

        with Session(engine) as session:
            for category_name, prompts in data.items():
                try:
                    category = AgentCategory(category_name)
                except ValueError:
                    continue

                for prompt_data in prompts:
                    agent_key = prompt_data.get("agent_key")
                    if not agent_key:
                        continue

                    # 查找已存在的 Prompt
                    existing = session.exec(
                        select(AgentPrompt).where(AgentPrompt.agent_key == agent_key)
                    ).first()

                    if existing:
                        # 保存版本历史
                        version_record = PromptVersion(
                            prompt_id=existing.id,
                            version=existing.version,
                            system_prompt=existing.system_prompt,
                            user_prompt_template=existing.user_prompt_template,
                            change_note="YAML import",
                            created_by=created_by,
                        )
                        session.add(version_record)

                        # 更新
                        existing.system_prompt = prompt_data.get("system_prompt", existing.system_prompt)
                        existing.user_prompt_template = prompt_data.get("user_prompt_template", existing.user_prompt_template)
                        existing.display_name = prompt_data.get("display_name", existing.display_name)
                        existing.description = prompt_data.get("description", existing.description)
                        if "available_variables" in prompt_data:
                            existing.available_variables = json.dumps(prompt_data["available_variables"])
                        existing.version += 1
                        existing.updated_at = datetime.now()
                        updated += 1
                    else:
                        # 创建新的
                        new_prompt = AgentPrompt(
                            agent_key=agent_key,
                            category=category,
                            display_name=prompt_data.get("display_name", agent_key),
                            description=prompt_data.get("description", ""),
                            system_prompt=prompt_data.get("system_prompt", ""),
                            user_prompt_template=prompt_data.get("user_prompt_template", ""),
                            available_variables=json.dumps(prompt_data.get("available_variables", [])),
                            version=1,
                            is_active=True,
                        )
                        session.add(new_prompt)
                        created += 1

            session.commit()

        self.refresh_cache()

        return {
            "success": True,
            "created": created,
            "updated": updated,
        }

    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "initialized": bool(self._prompts_cache),
            "prompts_count": len(self._prompts_cache),
            "cached_agents": list(self._prompts_cache.keys()),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
        }


# 全局单例
prompt_config_service = PromptConfigService()
