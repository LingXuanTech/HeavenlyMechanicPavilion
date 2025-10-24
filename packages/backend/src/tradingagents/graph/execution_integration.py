"""Integration module for connecting TradingAgentsGraph with execution services."""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ExecutionIntegration:
    """Helper class for integrating execution services with trading graph."""
    
    def __init__(self, execution_service=None, session_id: Optional[int] = None):
        """Initialize execution integration.
        
        Args:
            execution_service: ExecutionService instance
            session_id: Trading session ID
        """
        self.execution_service = execution_service
        self.session_id = session_id
        logger.info(f"Initialized ExecutionIntegration with session_id={session_id}")
    
    async def execute_graph_decision(
        self,
        db_session,
        portfolio_id: int,
        symbol: str,
        decision: str,
        current_price: float,
        state: Dict[str, Any],
    ):
        """Execute a decision from the trading graph.
        
        Args:
            db_session: Database session
            portfolio_id: Portfolio ID
            symbol: Stock symbol
            decision: Trading decision (BUY/SELL/HOLD)
            current_price: Current market price
            state: Full agent state with decision rationale
            
        Returns:
            Trade object if executed, None otherwise
        """
        if not self.execution_service:
            logger.warning("No execution service configured")
            return None
        
        # Extract decision rationale from state
        decision_rationale = self._extract_rationale(state)
        
        # Calculate confidence score from state (if available)
        confidence_score = self._calculate_confidence(state)
        
        logger.info(
            f"Executing graph decision: {decision} {symbol} @ ${current_price:.2f} "
            f"(confidence={confidence_score:.2f if confidence_score else 'N/A'})"
        )
        
        try:
            trade = await self.execution_service.execute_signal(
                session=db_session,
                portfolio_id=portfolio_id,
                symbol=symbol,
                signal=decision,
                current_price=current_price,
                decision_rationale=decision_rationale,
                confidence_score=confidence_score,
                session_id=self.session_id,
            )
            
            if trade:
                logger.info(f"Successfully executed trade: {trade.id}")
            else:
                logger.info("No trade executed (HOLD or filtered)")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error executing graph decision: {e}")
            return None
    
    def _extract_rationale(self, state: Dict[str, Any]) -> str:
        """Extract decision rationale from agent state.
        
        Args:
            state: Agent state dictionary
            
        Returns:
            Decision rationale string
        """
        rationale_parts = []
        
        # Include final trade decision
        if "final_trade_decision" in state:
            rationale_parts.append(f"Decision: {state['final_trade_decision']}")
        
        # Include investment plan
        if "investment_plan" in state:
            plan = state["investment_plan"]
            if isinstance(plan, str) and len(plan) < 500:
                rationale_parts.append(f"Plan: {plan}")
        
        # Include risk analysis
        if "risk_debate_state" in state:
            risk_state = state["risk_debate_state"]
            if "judge_decision" in risk_state:
                judge_decision = risk_state["judge_decision"]
                if isinstance(judge_decision, str) and len(judge_decision) < 500:
                    rationale_parts.append(f"Risk Assessment: {judge_decision}")
        
        return " | ".join(rationale_parts) if rationale_parts else "No rationale available"
    
    def _calculate_confidence(self, state: Dict[str, Any]) -> Optional[float]:
        """Calculate confidence score from agent state.
        
        This is a simplified heuristic based on debate consensus.
        
        Args:
            state: Agent state dictionary
            
        Returns:
            Confidence score (0-1) or None
        """
        # This is a placeholder implementation
        # In a more sophisticated version, you could analyze:
        # - Consensus among agents
        # - Strength of supporting data
        # - Historical accuracy
        
        # For now, return a default moderate confidence
        return 0.7


def create_execution_integration(
    execution_service=None,
    session_id: Optional[int] = None,
) -> ExecutionIntegration:
    """Factory function to create execution integration.
    
    Args:
        execution_service: ExecutionService instance
        session_id: Trading session ID
        
    Returns:
        ExecutionIntegration instance
    """
    return ExecutionIntegration(
        execution_service=execution_service,
        session_id=session_id,
    )
