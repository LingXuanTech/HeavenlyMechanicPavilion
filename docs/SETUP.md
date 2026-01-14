# TradingAgents 安装与配置指南

本文档将引导您完成 **TradingAgents** 的本地开发环境搭建。

---

## 1. 环境要求 (Prerequisites)

在开始之前，请确保您的系统已安装以下软件：
- **Python**: 3.10 或更高版本
- **Node.js**: 18.0 或更高版本 (建议使用 v20)
- **PNPM**: 建议使用最新版本 (`npm install -g pnpm`)
- **Docker & Docker Compose**: 用于运行数据库和 Redis

---

## 2. 后端配置 (Backend Setup)

### A. 安装依赖
进入后端目录并安装 Python 依赖：
```bash
cd packages/backend
# 建议使用虚拟环境
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### B. 环境变量
复制示例环境文件并填写您的 API Key：
```bash
cp .env.example .env
```
**必须填写的变量：**
- `OPENAI_API_KEY`: 您的 OpenAI 密钥。
- `ALPHA_VANTAGE_API_KEY`: 用于获取行情和基本面数据。
- `DATABASE_URL`: 例如 `postgresql+asyncpg://user:pass@localhost:5432/tradingagents`。

### C. 数据库初始化
运行 Alembic 迁移以创建表结构：
```bash
alembic upgrade head
```

---

## 3. 前端配置 (Frontend Setup)

进入前端目录并安装依赖：
```bash
cd packages/frontend
pnpm install
```

配置前端环境变量：
```bash
cp .env.example .env.local
# 确保 NEXT_PUBLIC_API_URL 指向后端地址 (默认 http://localhost:8000)
```

---

## 4. 运行服务 (Running the Services)

### 启动基础设施 (Docker)
在根目录下运行：
```bash
docker compose up -d postgres redis
```

### 启动后端 API
```bash
cd packages/backend
uvicorn app.main:app --reload
```

### 启动前端控制中心
```bash
cd packages/frontend
pnpm dev
```

---

## 5. 验证安装
访问 `http://localhost:3000`，您应该能看到 TradingAgents 的控制中心界面。如果后端连接正常，您可以在“会话管理”中尝试启动一个新的股票分析任务。

---
*本文档由 Architect 模式自动生成，最后更新日期：2026-01-14*