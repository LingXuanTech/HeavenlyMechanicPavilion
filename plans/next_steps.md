# 下一步开发计划

> 更新日期: 2026-01-30
> 基于代码实际状态与 `implementation_plan.md` 对比分析

## 📊 当前状态总结

**好消息**：实施计划中的所有核心功能（P0-P5）均已**完整实现**，远超文档记录进度。

| 阶段 | 计划状态 | 实际状态 | 备注 |
|------|---------|---------|------|
| P0 Scout 联网能力 | ✅ DONE | ✅ 完整实现 | DuckDuckGo + 工具链 |
| P1 并行架构 + 可观测性 | ✅ DONE | ✅ 完整实现 | LangSmith + Token 监控 |
| P2 A股深度适配 | 未标记完成 | ✅ 完整实现 | Policy/Fund Flow Agent + LHB/北向/解禁 |
| P2 数据底座加固 | 部分完成 | ✅ 完整实现 | Redis 缓存 + 降级机制 |
| P3 回测 + 舆情 | 未开始 | ✅ 完整实现 | BacktestService + SentimentAgent |
| P4 智能进化 | 未开始 | ✅ 完整实现 | AccuracyTracker + PromptOptimizer + ModelRacing |
| P5 前端体验 | 未开始 | ✅ 完整实现 | TradingView + Streaming + TTS |
| 认证系统 | 未计划 | ✅ 完整实现 | JWT + OAuth + WebAuthn/Passkey |

---

## 🎯 优先级 1：生产化就绪 (Production Readiness)

### 1.1 测试覆盖率提升 🔴 Critical
**现状**：仅 3 个测试文件，实际测试用例不足

**任务**：
- [ ] **单元测试** - 核心服务层覆盖
  - `services/data_router.py` - 多市场路由逻辑
  - `services/synthesizer.py` - JSON 合成准确性
  - `services/ai_config_service.py` - 动态配置管理
  - `services/memory_service.py` - 向量记忆 CRUD

- [ ] **集成测试** - API 端点验证
  - `/api/analyze` - SSE 流完整性
  - `/api/watchlist` - CRUD 操作
  - A股特色数据 API（LHB/北向/解禁）

- [ ] **Agent 测试** - Mock LLM 响应
  - Analyst 节点并行执行
  - Bull/Bear 辩论流程
  - 结构化输出 Schema 验证

**目标**：覆盖率 > 70%

### 1.2 文档与计划同步更新 🟡 High
**现状**：`implementation_plan.md` 严重滞后于代码实现

**任务**：
- [ ] 更新 `plans/implementation_plan.md` - 标记所有已完成项
- [ ] 更新 `docs/ARCH.md` - 补充新增 Agent（Policy, Sentiment, Fund Flow）
- [ ] 更新 `docs/CONTRIB.md` - 补充新 API 端点文档

---

## 🎯 优先级 2：功能完善与优化

### 2.1 Agent 图执行优化 🟡 High
**现状**：已实现并行，但可进一步优化

**任务**：
- [ ] **动态状态管理**（计划 2.1 遗留项）
  - 将 `AgentState` 中固定报告字段改为动态字典
  - 支持按需加载/卸载 Analyst 报告

- [ ] **条件路由增强**
  - 根据 symbol 市场类型自动选择 Analyst 子集
  - A股 → 启用 Policy + Fund Flow Agent
  - 美股 → 启用 Sentiment + Macro Agent

- [ ] **执行超时与降级**
  - 单个 Agent 超时处理（默认 60s）
  - 失败节点跳过 + 警告日志

### 2.2 A股能力深化 🟢 Medium
**现状**：基础数据已接入，需深化分析

**任务**：
- [ ] **政策分析增强**
  - 政策事件与个股关联（行业板块映射）
  - 政策情绪量化（利好/利空/中性）

- [ ] **资金流向深度分析**
  - 北向资金与板块轮动关联
  - 龙虎榜游资追踪（席位画像）
  - 解禁压力预警自动化推送

### 2.3 宏观分析增强 🟢 Medium
**现状**：Macro Agent 已实现基础功能

**任务**：
- [ ] **央行 NLP 分析**（计划 6.4）
  - 美联储 FOMC 纪要语义微操分析
  - 央行声明情绪追踪

- [ ] **跨资产联动**
  - 黄金/原油/美债收益率前导指标
  - 自动检测宏观事件对持仓影响

---

## 🎯 优先级 3：用户体验与交互

### 3.1 人机协同增强 🟢 Medium
**现状**：基础对话功能已实现

**任务**：
- [ ] **论点修正**（计划 6.2）
  - 允许用户修正 Agent 某个论点
  - 触发 Graph 局部重新运行

- [ ] **交互式决策**
  - 多空辩论投票功能
  - 用户反馈影响决策权重

### 3.2 推送与通知 🟢 Medium
**任务**：
- [ ] **信号推送**
  - Telegram Bot 接入
  - 微信机器人（个人号/企业微信）

- [ ] **定时分析报告**
  - 每日持仓分析汇总
  - 重大事件预警

### 3.3 移动端适配 🟡 Low
**任务**：
- [ ] 响应式布局优化
- [ ] PWA 支持（离线访问 + 推送通知）

---

## 🎯 优先级 4：高级功能扩展

### 4.1 多模态分析 🔵 Future
**任务**：
- [ ] **财报图表 Vision 识别**
  - 使用 GPT-4V / Gemini Vision 解析 PDF 图表

- [ ] **电话会录音转录**
  - Whisper 集成
  - 关键词提取与情绪分析

### 4.2 执行自动化 🔵 Future
**任务**：
- [ ] **模拟盘对接**
  - 模拟交易 API
  - 策略胜率实时验证

- [ ] **网格交易 Agent**
  - 自动化执行网格策略

### 4.3 知识图谱 🔵 Future
**任务**：
- [ ] **产业链穿透**
  - 上下游供应链知识图谱
  - 风险传导预警

---

## 📋 近期执行建议 (Sprint 1: 2 周)

| 优先级 | 任务 | 负责人 | 预估工时 |
|-------|------|--------|---------|
| 🔴 P0 | 单元测试 - data_router | - | 4h |
| 🔴 P0 | 单元测试 - synthesizer | - | 4h |
| 🔴 P0 | 集成测试 - analyze API | - | 6h |
| 🔴 P0 | 更新 implementation_plan.md | - | 2h |
| 🟡 P1 | Agent 超时处理 | - | 4h |
| 🟡 P1 | 市场类型条件路由 | - | 6h |
| 🟢 P2 | 政策-行业板块映射 | - | 8h |

---

## 🔧 技术债务清单

| 问题 | 影响 | 修复建议 |
|------|------|---------|
| 测试覆盖率不足 | 生产风险高 | Sprint 1 重点 |
| 文档滞后 | 新成员上手困难 | 定期同步 |
| 硬编码配置 | 灵活性差 | 移至 Settings |
| 日志级别不一致 | 排查困难 | 统一 structlog 配置 |

---

## 📝 变更日志

### 2026-01-30: 初始评估
- 完成全量代码状态分析
- 确认 P0-P5 全部实现
- 制定下一阶段优先级
