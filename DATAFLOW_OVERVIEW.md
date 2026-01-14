# TradingAgents 数据流集成概览

本文档详细说明了 **TradingAgents** 如何集成和路由来自不同供应商的金融数据。

---

## 1. 核心设计理念：统一接口与动态路由
项目通过 `packages/backend/src/tradingagents/dataflows/interface.py` 提供了一个统一的抽象层。智能体不需要关心数据来自哪个供应商，只需调用统一的方法（如 `get_stock_data`），系统会根据配置自动路由到具体的实现。

### 路由优先级
1. **工具级配置 (Tool-level)**: 在配置中明确指定某个方法使用的供应商。
2. **类别级配置 (Category-level)**: 按数据类别（如 `news_data`, `fundamental_data`）指定供应商。
3. **默认供应商**: 如果未指定，系统会按预设的优先级尝试可用供应商。

---

## 2. 数据分类与工具集

| 类别 | 核心方法 | 支持的供应商 |
| --- | --- | --- |
| **核心股票数据** | `get_stock_data` | Alpha Vantage, YFinance, Local (CSV) |
| **技术指标** | `get_indicators` | Alpha Vantage, YFinance (via Stockstats) |
| **基本面数据** | `get_fundamentals`, `get_balance_sheet`, `get_cashflow`, `get_income_statement` | Alpha Vantage, YFinance, SimFin (Local), OpenAI (LLM 提取) |
| **新闻与情绪** | `get_news`, `get_global_news`, `get_insider_sentiment`, `get_insider_transactions` | Alpha Vantage, Google News, Reddit, Finnhub, OpenAI |

---

## 3. 供应商集成细节

### YFinance (Yahoo Finance)
- **实现**: `y_finance.py`
- **特点**: 
    - 使用 `yfinance` 库获取实时和历史数据。
    - 集成了 `stockstats` 库，支持计算 RSI, MACD, Bollinger Bands 等多种技术指标。
    - 支持获取资产负债表、现金流量表和内部人交易数据。

### Alpha Vantage
- **实现**: `alpha_vantage_*.py` 系列模块。
- **特点**: 
    - 官方 API 支持，数据质量高。
    - 拥有完善的频率限制（Rate Limit）处理逻辑，支持自动切换到备用供应商。

### Local (本地数据)
- **实现**: `local.py`
- **特点**: 
    - 支持从本地 CSV 文件读取历史数据，适用于回测和离线开发。
    - 模拟了 Finnhub 和 SimFin 的接口。

### OpenAI / LLM 提取
- **实现**: `openai.py`
- **特点**: 
    - 利用 LLM 对非结构化新闻进行摘要和情绪提取。
    - 可以从文本中“推理”出基本面指标。

---

## 4. 容错与回退机制 (Fallback)
`route_to_vendor` 函数实现了强大的回退逻辑：
- 如果主供应商（如 Alpha Vantage）触发频率限制或请求失败，系统会自动尝试列表中的下一个供应商（如 YFinance）。
- 支持多供应商数据聚合：如果配置了多个供应商（逗号分隔），系统可以收集并合并来自多个源的数据。

---

## 5. 缓存机制
- **文件缓存**: 许多 Dataflow 实现（如 YFinance）会将下载的数据以 CSV 形式缓存在 `data_cache/` 目录中，以减少重复请求并提高性能。
- **Redis 缓存**: 后端服务层进一步集成了 Redis，用于缓存 API 响应。

---
*本文档由 Architect 模式自动梳理生成，最后更新日期：2026-01-14*