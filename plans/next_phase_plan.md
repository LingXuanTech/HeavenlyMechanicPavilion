# Stock Agents Monitor - 下一阶段开发完善计划

> 基于代码审查的全面改进路线图（2026-01）

## 执行摘要

| 维度 | 当前状态 | 目标状态 | 优先级 |
|------|---------|---------|--------|
| 测试覆盖 | ~0% | 80%+ | P0 |
| 安全加固 | 开发模式 | 生产就绪 | P0 |
| 类型安全 | 部分 | 严格 | P1 |
| 性能优化 | 基础 | 优化 | P1 |
| 功能完整 | 80% | 100% | P2 |
| 可观测性 | 基础 | 完善 | P2 |

---

## Phase 1: 安全加固 & 基础质量（1 周）

### 1.1 安全问题修复 [P0]

#### CORS 限制
```python
# apps/server/config/settings.py
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # 生产环境添加实际域名
]
```

**任务清单**：
- [ ] 修改 `settings.py` 移除 `["*"]` 默认值
- [ ] 添加环境变量 `CORS_ORIGINS` 支持（逗号分隔）
- [ ] 在 docker-compose.yml 中配置生产环境 origins

#### API Key 安全
- [ ] 移除 `settings.py:11` 的默认密钥 `"dev-key-12345"`
- [ ] 生产环境强制要求 `API_KEY_ENABLED=true`
- [ ] 添加启动检查：未配置 API_KEY 时拒绝启动（生产模式）

#### 数据库凭据
- [ ] 移除 docker-compose.yml 中的默认密码
- [ ] 添加 `.env.production.example` 模板（无默认值）
- [ ] 在 README 中说明生产部署安全要求

### 1.2 错误处理规范化 [P0]

**目标**：消除所有裸 `except:` 块，实现统一错误处理

#### 后端错误处理
- [ ] 创建 `apps/server/api/exceptions.py`：
  ```python
  class AppException(Exception):
      def __init__(self, code: str, message: str, status_code: int = 400):
          self.code = code
          self.message = message
          self.status_code = status_code

  class DataSourceError(AppException): ...
  class AnalysisError(AppException): ...
  class AuthenticationError(AppException): ...
  ```
- [ ] 添加全局异常处理器到 `main.py`
- [ ] 修复 `watchlist.py:36` 的裸 except
- [ ] 修复 `memory_service.py:208` 的裸 except
- [ ] 审查并修复其他 79 处 `except Exception` 块

#### 前端错误处理
- [ ] 创建 `apps/client/components/ErrorBoundary.tsx`
- [ ] 在 `index.tsx` 中包裹 `<App />` 组件
- [ ] 为 `useStockAnalysis` 添加 SSE 失败重试机制
- [ ] 统一 API 错误展示（Toast 或 Alert 组件）

---

## Phase 2: 测试体系建设（2 周）

### 2.1 后端测试 [P0]

#### 基础设施
- [ ] 创建 `apps/server/tests/conftest.py`（pytest fixtures）
- [ ] 配置 `pyproject.toml` 中的 pytest 设置
- [ ] 创建测试数据库（SQLite in-memory）
- [ ] 添加 mock 工厂（LLM、数据源）

#### 单元测试（目标覆盖 80%）
```
tests/
├── conftest.py
├── unit/
│   ├── test_data_router.py      # MarketRouter 路由逻辑
│   ├── test_synthesizer.py      # JSON 合成逻辑
│   ├── test_prompt_manager.py   # Prompt 加载和变量注入
│   ├── test_memory_service.py   # ChromaDB 操作
│   └── test_models.py           # SQLModel 验证
├── integration/
│   ├── test_analyze_api.py      # /api/analyze 端点
│   ├── test_watchlist_api.py    # /api/watchlist 端点
│   ├── test_market_api.py       # /api/market 端点
│   └── test_sse_stream.py       # SSE 流测试
└── fixtures/
    ├── mock_llm_responses.py
    └── sample_market_data.py
```

