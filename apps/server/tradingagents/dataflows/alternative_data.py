"""另类数据适配器

为分析 Agent 提供另类数据源接入（AH 溢价、专利等）。
作为 tradingagents 框架内的数据流模块，供 Agent 工具调用。
"""

import json
import structlog

logger = structlog.get_logger(__name__)


def get_ah_premium_data(symbol: str = "") -> str:
    """获取 AH 溢价数据

    Args:
        symbol: 可选，指定个股代码获取详情；为空则返回排行榜

    Returns:
        JSON 格式的 AH 溢价数据
    """
    try:
        from services.alternative_data_service import ah_premium_service

        if symbol:
            result = ah_premium_service.get_ah_premium_detail(symbol)
        else:
            result = ah_premium_service.get_ah_premium_list(limit=20)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("Failed to get AH premium data", symbol=symbol, error=str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def get_patent_data(symbol: str, company_name: str = "") -> str:
    """获取专利分析数据

    Args:
        symbol: 股票代码
        company_name: 公司名称（可选）

    Returns:
        JSON 格式的专利分析数据
    """
    try:
        from services.alternative_data_service import patent_service

        result = patent_service.get_patent_analysis(symbol, company_name)
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error("Failed to get patent data", symbol=symbol, error=str(e))
        return json.dumps({"error": str(e)}, ensure_ascii=False)
