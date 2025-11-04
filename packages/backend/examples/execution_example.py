"""Example demonstrating the execution pipeline and risk management services."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    logger.info("=" * 80)
    logger.info("Trading Execution and Risk Management Example")
    logger.info("=" * 80)
    
    # Note: This is a demonstration script showing the API usage
    # In production, use the FastAPI endpoints instead
    
    from app.db.models import Portfolio
    from app.repositories import PortfolioRepository
    from app.services import (
        ExecutionService,
        MarketDataService,
        PositionSizingMethod,
        PositionSizingService,
        RiskConstraints,
        RiskManagementService,
        SimulatedBroker,
    )
    
    # Create database engine (use your actual database URL)
    database_url = "sqlite+aiosqlite:///./test_trading.db"
    engine = create_async_engine(database_url, echo=False)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # 1. Create or get a portfolio
        logger.info("\n" + "=" * 80)
        logger.info("Step 1: Portfolio Setup")
        logger.info("=" * 80)
        
        portfolio_repo = PortfolioRepository(session)
        
        portfolio = await portfolio_repo.get_by_name("Demo Portfolio")
        
        if not portfolio:
            portfolio = Portfolio(
                name="Demo Portfolio",
                description="Demo portfolio for testing execution services",
                initial_capital=100000.0,
                current_capital=100000.0,
                currency="USD",
            )
            portfolio = await portfolio_repo.create(portfolio)
            await session.commit()
            logger.info(f"Created new portfolio: {portfolio.name}")
        else:
            logger.info(f"Using existing portfolio: {portfolio.name}")
        
        logger.info(f"Portfolio capital: ${portfolio.current_capital:,.2f}")
        
        # 2. Initialize services
        logger.info("\n" + "=" * 80)
        logger.info("Step 2: Service Initialization")
        logger.info("=" * 80)
        
        # Create broker adapter
        broker = SimulatedBroker(
            initial_capital=portfolio.current_capital,
            commission_per_trade=0.0,
            slippage_percent=0.001,
            market_data_service=MarketDataService(),
        )
        logger.info("✓ Initialized SimulatedBroker")
        
        # Create position sizing service
        position_sizing = PositionSizingService(
            method=PositionSizingMethod.RISK_BASED,
            default_percentage=0.05,
            max_position_size=0.20,
            risk_per_trade=0.02,
        )
        logger.info("✓ Initialized PositionSizingService (risk-based)")
        
        # Create risk management service
        risk_constraints = RiskConstraints(
            max_position_weight=0.20,
            max_portfolio_exposure=1.0,
            default_stop_loss_pct=0.10,
            default_take_profit_pct=0.20,
        )
        risk_management = RiskManagementService(constraints=risk_constraints)
        logger.info("✓ Initialized RiskManagementService")
        
        # Create execution service
        execution_service = ExecutionService(
            broker=broker,
            position_sizing_service=position_sizing,
            risk_management_service=risk_management,
        )
        logger.info("✓ Initialized ExecutionService")
        
        # 3. Execute trading signals
        logger.info("\n" + "=" * 80)
        logger.info("Step 3: Execute Trading Signals")
        logger.info("=" * 80)
        
        signals = [
            ("AAPL", "BUY", 150.0, "Strong buy signal from analyst consensus", 0.85),
            ("MSFT", "BUY", 380.0, "Positive earnings outlook", 0.75),
            ("GOOGL", "BUY", 140.0, "Market momentum indicator", 0.70),
        ]
        
        for symbol, signal, price, rationale, confidence in signals:
            logger.info(f"\n--- Executing: {signal} {symbol} @ ${price:.2f} ---")
            
            trade = await execution_service.execute_signal(
                session=session,
                portfolio_id=portfolio.id,
                symbol=symbol,
                signal=signal,
                current_price=price,
                decision_rationale=rationale,
                confidence_score=confidence,
            )
            
            if trade:
                logger.info(
                    f"✓ Trade executed: {trade.action} {trade.filled_quantity} "
                    f"{trade.symbol} @ ${trade.average_fill_price:.2f}"
                )
            else:
                logger.info("✗ Trade not executed")
        
        await session.commit()
        
        # 4. Check portfolio state
        logger.info("\n" + "=" * 80)
        logger.info("Step 4: Portfolio State")
        logger.info("=" * 80)
        
        from app.repositories import PositionRepository
        
        position_repo = PositionRepository(session)
        positions = await position_repo.get_by_portfolio(portfolio.id)
        
        logger.info(f"\nTotal positions: {len(positions)}")
        for pos in positions:
            if pos.quantity > 0:
                position_value = pos.quantity * pos.current_price
                logger.info(
                    f"  {pos.symbol}: {pos.quantity} shares @ ${pos.current_price:.2f} "
                    f"= ${position_value:,.2f}"
                )
        
        # Refresh portfolio
        portfolio = await portfolio_repo.get(portfolio.id)
        logger.info(f"\nPortfolio cash: ${portfolio.current_capital:,.2f}")
        
        # 5. Calculate risk metrics
        logger.info("\n" + "=" * 80)
        logger.info("Step 5: Risk Diagnostics")
        logger.info("=" * 80)
        
        current_prices = {pos.symbol: pos.current_price for pos in positions}
        
        diagnostics = await risk_management.calculate_diagnostics(
            portfolio_id=portfolio.id,
            positions=positions,
            current_prices=current_prices,
        )
        
        logger.info(f"\nPortfolio Value: ${diagnostics.portfolio_value:,.2f}")
        logger.info(f"Number of Positions: {diagnostics.number_of_positions}")
        logger.info(f"Total Exposure: ${diagnostics.total_exposure:,.2f}")
        logger.info(f"Long Exposure: ${diagnostics.long_exposure:,.2f}")
        logger.info(f"Net Exposure: ${diagnostics.net_exposure:,.2f}")
        
        if diagnostics.largest_position_weight:
            logger.info(
                f"Largest Position: {diagnostics.largest_position_weight:.1%}"
            )
        
        if diagnostics.warnings:
            logger.warning("\nRisk Warnings:")
            for warning in diagnostics.warnings:
                logger.warning(f"  ⚠ {warning}")
        else:
            logger.info("\n✓ No risk warnings")
        
        # 6. Demonstrate stop-loss / take-profit
        logger.info("\n" + "=" * 80)
        logger.info("Step 6: Stop-Loss / Take-Profit Check")
        logger.info("=" * 80)
        
        logger.info("\nChecking positions for stop-loss or take-profit triggers...")
        
        # Simulate price changes to trigger stop-loss
        for pos in positions:
            if pos.quantity > 0:
                # Check with current price
                stop_loss_triggered = risk_management.check_stop_loss(
                    pos, pos.current_price
                )
                take_profit_triggered = risk_management.check_take_profit(
                    pos, pos.current_price
                )
                
                if stop_loss_triggered:
                    logger.warning(f"  Stop-loss would trigger for {pos.symbol}")
                elif take_profit_triggered:
                    logger.info(f"  Take-profit would trigger for {pos.symbol}")
                else:
                    pnl_pct = (
                        (pos.current_price - pos.average_cost) / pos.average_cost
                    )
                    logger.info(
                        f"  {pos.symbol}: P&L {pnl_pct:+.1%} (no triggers)"
                    )
        
        # 7. Demonstrate force exit
        logger.info("\n" + "=" * 80)
        logger.info("Step 7: Force Exit Position")
        logger.info("=" * 80)
        
        if positions and positions[0].quantity > 0:
            pos = positions[0]
            logger.info(f"\nForcing exit of position: {pos.symbol}")
            
            trade = await execution_service.force_exit_position(
                session=session,
                portfolio_id=portfolio.id,
                symbol=pos.symbol,
                reason="Demonstration force exit",
            )
            
            if trade:
                logger.info(
                    f"✓ Position exited: {trade.action} {trade.filled_quantity} "
                    f"{trade.symbol} @ ${trade.average_fill_price:.2f}"
                )
            
            await session.commit()
        
        logger.info("\n" + "=" * 80)
        logger.info("Example Complete!")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("  1. Start a trading session via POST /trading/sessions/start")
        logger.info("  2. Execute signals via POST /trading/execute")
        logger.info("  3. Monitor risk via GET /trading/risk/diagnostics/{portfolio_id}")
        logger.info("  4. View portfolio state via GET /trading/portfolio/{portfolio_id}/state")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
