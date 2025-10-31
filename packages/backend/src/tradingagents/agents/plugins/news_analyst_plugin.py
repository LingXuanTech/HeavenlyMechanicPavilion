"""News analyst agent plugin."""

from typing import Any, Callable, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..plugin_base import AgentCapability, AgentPlugin, AgentRole
from ..utils.agent_utils import get_global_news, get_news


class NewsAnalystPlugin(AgentPlugin):
    """News analyst agent for news and macroeconomic analysis."""

    @property
    def name(self) -> str:
        return "news_analyst"

    @property
    def role(self) -> AgentRole:
        return AgentRole.ANALYST

    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.NEWS_ANALYSIS]

    @property
    def prompt_template(self) -> str:
        return (
            "You are a news researcher tasked with analyzing recent news and trends over the past week. Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. Use the available tools: get_news(query, start_date, end_date) for company-specific or targeted news searches, and get_global_news(curr_date, look_back_days, limit) for broader macroeconomic news. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions."
            " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
        )

    @property
    def description(self) -> str:
        return "News analyst specializing in news and macroeconomic trends"

    @property
    def required_tools(self) -> List[str]:
        return ["get_news", "get_global_news"]

    @property
    def llm_type(self) -> str:
        return "quick"

    @property
    def slot_name(self) -> Optional[str]:
        return "news"

    def get_conditional_logic(self) -> Optional[str]:
        return "should_continue_news"

    def get_tools_node_name(self) -> Optional[str]:
        return "tools_news"

    def create_node(self, llm: BaseChatModel, memory: Optional[Any] = None, **kwargs) -> Callable:
        """Create the news analyst node function."""

        def news_analyst_node(state):
            current_date = state["trade_date"]
            ticker = state["company_of_interest"]

            tools = [get_news, get_global_news]
            system_message = self.prompt_template

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful AI assistant, collaborating with other assistants."
                        " Use the provided tools to progress towards answering the question."
                        " If you are unable to fully answer, that's OK; another assistant with different tools"
                        " will help where you left off. Execute what you can to make progress."
                        " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                        " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                        " You have access to the following tools: {tool_names}.\n{system_message}"
                        "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
                    ),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
            prompt = prompt.partial(current_date=current_date)
            prompt = prompt.partial(ticker=ticker)

            chain = prompt | llm.bind_tools(tools)
            result = chain.invoke(state["messages"])

            report = ""
            if len(result.tool_calls) == 0:
                report = result.content

            return {
                "messages": [result],
                "news_report": report,
            }

        return news_analyst_node
