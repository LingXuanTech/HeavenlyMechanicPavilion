# Runbook - 运维手册

> Stock Agents Monitor 部署和运维指南
> 最后更新: 2026-01-28

## 目录

1. [部署流程](#部署流程)
2. [监控和告警](#监控和告警)
3. [常见问题排查](#常见问题排查)
4. [回滚流程](#回滚流程)
5. [维护操作](#维护操作)

---

## 部署流程

### Docker Compose 部署

```bash
# 1. 克隆仓库
git clone <repo-url>
cd my-trading

# 2. 配置环境变量
cp apps/server/.env.example apps/server/.env
# 编辑 .env 文件配置必要的 API 密钥

# 3. 启动服务
docker compose up -d

# 4. 验证服务状态
curl http://localhost:8000/health
curl http://localhost:3000
```

### 生产环境检查清单

- [ ] `API_KEY_ENABLED=true` 并配置安全的 `API_KEY`
- [ ] 至少配置一个 LLM API 密钥 (OPENAI/GOOGLE/ANTHROPIC)
- [ ] 配置 `CORS_ORIGINS` 为实际域名
- [ ] 数据库使用 PostgreSQL (`DATABASE_MODE=postgresql`)
- [ ] 配置 Redis 用于缓存 (`REDIS_URL`)
- [ ] 检查日志输出 (`docker logs stock-agents-server`)

### Kubernetes 部署

```yaml
# 健康检查探针配置
livenessProbe:
  httpGet:
    path: /api/health/liveness
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /api/health/readiness
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

---

## 监控和告警

### 健康检查端点

| 端点 | 用途 | 响应码 |
|------|------|--------|
| `GET /health` | 基础健康检查 | 200 |
| `GET /api/health/` | 快速健康探针 | 200/503 |
| `GET /api/health/report` | 详细健康报告 | 200 |
| `GET /api/health/components` | 组件状态 | 200 |
| `GET /api/health/metrics` | 系统指标 (CPU/内存/磁盘) | 200 |
| `GET /api/health/api-metrics` | API 性能指标 | 200 |
| `GET /api/health/liveness` | K8s 存活探针 | 200 |
| `GET /api/health/readiness` | K8s 就绪探针 | 200/503 |

### 关键指标监控

**系统指标** (`/api/health/metrics`):
```json
{
  "cpu_percent": 25.5,
  "memory_percent": 45.2,
  "memory_used_mb": 1024,
  "disk_percent": 60.0
}
```

**API 性能指标** (`/api/health/api-metrics`):
```json
{
  "global": {
    "total_requests": 10000,
    "total_errors": 10,
    "avg_duration_ms": 120.5,
    "error_rate_pct": 0.1
  },
  "window": {
    "window_minutes": 60,
    "requests_per_minute": 15.5
  },
  "by_path": {
    "GET /api/analyze/latest/{symbol}": {
      "requests": 500,
      "avg_duration_ms": 50.2,
      "error_rate_pct": 0.0
    }
  }
}
```

### 告警阈值建议

| 指标 | 警告 | 严重 |
|------|------|------|
| CPU 使用率 | > 70% | > 90% |
| 内存使用率 | > 80% | > 95% |
| 磁盘使用率 | > 80% | > 95% |
| API 错误率 | > 1% | > 5% |
| 平均响应时间 | > 500ms | > 2000ms |
| 健康状态 | degraded | unhealthy |

### 日志格式

所有日志使用 JSON 格式输出，包含请求追踪 ID：

```json
{
  "timestamp": "2026-01-28T10:30:45.123456+00:00",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "level": "info",
  "event": "Request completed",
  "method": "GET",
  "path": "/api/analyze/latest/AAPL",
  "status_code": 200,
  "duration_ms": 45.2
}
```

**日志查询示例 (使用 jq)**:
```bash
# 查看错误日志
docker logs stock-agents-server | jq 'select(.level == "error")'

# 按请求 ID 追踪
docker logs stock-agents-server | jq 'select(.request_id == "550e8400...")'

# 查看慢请求 (> 1秒)
docker logs stock-agents-server | jq 'select(.duration_ms > 1000)'
```

---

## 常见问题排查

### 1. 服务无法启动

**症状**: `docker logs` 显示启动失败

**排查步骤**:
```bash
# 检查环境变量
docker exec stock-agents-server env | grep -E "(API_KEY|DATABASE)"

# 检查数据库连接
docker exec stock-agents-server python -c "from db.models import engine; print(engine.url)"

# 检查 LLM API 密钥
docker exec stock-agents-server python -c "from config.settings import settings; print(bool(settings.OPENAI_API_KEY or settings.GOOGLE_API_KEY))"
```

**常见原因**:
- 缺少必要的 API 密钥
- 数据库连接失败
- 端口被占用

### 2. Agent 分析超时

**症状**: 分析任务卡在某个阶段

**排查步骤**:
```bash
# 检查任务状态
curl http://localhost:8000/api/analyze/status/{task_id}

# 检查调度器状态
curl http://localhost:8000/api/admin/scheduler/status

# 查看分析日志
docker logs stock-agents-server | grep -E "(task_id|analysis)"
```

**常见原因**:
- LLM API 限流
- 数据源 API 超时
- 内存不足

### 3. 数据源返回空数据

**症状**: 股票价格或新闻数据为空

**排查步骤**:
```bash
# 检查数据源状态
curl http://localhost:8000/api/health/components | jq '.[] | select(.name == "market_watcher")'

# 测试 yfinance
docker exec stock-agents-server python -c "import yfinance as yf; print(yf.Ticker('AAPL').info)"

# 测试 AkShare (A股)
docker exec stock-agents-server python -c "import akshare as ak; print(ak.stock_zh_a_spot_em().head())"
```

**常见原因**:
- API 密钥过期
- 网络问题
- 非交易时间

### 4. 缓存问题

**症状**: 数据不更新或返回过期数据

**排查步骤**:
```bash
# 检查 Redis 连接 (如果使用)
docker exec stock-agents-server python -c "from services.cache_service import cache_service; print(cache_service._backend.__class__.__name__)"

# 清除任务缓存
curl -X DELETE http://localhost:8000/api/health/api-metrics
```

### 5. 前端无法连接后端

**症状**: CORS 错误或连接被拒绝

**排查步骤**:
```bash
# 检查 CORS 配置
docker exec stock-agents-server python -c "from config.settings import settings; print(settings.CORS_ORIGINS)"

# 检查网络连通性
curl -I http://localhost:8000/api/health
```

**常见原因**:
- CORS_ORIGINS 未配置前端域名
- 端口映射错误
- 防火墙限制

### 6. AI 配置问题

**症状**: AI 分析失败，提示 "No LLM configured" 或模型调用错误

**排查步骤**:
```bash
# 检查 AI 配置状态
curl http://localhost:8000/api/ai/status

# 列出所有提供商
curl http://localhost:8000/api/ai/providers

# 检查模型配置
curl http://localhost:8000/api/ai/models

# 测试特定提供商连接
curl -X POST http://localhost:8000/api/ai/providers/{provider_id}/test

# 检查加密密钥文件
docker exec stock-agents-server ls -la ./db/.encryption_key

# 强制刷新配置缓存
curl -X POST http://localhost:8000/api/ai/refresh
```

**常见原因**:
- 未配置任何 AI 提供商
- API 密钥无效或过期
- 模型名称错误
- 提供商被禁用
- 加密密钥文件丢失（需要重新配置 API 密钥）

**解决方案**:
1. 通过 UI (侧边栏 → AI Config) 或 API 添加提供商
2. 使用 "Test" 功能验证连接
3. 确保为 deep_think/quick_think/synthesis 分配了模型
4. 检查提供商是否启用 (`is_enabled: true`)

### 7. AI 密钥加密问题

**症状**: 服务重启后 AI 配置失效

**排查步骤**:
```bash
# 检查加密密钥是否存在
docker exec stock-agents-server cat ./db/.encryption_key 2>/dev/null && echo "Key exists" || echo "Key missing"

# 检查环境变量
docker exec stock-agents-server printenv | grep AI_CONFIG_ENCRYPTION_KEY
```

**解决方案**:
- 确保 `./db/.encryption_key` 文件在部署中持久化
- 或在环境变量中设置 `AI_CONFIG_ENCRYPTION_KEY`
- 如密钥丢失，需重新配置所有 AI 提供商的 API 密钥

---

## 回滚流程

### Docker Compose 回滚

```bash
# 1. 停止当前服务
docker compose down

# 2. 切换到上一个版本
git checkout <previous-tag>

# 3. 重新构建并启动
docker compose build
docker compose up -d

# 4. 验证服务
curl http://localhost:8000/health
```

### 数据库回滚

**SQLite**:
```bash
# 备份当前数据库
cp db/trading.db db/trading.db.bak.$(date +%Y%m%d)

# 恢复备份
cp db/trading.db.bak.<date> db/trading.db
```

**PostgreSQL**:
```bash
# 恢复备份
pg_restore -d trading backup.dump
```

### 紧急回滚检查清单

1. [ ] 确认回滚版本号
2. [ ] 通知相关人员
3. [ ] 执行回滚操作
4. [ ] 验证服务健康状态
5. [ ] 检查日志是否有异常
6. [ ] 更新事件记录

---

## 维护操作

### 数据库维护

```bash
# 清理旧的分析记录 (保留最近 30 天)
docker exec stock-agents-server python -c "
from db.models import Session, engine, AnalysisResult
from datetime import datetime, timedelta
with Session(engine) as s:
    cutoff = datetime.now() - timedelta(days=30)
    deleted = s.query(AnalysisResult).filter(AnalysisResult.created_at < cutoff).delete()
    s.commit()
    print(f'Deleted {deleted} old records')
"
```

### 缓存清理

```bash
# 清理 API 指标
curl -X DELETE http://localhost:8000/api/health/api-metrics

# 清理健康检查错误历史
curl -X DELETE http://localhost:8000/api/health/errors
```

### 日志轮转

Docker 默认日志配置:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

### 定期维护任务

| 任务 | 频率 | 命令/操作 |
|------|------|-----------|
| 健康检查 | 每分钟 | `GET /api/health/` |
| 性能指标收集 | 每 5 分钟 | `GET /api/health/api-metrics` |
| AI 配置状态检查 | 每小时 | `GET /api/ai/status` |
| 日志备份 | 每日 | 备份 Docker 日志 |
| 数据库备份 | 每日 | pg_dump / SQLite 备份 |
| 清理旧数据 | 每周 | 删除 30 天前的分析记录 |
| 依赖安全扫描 | 每周 | `pip-audit` / `npm audit` |
| AI 提供商连接测试 | 每周 | `POST /api/ai/providers/{id}/test` |

### AI 配置备份

```bash
# 备份 AI 配置相关数据
# 1. 导出提供商配置 (不含 API 密钥)
curl http://localhost:8000/api/ai/providers > ai_providers_backup.json

# 2. 导出模型配置
curl http://localhost:8000/api/ai/models > ai_models_backup.json

# 3. 备份加密密钥 (重要!)
docker cp stock-agents-server:/app/db/.encryption_key ./encryption_key.backup

# 恢复时需要同时恢复加密密钥和数据库
```

---

## 联系信息

- **技术支持**: 参见 GitHub Issues
- **文档**: `/docs` 目录
- **API 文档**: `http://localhost:8000/api/openapi.json`
