import structlog
from openai import OpenAI
from .config import get_config

logger = structlog.get_logger(__name__)


def _get_openai_client():
    """获取 OpenAI 客户端（统一通过 ai_config_service）

    Returns:
        (OpenAI client, model_name) 元组，或 (None, None) 当无可用 OpenAI 提供商时
    """
    # 优先从 ai_config_service 获取配置
    try:
        from services.ai_config_service import ai_config_service
        client_config = ai_config_service.get_openai_client_config()
        if client_config:
            client = OpenAI(base_url=client_config["base_url"], api_key=client_config["api_key"])
            config = get_config()
            model = config.get("quick_think_llm", "gpt-4o-mini")
            return client, model
    except Exception as e:
        logger.debug("ai_config_service unavailable for OpenAI client", error=str(e))

    # 降级：使用 config 中的 backend_url（CLI 模式）
    config = get_config()
    backend_url = config.get("backend_url")
    if backend_url:
        try:
            client = OpenAI(base_url=backend_url)
            return client, config.get("quick_think_llm", "gpt-4o-mini")
        except Exception as e:
            logger.debug("Failed to create OpenAI client from config", error=str(e))

    return None, None


def get_stock_news_openai(query, start_date, end_date):
    client, model = _get_openai_client()
    if client is None:
        logger.warning("OpenAI client unavailable, skipping stock news fetch via Responses API")
        return ""

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Social Media for {query} from {start_date} to {end_date}? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text


def get_global_news_openai(curr_date, look_back_days=7, limit=5):
    client, model = _get_openai_client()
    if client is None:
        logger.warning("OpenAI client unavailable, skipping global news fetch via Responses API")
        return ""

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search global or macroeconomics news from {look_back_days} days before {curr_date} to {curr_date} that would be informative for trading purposes? Make sure you only get the data posted during that period. Limit the results to {limit} articles.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text


def get_fundamentals_openai(ticker, curr_date):
    client, model = _get_openai_client()
    if client is None:
        logger.warning("OpenAI client unavailable, skipping fundamentals fetch via Responses API")
        return ""

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Fundamental for discussions on {ticker} during of the month before {curr_date} to the month of {curr_date}. Make sure you only get the data posted during that period. List as a table, with PE/PS/Cash flow/ etc",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text
