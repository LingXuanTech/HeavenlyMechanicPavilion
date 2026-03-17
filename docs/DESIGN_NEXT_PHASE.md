# 下一阶段功能设计方案

> 最后更新: 2026-02-05

本文档包含四个规划中功能的完整技术设计方案：
1. [智能推送机器人](#1-智能推送机器人)
2. [WhaleWatcher 筹码追踪](#2-whalewatcher-筹码追踪)
3. [蒙特卡洛/VaR 风险建模](#3-蒙特卡洛var-风险建模)
4. [ExecutionAgent 自动执行](#4-executionagent-自动执行)

---

## 1. 智能推送机器人

### 1.1 功能概述

构建多渠道消息推送系统，将重大分析信号、市场异动、定时报告等信息实时推送给用户。

**核心能力**：
- 📱 多渠道支持：Telegram Bot、企业微信、钉钉、邮件
- 🎯 智能过滤：基于信号强度、置信度、用户偏好过滤推送
- ⏰ 定时摘要：每日早盘/收盘自动发送持仓摘要
- 🚨 实时告警：价格突破、信号变化、异常波动即时通知

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        推送触发源                                │
├─────────────────────────────────────────────────────────────────┤
│  AnalysisResult    │  PriceAlert    │  Scheduler   │  Manual    │
│  (分析完成事件)     │  (价格突破)     │  (定时任务)   │  (手动触发) │
└─────────┬───────────────┬──────────────┬──────────────┬─────────┘
          │               │              │              │
          ▼               ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NotificationService                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ EventRouter │→ │ RuleEngine  │→ │ Formatter   │             │
│  │ (事件路由)   │  │ (规则过滤)   │  │ (消息格式化) │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ TelegramAdapter │ │ WeChatAdapter   │ │ EmailAdapter    │
│                 │ │ (企业微信)       │ │                 │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
   Telegram API        WeChat Work API      SMTP Server
```

### 1.3 数据模型

```python
# apps/server/db/models.py 新增

class NotificationChannel(SQLModel, table=True):
    """用户通知渠道配置"""
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    channel_type: str  # telegram | wechat_work | dingtalk | email
    channel_config: dict  # {"chat_id": "xxx", "bot_token": "xxx"}
    is_enabled: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationRule(SQLModel, table=True):
    """推送规则配置"""
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    rule_type: str  # signal_change | price_alert | daily_summary | analysis_complete

    # 过滤条件 (JSON)
    conditions: dict  # {"min_confidence": 70, "signals": ["STRONG_BUY", "STRONG_SELL"]}

    # 适用股票 (空=全部自选股)
    symbols: list[str] | None = None

    # 推送渠道 (空=全部启用渠道)
    channel_ids: list[int] | None = None

    is_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationLog(SQLModel, table=True):
    """推送日志"""
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    channel_id: int = Field(foreign_key="notificationchannel.id")

    event_type: str
    symbol: str | None
    title: str
    content: str

    status: str  # pending | sent | failed
    error_message: str | None = None

    sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 1.4 核心服务设计

```python
# apps/server/services/notification_service.py

from abc import ABC, abstractmethod
from typing import Protocol
import httpx


class MessagePayload(BaseModel):
    """统一消息载体"""
    event_type: str  # signal_change | price_alert | daily_summary
    title: str
    summary: str
    details: dict
    symbol: str | None = None
    signal: str | None = None
    confidence: int | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChannelAdapter(Protocol):
    """渠道适配器协议"""
    async def send(self, channel_config: dict, message: str) -> bool: ...
    def format_message(self, payload: MessagePayload) -> str: ...


class TelegramAdapter:
    """Telegram Bot 适配器"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)

    def format_message(self, payload: MessagePayload) -> str:
        """格式化为 Telegram Markdown"""
        emoji_map = {
            "STRONG_BUY": "🚀",
            "BUY": "📈",
            "HOLD": "⏸️",
            "SELL": "📉",
            "STRONG_SELL": "🔻"
        }
        signal_emoji = emoji_map.get(payload.signal, "📊")

        lines = [
            f"*{signal_emoji} {payload.title}*",
            f"",
            f"📌 *股票*: `{payload.symbol}`" if payload.symbol else "",
            f"🎯 *信号*: {payload.signal}" if payload.signal else "",
            f"📊 *置信度*: {payload.confidence}%" if payload.confidence else "",
            f"",
            f"{payload.summary}",
            f"",
            f"🕐 {payload.timestamp.strftime('%Y-%m-%d %H:%M')}"
        ]
        return "\n".join(line for line in lines if line is not None)

    async def send(self, channel_config: dict, message: str) -> bool:
        """发送 Telegram 消息"""
        bot_token = channel_config["bot_token"]
        chat_id = channel_config["chat_id"]

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            resp = await self.client.post(url, json=data)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False


class WeChatWorkAdapter:
    """企业微信机器人适配器"""

    def format_message(self, payload: MessagePayload) -> str:
        """格式化为企业微信 Markdown"""
        lines = [
            f"## {payload.title}",
            f"> {payload.summary}",
            f"",
            f"**股票**: {payload.symbol}" if payload.symbol else "",
            f"**信号**: <font color=\"{'green' if 'BUY' in (payload.signal or '') else 'red'}\">{payload.signal}</font>" if payload.signal else "",
            f"**置信度**: {payload.confidence}%" if payload.confidence else "",
        ]
        return "\n".join(line for line in lines if line)

    async def send(self, channel_config: dict, message: str) -> bool:
        """发送企业微信消息"""
        webhook_url = channel_config["webhook_url"]

        data = {
            "msgtype": "markdown",
            "markdown": {"content": message}
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=data)
            return resp.status_code == 200


class NotificationService:
    """通知服务主类"""

    def __init__(self, session: Session):
        self.session = session
        self.adapters: dict[str, ChannelAdapter] = {
            "telegram": TelegramAdapter(),
            "wechat_work": WeChatWorkAdapter(),
            "dingtalk": DingTalkAdapter(),
            "email": EmailAdapter(),
        }

    async def notify_analysis_complete(
        self,
        user_id: int,
        analysis: AnalysisResult
    ):
        """分析完成通知"""
        payload = MessagePayload(
            event_type="analysis_complete",
            title=f"{analysis.symbol} 分析完成",
            summary=analysis.reasoning[:200] + "..." if len(analysis.reasoning) > 200 else analysis.reasoning,
            details={"full_report": analysis.full_report_json},
            symbol=analysis.symbol,
            signal=analysis.signal,
            confidence=analysis.confidence,
        )
        await self._dispatch(user_id, payload)

    async def notify_signal_change(
        self,
        user_id: int,
        symbol: str,
        old_signal: str,
        new_signal: str,
        confidence: int
    ):
        """信号变化通知"""
        payload = MessagePayload(
            event_type="signal_change",
            title=f"⚡ {symbol} 信号变化",
            summary=f"信号从 {old_signal} 变为 {new_signal}",
            details={"old_signal": old_signal, "new_signal": new_signal},
            symbol=symbol,
            signal=new_signal,
            confidence=confidence,
        )
        await self._dispatch(user_id, payload)

    async def notify_price_alert(
        self,
        user_id: int,
        symbol: str,
        alert_type: str,  # breakout_high | breakout_low | target_reached | stop_loss
        current_price: float,
        threshold_price: float
    ):
        """价格告警通知"""
        alert_titles = {
            "breakout_high": f"📈 {symbol} 突破新高",
            "breakout_low": f"📉 {symbol} 跌破新低",
            "target_reached": f"🎯 {symbol} 到达目标价",
            "stop_loss": f"🚨 {symbol} 触发止损",
        }

        payload = MessagePayload(
            event_type="price_alert",
            title=alert_titles.get(alert_type, f"📊 {symbol} 价格提醒"),
            summary=f"当前价格 {current_price}，阈值 {threshold_price}",
            details={
                "alert_type": alert_type,
                "current_price": current_price,
                "threshold_price": threshold_price
            },
            symbol=symbol,
        )
        await self._dispatch(user_id, payload)

    async def send_daily_summary(self, user_id: int):
        """发送每日摘要"""
        # 获取用户自选股
        watchlist = self.session.exec(
            select(Watchlist).where(Watchlist.user_id == user_id)
        ).all()

        # 获取最新分析
        summaries = []
        for item in watchlist:
            analysis = self.session.exec(
                select(AnalysisResult)
                .where(AnalysisResult.symbol == item.symbol)
                .order_by(AnalysisResult.created_at.desc())
                .limit(1)
            ).first()
            if analysis:
                summaries.append({
                    "symbol": item.symbol,
                    "signal": analysis.signal,
                    "confidence": analysis.confidence
                })

        payload = MessagePayload(
            event_type="daily_summary",
            title="📊 每日持仓摘要",
            summary=f"共 {len(summaries)} 只股票",
            details={"positions": summaries},
        )
        await self._dispatch(user_id, payload)

    async def _dispatch(self, user_id: int, payload: MessagePayload):
        """分发消息到各渠道"""
        # 1. 获取用户规则
        rules = self.session.exec(
            select(NotificationRule)
            .where(NotificationRule.user_id == user_id)
            .where(NotificationRule.rule_type == payload.event_type)
            .where(NotificationRule.is_enabled == True)
        ).all()

        # 2. 规则匹配
        for rule in rules:
            if not self._match_rule(rule, payload):
                continue

            # 3. 获取渠道
            channels = self.session.exec(
                select(NotificationChannel)
                .where(NotificationChannel.user_id == user_id)
                .where(NotificationChannel.is_enabled == True)
            ).all()

            if rule.channel_ids:
                channels = [c for c in channels if c.id in rule.channel_ids]

            # 4. 发送
            for channel in channels:
                await self._send_to_channel(channel, payload)

    def _match_rule(self, rule: NotificationRule, payload: MessagePayload) -> bool:
        """规则匹配"""
        conditions = rule.conditions or {}

        # 股票过滤
        if rule.symbols and payload.symbol not in rule.symbols:
            return False

        # 置信度过滤
        if "min_confidence" in conditions:
            if payload.confidence and payload.confidence < conditions["min_confidence"]:
                return False

        # 信号过滤
        if "signals" in conditions:
            if payload.signal and payload.signal not in conditions["signals"]:
                return False

        return True

    async def _send_to_channel(
        self,
        channel: NotificationChannel,
        payload: MessagePayload
    ):
        """发送到指定渠道"""
        adapter = self.adapters.get(channel.channel_type)
        if not adapter:
            return

        message = adapter.format_message(payload)
        success = await adapter.send(channel.channel_config, message)

        # 记录日志
        log = NotificationLog(
            user_id=channel.user_id,
            channel_id=channel.id,
            event_type=payload.event_type,
            symbol=payload.symbol,
            title=payload.title,
            content=message,
            status="sent" if success else "failed",
            sent_at=datetime.utcnow() if success else None,
        )
        self.session.add(log)
        self.session.commit()
```

### 1.5 API 设计

```python
# apps/server/api/routes/system/notification.py

router = APIRouter(prefix="/notification", tags=["notification"])


# ===== 渠道管理 =====

@router.get("/channels", response_model=list[NotificationChannelResponse])
async def list_channels(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """获取用户通知渠道列表"""
    pass


@router.post("/channels", response_model=NotificationChannelResponse)
async def create_channel(
    data: NotificationChannelCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """创建通知渠道"""
    pass


@router.put("/channels/{channel_id}")
async def update_channel(channel_id: int, data: NotificationChannelUpdate): ...


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: int): ...


@router.post("/channels/{channel_id}/test")
async def test_channel(channel_id: int):
    """测试渠道连通性"""
    pass


# ===== 规则管理 =====

@router.get("/rules", response_model=list[NotificationRuleResponse])
async def list_rules(user: User = Depends(get_current_user)): ...


@router.post("/rules", response_model=NotificationRuleResponse)
async def create_rule(data: NotificationRuleCreate): ...


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, data: NotificationRuleUpdate): ...


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int): ...


# ===== 推送日志 =====

@router.get("/logs", response_model=list[NotificationLogResponse])
async def list_logs(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user)
): ...


# ===== 手动触发 =====

@router.post("/send/daily-summary")
async def trigger_daily_summary(user: User = Depends(get_current_user)):
    """手动触发每日摘要"""
    pass
```

### 1.6 定时任务集成

```python
# apps/server/services/scheduler.py 扩展

def setup_notification_jobs(scheduler: APScheduler):
    """设置通知相关定时任务"""

    # 早盘摘要 (交易日 9:00)
    scheduler.add_job(
        send_morning_briefing,
        CronTrigger(hour=9, minute=0, day_of_week="mon-fri"),
        id="morning_briefing",
        replace_existing=True
    )

    # 收盘摘要 (交易日 15:30)
    scheduler.add_job(
        send_closing_summary,
        CronTrigger(hour=15, minute=30, day_of_week="mon-fri"),
        id="closing_summary",
        replace_existing=True
    )

    # 价格监控 (每分钟)
    scheduler.add_job(
        check_price_alerts,
        IntervalTrigger(minutes=1),
        id="price_alerts",
        replace_existing=True
    )
```

### 1.7 前端组件

```typescript
// apps/client/pages/NotificationSettingsPage.tsx

interface NotificationSettingsPageProps {}

export function NotificationSettingsPage() {
  const { data: channels } = useNotificationChannels();
  const { data: rules } = useNotificationRules();

  return (
    <PageLayout title="通知设置">
      {/* 渠道配置 */}
      <Card title="推送渠道">
        <ChannelList channels={channels} />
        <AddChannelButton />
      </Card>

      {/* 规则配置 */}
      <Card title="推送规则">
        <RuleList rules={rules} />
        <AddRuleButton />
      </Card>

      {/* 推送历史 */}
      <Card title="推送历史">
        <NotificationLogTable />
      </Card>
    </PageLayout>
  );
}
```

### 1.8 实现步骤

| 阶段 | 任务 | 工时 |
|------|------|------|
| **Phase 1** | 数据模型 + NotificationService 核心 | 2天 |
| **Phase 2** | Telegram 适配器 + 测试 | 1天 |
| **Phase 3** | 企业微信/钉钉适配器 | 1天 |
| **Phase 4** | API 路由 + 规则引擎 | 2天 |
| **Phase 5** | 定时任务集成 + 价格监控 | 1天 |
| **Phase 6** | 前端页面 | 2天 |
| **Phase 7** | 测试 + 文档 | 1天 |
| **总计** | | **10天** |

### 1.9 依赖项

```toml
# pyproject.toml 新增
python-telegram-bot = ">=21.0"
```

---

## 2. WhaleWatcher 筹码追踪

### 2.1 功能概述

追踪机构投资者和内部人的持仓变动，为散户提供"跟随聪明资金"的决策参考。

**核心能力**：
- 🏦 13F 机构持仓：追踪对冲基金、共同基金季度持仓披露
- 👔 内部人交易：监控高管、董事的买卖行为
- 📊 L2 大单流向：实时监控大额委托单（A股特色）
- 🔔 异动告警：机构大幅增减仓、内部人集中买卖

### 2.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         数据源层                                 │
├─────────────────────────────────────────────────────────────────┤
│  SEC EDGAR API     │  OpenInsider      │  AkShare L2           │
│  (13F 文件)         │  (内部人交易)      │  (A股大单)             │
└─────────┬───────────────┬──────────────────┬────────────────────┘
          │               │                  │
          ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WhaleDataCollector                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 13FParser   │  │ InsiderParser│  │ L2BigOrder  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WhaleWatcherAgent                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 筹码分布分析 │  │ 趋势识别    │  │ 信号生成    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                      TradingAgentsGraph
                       (注入分析流程)
```

### 2.3 数据模型

```python
# apps/server/db/models.py 新增

class InstitutionalHolding(SQLModel, table=True):
    """机构持仓记录 (13F)"""
    id: int | None = Field(default=None, primary_key=True)

    # 机构信息
    cik: str = Field(index=True)  # SEC CIK 号
    manager_name: str  # 机构名称

    # 持仓信息
    symbol: str = Field(index=True)
    cusip: str  # CUSIP 证券标识
    shares: int  # 持股数量
    value_usd: float  # 市值 (USD)

    # 变动信息
    shares_change: int | None  # 较上期变化
    change_pct: float | None  # 变化百分比
    change_type: str | None  # new | increased | decreased | sold_out | unchanged

    # 披露信息
    report_date: date  # 报告期 (季度末)
    filed_date: date  # 申报日期

    created_at: datetime = Field(default_factory=datetime.utcnow)


class InsiderTransaction(SQLModel, table=True):
    """内部人交易记录"""
    id: int | None = Field(default=None, primary_key=True)

    symbol: str = Field(index=True)

    # 内部人信息
    insider_name: str
    insider_title: str  # CEO | CFO | Director | 10% Owner

    # 交易信息
    transaction_type: str  # P (Purchase) | S (Sale) | A (Award) | G (Gift)
    shares: int
    price: float | None
    value_usd: float | None

    # 持仓信息
    shares_owned_after: int | None

    # 时间
    transaction_date: date
    filed_date: date

    created_at: datetime = Field(default_factory=datetime.utcnow)


class BigOrderFlow(SQLModel, table=True):
    """A股大单流向 (L2)"""
    id: int | None = Field(default=None, primary_key=True)

    symbol: str = Field(index=True)
    trade_date: date = Field(index=True)

    # 大单统计 (单笔 > 50万)
    big_order_buy_count: int
    big_order_buy_volume: int
    big_order_buy_amount: float

    big_order_sell_count: int
    big_order_sell_volume: int
    big_order_sell_amount: float

    # 净流入
    big_order_net_amount: float
    big_order_net_ratio: float  # 占成交额比例

    # 超大单统计 (单笔 > 100万)
    super_big_buy_amount: float
    super_big_sell_amount: float
    super_big_net_amount: float

    # 主力控盘度估算
    main_force_ratio: float | None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class WhaleAlert(SQLModel, table=True):
    """巨鲸异动告警"""
    id: int | None = Field(default=None, primary_key=True)

    symbol: str = Field(index=True)
    alert_type: str  # institutional_increase | insider_cluster_buy | big_order_surge

    title: str
    description: str

    # 关联数据
    related_holdings: list[int] | None  # InstitutionalHolding IDs
    related_transactions: list[int] | None  # InsiderTransaction IDs

    severity: str  # info | warning | critical

    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 2.4 数据采集服务

```python
# apps/server/services/whale_data_service.py

class WhaleDataService:
    """巨鲸数据采集服务"""

    def __init__(self, session: Session):
        self.session = session
        self.sec_client = SECEdgarClient()
        self.insider_client = OpenInsiderClient()

    async def sync_13f_holdings(self, cik: str | None = None):
        """同步 13F 机构持仓"""
        # 获取最新 13F 文件列表
        filings = await self.sec_client.get_13f_filings(cik=cik, limit=100)

        for filing in filings:
            # 解析持仓数据
            holdings = await self.sec_client.parse_13f_holding(filing["url"])

            # 计算变动
            previous = self._get_previous_holdings(filing["cik"], filing["report_date"])

            for holding in holdings:
                change_info = self._calculate_change(holding, previous)

                record = InstitutionalHolding(
                    cik=filing["cik"],
                    manager_name=filing["manager_name"],
                    symbol=holding["symbol"],
                    cusip=holding["cusip"],
                    shares=holding["shares"],
                    value_usd=holding["value"],
                    shares_change=change_info["shares_change"],
                    change_pct=change_info["change_pct"],
                    change_type=change_info["change_type"],
                    report_date=filing["report_date"],
                    filed_date=filing["filed_date"],
                )
                self.session.add(record)

        self.session.commit()

    async def sync_insider_transactions(self, symbol: str | None = None):
        """同步内部人交易"""
        transactions = await self.insider_client.get_transactions(
            symbol=symbol,
            days=30
        )

        for tx in transactions:
            record = InsiderTransaction(
                symbol=tx["symbol"],
                insider_name=tx["insider_name"],
                insider_title=tx["insider_title"],
                transaction_type=tx["transaction_type"],
                shares=tx["shares"],
                price=tx.get("price"),
                value_usd=tx.get("value"),
                shares_owned_after=tx.get("shares_owned_after"),
                transaction_date=tx["transaction_date"],
                filed_date=tx["filed_date"],
            )
            self.session.add(record)

        self.session.commit()

    async def sync_big_order_flow(self, symbol: str):
        """同步 A股大单流向"""
        # 使用 AkShare 获取大单数据
        data = ak.stock_individual_fund_flow(stock=symbol, market="sh")

        for _, row in data.iterrows():
            record = BigOrderFlow(
                symbol=symbol,
                trade_date=row["日期"],
                big_order_buy_count=row["大单买入笔数"],
                big_order_buy_volume=row["大单买入量"],
                big_order_buy_amount=row["大单买入额"],
                big_order_sell_count=row["大单卖出笔数"],
                big_order_sell_volume=row["大单卖出量"],
                big_order_sell_amount=row["大单卖出额"],
                big_order_net_amount=row["大单净额"],
                big_order_net_ratio=row["大单净占比"],
                super_big_buy_amount=row["超大单买入额"],
                super_big_sell_amount=row["超大单卖出额"],
                super_big_net_amount=row["超大单净额"],
            )
            self.session.merge(record)

        self.session.commit()


class SECEdgarClient:
    """SEC EDGAR API 客户端"""

    BASE_URL = "https://data.sec.gov"

    async def get_13f_filings(self, cik: str | None = None, limit: int = 100):
        """获取 13F 文件列表"""
        # SEC EDGAR API 调用
        pass

    async def parse_13f_holding(self, filing_url: str) -> list[dict]:
        """解析 13F XML 文件"""
        pass


class OpenInsiderClient:
    """OpenInsider 数据客户端"""

    async def get_transactions(self, symbol: str | None = None, days: int = 30):
        """获取内部人交易"""
        pass
```

### 2.5 WhaleWatcher Agent

```python
# apps/server/tradingagents/agents/analysts/whale_watcher.py

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate


class WhaleWatcherAgent:
    """筹码追踪分析师"""

    def __init__(self, llm, tools: list):
        self.llm = llm
        self.tools = tools

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位专业的筹码分析师，专注于追踪机构投资者和内部人的交易行为。

你的分析维度包括：
1. **13F 机构持仓分析**
   - 顶级对冲基金的持仓变动
   - 机构共识度（多少家机构持有）
   - 季度环比变化趋势

2. **内部人交易分析**
   - 高管买卖信号（CEO/CFO 买入是强信号）
   - 集群买卖（多人同时买入）
   - 交易金额相对薪酬比例

3. **大单流向分析**（A股）
   - 主力资金净流入/流出
   - 大单买卖比例
   - 超大单异动

4. **综合筹码判断**
   - 筹码集中度变化
   - 聪明资金动向
   - 潜在风险信号

请基于数据给出客观、量化的分析，避免主观臆断。"""),
            ("human", """请分析 {symbol} 的筹码情况：

## 机构持仓数据 (13F)
{institutional_data}

## 内部人交易数据
{insider_data}

## 大单流向数据
{big_order_data}

请给出：
1. 机构动向总结
2. 内部人信号解读
3. 主力资金判断
4. 综合筹码评级 (1-10)
5. 关键风险提示""")
        ])

    async def analyze(self, state: AgentState) -> dict:
        symbol = state["symbol"]

        # 获取数据
        institutional_data = await self._get_institutional_data(symbol)
        insider_data = await self._get_insider_data(symbol)
        big_order_data = await self._get_big_order_data(symbol)

        # 生成分析
        chain = self.prompt | self.llm
        response = await chain.ainvoke({
            "symbol": symbol,
            "institutional_data": institutional_data,
            "insider_data": insider_data,
            "big_order_data": big_order_data,
        })

        return {"whale_report": response.content}

    async def _get_institutional_data(self, symbol: str) -> str:
        """获取机构持仓数据"""
        # 调用 whale_data_service
        pass

    async def _get_insider_data(self, symbol: str) -> str:
        """获取内部人交易数据"""
        pass

    async def _get_big_order_data(self, symbol: str) -> str:
        """获取大单流向数据"""
        pass
```

### 2.6 API 设计

```python
# apps/server/api/routes/market/whale.py

router = APIRouter(prefix="/whale", tags=["whale"])


@router.get("/institutional/{symbol}", response_model=InstitutionalHoldingResponse)
async def get_institutional_holdings(
    symbol: str,
    quarters: int = 4,  # 最近几个季度
    min_value: float | None = None,  # 最小持仓市值过滤
):
    """获取机构持仓"""
    pass


@router.get("/institutional/top-holders/{symbol}")
async def get_top_holders(symbol: str, limit: int = 20):
    """获取前 N 大机构持有者"""
    pass


@router.get("/institutional/changes/{symbol}")
async def get_holding_changes(symbol: str, change_type: str | None = None):
    """获取机构持仓变动"""
    pass


@router.get("/insider/{symbol}", response_model=list[InsiderTransactionResponse])
async def get_insider_transactions(
    symbol: str,
    days: int = 90,
    transaction_type: str | None = None,  # P | S
):
    """获取内部人交易"""
    pass


@router.get("/insider/cluster-buys")
async def get_cluster_buys(days: int = 30, min_insiders: int = 3):
    """获取内部人集群买入（多人同时买入）"""
    pass


@router.get("/big-orders/{symbol}", response_model=list[BigOrderFlowResponse])
async def get_big_order_flow(symbol: str, days: int = 30):
    """获取大单流向（A股）"""
    pass


@router.get("/alerts", response_model=list[WhaleAlertResponse])
async def get_whale_alerts(
    symbol: str | None = None,
    days: int = 7,
    severity: str | None = None,
):
    """获取巨鲸异动告警"""
    pass


@router.post("/sync/{symbol}")
async def sync_whale_data(symbol: str, background_tasks: BackgroundTasks):
    """手动触发数据同步"""
    pass
```

### 2.7 前端组件

```typescript
// apps/client/components/WhalePanel.tsx

export function WhalePanel({ symbol }: { symbol: string }) {
  const { data: institutional } = useInstitutionalHoldings(symbol);
  const { data: insider } = useInsiderTransactions(symbol);
  const { data: bigOrders } = useBigOrderFlow(symbol);

  return (
    <div className="space-y-6">
      {/* 机构持仓 */}
      <Card title="🏦 机构持仓">
        <InstitutionalChart data={institutional} />
        <TopHoldersTable holders={institutional?.top_holders} />
      </Card>

      {/* 内部人交易 */}
      <Card title="👔 内部人交易">
        <InsiderTimeline transactions={insider} />
        <ClusterBuyAlert />
      </Card>

      {/* 大单流向 (A股) */}
      {symbol.endsWith('.SH') || symbol.endsWith('.SZ') ? (
        <Card title="📊 主力资金">
          <BigOrderChart data={bigOrders} />
          <NetFlowIndicator value={bigOrders?.net_amount} />
        </Card>
      ) : null}

      {/* 筹码评级 */}
      <Card title="🎯 筹码综合评级">
        <WhaleScoreGauge score={8.5} />
      </Card>
    </div>
  );
}
```

### 2.8 实现步骤

| 阶段 | 任务 | 工时 |
|------|------|------|
| **Phase 1** | 数据模型设计 + 迁移 | 1天 |
| **Phase 2** | SEC EDGAR 13F 采集 | 3天 |
| **Phase 3** | 内部人交易采集 | 2天 |
| **Phase 4** | A股大单流向集成 | 2天 |
| **Phase 5** | WhaleWatcherAgent 实现 | 3天 |
| **Phase 6** | API 路由开发 | 2天 |
| **Phase 7** | 告警规则引擎 | 2天 |
| **Phase 8** | 前端组件开发 | 3天 |
| **Phase 9** | 测试 + 文档 | 2天 |
| **总计** | | **20天** |

### 2.9 依赖项

```toml
# pyproject.toml 新增
sec-edgar-downloader = ">=5.0"
```

---

## 3. 蒙特卡洛/VaR 风险建模

### 3.1 功能概述

构建机构级风险量化系统，为投资组合提供科学的风险评估和压力测试能力。

**核心能力**：
- 📉 VaR 计算：历史模拟法、参数法、蒙特卡洛法
- 🎲 蒙特卡洛模拟：价格路径模拟、收益分布预测
- 🔥 压力测试：历史情景、假设情景、极端事件
- 📊 风险归因：Beta 分解、因子暴露、尾部风险

### 3.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        风险计算引擎                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ VaRCalculator   │  │ MonteCarloEngine│  │ StressTester    │ │
│  │                 │  │                 │  │                 │ │
│  │ - Historical    │  │ - GBM 模型      │  │ - 历史情景      │ │
│  │ - Parametric    │  │ - Jump Diffusion│  │ - 假设情景      │ │
│  │ - Monte Carlo   │  │ - GARCH         │  │ - 极端事件      │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │          │
│           └────────────────────┼────────────────────┘          │
│                                │                               │
│                                ▼                               │
│                    ┌─────────────────────┐                     │
│                    │ RiskAggregator      │                     │
│                    │ (风险指标聚合)       │                     │
│                    └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ RiskManagerAgent    │
                    │ (注入分析流程)       │
                    └─────────────────────┘
```

### 3.3 数据模型

```python
# apps/server/db/models.py 新增

class RiskMetrics(SQLModel, table=True):
    """风险指标快照"""
    id: int | None = Field(default=None, primary_key=True)

    # 标的
    symbol: str | None = Field(index=True)  # 单只股票
    portfolio_id: int | None = None  # 或组合

    calculation_date: date = Field(index=True)

    # VaR 指标
    var_95_1d: float  # 95% 置信度 1 日 VaR
    var_99_1d: float  # 99% 置信度 1 日 VaR
    var_95_10d: float  # 95% 置信度 10 日 VaR
    cvar_95_1d: float  # 条件 VaR (Expected Shortfall)

    # 波动率
    volatility_daily: float  # 日波动率
    volatility_annual: float  # 年化波动率

    # Beta 和相关性
    beta_sp500: float | None
    beta_csi300: float | None  # A股
    correlation_market: float

    # 蒙特卡洛结果
    mc_mean_return: float | None
    mc_median_return: float | None
    mc_5th_percentile: float | None
    mc_95th_percentile: float | None

    # 尾部风险
    skewness: float
    kurtosis: float
    max_drawdown_historical: float

    created_at: datetime = Field(default_factory=datetime.utcnow)


class StressTestResult(SQLModel, table=True):
    """压力测试结果"""
    id: int | None = Field(default=None, primary_key=True)

    symbol: str | None = Field(index=True)
    portfolio_id: int | None = None

    scenario_name: str  # 2008_financial_crisis | covid_crash | rate_hike_shock
    scenario_type: str  # historical | hypothetical | extreme

    # 情景参数
    scenario_params: dict  # {"market_drop": -30, "vol_spike": 2.5}

    # 结果
    portfolio_return: float  # 组合收益率
    max_drawdown: float
    recovery_days: int | None

    # 影响分解
    impact_by_sector: dict | None  # {"tech": -15%, "finance": -20%}
    impact_by_factor: dict | None  # {"market": -25%, "size": -5%}

    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class MonteCarloSimulation(SQLModel, table=True):
    """蒙特卡洛模拟记录"""
    id: int | None = Field(default=None, primary_key=True)

    symbol: str | None = Field(index=True)
    portfolio_id: int | None = None

    # 模拟参数
    model_type: str  # gbm | jump_diffusion | garch
    num_simulations: int  # 模拟次数 (通常 10000)
    time_horizon_days: int  # 预测期限

    # 输入参数
    initial_price: float
    drift: float  # μ
    volatility: float  # σ

    # 结果分布
    final_prices: list[float]  # 所有模拟的最终价格
    paths_sample: list[list[float]] | None  # 抽样路径 (用于可视化)

    # 统计摘要
    mean_final_price: float
    median_final_price: float
    std_final_price: float
    percentiles: dict  # {5: xxx, 25: xxx, 50: xxx, 75: xxx, 95: xxx}

    # 概率分析
    prob_above_current: float  # 高于当前价的概率
    prob_loss_10pct: float  # 下跌 10% 的概率
    prob_gain_20pct: float  # 上涨 20% 的概率

    calculated_at: datetime = Field(default_factory=datetime.utcnow)
```

### 3.4 风险计算引擎

```python
# apps/server/services/risk_engine.py

import numpy as np
from scipy import stats
from typing import Literal


class VaRCalculator:
    """VaR 计算器"""

    def __init__(self, returns: np.ndarray):
        """
        Args:
            returns: 历史收益率序列
        """
        self.returns = returns

    def historical_var(
        self,
        confidence: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """历史模拟法 VaR"""
        # 调整到目标期限 (假设收益率独立同分布)
        adjusted_returns = self.returns * np.sqrt(horizon_days)

        # 计算分位数
        var = np.percentile(adjusted_returns, (1 - confidence) * 100)
        return abs(var)

    def parametric_var(
        self,
        confidence: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """参数法 VaR (假设正态分布)"""
        mu = self.returns.mean()
        sigma = self.returns.std()

        # Z 分数
        z = stats.norm.ppf(1 - confidence)

        # VaR
        var = -(mu * horizon_days + z * sigma * np.sqrt(horizon_days))
        return abs(var)

    def monte_carlo_var(
        self,
        confidence: float = 0.95,
        horizon_days: int = 1,
        num_simulations: int = 10000
    ) -> float:
        """蒙特卡洛法 VaR"""
        mu = self.returns.mean()
        sigma = self.returns.std()

        # 模拟
        simulated_returns = np.random.normal(
            mu * horizon_days,
            sigma * np.sqrt(horizon_days),
            num_simulations
        )

        var = np.percentile(simulated_returns, (1 - confidence) * 100)
        return abs(var)

    def expected_shortfall(
        self,
        confidence: float = 0.95,
        horizon_days: int = 1
    ) -> float:
        """条件 VaR (Expected Shortfall / CVaR)"""
        var = self.historical_var(confidence, horizon_days)

        # ES = 超过 VaR 的平均损失
        adjusted_returns = self.returns * np.sqrt(horizon_days)
        tail_returns = adjusted_returns[adjusted_returns <= -var]

        if len(tail_returns) == 0:
            return var

        return abs(tail_returns.mean())


class MonteCarloEngine:
    """蒙特卡洛模拟引擎"""

    def __init__(
        self,
        initial_price: float,
        returns: np.ndarray,
        model: Literal["gbm", "jump_diffusion", "garch"] = "gbm"
    ):
        self.initial_price = initial_price
        self.returns = returns
        self.model = model

        # 估计参数
        self.mu = returns.mean() * 252  # 年化漂移
        self.sigma = returns.std() * np.sqrt(252)  # 年化波动率

    def simulate_gbm(
        self,
        horizon_days: int,
        num_simulations: int = 10000,
        num_steps: int | None = None
    ) -> dict:
        """几何布朗运动模拟"""
        if num_steps is None:
            num_steps = horizon_days

        dt = horizon_days / 252 / num_steps

        # 生成随机路径
        Z = np.random.standard_normal((num_simulations, num_steps))

        # GBM: dS = μSdt + σSdW
        drift = (self.mu - 0.5 * self.sigma**2) * dt
        diffusion = self.sigma * np.sqrt(dt) * Z

        log_returns = drift + diffusion
        log_prices = np.cumsum(log_returns, axis=1)

        paths = self.initial_price * np.exp(log_prices)
        final_prices = paths[:, -1]

        return {
            "final_prices": final_prices,
            "paths_sample": paths[:100].tolist(),  # 保存 100 条路径用于可视化
            "statistics": self._calculate_statistics(final_prices)
        }

    def simulate_jump_diffusion(
        self,
        horizon_days: int,
        num_simulations: int = 10000,
        jump_intensity: float = 0.1,  # 年均跳跃次数
        jump_mean: float = -0.05,  # 跳跃均值
        jump_std: float = 0.1  # 跳跃标准差
    ) -> dict:
        """跳跃扩散模型 (Merton)"""
        dt = horizon_days / 252
        num_steps = horizon_days

        paths = np.zeros((num_simulations, num_steps))
        paths[:, 0] = self.initial_price

        for t in range(1, num_steps):
            # 扩散部分
            dW = np.random.standard_normal(num_simulations) * np.sqrt(dt/num_steps)
            diffusion = self.sigma * paths[:, t-1] * dW

            # 跳跃部分
            jump_count = np.random.poisson(jump_intensity * dt/num_steps, num_simulations)
            jump_size = np.random.normal(jump_mean, jump_std, num_simulations) * jump_count

            # 价格更新
            paths[:, t] = paths[:, t-1] * (1 + self.mu * dt/num_steps + diffusion/paths[:, t-1] + jump_size)
            paths[:, t] = np.maximum(paths[:, t], 0.01)  # 防止负价格

        final_prices = paths[:, -1]

        return {
            "final_prices": final_prices,
            "paths_sample": paths[:100].tolist(),
            "statistics": self._calculate_statistics(final_prices)
        }

    def _calculate_statistics(self, final_prices: np.ndarray) -> dict:
        """计算统计摘要"""
        current = self.initial_price

        return {
            "mean": float(final_prices.mean()),
            "median": float(np.median(final_prices)),
            "std": float(final_prices.std()),
            "percentiles": {
                5: float(np.percentile(final_prices, 5)),
                25: float(np.percentile(final_prices, 25)),
                50: float(np.percentile(final_prices, 50)),
                75: float(np.percentile(final_prices, 75)),
                95: float(np.percentile(final_prices, 95)),
            },
            "prob_above_current": float((final_prices > current).mean()),
            "prob_loss_10pct": float((final_prices < current * 0.9).mean()),
            "prob_gain_20pct": float((final_prices > current * 1.2).mean()),
        }


class StressTester:
    """压力测试器"""

    # 预定义历史情景
    HISTORICAL_SCENARIOS = {
        "2008_financial_crisis": {
            "name": "2008 金融危机",
            "period": ("2008-09-01", "2009-03-09"),
            "market_drop": -0.57,
            "vol_multiplier": 3.0,
        },
        "covid_crash": {
            "name": "2020 新冠崩盘",
            "period": ("2020-02-19", "2020-03-23"),
            "market_drop": -0.34,
            "vol_multiplier": 4.0,
        },
        "2022_rate_hike": {
            "name": "2022 加息周期",
            "period": ("2022-01-01", "2022-10-12"),
            "market_drop": -0.27,
            "vol_multiplier": 1.5,
        },
        "china_2015_crash": {
            "name": "2015 A股股灾",
            "period": ("2015-06-12", "2015-08-26"),
            "market_drop": -0.45,
            "vol_multiplier": 3.5,
        },
    }

    # 预定义假设情景
    HYPOTHETICAL_SCENARIOS = {
        "rate_hike_shock": {
            "name": "利率冲击 (+200bp)",
            "params": {"rate_change": 0.02, "market_sensitivity": -0.15},
        },
        "inflation_surge": {
            "name": "通胀飙升",
            "params": {"inflation_change": 0.03, "market_sensitivity": -0.10},
        },
        "geopolitical_crisis": {
            "name": "地缘政治危机",
            "params": {"market_drop": -0.20, "vol_spike": 2.0},
        },
        "tech_bubble_burst": {
            "name": "科技泡沫破裂",
            "params": {"tech_drop": -0.40, "other_drop": -0.15},
        },
    }

    def __init__(self, portfolio: dict[str, float], prices: dict[str, float]):
        """
        Args:
            portfolio: {symbol: weight}
            prices: {symbol: current_price}
        """
        self.portfolio = portfolio
        self.prices = prices

    def run_historical_scenario(self, scenario_key: str) -> dict:
        """运行历史情景测试"""
        scenario = self.HISTORICAL_SCENARIOS[scenario_key]

        # 简化计算：使用市场跌幅 * Beta
        total_loss = 0
        impact_by_symbol = {}

        for symbol, weight in self.portfolio.items():
            beta = self._get_beta(symbol)
            symbol_loss = scenario["market_drop"] * beta * weight
            total_loss += symbol_loss
            impact_by_symbol[symbol] = symbol_loss

        return {
            "scenario_name": scenario["name"],
            "portfolio_return": total_loss,
            "impact_by_symbol": impact_by_symbol,
            "max_drawdown": abs(total_loss),
        }

    def run_hypothetical_scenario(self, scenario_key: str) -> dict:
        """运行假设情景测试"""
        scenario = self.HYPOTHETICAL_SCENARIOS[scenario_key]
        params = scenario["params"]

        # 根据情景类型计算影响
        if "market_drop" in params:
            return self._apply_market_shock(params["market_drop"], params.get("vol_spike", 1.0))
        elif "rate_change" in params:
            return self._apply_rate_shock(params["rate_change"], params["market_sensitivity"])
        else:
            raise ValueError(f"Unknown scenario params: {params}")

    def _get_beta(self, symbol: str) -> float:
        """获取股票 Beta"""
        # TODO: 从数据库或计算获取
        return 1.0

    def _apply_market_shock(self, drop: float, vol_spike: float) -> dict:
        """应用市场冲击"""
        total_loss = 0
        for symbol, weight in self.portfolio.items():
            beta = self._get_beta(symbol)
            symbol_loss = drop * beta * weight
            total_loss += symbol_loss

        return {
            "portfolio_return": total_loss,
            "max_drawdown": abs(total_loss),
            "volatility_impact": vol_spike,
        }

    def _apply_rate_shock(self, rate_change: float, sensitivity: float) -> dict:
        """应用利率冲击"""
        # 简化：所有股票受相同影响
        total_loss = sensitivity * (rate_change / 0.01)  # 每 1% 利率变化

        return {
            "portfolio_return": total_loss,
            "rate_sensitivity": sensitivity,
        }
```

### 3.5 风险服务层

```python
# apps/server/services/risk_service.py

class RiskService:
    """风险分析服务"""

    def __init__(self, session: Session, data_router: MarketRouter):
        self.session = session
        self.data_router = data_router

    async def calculate_risk_metrics(
        self,
        symbol: str,
        lookback_days: int = 252
    ) -> RiskMetrics:
        """计算单只股票风险指标"""
        # 获取历史价格
        prices = await self.data_router.get_history(symbol, days=lookback_days)
        returns = prices["close"].pct_change().dropna().values

        # VaR 计算
        var_calc = VaRCalculator(returns)

        # 蒙特卡洛模拟
        mc_engine = MonteCarloEngine(
            initial_price=prices["close"].iloc[-1],
            returns=returns
        )
        mc_result = mc_engine.simulate_gbm(horizon_days=30)

        # 构建结果
        metrics = RiskMetrics(
            symbol=symbol,
            calculation_date=date.today(),
            var_95_1d=var_calc.historical_var(0.95, 1),
            var_99_1d=var_calc.historical_var(0.99, 1),
            var_95_10d=var_calc.historical_var(0.95, 10),
            cvar_95_1d=var_calc.expected_shortfall(0.95, 1),
            volatility_daily=float(returns.std()),
            volatility_annual=float(returns.std() * np.sqrt(252)),
            beta_sp500=await self._calculate_beta(returns, "SPY"),
            skewness=float(stats.skew(returns)),
            kurtosis=float(stats.kurtosis(returns)),
            max_drawdown_historical=self._calculate_max_drawdown(prices["close"]),
            mc_mean_return=mc_result["statistics"]["mean"] / prices["close"].iloc[-1] - 1,
            mc_median_return=mc_result["statistics"]["median"] / prices["close"].iloc[-1] - 1,
            mc_5th_percentile=mc_result["statistics"]["percentiles"][5] / prices["close"].iloc[-1] - 1,
            mc_95th_percentile=mc_result["statistics"]["percentiles"][95] / prices["close"].iloc[-1] - 1,
        )

        self.session.add(metrics)
        self.session.commit()

        return metrics

    async def calculate_portfolio_risk(
        self,
        portfolio: dict[str, float]  # {symbol: weight}
    ) -> dict:
        """计算组合风险"""
        # 获取各股票收益率
        returns_matrix = []
        symbols = list(portfolio.keys())

        for symbol in symbols:
            prices = await self.data_router.get_history(symbol, days=252)
            returns_matrix.append(prices["close"].pct_change().dropna().values)

        returns_df = pd.DataFrame(dict(zip(symbols, returns_matrix)))
        weights = np.array([portfolio[s] for s in symbols])

        # 组合收益率
        portfolio_returns = (returns_df * weights).sum(axis=1).values

        # 组合 VaR
        var_calc = VaRCalculator(portfolio_returns)

        # 相关性矩阵
        correlation_matrix = returns_df.corr()

        # 风险贡献
        cov_matrix = returns_df.cov() * 252  # 年化
        portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
        marginal_risk = cov_matrix @ weights / portfolio_vol
        risk_contribution = weights * marginal_risk / portfolio_vol

        return {
            "portfolio_var_95": var_calc.historical_var(0.95, 1),
            "portfolio_cvar_95": var_calc.expected_shortfall(0.95, 1),
            "portfolio_volatility": float(portfolio_returns.std() * np.sqrt(252)),
            "correlation_matrix": correlation_matrix.to_dict(),
            "risk_contribution": dict(zip(symbols, risk_contribution.tolist())),
            "diversification_ratio": self._calculate_diversification_ratio(weights, cov_matrix),
        }

    async def run_stress_test(
        self,
        portfolio: dict[str, float],
        scenario: str
    ) -> StressTestResult:
        """运行压力测试"""
        prices = {}
        for symbol in portfolio:
            price_data = await self.data_router.get_price(symbol)
            prices[symbol] = price_data["price"]

        tester = StressTester(portfolio, prices)

        if scenario in StressTester.HISTORICAL_SCENARIOS:
            result = tester.run_historical_scenario(scenario)
            scenario_type = "historical"
        else:
            result = tester.run_hypothetical_scenario(scenario)
            scenario_type = "hypothetical"

        record = StressTestResult(
            scenario_name=scenario,
            scenario_type=scenario_type,
            portfolio_return=result["portfolio_return"],
            max_drawdown=result["max_drawdown"],
            impact_by_sector=result.get("impact_by_symbol"),
        )

        self.session.add(record)
        self.session.commit()

        return record

    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """计算最大回撤"""
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        return float(drawdown.min())

    def _calculate_diversification_ratio(
        self,
        weights: np.ndarray,
        cov_matrix: pd.DataFrame
    ) -> float:
        """计算分散化比率"""
        portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
        weighted_vol = (weights * np.sqrt(np.diag(cov_matrix))).sum()
        return float(weighted_vol / portfolio_vol)
```

### 3.6 API 设计

```python
# apps/server/api/routes/analysis/risk.py

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/metrics/{symbol}", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    symbol: str,
    recalculate: bool = False
):
    """获取股票风险指标"""
    pass


@router.get("/portfolio", response_model=PortfolioRiskResponse)
async def get_portfolio_risk(
    user: User = Depends(get_current_user)
):
    """获取用户组合风险"""
    pass


@router.post("/monte-carlo/{symbol}", response_model=MonteCarloResponse)
async def run_monte_carlo(
    symbol: str,
    horizon_days: int = 30,
    num_simulations: int = 10000,
    model: str = "gbm"
):
    """运行蒙特卡洛模拟"""
    pass


@router.get("/stress-test/scenarios")
async def list_stress_scenarios():
    """列出可用压力测试情景"""
    return {
        "historical": list(StressTester.HISTORICAL_SCENARIOS.keys()),
        "hypothetical": list(StressTester.HYPOTHETICAL_SCENARIOS.keys()),
    }


@router.post("/stress-test", response_model=StressTestResponse)
async def run_stress_test(
    scenario: str,
    user: User = Depends(get_current_user)
):
    """运行压力测试"""
    pass


@router.get("/var-attribution/{symbol}")
async def get_var_attribution(symbol: str):
    """VaR 归因分析"""
    pass
```

### 3.7 前端组件

```typescript
// apps/client/components/RiskDashboard.tsx

export function RiskDashboard({ symbol }: { symbol?: string }) {
  const { data: metrics } = useRiskMetrics(symbol);
  const { data: monteCarlo } = useMonteCarloSimulation(symbol);
  const { data: stressTests } = useStressTests();

  return (
    <div className="grid grid-cols-2 gap-6">
      {/* VaR 仪表盘 */}
      <Card title="📊 VaR 指标">
        <VaRGauge
          var95={metrics?.var_95_1d}
          var99={metrics?.var_99_1d}
          cvar={metrics?.cvar_95_1d}
        />
        <VaRBreakdown data={metrics} />
      </Card>

      {/* 蒙特卡洛模拟 */}
      <Card title="🎲 价格模拟 (30天)">
        <MonteCarloChart
          paths={monteCarlo?.paths_sample}
          percentiles={monteCarlo?.percentiles}
        />
        <ProbabilityTable
          probAbove={monteCarlo?.prob_above_current}
          probLoss10={monteCarlo?.prob_loss_10pct}
          probGain20={monteCarlo?.prob_gain_20pct}
        />
      </Card>

      {/* 压力测试 */}
      <Card title="🔥 压力测试" className="col-span-2">
        <StressTestScenarioSelector />
        <StressTestResults results={stressTests} />
      </Card>

      {/* 风险归因 */}
      <Card title="📈 风险归因">
        <BetaChart symbol={symbol} />
        <VolatilityHistory symbol={symbol} />
      </Card>
    </div>
  );
}
```

### 3.8 实现步骤

| 阶段 | 任务 | 工时 |
|------|------|------|
| **Phase 1** | 数据模型 + VaR 计算器 | 2天 |
| **Phase 2** | 蒙特卡洛引擎 (GBM) | 2天 |
| **Phase 3** | 跳跃扩散 + GARCH 模型 | 3天 |
| **Phase 4** | 压力测试器 | 2天 |
| **Phase 5** | RiskService 集成 | 2天 |
| **Phase 6** | API 路由开发 | 2天 |
| **Phase 7** | 前端可视化组件 | 4天 |
| **Phase 8** | 测试 + 文档 | 2天 |
| **总计** | | **19天** |

### 3.9 依赖项

```toml
# pyproject.toml 新增
arch = ">=6.0"  # GARCH 模型
```

---

## 4. ExecutionAgent 自动执行

### 4.1 功能概述

构建交易执行自动化系统，将 Agent 分析信号转化为实际交易指令。

**核心能力**：
- 🎯 信号转订单：根据分析结果自动生成交易指令
- 📊 策略执行：网格交易、定投、止盈止损
- 🔗 券商对接：模拟盘 API、实盘 API（需授权）
- 📈 执行监控：订单状态追踪、滑点分析

### 4.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        信号来源                                  │
├─────────────────────────────────────────────────────────────────┤
│  AnalysisResult    │  PriceAlert    │  ManualTrigger            │
│  (Agent 信号)       │  (价格触发)     │  (手动指令)               │
└─────────┬───────────────┬──────────────┬────────────────────────┘
          │               │              │
          ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ExecutionAgent                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ SignalProcessor │→ │ RiskChecker     │→ │ OrderGenerator  │ │
│  │ (信号解析)       │  │ (风控检查)       │  │ (订单生成)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ PaperTradeEngine│ │ GridTradeEngine │ │ DCAEngine       │
│ (模拟盘)         │ │ (网格交易)       │ │ (定投)          │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BrokerAdapter                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ MockBroker  │  │ IBKRAdapter │  │ FutuAdapter │             │
│  │ (模拟)       │  │ (盈透证券)   │  │ (富途)      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 数据模型

```python
# apps/server/db/models.py 新增

class TradingAccount(SQLModel, table=True):
    """交易账户"""
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    account_name: str
    broker_type: str  # mock | ibkr | futu | alpaca

    # 账户配置 (加密存储)
    credentials_encrypted: str | None  # API Key 等

    # 账户状态
    is_paper: bool = True  # 模拟盘 vs 实盘
    is_enabled: bool = True

    # 余额 (模拟盘)
    cash_balance: float = 100000.0

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Position(SQLModel, table=True):
    """持仓"""
    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id", index=True)

    symbol: str = Field(index=True)
    quantity: int
    avg_cost: float
    current_price: float | None

    # 盈亏
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None

    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Order(SQLModel, table=True):
    """订单"""
    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id", index=True)

    # 订单标识
    client_order_id: str = Field(unique=True)
    broker_order_id: str | None = None

    # 订单信息
    symbol: str = Field(index=True)
    side: str  # buy | sell
    order_type: str  # market | limit | stop | stop_limit
    quantity: int
    limit_price: float | None
    stop_price: float | None

    # 订单来源
    trigger_source: str  # agent_signal | grid_strategy | dca | manual
    trigger_id: str | None  # 关联的分析 ID 或策略 ID

    # 状态
    status: str  # pending | submitted | partial | filled | cancelled | rejected
    filled_quantity: int = 0
    avg_fill_price: float | None = None

    # 时间
    created_at: datetime = Field(default_factory=datetime.utcnow)
    submitted_at: datetime | None = None
    filled_at: datetime | None = None


class TradingStrategy(SQLModel, table=True):
    """交易策略配置"""
    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="tradingaccount.id", index=True)

    strategy_type: str  # agent_follow | grid | dca
    symbol: str

    # 策略参数
    config: dict  # 策略特定配置

    # 状态
    is_active: bool = True

    # 统计
    total_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class GridStrategy(SQLModel, table=True):
    """网格交易策略"""
    id: int | None = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key="tradingstrategy.id")

    # 网格参数
    price_upper: float
    price_lower: float
    grid_count: int
    quantity_per_grid: int

    # 当前状态
    active_grids: dict  # {price_level: order_id}

    # 统计
    completed_cycles: int = 0
    total_profit: float = 0.0


class DCAStrategy(SQLModel, table=True):
    """定投策略"""
    id: int | None = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key="tradingstrategy.id")

    # 定投参数
    amount_per_period: float
    frequency: str  # daily | weekly | biweekly | monthly

    # 触发条件 (可选)
    buy_on_dip: bool = False  # 下跌加仓
    dip_threshold: float = 0.05  # 5% 下跌触发

    # 状态
    next_execution: datetime | None
    total_invested: float = 0.0
    total_shares: int = 0
```

### 4.4 执行引擎

```python
# apps/server/services/execution_service.py

from abc import ABC, abstractmethod
from typing import Protocol
import uuid


class BrokerAdapter(Protocol):
    """券商适配器协议"""
    async def submit_order(self, order: Order) -> str: ...
    async def cancel_order(self, broker_order_id: str) -> bool: ...
    async def get_order_status(self, broker_order_id: str) -> dict: ...
    async def get_positions(self) -> list[dict]: ...
    async def get_account_info(self) -> dict: ...


class MockBrokerAdapter:
    """模拟券商 (Paper Trading)"""

    def __init__(self, account: TradingAccount, session: Session):
        self.account = account
        self.session = session

    async def submit_order(self, order: Order) -> str:
        """提交订单 (模拟成交)"""
        broker_order_id = f"MOCK_{uuid.uuid4().hex[:8]}"

        # 模拟即时成交
        if order.order_type == "market":
            # 获取当前价格
            price = await self._get_current_price(order.symbol)

            # 更新订单
            order.broker_order_id = broker_order_id
            order.status = "filled"
            order.filled_quantity = order.quantity
            order.avg_fill_price = price
            order.filled_at = datetime.utcnow()

            # 更新持仓
            await self._update_position(order, price)

            # 更新现金
            await self._update_cash(order, price)

        elif order.order_type == "limit":
            order.broker_order_id = broker_order_id
            order.status = "submitted"
            # 限价单需要价格匹配才成交

        self.session.commit()
        return broker_order_id

    async def _get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        # 调用 MarketRouter
        pass

    async def _update_position(self, order: Order, price: float):
        """更新持仓"""
        position = self.session.exec(
            select(Position)
            .where(Position.account_id == self.account.id)
            .where(Position.symbol == order.symbol)
        ).first()

        if order.side == "buy":
            if position:
                # 加仓
                total_cost = position.avg_cost * position.quantity + price * order.quantity
                total_qty = position.quantity + order.quantity
                position.avg_cost = total_cost / total_qty
                position.quantity = total_qty
            else:
                # 新建仓位
                position = Position(
                    account_id=self.account.id,
                    symbol=order.symbol,
                    quantity=order.quantity,
                    avg_cost=price,
                    current_price=price,
                )
                self.session.add(position)

        elif order.side == "sell":
            if position:
                position.quantity -= order.quantity
                if position.quantity <= 0:
                    self.session.delete(position)

    async def _update_cash(self, order: Order, price: float):
        """更新现金余额"""
        amount = price * order.quantity

        if order.side == "buy":
            self.account.cash_balance -= amount
        else:
            self.account.cash_balance += amount


class IBKRAdapter:
    """盈透证券适配器 (预留)"""

    def __init__(self, credentials: dict):
        self.credentials = credentials
        # TODO: 初始化 IB Gateway 连接

    async def submit_order(self, order: Order) -> str:
        raise NotImplementedError("IBKR integration not yet implemented")


class ExecutionService:
    """交易执行服务"""

    def __init__(self, session: Session, data_router: MarketRouter):
        self.session = session
        self.data_router = data_router

    def get_broker_adapter(self, account: TradingAccount) -> BrokerAdapter:
        """获取券商适配器"""
        adapters = {
            "mock": lambda: MockBrokerAdapter(account, self.session),
            "ibkr": lambda: IBKRAdapter(account.credentials_encrypted),
            # "futu": lambda: FutuAdapter(...),
        }
        return adapters[account.broker_type]()

    async def execute_signal(
        self,
        account_id: int,
        analysis: AnalysisResult,
        config: dict | None = None
    ) -> Order | None:
        """
        根据分析信号执行交易

        Args:
            account_id: 交易账户 ID
            analysis: Agent 分析结果
            config: 执行配置 {
                "position_size_pct": 0.1,  # 仓位比例
                "use_limit_order": False,
                "limit_offset_pct": 0.005,  # 限价偏移
            }
        """
        account = self.session.get(TradingAccount, account_id)
        if not account or not account.is_enabled:
            return None

        config = config or {}

        # 1. 信号解析
        signal_action = self._parse_signal(analysis.signal)
        if signal_action is None:
            return None  # HOLD 信号不交易

        # 2. 风控检查
        risk_check = await self._check_risk(account, analysis)
        if not risk_check["passed"]:
            logger.warning(f"Risk check failed: {risk_check['reason']}")
            return None

        # 3. 计算订单参数
        order_params = await self._calculate_order_params(
            account, analysis, signal_action, config
        )

        # 4. 创建订单
        order = Order(
            account_id=account_id,
            client_order_id=f"SIG_{analysis.id}_{uuid.uuid4().hex[:6]}",
            symbol=analysis.symbol,
            side=order_params["side"],
            order_type=order_params["order_type"],
            quantity=order_params["quantity"],
            limit_price=order_params.get("limit_price"),
            trigger_source="agent_signal",
            trigger_id=str(analysis.id),
            status="pending",
        )
        self.session.add(order)
        self.session.commit()

        # 5. 提交订单
        adapter = self.get_broker_adapter(account)
        try:
            broker_order_id = await adapter.submit_order(order)
            order.broker_order_id = broker_order_id
            order.submitted_at = datetime.utcnow()
            self.session.commit()
        except Exception as e:
            order.status = "rejected"
            logger.error(f"Order submission failed: {e}")

        return order

    def _parse_signal(self, signal: str) -> str | None:
        """解析信号为交易动作"""
        buy_signals = {"STRONG_BUY", "BUY"}
        sell_signals = {"STRONG_SELL", "SELL"}

        if signal in buy_signals:
            return "buy"
        elif signal in sell_signals:
            return "sell"
        return None  # HOLD

    async def _check_risk(
        self,
        account: TradingAccount,
        analysis: AnalysisResult
    ) -> dict:
        """风控检查"""
        checks = []

        # 1. 置信度检查
        if analysis.confidence < 60:
            checks.append("Confidence too low")

        # 2. 风险评分检查
        report = analysis.full_report_json or {}
        risk_score = report.get("riskAssessment", {}).get("score", 10)
        if risk_score > 7:
            checks.append("Risk score too high")

        # 3. 账户余额检查
        if account.cash_balance < 1000:
            checks.append("Insufficient cash")

        # 4. 持仓集中度检查
        # TODO: 检查单只股票持仓不超过总资产 20%

        return {
            "passed": len(checks) == 0,
            "reason": "; ".join(checks) if checks else None
        }

    async def _calculate_order_params(
        self,
        account: TradingAccount,
        analysis: AnalysisResult,
        action: str,
        config: dict
    ) -> dict:
        """计算订单参数"""
        # 获取当前价格
        price_data = await self.data_router.get_price(analysis.symbol)
        current_price = price_data["price"]

        # 计算数量
        position_size_pct = config.get("position_size_pct", 0.1)

        if action == "buy":
            amount = account.cash_balance * position_size_pct
            quantity = int(amount / current_price)
        else:
            # 卖出：获取当前持仓
            position = self.session.exec(
                select(Position)
                .where(Position.account_id == account.id)
                .where(Position.symbol == analysis.symbol)
            ).first()
            quantity = position.quantity if position else 0

        # 订单类型
        if config.get("use_limit_order"):
            order_type = "limit"
            offset = config.get("limit_offset_pct", 0.005)
            if action == "buy":
                limit_price = current_price * (1 - offset)
            else:
                limit_price = current_price * (1 + offset)
        else:
            order_type = "market"
            limit_price = None

        return {
            "side": action,
            "order_type": order_type,
            "quantity": quantity,
            "limit_price": limit_price,
        }


class GridTradeEngine:
    """网格交易引擎"""

    def __init__(
        self,
        strategy: GridStrategy,
        account: TradingAccount,
        session: Session
    ):
        self.strategy = strategy
        self.account = account
        self.session = session

    def calculate_grid_levels(self) -> list[float]:
        """计算网格价位"""
        price_range = self.strategy.price_upper - self.strategy.price_lower
        grid_size = price_range / self.strategy.grid_count

        levels = []
        for i in range(self.strategy.grid_count + 1):
            level = self.strategy.price_lower + i * grid_size
            levels.append(round(level, 2))

        return levels

    async def check_and_execute(self, current_price: float):
        """检查价格并执行网格交易"""
        levels = self.calculate_grid_levels()

        for i, level in enumerate(levels[:-1]):
            next_level = levels[i + 1]

            # 价格进入网格区间
            if level <= current_price < next_level:
                # 检查是否有该网格的挂单
                grid_key = f"{level}_{next_level}"

                if grid_key not in self.strategy.active_grids:
                    # 挂买单在下边界，卖单在上边界
                    await self._place_grid_orders(level, next_level)

    async def _place_grid_orders(self, buy_price: float, sell_price: float):
        """在网格边界挂单"""
        # 挂限价买单
        buy_order = Order(
            account_id=self.account.id,
            client_order_id=f"GRID_BUY_{uuid.uuid4().hex[:6]}",
            symbol=self.strategy.symbol,
            side="buy",
            order_type="limit",
            quantity=self.strategy.quantity_per_grid,
            limit_price=buy_price,
            trigger_source="grid_strategy",
            trigger_id=str(self.strategy.id),
            status="pending",
        )

        # 挂限价卖单
        sell_order = Order(
            account_id=self.account.id,
            client_order_id=f"GRID_SELL_{uuid.uuid4().hex[:6]}",
            symbol=self.strategy.symbol,
            side="sell",
            order_type="limit",
            quantity=self.strategy.quantity_per_grid,
            limit_price=sell_price,
            trigger_source="grid_strategy",
            trigger_id=str(self.strategy.id),
            status="pending",
        )

        self.session.add_all([buy_order, sell_order])
        self.session.commit()


class DCAEngine:
    """定投引擎"""

    def __init__(
        self,
        strategy: DCAStrategy,
        account: TradingAccount,
        session: Session
    ):
        self.strategy = strategy
        self.account = account
        self.session = session

    async def should_execute(self, current_price: float | None = None) -> bool:
        """判断是否应该执行定投"""
        now = datetime.utcnow()

        # 时间触发
        if self.strategy.next_execution and now >= self.strategy.next_execution:
            return True

        # 下跌加仓触发
        if self.strategy.buy_on_dip and current_price:
            # TODO: 获取最近高点，计算跌幅
            pass

        return False

    async def execute(self):
        """执行定投"""
        # 获取当前价格
        # 计算可买数量
        # 创建市价买单
        # 更新下次执行时间
        pass

    def _calculate_next_execution(self) -> datetime:
        """计算下次执行时间"""
        now = datetime.utcnow()

        if self.strategy.frequency == "daily":
            return now + timedelta(days=1)
        elif self.strategy.frequency == "weekly":
            return now + timedelta(weeks=1)
        elif self.strategy.frequency == "biweekly":
            return now + timedelta(weeks=2)
        elif self.strategy.frequency == "monthly":
            return now + timedelta(days=30)
```

### 4.5 API 设计

```python
# apps/server/api/routes/trading/execution.py

router = APIRouter(prefix="/execution", tags=["execution"])


# ===== 账户管理 =====

@router.get("/accounts", response_model=list[TradingAccountResponse])
async def list_accounts(user: User = Depends(get_current_user)):
    """获取交易账户列表"""
    pass


@router.post("/accounts", response_model=TradingAccountResponse)
async def create_account(
    data: TradingAccountCreate,
    user: User = Depends(get_current_user)
):
    """创建交易账户"""
    pass


@router.get("/accounts/{account_id}/positions")
async def get_positions(account_id: int):
    """获取持仓"""
    pass


@router.get("/accounts/{account_id}/orders")
async def get_orders(
    account_id: int,
    status: str | None = None,
    limit: int = 50
):
    """获取订单历史"""
    pass


# ===== 手动交易 =====

@router.post("/orders", response_model=OrderResponse)
async def place_order(
    data: OrderCreate,
    user: User = Depends(get_current_user)
):
    """手动下单"""
    pass


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: int):
    """取消订单"""
    pass


# ===== 信号执行 =====

@router.post("/execute-signal/{analysis_id}")
async def execute_signal(
    analysis_id: int,
    account_id: int,
    config: ExecutionConfig | None = None,
    user: User = Depends(get_current_user)
):
    """根据分析信号执行交易"""
    pass


# ===== 策略管理 =====

@router.get("/strategies", response_model=list[TradingStrategyResponse])
async def list_strategies(user: User = Depends(get_current_user)):
    """获取交易策略列表"""
    pass


@router.post("/strategies/grid", response_model=TradingStrategyResponse)
async def create_grid_strategy(
    data: GridStrategyCreate,
    user: User = Depends(get_current_user)
):
    """创建网格交易策略"""
    pass


@router.post("/strategies/dca", response_model=TradingStrategyResponse)
async def create_dca_strategy(
    data: DCAStrategyCreate,
    user: User = Depends(get_current_user)
):
    """创建定投策略"""
    pass


@router.put("/strategies/{strategy_id}/toggle")
async def toggle_strategy(strategy_id: int):
    """启用/停用策略"""
    pass


# ===== 执行统计 =====

@router.get("/statistics/{account_id}")
async def get_execution_statistics(account_id: int):
    """获取执行统计"""
    pass
```

### 4.6 前端组件

```typescript
// apps/client/pages/TradingPage.tsx

export function TradingPage() {
  const { data: accounts } = useTradingAccounts();
  const { data: positions } = usePositions(selectedAccountId);
  const { data: orders } = useOrders(selectedAccountId);
  const { data: strategies } = useTradingStrategies();

  return (
    <PageLayout title="交易执行">
      {/* 账户选择 */}
      <AccountSelector
        accounts={accounts}
        selected={selectedAccountId}
        onSelect={setSelectedAccountId}
      />

      {/* 账户概览 */}
      <div className="grid grid-cols-3 gap-4">
        <Card title="💰 账户余额">
          <AccountBalance account={selectedAccount} />
        </Card>
        <Card title="📊 持仓市值">
          <PositionValue positions={positions} />
        </Card>
        <Card title="📈 今日盈亏">
          <DailyPnL accountId={selectedAccountId} />
        </Card>
      </div>

      {/* 持仓列表 */}
      <Card title="📋 当前持仓">
        <PositionTable positions={positions} />
      </Card>

      {/* 订单管理 */}
      <Card title="📝 订单">
        <Tabs>
          <Tab label="活动订单">
            <ActiveOrdersTable orders={orders?.active} />
          </Tab>
          <Tab label="历史订单">
            <OrderHistoryTable orders={orders?.history} />
          </Tab>
        </Tabs>
      </Card>

      {/* 策略管理 */}
      <Card title="🤖 自动策略">
        <StrategyList strategies={strategies} />
        <AddStrategyButton />
      </Card>

      {/* 快捷交易面板 */}
      <QuickTradePanel accountId={selectedAccountId} />
    </PageLayout>
  );
}
```

### 4.7 安全考量

```yaml
# 安全设计原则

1. 模拟盘优先:
   - 默认创建模拟账户
   - 实盘需要额外授权流程
   - 实盘有每日交易限额

2. 风控强制:
   - 单笔订单金额上限
   - 单日交易次数上限
   - 持仓集中度限制 (单只股票 < 20%)
   - 亏损熔断 (单日亏损 > 5% 暂停)

3. 确认机制:
   - 大额订单需二次确认
   - 实盘订单需 2FA 验证
   - 策略启动需明确确认

4. 审计日志:
   - 所有交易操作记录
   - IP 地址追踪
   - 异常行为告警

5. 券商凭证:
   - API Key 加密存储
   - 支持只读权限测试
   - 定期凭证轮换
```

### 4.8 实现步骤

| 阶段 | 任务 | 工时 |
|------|------|------|
| **Phase 1** | 数据模型 + MockBroker | 3天 |
| **Phase 2** | ExecutionService 核心 | 3天 |
| **Phase 3** | 信号转订单逻辑 | 2天 |
| **Phase 4** | 网格交易引擎 | 3天 |
| **Phase 5** | 定投引擎 | 2天 |
| **Phase 6** | API 路由开发 | 2天 |
| **Phase 7** | 风控模块 | 2天 |
| **Phase 8** | 前端页面开发 | 4天 |
| **Phase 9** | IBKR/Futu 适配器 (可选) | 5天 |
| **Phase 10** | 测试 + 文档 | 3天 |
| **总计** | | **29天** |

### 4.9 依赖项

```toml
# pyproject.toml 新增
ib_insync = ">=0.9"  # 盈透证券 API (可选)
futu-api = ">=9.0"   # 富途 API (可选)
```

---

## 5. 总结与优先级建议

### 5.1 工时估算

| 功能 | 工时 | 复杂度 | 价值 |
|------|------|--------|------|
| 智能推送机器人 | 10天 | 低 | 高 |
| WhaleWatcher 筹码追踪 | 20天 | 中 | 高 |
| 蒙特卡洛/VaR 风险建模 | 19天 | 中 | 中 |
| ExecutionAgent 自动执行 | 29天 | 高 | 高 |
| **总计** | **78天** | | |

### 5.2 推荐实施顺序

```
Phase 1 (立即启动):
├── 智能推送机器人 (10天)
│   └── 快速见效，提升用户粘性
│
Phase 2 (第 2-4 周):
├── WhaleWatcher 筹码追踪 (20天)
│   └── 差异化竞争力，高价值数据
│
Phase 3 (第 5-7 周):
├── 蒙特卡洛/VaR 风险建模 (19天)
│   └── 机构级能力，与现有 RiskManager 集成
│
Phase 4 (第 8-12 周):
└── ExecutionAgent 自动执行 (29天)
    └── 最高复杂度，需要模拟盘充分测试
```

### 5.3 技术债务处理

建议在每个 Phase 开始前处理相关技术债务：
- Phase 1 前：修复 `north_money_service.py` 的 TODO
- Phase 2 前：完善测试 mock 机制
- Phase 3 前：添加 Alembic 数据库迁移

---

**文档版本**: 1.0
**作者**: Claude Code
**日期**: 2026-02-05
