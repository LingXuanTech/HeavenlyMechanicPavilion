
# TradingAgents 项目改进路线图

## 📊 当前状态评估

### ✅ 已完成的优势

1. **核心架构稳固**
   - ✅ 多智能体 LangGraph 编排系统运行良好
   - ✅ 插件化架构支持热重载
   - ✅ 完整的 FastAPI REST API
   - ✅ Next.js 前端控制中心
   - ✅ Docker 容器化部署

2. **功能完整性**
   - ✅ 12+ 专业智能体角色
   - ✅ 5 个 LLM 提供商集成
   - ✅ 8+ 数据供应商支持
   - ✅ 实时 SSE/WebSocket 流
   - ✅ 回测系统基础

3. **代码质量**
   - ✅ 类型安全（Python + TypeScript）
   - ✅ 仓储模式数据访问
   - ✅ 测试框架完整
   - ✅ 文档齐全（15+ 页面）

### ⚠️ 已知问题和限制

#### 高优先级问题

1. **事件历史不持久化** 🔴
   - **问题**: 事件仅存储在内存 deque 中
   - **影响**: 服务重启后历史丢失
   - **风险**: 高 - 数据丢失

2. **MarketDataService 缓存不一致** 🟡
   - **问题**: 使用实例级 dict 而非 Redis
   - **影响**: 无法跨实例共享缓存
   - **风险**: 中 - 性能和扩展性

3. **循环导入问题** 🟡
   - **问题**: Trade 和 Execution 模型循环依赖
   - **影响**: 测试失败，代码异味
   - **风险**: 中 - 技术债务

4. **缺少实时券商集成** 🔴
   - **问题**: 仅有模拟券商
   - **影响**: 无法进行实盘交易
   - **风险**: 高 - 关键功能缺失

#### 中优先级问题

5. **事件历史无分页** 🟡
   - **问题**: 大型会话可能有数千个事件
   - **影响**: 性能问题，内存占用
   - **风险**: 中 - 可扩展性

6. **WebSocket 实现不完善** 🟡
   - **问题**: SSE 为主，WebSocket 次要
   - **影响**: 双向通信受限
   - **风险**: 低 - 功能限制

7. **智能体性能分析缺失** 🟡
   - **问题**: 无法追踪哪些智能体表现最好
   - **影响**: 难以优化智能体配置
   - **风险**: 中 - 缺少洞察

#### 低优先级问题

8. **API 文档不完整** 🟢
   - **问题**: OpenAPI 描述不够详细
   - **影响**: 集成难度增加
   - **风险**: 低 - 开发者体验

9. **测试覆盖率不足** 🟢
   - **当前**: ~60%
   - **目标**: >80%
   - **风险**: 低 - 质量保证

---

## 🎯 改进路线图

### 第一阶段: 架构修复 (2-3 周)

#### 任务 1.1: 事件历史持久化 ⭐⭐⭐
**优先级**: P0 (最高)
**工作量**: 2-3 天
**负责人**: 后端开发

**实施步骤**:
```sql
-- 1. 创建数据库表
CREATE TABLE session_events (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES analysis_sessions(id),
    event_type VARCHAR(50) NOT NULL,
    message TEXT,
    payload JSONB,
    timestamp TIMESTAMP NOT NULL,
    sequence_number INTEGER NOT NULL,
    INDEX idx_session_events_session (session_id),
    INDEX idx_session_events_timestamp (timestamp),
    INDEX idx_session_events_sequence (session_id, sequence_number)
);
```

```python
# 2. 更新 SessionEventManager
class SessionEventManager:
    def __init__(
        self,
        event_repo: SessionEventRepository,
        buffer_size: int = 100,
        persist_events: bool = True
    ):
        self._buffer = deque(maxlen=buffer_size)
        self._event_repo = event_repo
        self._persist = persist_events
    
    async def publish(
        self,
        session_id: str,
        event_type: str,
        message: str,
        payload: Dict = None
    ):
        event = SessionEvent(...)
        
        # 内存缓冲（快速访问）
        self._buffer.append(event)
        
        # 异步持久化（不阻塞）
        if self._persist:
            asyncio.create_task(
                self._event_repo.create(event)
            )
```

```python
# 3. API 端点添加分页
@router.get("/sessions/{id}/events-history")
async def get_events_history(
    id: str,
    skip: int = 0,
    limit: int = 50,
    order: str = "asc"
):
    events = await event_repo.get_paginated(
        session_id=id,
        skip=skip,
        limit=limit,
        order_by=order
    )
    total = await event_repo.count(session_id=id)
    
    return {
        "events": events,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total
    }
```

**验收标准**:
- ✅ 事件在服务重启后仍然存在
- ✅ 支持分页查询（skip/limit）
- ✅ 性能影响 < 10%
- ✅ 所有测试通过

---

#### 任务 1.2: MarketDataService Redis 集成 ⭐⭐
**优先级**: P1
**工作量**: 1-2 天
**负责人**: 后端开发