**优先级任务**：
- [ ] `test_data_router.py`：测试市场识别 + 数据源降级
- [ ] `test_analyze_api.py`：测试分析流程 + SSE 事件
- [ ] `test_watchlist_api.py`：测试 CRUD 操作

### 2.2 前端测试 [P1]

#### 基础设施
- [ ] 安装 Vitest + Testing Library
- [ ] 配置 `vite.config.ts` 中的测试设置
- [ ] 创建 mock API 工具

#### 组件测试
```
__tests__/
├── components/
│   ├── StockCard.test.tsx
│   ├── StockDetailModal.test.tsx
│   └── Sidebar.test.tsx
├── hooks/
│   ├── useWatchlist.test.ts
│   ├── useAnalysis.test.ts
│   └── usePrices.test.ts
└── services/
    └── api.test.ts
```

---

## Phase 3: 类型安全强化（1 周）

### 3.1 TypeScript 严格模式 [P1]

- [ ] 在 `tsconfig.json` 中启用：
  ```json
  {
    "compilerOptions": {
      "strict": true,
      "noImplicitAny": true,
      "strictNullChecks": true
    }
  }
  ```
- [ ] 修复所有 `any` 类型（10 处）：
  - `services/geminiService.ts:214`
  - `hooks/usePrices.ts:36,61`
  - `services/api.ts:81,94,260,319,342`
  - `components/PromptEditor.tsx:82`

### 3.2 API 类型对齐 [P1]

- [ ] 为所有 API 响应创建 TypeScript 接口
- [ ] 使用 Zod 进行运行时类型验证
- [ ] 生成 OpenAPI 到 TypeScript 类型（可选：使用 openapi-typescript）

### 3.3 Python 类型完善 [P2]

- [ ] 为所有公共函数添加返回类型注解
- [ ] 使用 `mypy` 进行静态类型检查
- [ ] 配置 `pyproject.toml` 中的 mypy 设置

---

## Phase 4: 性能优化（1-2 周）

### 4.1 异步 IO 改造 [P1]

**问题**：同步 `requests` 库阻塞事件循环

**解决方案**：
- [ ] 安装 `httpx`：`pip install httpx`
- [ ] 重构 `data_router.py`：
  ```python
  import httpx

  async with httpx.AsyncClient() as client:
      response = await client.get(url, timeout=10)
  ```
- [ ] 重构以下文件：
  - `tradingagents/dataflows/googlenews_utils.py`
  - `tradingagents/dataflows/alpha_vantage_common.py`
  - `tradingagents/dataflows/reddit_utils.py`

### 4.2 缓存层增强 [P1]

#### Redis 集成
- [ ] 添加 Redis 客户端配置到 `settings.py`
- [ ] 创建 `services/cache_service.py`：
  ```python
  class CacheService:
      async def get(self, key: str) -> Optional[str]: ...
      async def set(self, key: str, value: str, ttl: int): ...
      async def delete(self, key: str): ...
  ```
- [ ] 迁移任务状态到 Redis（替代内存 `tasks = {}`）
- [ ] 实现价格数据缓存（TTL 5 分钟）

#### 前端缓存优化
- [ ] 调整 TanStack Query 的 `staleTime` 策略
- [ ] 为大型列表实现虚拟滚动

### 4.3 数据库优化 [P2]

- [ ] 为 `AnalysisResult` 添加复合索引：`(symbol, created_at)`
- [ ] 实现分页查询（`/api/analyze/history`）
- [ ] 添加数据库连接池监控

---

## Phase 5: 功能完善（2-3 周）

### 5.1 Portfolio Agent 完整实现 [P2]

**PRD 要求**：分析 Watchlist 股票间的相关性，建议仓位配置

- [ ] 完善 `tradingagents/agents/analysts/portfolio_agent.py`
- [ ] 实现相关性矩阵计算（Pearson Correlation）
- [ ] 添加风险集中度检测
- [ ] 创建 `/api/portfolio/optimize` 端点
- [ ] 前端添加相关性热力图组件

### 5.2 Scout Agent 增强 [P2]

