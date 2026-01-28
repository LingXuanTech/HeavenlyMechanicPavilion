from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_sentiment,
    get_insider_transactions,
    get_global_news
)


def create_msg_delete(keep_last_n: int = 0):
    """创建消息删除节点

    Args:
        keep_last_n: 保留最后 N 条消息（默认 0 表示全部删除）

    Returns:
        消息删除函数
    """
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        if keep_last_n > 0 and len(messages) > keep_last_n:
            # 保留最后 N 条消息
            removal_operations = [RemoveMessage(id=m.id) for m in messages[:-keep_last_n]]
        else:
            # 删除所有消息
            removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


def create_msg_delete_parallel(keep_last_n: int = 3):
    """创建并行模式下的消息删除节点

    在并行执行时保留更多上下文，防止消息丢失。

    Args:
        keep_last_n: 保留最后 N 条消息（默认 3）

    Returns:
        消息删除函数
    """
    def delete_messages_parallel(state):
        """并行模式消息清理，保留更多上下文"""
        messages = state.get("messages", [])

        # 保留最后 N 条消息
        if len(messages) > keep_last_n:
            removal_ops = [RemoveMessage(id=m.id) for m in messages[:-keep_last_n]]
        else:
            removal_ops = []

        # 添加占位消息
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_ops + [placeholder]}

    return delete_messages_parallel


        