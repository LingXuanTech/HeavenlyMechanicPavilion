"""另类数据服务

提供 AH 溢价套利信号和专利数据分析。
"""

import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)

# ============ 缓存 ============

_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL_SHORT = 300   # 5 分钟（AH 溢价实时数据）
_CACHE_TTL_LONG = 3600   # 1 小时（专利数据）


def _get_cache(key: str, ttl: int = _CACHE_TTL_SHORT) -> Optional[Any]:
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["timestamp"] < ttl:
            return entry["data"]
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data: Any) -> None:
    _cache[key] = {"data": data, "timestamp": time.time()}


def _cache_key(*args) -> str:
    raw = "|".join(str(a) for a in args)
    return hashlib.md5(raw.encode()).hexdigest()


# ============ AH 溢价服务 ============

class AHPremiumService:
    """AH 股溢价分析服务

    通过 AkShare 获取 AH 股溢价数据，计算溢价率、历史分位数和套利信号。
    """

    def get_ah_premium_list(self, sort_by: str = "premium_rate", limit: int = 50) -> Dict[str, Any]:
        """获取 AH 溢价排行榜

        Args:
            sort_by: 排序字段 (premium_rate / a_price / h_price)
            limit: 返回数量

        Returns:
            AH 溢价排行数据
        """
        cache_k = _cache_key("ah_premium_list", sort_by, limit)
        cached = _get_cache(cache_k)
        if cached:
            return cached

        try:
            import akshare as ak

            df = ak.stock_zh_ah_spot_em()
            if df is None or df.empty:
                return {"error": "No AH premium data available", "stocks": []}

            stocks = []
            for _, row in df.iterrows():
                try:
                    a_code = str(row.get("A股代码", ""))
                    h_code = str(row.get("H股代码", ""))
                    name = str(row.get("名称", ""))
                    a_price = float(row.get("A股价格", 0))
                    h_price = float(row.get("H股价格", 0))

                    # 计算溢价率
                    # AH 溢价率 = (A股价格 / H股价格 * 汇率 - 1) * 100
                    # AkShare 通常已经提供了溢价率
                    premium_rate = float(row.get("比价(A/H)", 0))
                    if premium_rate == 0 and h_price > 0:
                        # 简化计算（不含汇率）
                        premium_rate = round(a_price / h_price, 4)

                    stocks.append({
                        "a_code": a_code,
                        "h_code": h_code,
                        "name": name,
                        "a_price": a_price,
                        "h_price": h_price,
                        "premium_rate": premium_rate,
                        "premium_pct": round((premium_rate - 1) * 100, 2) if premium_rate > 0 else 0,
                    })
                except (ValueError, TypeError) as e:
                    logger.debug("Skipping invalid AH row", error=str(e))
                    continue

            # 排序
            if sort_by == "premium_rate":
                stocks.sort(key=lambda x: x["premium_pct"], reverse=True)
            elif sort_by == "a_price":
                stocks.sort(key=lambda x: x["a_price"], reverse=True)

            result = {
                "timestamp": datetime.now().isoformat(),
                "total": len(stocks),
                "stocks": stocks[:limit],
                "stats": self._calculate_stats(stocks),
            }

            _set_cache(cache_k, result)
            return result

        except ImportError:
            logger.error("AkShare not installed")
            return {"error": "AkShare not installed", "stocks": []}
        except Exception as e:
            logger.error("Failed to get AH premium list", error=str(e))
            return {"error": str(e), "stocks": []}

    def get_ah_premium_detail(self, symbol: str) -> Dict[str, Any]:
        """获取个股 AH 溢价详情

        Args:
            symbol: A 股代码（如 600036.SH 或 600036）

        Returns:
            个股 AH 溢价详情
        """
        cache_k = _cache_key("ah_premium_detail", symbol)
        cached = _get_cache(cache_k)
        if cached:
            return cached

        try:
            # 获取全量数据并筛选
            all_data = self.get_ah_premium_list(limit=500)
            stocks = all_data.get("stocks", [])

            # 清理 symbol
            clean_symbol = symbol.replace(".SH", "").replace(".SZ", "").replace(".SS", "")

            target = None
            for s in stocks:
                if clean_symbol in s.get("a_code", ""):
                    target = s
                    break

            if not target:
                return {"error": f"Symbol {symbol} not found in AH stocks", "found": False}

            # 获取历史溢价数据
            history = self._get_ah_history(clean_symbol)

            result = {
                "found": True,
                "current": target,
                "history": history,
                "signal": self._generate_arbitrage_signal(target, history),
                "timestamp": datetime.now().isoformat(),
            }

            _set_cache(cache_k, result)
            return result

        except Exception as e:
            logger.error("Failed to get AH premium detail", symbol=symbol, error=str(e))
            return {"error": str(e), "found": False}

    def _get_ah_history(self, a_code: str) -> List[Dict[str, Any]]:
        """获取 AH 溢价历史数据"""
        try:
            import akshare as ak

            df = ak.stock_zh_ah_daily(symbol=a_code, start_year="2024")
            if df is None or df.empty:
                return []

            history = []
            for _, row in df.tail(60).iterrows():  # 最近 60 个交易日
                try:
                    history.append({
                        "date": str(row.get("date", "")),
                        "ratio": float(row.get("比价", row.get("ratio", 0))),
                    })
                except (ValueError, TypeError):
                    continue

            return history

        except Exception as e:
            logger.debug("Failed to get AH history", a_code=a_code, error=str(e))
            return []

    def _calculate_stats(self, stocks: List[Dict]) -> Dict[str, Any]:
        """计算 AH 溢价统计数据"""
        if not stocks:
            return {}

        premiums = [s["premium_pct"] for s in stocks if s.get("premium_pct")]
        if not premiums:
            return {}

        return {
            "avg_premium_pct": round(sum(premiums) / len(premiums), 2),
            "max_premium_pct": round(max(premiums), 2),
            "min_premium_pct": round(min(premiums), 2),
            "median_premium_pct": round(sorted(premiums)[len(premiums) // 2], 2),
            "discount_count": sum(1 for p in premiums if p < 0),
            "premium_count": sum(1 for p in premiums if p > 0),
            "total_count": len(premiums),
        }

    def _generate_arbitrage_signal(
        self, current: Dict, history: List[Dict]
    ) -> Dict[str, Any]:
        """生成套利信号"""
        premium_pct = current.get("premium_pct", 0)

        # 基于历史分位数判断
        if history:
            historical_ratios = [h["ratio"] for h in history if h.get("ratio")]
            if historical_ratios:
                current_ratio = current.get("premium_rate", 1)
                sorted_ratios = sorted(historical_ratios)
                percentile = sum(1 for r in sorted_ratios if r <= current_ratio) / len(sorted_ratios) * 100

                if percentile >= 90:
                    signal = "STRONG_SELL_A"
                    description = f"A股溢价处于历史 {percentile:.0f}% 分位，极度偏高"
                elif percentile >= 75:
                    signal = "SELL_A"
                    description = f"A股溢价处于历史 {percentile:.0f}% 分位，偏高"
                elif percentile <= 10:
                    signal = "STRONG_BUY_A"
                    description = f"A股溢价处于历史 {percentile:.0f}% 分位，极度偏低"
                elif percentile <= 25:
                    signal = "BUY_A"
                    description = f"A股溢价处于历史 {percentile:.0f}% 分位，偏低"
                else:
                    signal = "NEUTRAL"
                    description = f"A股溢价处于历史 {percentile:.0f}% 分位，正常范围"

                return {
                    "signal": signal,
                    "description": description,
                    "percentile": round(percentile, 1),
                    "current_premium_pct": premium_pct,
                    "historical_avg": round(sum(historical_ratios) / len(historical_ratios), 4),
                }

        # 无历史数据时的简单判断
        if premium_pct > 100:
            return {"signal": "STRONG_SELL_A", "description": "A股溢价超过100%，极度偏高"}
        elif premium_pct > 50:
            return {"signal": "SELL_A", "description": "A股溢价超过50%，偏高"}
        elif premium_pct < -20:
            return {"signal": "STRONG_BUY_A", "description": "A股折价超过20%，极度偏低"}
        elif premium_pct < 0:
            return {"signal": "BUY_A", "description": "A股折价，可能存在套利机会"}
        else:
            return {"signal": "NEUTRAL", "description": "溢价在正常范围"}


# ============ 专利监控服务 ============

class PatentService:
    """专利监控服务

    通过 DuckDuckGo 搜索和 LLM 分析公司专利趋势。
    """

    def get_patent_analysis(self, symbol: str, company_name: str = "") -> Dict[str, Any]:
        """获取公司专利分析

        Args:
            symbol: 股票代码
            company_name: 公司名称（可选，用于搜索）

        Returns:
            专利分析结果
        """
        cache_k = _cache_key("patent_analysis", symbol)
        cached = _get_cache(cache_k, ttl=_CACHE_TTL_LONG)
        if cached:
            return cached

        try:
            # 如果没有提供公司名，尝试获取
            if not company_name:
                company_name = self._get_company_name(symbol)

            search_name = company_name or symbol

            # 搜索专利信息
            patent_news = self._search_patents(search_name)
            tech_trends = self._search_tech_trends(search_name)

            result = {
                "symbol": symbol,
                "company_name": search_name,
                "timestamp": datetime.now().isoformat(),
                "patent_news": patent_news,
                "tech_trends": tech_trends,
                "analysis_hint": (
                    f"Based on the patent and technology data above for {search_name}, analyze: "
                    "1) Patent filing trends (increasing/decreasing), "
                    "2) Key technology areas and R&D focus, "
                    "3) Competitive positioning in patent landscape, "
                    "4) Potential impact on future revenue"
                ),
            }

            _set_cache(cache_k, result)
            return result

        except Exception as e:
            logger.error("Patent analysis failed", symbol=symbol, error=str(e))
            return {
                "symbol": symbol,
                "error": str(e),
                "patent_news": [],
                "tech_trends": [],
            }

    def _get_company_name(self, symbol: str) -> str:
        """获取公司名称"""
        try:
            from services.data_router import MarketRouter
            router = MarketRouter()
            price_data = router.get_price(symbol)
            return price_data.get("name", "") if price_data else ""
        except Exception:
            return ""

    def _search_patents(self, company_name: str) -> List[Dict[str, Any]]:
        """搜索公司专利信息"""
        try:
            from duckduckgo_search import DDGS
            ddgs = DDGS()

            # 多语言搜索
            queries = [
                f"{company_name} patent filing 2024 2025",
                f"{company_name} 专利 申请 技术",
            ]

            all_results = []
            for q in queries:
                try:
                    results = list(ddgs.text(q, max_results=5, timelimit="y"))
                    all_results.extend(results)
                except Exception:
                    continue

            formatted = []
            seen = set()
            for r in all_results:
                url = r.get("href", "")
                if url in seen:
                    continue
                seen.add(url)
                formatted.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "url": url,
                })

            return formatted[:8]

        except ImportError:
            logger.warning("duckduckgo-search not installed")
            return []
        except Exception as e:
            logger.warning("Patent search failed", error=str(e))
            return []

    def _search_tech_trends(self, company_name: str) -> List[Dict[str, Any]]:
        """搜索公司技术趋势"""
        try:
            from duckduckgo_search import DDGS
            ddgs = DDGS()

            query = f"{company_name} R&D technology innovation research"
            results = list(ddgs.text(query, max_results=5, timelimit="y"))

            return [
                {
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "url": r.get("href", ""),
                }
                for r in results
            ]

        except Exception as e:
            logger.warning("Tech trends search failed", error=str(e))
            return []


# ============ 单例实例 ============

ah_premium_service = AHPremiumService()
patent_service = PatentService()
