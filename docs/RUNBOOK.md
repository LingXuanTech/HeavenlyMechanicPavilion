# Runbook - 运维手册

> 最后更新: 2026-02-11
> 适用范围：HeavenlyMechanicPavilion（apps/client + apps/server）

## 1. 快速启动

### 1.1 本地开发（推荐）

```bash
# 安装依赖
moon run :install

# 启动后端
moon run server:dev

# 启动前端
moon run client:dev
```

- 前端默认地址：`http://localhost:3000`
- 后端健康检查：`http://localhost:8000/health`
- OpenAPI：`http://localhost:8000/api/openapi.json`

### 1.2 Docker Compose

```bash
cp .env.example .env
# 按需填写 API key / 数据库配置

docker compose up -d
```

容器名称：
- `stock-agents-backend`
- `stock-agents-frontend`
- `stock-agents-postgres`（可选 profile）
- `stock-agents-redis`（可选 profile）

## 2. 环境变量最小集

### 2.1 必填（至少一项 LLM）

- `OPENAI_API_KEY` 或 `GOOGLE_API_KEY` 或 `ANTHROPIC_API_KEY`

### 2.2 常用运行配置

- `ENV=development|production`
- `DATABASE_MODE=sqlite|postgresql`
- `DATABASE_URL=sqlite:///./db/trading.db`（sqlite 模式）
- `REDIS_URL=redis://localhost:6379`（启用缓存/队列）
- `USE_TASK_QUEUE=true|false`（队列模式开关）
- `API_KEY_ENABLED=true|false`
- `API_KEY=...`（开启 admin key 时必填）
- `CORS_ORIGINS=http://localhost:3000,...`

## 3. 任务执行模式

## 3.1 后台任务模式（默认）

- 条件：`USE_TASK_QUEUE=false` 或未配置 `REDIS_URL`
- 执行方式：FastAPI `BackgroundTasks`
- 适用：本地开发、轻量环境

## 3.2 队列模式（生产建议）

- 条件：`USE_TASK_QUEUE=true` 且配置 `REDIS_URL`
- 执行方式：Redis Stream + Worker

启动示例：

```bash
# API
moon run server:dev

# Worker（可多实例）
cd apps/server
uv run python -m workers.analysis_worker --name worker-1
uv run python -m workers.analysis_worker --name worker-2
```

## 4. 健康检查与监控

常用端点：

- `GET /health`：基础探针
- `GET /api/health/`：快速健康
- `GET /api/health/report`：完整报告
- `GET /api/health/components`：组件状态
- `GET /api/health/metrics`：系统资源
- `GET /api/health/api-metrics`：API 指标
- `GET /api/health/liveness`：K8s liveness
- `GET /api/health/readiness`：K8s readiness

建议阈值：

- CPU > 70%（告警） / > 90%（严重）
- 内存 > 80%（告警） / > 95%（严重）
- API 错误率 > 1%（告警） / > 5%（严重）
- 平均延迟 > 500ms（告警） / > 2000ms（严重）

## 5. 常见运维操作

### 5.1 查看日志

```bash
# 后端日志
docker logs stock-agents-backend -f

# 前端日志
docker logs stock-agents-frontend -f
```

### 5.2 查看队列状态（Redis）

```bash
redis-cli
XLEN analysis:tasks
XINFO GROUPS analysis:tasks
XPENDING analysis:tasks analysis_workers
XLEN analysis:dlq
```

### 5.3 任务状态查询

```bash
curl http://localhost:8000/api/analyze/status/{task_id}
```

## 6. 故障排查流程

1. 检查基础探针：`/health`、`/api/health/readiness`
2. 检查外部依赖：数据库、Redis、LLM API 可用性
3. 检查任务模式：确认 `USE_TASK_QUEUE` 与 `REDIS_URL` 是否一致
4. 检查 worker 消费：是否有积压、是否持续 ACK
5. 检查最近发布变更：是否涉及路由、schema、环境变量

## 7. 回滚建议

1. 回滚应用镜像到上一个稳定 tag
2. 保持数据库 schema 向后兼容（Alembic 回滚需先评估）
3. 回滚前导出关键数据（分析结果、用户、配置）
4. 回滚后执行 smoke test：
   - 登录/鉴权
   - 分析任务创建
   - SSE 流接收
   - 健康检查端点

## 8. 发布前检查清单

- [ ] `moon run :lint` 通过
- [ ] `moon run :typecheck` 通过
- [ ] `moon run :test` 通过
- [ ] 前后端 OpenAPI 类型同步校验通过
- [ ] 关键环境变量已注入
- [ ] 健康检查与报警策略已配置
