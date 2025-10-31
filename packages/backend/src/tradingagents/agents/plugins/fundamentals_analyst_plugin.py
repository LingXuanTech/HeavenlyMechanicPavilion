"""Fundamentals analyst agent plugin."""

from typing import Any, Callable, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from ..plugin_base import AgentCapability, AgentPlugin, AgentRole
from ..utils.fundamental_data_tools import (
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
)


class FundamentalsAnalystPlugin(AgentPlugin):
    """Fundamentals analyst specializing in financial statements and company fundamentals."""

    @property
    def name(self) -> str:
        return "fundamentals_analyst"

    @property
    def role(self) -> AgentRole:
        return AgentRole.ANALYST

    @property
    def capabilities(self) -> List[AgentCapability]:
        return [AgentCapability.FUNDAMENTAL_ANALYSIS]

    @property
    def prompt_template(self) -> str:
        return "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read. Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."

    @property
    def description(self) -> str:
        return "Fundamentals analyst specializing in financial statements and company fundamentals"

    @property
    def required_tools(self) -> List[str]:
        return ["get_fundamentals", "get_balance_sheet", "get_cashflow", "get_income_statement"]

    @property
    def llm_type(self) -> str:
        return "quick"

    @property
    def slot_name(self) -> Optional[str]:
        return "fundamentals"

    def get_conditional_logic(self) -> Optional[str]:
        return "should_continue_fundamentals"

    def get_tools_node_name(self) -> Optional[str]:
        return "tools_fundamentals"

    def create_node(self, llm: BaseChatModel, memory: Optional[Any] = None, **kwargs) -> Callable:
        """Create the fundamentals analyst node function."""

        def fundamentals_analyst_node(state):
            current_date = state["trade_date"]
            ticker = state["company_of_interest"]

            tools = [get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement]
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
                        "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
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
                "fundamentals_report": report,
            }

        return fundamentals_analyst_node
