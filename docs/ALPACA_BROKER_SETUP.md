# Alpaca 券商集成指南

本指南介绍如何在 TradingAgents 项目中配置和使用 Alpaca 券商进行自动交易。

## 目录

- [前置要求](#前置要求)
- [获取 Alpaca API Key](#获取-alpaca-api-key)
- [配置环境变量](#配置环境变量)
- [使用说明](#使用说明)
- [Paper Trading vs Live Trading](#paper-trading-vs-live-trading)
- [常见问题](#常见问题)

## 前置要求

1. 注册 Alpaca 账户
2. 安装项目依赖（包含 `alpaca-py>=0.7.0`）
3. 完成项目基础配置

## 获取 Alpaca API Key

### 1. 注册账户

访问 [Alpaca Markets](https://alpaca.markets/) 并注册账户：

- 免费账户即可使用 Paper Trading（模拟交易）
- Live Trading 需要完成身份验证和资金入金

### 2. 生成 API Key

1. 登录 Alpaca 控制台
2. 进入 **Settings** → **API Keys**
3. 点击 **Generate New Key**
4. 选择 API Key 类型：
   - **Paper Trading**: 用于模拟交易测试
   - **Live Trading**: 用于实盘交易（需要完成账户验证）
5. 保存生成的 API Key 和 Secret（只显示一次）

## 配置环境变量

在项目根目录的 `.env` 文件中添加以下配置：

### Paper Trading 配置（推荐用于测试）

```bash
# 券商类型
BROKER_TYPE=alpaca

# Alpaca API 凭证
ALPACA_API_KEY=your_paper_trading_api_key
ALPACA_API_SECRET=your_paper_trading_api_secret

# Alpaca 基础 URL（Paper Trading）
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Live Trading 配置

```bash
# 券商类型
BROKER_TYPE=alpaca

# Alpaca API 凭证（使用 Live Trading Key）
ALPACA_API_KEY=your_live_trading_api_key
ALPACA_API_SECRET=your_live_trading_api_secret

# Alpaca 基础 URL（Live Trading）
# 注意：Live Trading 会自动设置为 https://api.alpaca.markets
ALPACA_BASE_URL=https://api.alpaca.markets
```

### 使用模拟器（默认）

如果不配置 Alpaca 凭证，系统会自动使用内置模拟器：

```bash
# 使用内置模拟器
BROKER_TYPE=simulated
```

## 使用说明

### 启动自动交易

使用 Alpaca Paper Trading：

```python
import httpx

# 启动自动交易
response = httpx.post(
    "http://localhost:8000/api/auto-trading/start",
    json={
        "portfolio_id": "my_portfolio",
        "symbols": ["AAPL", "GOOGL", "MSFT"],
        "interval_seconds": 3600,  # 每小时执行一次
        "session_type": "PAPER"  # Paper Trading
    }
)
```

使用 Alpaca Live Trading：

```python
response = httpx.post(
    "http://localhost:8000/api/auto-trading/start",
    json={
        "portfolio_id": "my_portfolio",
        "symbols": ["AAPL", "GOOGL", "MSFT"],
        "interval_seconds": 3600,
        "session_type": "LIVE"  # Live Trading
    }
)
```

### 手动执行单次交易

```python
response = httpx.post(
    "http://localhost:8000/api/auto-trading/run-once",
    json={
        "portfolio_id": "my_portfolio",
        "symbols": ["AAPL"],
        "session_type": "PAPER"
    }
)
```

### 停止自动交易

```python
response = httpx.post(
    "http://localhost:8000/api/auto-trading/stop",
    json={
        "portfolio_id": "my_portfolio"
    }
)
```

### 查询交易状态

```python
response = httpx.get(
    "http://localhost:8000/api/auto-trading/status/my_portfolio"
)
```

## Paper Trading vs Live Trading

### Paper Trading（模拟交易）

**优点**：
- 免费使用，无需资金
- 完全模拟真实市场环境
- 适合策略测试和开发
- 无风险

**特点**：
- 使用虚拟资金
- 订单执行在模拟环境
- 可以测试所有功能
- 数据延迟与实盘一致

**使用场景**：
- 开发和测试阶段
- 策略验证
- 学习和练习

### Live Trading（实盘交易）

**注意事项**：
- 使用真实资金
- 需要完成账户验证
- 订单会在真实市场执行
- 存在实际盈亏风险

**要求**：
- Alpaca 账户验证完成
- 账户有足够资金
- 理解交易风险
- 遵守交易规则

**使用场景**：
- 策略已充分测试
- 准备进行实盘交易
- 有风险承受能力

## 常见问题

### 1. API Key 无效

**问题**：提示 API Key 或 Secret 无效

**解决方案**：
- 检查 `.env` 文件中的凭证是否正确
- 确认使用的是对应环境的 Key（Paper 或 Live）
- 重新生成 API Key

### 2. 连接超时

**问题**：无法连接到 Alpaca API

**解决方案**：
- 检查网络连接
- 确认 `ALPACA_BASE_URL` 配置正确
- Paper Trading: `https://paper-api.alpaca.markets`
- Live Trading: `https://api.alpaca.markets`

### 3. 订单被拒绝

**问题**：订单提交失败

**可能原因**：
- 账户购买力不足
- 股票代码无效
- 市场未开市
- 订单参数无效

**解决方案**：
- 检查账户余额
- 验证股票代码
- 确认交易时间
- 查看详细错误信息

### 4. 市场数据延迟

**问题**：价格数据不是实时的

**说明**：
- Alpaca 免费账户提供 15 分钟延迟数据
- 升级账户可获取实时数据
- Paper Trading 使用与实盘相同的数据源

### 5. 环境变量不生效

**问题**：配置后仍使用模拟器

**解决方案**：
1. 检查 `.env` 文件位置（应在项目根目录）
2. 重启应用服务
3. 确认环境变量加载正确：
   ```python
   from app.config.settings import get_settings
   settings = get_settings()
   print(f"Broker Type: {settings.broker_type}")
   print(f"API Key: {settings.alpaca_api_key[:8]}...")
   ```

## 安全建议

1. **保护 API 凭证**
   - 不要提交 `.env` 文件到版本控制
   - 使用环境变量管理敏感信息
   - 定期轮换 API Key

2. **测试先行**
   - 始终先在 Paper Trading 测试
   - 确认策略稳定后再上线实盘
   - 使用小额资金开始实盘交易

3. **风险控制**
   - 设置止损和止盈
   - 控制单笔交易规模
   - 监控账户状态

4. **日志审计**
   - 记录所有交易操作
   - 定期检查交易日志
   - 分析异常情况

## 参考资源

- [Alpaca API 文档](https://alpaca.markets/docs/)
- [alpaca-py SDK 文档](https://alpaca.markets/docs/python-sdk/)
- [TradingAgents 项目文档](./README.md)
- [自动交易改进方案](../AUTO_TRADING_IMPROVEMENT_PLAN.md)

## 支持

如有问题，请参考：
1. 本文档的常见问题部分
2. Alpaca 官方支持
3. 项目 Issue Tracker