**当前状态**：基础实现，缺乏完整市场扫描

- [ ] 集成 Google Search API 进行市场扫描
- [ ] 添加行业筛选能力
- [ ] 实现趋势识别算法
- [ ] 前端 Scout 结果展示优化

### 5.3 TTS 语音播报集成 [P2]

**当前状态**：后端生成 `anchor_script`，前端未集成播放

- [ ] 前端添加 Web Speech API 集成
- [ ] 创建 `components/AudioBriefing.tsx`
- [ ] 在 `StockDetailModal` 中添加播放按钮
- [ ] 可选：集成 Gemini TTS API

### 5.4 调度器管理 UI [P3]

- [ ] 创建 `/api/admin/scheduler` 端点：
  - `GET /jobs`：获取所有定时任务
  - `POST /jobs/{job_id}/trigger`：手动触发
  - `DELETE /jobs/{job_id}`：删除任务
- [ ] 前端添加 `components/SchedulerPanel.tsx`
- [ ] 实现任务状态可视化

---

## Phase 6: 可观测性增强（1 周）

### 6.1 结构化日志 [P2]

- [ ] 统一日志格式（已使用 structlog）
- [ ] 添加请求追踪 ID（`X-Request-ID`）
- [ ] 配置日志轮转和归档
- [ ] 可选：集成 ELK Stack 或 Loki

### 6.2 监控指标 [P2]

- [ ] 集成 Prometheus metrics：
  - API 请求延迟
  - Agent 执行时间
  - 数据源成功率
  - 缓存命中率
- [ ] 创建 Grafana 仪表板模板

### 6.3 健康检查增强 [P2]

- [ ] 完善 `/health/report` 端点
- [ ] 添加 LLM API 可用性检测
- [ ] 添加数据源连通性检测
- [ ] 配置 Kubernetes 就绪探针（如适用）

---

## Phase 7: 部署优化（1 周）

### 7.1 Docker 优化 [P2]

- [ ] 验证 `apps/client/nginx.conf` 存在且正确
- [ ] 优化后端 Dockerfile（减小镜像大小）
- [ ] 添加健康检查到 Dockerfile
- [ ] 配置多架构构建（ARM64 支持）

### 7.2 CI/CD 流水线 [P2]

- [ ] 创建 `.github/workflows/ci.yml`：
  - Lint（ESLint + Ruff）
  - 类型检查（TypeScript + mypy）
  - 单元测试
  - 构建验证
- [ ] 创建 `.github/workflows/cd.yml`：
  - Docker 镜像构建
  - 推送到 Container Registry

### 7.3 依赖安全 [P2]

- [ ] 为 `requirements.txt` 添加版本约束
- [ ] 配置 `pip-audit` 定期扫描
- [ ] 前端使用 `npm audit` + Dependabot

---

## 里程碑时间线

```
Week 1:  Phase 1 - 安全加固 & 基础质量
Week 2-3: Phase 2 - 测试体系建设
Week 4:  Phase 3 - 类型安全强化
Week 5-6: Phase 4 - 性能优化
Week 7-9: Phase 5 - 功能完善
Week 10: Phase 6 - 可观测性增强
Week 11: Phase 7 - 部署优化
```

---

## 附录：快速参考

### 关键文件路径

| 组件 | 路径 |
|------|------|
| 后端入口 | `apps/server/main.py` |
| 配置管理 | `apps/server/config/settings.py` |
| 数据路由 | `apps/server/services/data_router.py` |
| Agent 图 | `apps/server/tradingagents/graph/trading_graph.py` |
| 前端入口 | `apps/client/index.tsx` |
| 类型定义 | `apps/client/types.ts` |
| API 服务 | `apps/client/services/api.ts` |

### 命令速查

```bash
# 后端开发
cd apps/server && python main.py
pytest tests/ -v --cov=.

# 前端开发
cd apps/client && npm run dev
npm run test

# Docker
docker compose up
docker compose --profile postgresql up

# 代码质量
ruff check apps/server/
npm run lint
```
