# TradingAgents/graph/signal_processing.py

from typing import Any, Sequence


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: Any) -> None:
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """Process a full trading signal to extract the core decision."""
        messages: Sequence[tuple[str, str]] = [
            (
                "system",
                "You are an efficient assistant designed to analyze paragraphs or financial reports provided by a group of analysts. Your task is to extract the investment decision: SELL, BUY, or HOLD. Provide only the extracted decision (SELL, BUY, or HOLD) as your output, without adding any additional text or information.",
            ),
            ("human", full_signal),
        ]

        response = self.quick_thinking_llm.invoke(messages)
        return getattr(response, "content", "").strip()