**实施步骤**:
```python
# 1. 重构 MarketDataService
class MarketDataService:
    def __init__(
        self,
        vendor_router: VendorRouter,
        cache_service: CacheService,  # 注入 Redis
        cache_ttl: int = 300
    ):
        self._router = vendor_router
        self._cache = cache_service
        self._ttl = cache_ttl
    
    async def get_market_price(
        self,
        symbol: str,
        use_cache: bool = True
    ) -> MarketPrice:
        # 1. 尝试 Redis 缓存
        if use_cache:
            cached = await self._cache.get_market_data(symbol)
            if cached:
                return MarketPrice.from_cache(cached)
        
        # 2. 从供应商获取
        data = await self._router.route_to_vendor(
            "get_stock_data",
            symbol=symbol
        )
        
        # 3. 写入 Redis
        await self._cache.set_market_data(
            symbol,
            data,
            ttl=self._ttl
        )
        
        return MarketPrice.from_vendor(data)
```

**验收标准**:
- ✅ MarketDataService 使用 Redis
- ✅ 跨实例缓存共享工作
- ✅ 缓存 TTL 可配置
- ✅ 性能无回归

---

#### 任务 1.3: 修复循环导入 ⭐
**优先级**: P1
**工作量**: 1 天
**负责人**: 后端开发

**解决方案**:
```python
# 选项 A: 使用 TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.execution import Execution

class Trade(SQLModel, table=True):
    # 使用字符串引用
    executions: List["Execution"] = Relationship(
        back_populates="trade",
        sa_relationship_kwargs={"lazy": "select"}
    )

# 选项 B: 延迟导入
class Trade(SQLModel, table=True):
    def get_executions(self) -> List["Execution"]:
        from app.db.models.execution import Execution
        return self.executions
```

**验收标准**:
- ✅ 没有循环导入错误
- ✅ 所有测试通过
- ✅ 关系加载正常

---

### 第二阶段: 核心功能增强 (3-4 周)

#### 任务 2.1: Alpaca 券商集成 ⭐⭐⭐
**优先级**: P0 (实盘交易必需)
**工作量**: 3-5 天
**负责人**: 后端开发 + QA

**实施步骤**:
```python
# 1. 实现 AlpacaBroker
class AlpacaBroker(BrokerAdapter):
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str,  # paper vs live
        paper_trading: bool = True
    ):
        self.api = alpaca.TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper_trading
        )
    
    async def place_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None
    ) -> Order:
        # 实现订单提交逻辑
        request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=side.value,
            type=order_type.value,
            time_in_force=TimeInForce.DAY
        )
        
        alpaca_order = self.api.submit_order(request)
        return Order.from_alpaca(alpaca_order)
    
    async def get_positions(self) -> List[Position]:
        positions = self.api.get_all_positions()
        return [Position.from_alpaca(p) for p in positions]
    
    async def cancel_order(self, order_id: str) -> bool:
        try:
            self.api.cancel_order_by_id(order_id)
            return True
        except APIError as e:
            logger.error(f"Cancel failed: {e}")
            return False
```

```yaml
# 2. 配置
# .env
BROKER_TYPE=alpaca  # or simulated
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # paper trading
ALPACA_PAPER_TRADING=true
```

```python
# 3. 工厂模式
class BrokerFactory:
    @staticmethod
    def create(broker_type: str) -> BrokerAdapter:
        if broker_type == "simulated":
            return SimulatedBroker()
        elif broker_type == "alpaca":
            return AlpacaBroker(
                api_key=settings.ALPACA_API_KEY,
                secret_key=settings.ALPACA_SECRET_KEY,
                paper_trading=settings.ALPACA_PAPER_TRADING
            )
        else:
            raise ValueError(f"Unknown broker: {broker_type}")
```

**测试计划**:
1. 单元测试（模拟 Alpaca API）
2. 集成测试（纸面账户）
3. 手动测试清单：
   - ✅ 下单成功
   - ✅ 订单状态同步
   - ✅ 持仓查询准确
   - ✅ 取消订单工作
   - ✅ 错误处理正确

**风险控制**:
- 🛡️ 默认纸面交易模式
- 🛡️ 实盘需要明确配置
- 🛡️ 订单金额限制
- 🛡️ 断路器模式

**验收标准**:
- ✅ Alpaca 订单执行工作
- ✅ 持仓同步准确
- ✅ 纸面测试通过
- ✅ 文档完整

---

#### 任务 2.2: 智能体性能分析系统 ⭐⭐
**优先级**: P1
**工作量**: 4-5 天
**负责人**: 后端开发 + 前端开发

**数据模型**:
```python
class AgentPerformance(SQLModel, table=True):
    __tablename__ = "agent_performance"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agent_id: str = Field(index=True)
    session_id: UUID = Field(foreign_key="analysis_sessions.id")
    
    # 性能指标
    confidence_score: float  # 智能体置信度
    decision_accuracy: Optional[float]  # 决策准确性
    execution_time_ms: int  # 执行时间
    contribution_weight: float  # 对最终决策的贡献权重
    
    # 结果跟踪
    decision_outcome: Optional[str]  # "correct", "incorrect", "pending"
    pnl_impact: Optional[Decimal]  # 对盈亏的影响
    
    # 元数据
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict, sa_column=Column(JSON))
```

**分析服务**:
```python
class AgentAnalyticsService:
    async def get_agent_leaderboard(
        self,
        time_range: str = "30d",
        metric: str = "accuracy",
        limit: int = 10
    ) -> List[AgentRanking]:
        """获取智能体排行榜"""
        
    async def get_agent_trend(
        self,
        agent_id: str,
        metric: str,
        time_range: str = "30d"
    ) -> TimeSeries:
        """获取智能体性能趋势"""
        
    async def compare_agents(
        self,
        agent_ids: List[str],
        metrics: List[str],
        time_range: str = "30d"
    ) -> 