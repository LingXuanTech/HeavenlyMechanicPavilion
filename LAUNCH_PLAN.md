# TradingAgents 上线发布计划 (Launch Plan)

本文档为 **TradingAgents** 项目从开发环境迁移到生产环境提供详细的执行步骤。

---

## 1. 上线前准备清单 (Pre-launch Checklist)

### 🔑 凭据与 API 密钥
- [ ] 获取 **OpenAI API Key** (生产环境建议使用独立账号)。
- [ ] 获取 **Alpha Vantage API Key** (建议使用 Premium 密钥以获得更高频率)。
- [ ] 生成强密码：
    - `POSTGRES_PASSWORD`
    - `REDIS_PASSWORD`
- [ ] (可选) 获取 **Finnhub** 或 **Reddit** API 凭据以增强数据源。

### 🌐 域名与网络
- [ ] 准备生产环境域名 (例如 `trading.yourdomain.com`)。
- [ ] 获取 SSL 证书 (建议使用 Let's Encrypt)。
- [ ] 确认服务器 80 和 443 端口已开放。

---

## 2. 环境配置步骤

### A. 环境变量配置
1. 复制 `.env.docker` 到生产服务器并重命名为 `.env`。
2. 更新以下关键变量：
   ```bash
   DEBUG=false
   NEXT_PUBLIC_API_URL=https://your-api-domain.com
   POSTGRES_PASSWORD=你的强密码
   REDIS_PASSWORD=你的强密码
   OPENAI_API_KEY=你的密钥
   ```

### B. 数据库迁移配置
修改 `packages/backend/alembic.ini`，确保生产环境下指向 PostgreSQL：
```ini
# 生产环境应通过环境变量注入，或在此修改模板
sqlalchemy.url = postgresql+asyncpg://tradingagents:${POSTGRES_PASSWORD}@postgres:5432/tradingagents
```

---

## 3. 部署执行流程

### 第一步：构建镜像
在项目根目录下执行：
```bash
docker compose build
```

### 第二步：启动基础服务
先启动数据库和 Redis，确保它们就绪：
```bash
docker compose up -d postgres redis
```

### 第三步：执行数据库迁移
在后端容器中运行 Alembic 迁移脚本：
```bash
docker compose run --rm backend alembic upgrade head
```

### 第四步：启动全量服务
使用生产配置文件启动所有组件：
```bash
# 启动后端、Worker、前端和 Nginx
PROFILE=frontend,workers,nginx docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 4. 验证与监控

### 🔍 健康检查
- 访问 `https://your-domain.com/health` 确认后端状态。
- 访问 `https://your-domain.com/api/monitoring/health` 查看综合健康报告。

### 📊 监控指标
- 检查 Prometheus 指标端点：`/api/monitoring/metrics`。
- 观察 `docker compose logs -f backend` 确认无启动报错。

---

## 5. 安全加固建议
1. **防火墙**: 仅允许 Nginx 容器暴露 80/443 端口，数据库和 Redis 端口不应直接对外开放。
2. **SSL**: 修改 `nginx/nginx.conf`，取消 HTTPS Server 块的注释，并配置证书路径。
3. **速率限制**: 根据生产流量调整 Nginx 中的 `limit_req_zone` 参数。

---
*本文档由 Architect 模式自动生成，最后更新日期：2026-01-14*