#!/usr/bin/env python
"""Simple test script for the persistence layer."""

import asyncio
from datetime import datetime

from app.config import Settings
from app.db import init_db
from app.db.models import Portfolio, Position, Trade
from app.repositories import PortfolioRepository, PositionRepository, TradeRepository


async def main():
    """Test the persistence layer."""
    print("Testing TradingAgents Persistence Layer")
    print("=" * 50)
    
    # Initialize settings
    settings = Settings()
    print(f"Database URL: {settings.database_url}")
    print(f"Redis Enabled: {settings.redis_enabled}")
    
    # Initialize database
    db_manager = init_db(database_url=settings.database_url, echo=False)
    print("Database manager initialized")
    
    # Create tables
    await db_manager.create_tables()
    print("Database tables created")
    
    # Test repository operations
    async for session in db_manager.get_session():
        print("\nTesting Portfolio Repository:")
        portfolio_repo = PortfolioRepository(session)
        
        # Create a portfolio
        portfolio = Portfolio(
            name="test_portfolio",
            description="Test portfolio for persistence layer",
            initial_capital=100000.0,
            current_capital=100000.0,
            currency="USD",
        )
        created_portfolio = await portfolio_repo.create(portfolio)
        print(f"  Created portfolio: ID={created_portfolio.id}, Name={created_portfolio.name}")
        
        # Get portfolio by name
        retrieved = await portfolio_repo.get_by_name("test_portfolio")
        print(f"  Retrieved portfolio: ID={retrieved.id}, Capital=${retrieved.current_capital}")
        
        print("\nTesting Position Repository:")
        position_repo = PositionRepository(session)
        
        # Create a position
        position = Position(
            portfolio_id=created_portfolio.id,
            symbol="AAPL",
            quantity=100,
            average_cost=150.0,
            current_price=155.0,
            unrealized_pnl=500.0,
            position_type="LONG",
        )
        created_position = await position_repo.create(position)
        print(f"  Created position: {created_position.symbol} x {created_position.quantity}")
        
        # Get positions for portfolio
        positions = await position_repo.get_by_portfolio(created_portfolio.id)
        print(f"  Portfolio has {len(positions)} position(s)")
        
        print("\nTesting Trade Repository:")
        trade_repo = TradeRepository(session)
        
        # Create a trade
        trade = Trade(
            portfolio_id=created_portfolio.id,
            symbol="AAPL",
            action="BUY",
            quantity=100,
            order_type="MARKET",
            status="FILLED",
            filled_quantity=100,
            average_fill_price=150.0,
            decision_rationale="Test trade",
            confidence_score=0.85,
        )
        created_trade = await trade_repo.create(trade)
        print(f"  Created trade: {created_trade.action} {created_trade.quantity} {created_trade.symbol}")
        
        # Get trades for portfolio
        trades = await trade_repo.get_by_portfolio(created_portfolio.id)
        print(f"  Portfolio has {len(trades)} trade(s)")
        
        # Get trades by status
        filled_trades = await trade_repo.get_by_status("FILLED")
        print(f"  Found {len(filled_trades)} FILLED trade(s)")
    
    # Close database
    await db_manager.close()
    print("\nDatabase connections closed")
    print("=" * 50)
    print("✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
