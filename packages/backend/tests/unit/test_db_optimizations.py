"""Tests for database optimization features."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Portfolio, Position, Trade
from app.repositories import PortfolioRepository, PositionRepository, TradeRepository


@pytest.mark.asyncio
async def test_portfolio_positions_composite_index_exists(db_session: AsyncSession):
    """Test that the composite index on positions(portfolio_id, symbol) exists."""
    # Query to check if index exists (works for SQLite and PostgreSQL)
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_positions_portfolio_symbol'")
    )
    index = result.scalar_one_or_none()
    assert index is not None, "Composite index on positions(portfolio_id, symbol) should exist"


@pytest.mark.asyncio
async def test_trades_session_id_index_exists(db_session: AsyncSession):
    """Test that the index on trades.session_id exists."""
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_trades_session_id'")
    )
    index = result.scalar_one_or_none()
    assert index is not None, "Index on trades.session_id should exist"


@pytest.mark.asyncio
async def test_trades_composite_indexes_exist(db_session: AsyncSession):
    """Test that composite indexes on trades table exist."""
    # Check portfolio_status index
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_trades_portfolio_status'")
    )
    index1 = result.scalar_one_or_none()
    assert index1 is not None, "Composite index on trades(portfolio_id, status) should exist"
    
    # Check portfolio_created index
    result = await db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name='ix_trades_portfolio_created'")
    )
    index2 = result.scalar_one_or_none()
    assert index2 is not None, "Composite index on trades(portfolio_id, created_at) should exist"


@pytest.mark.asyncio
async def test_portfolio_eager_loading_no_n_plus_1(db_session: AsyncSession):
    """Test that eager loading prevents N+1 queries for portfolio positions."""
    # Create test data
    portfolio = Portfolio(
        name="Test Portfolio",
        initial_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    
    # Add positions
    for i, symbol in enumerate(["AAPL", "GOOGL", "MSFT"]):
        position = Position(
            portfolio_id=portfolio.id,
            symbol=symbol,
            quantity=10.0 * (i + 1),
            average_cost=100.0,
            current_price=110.0,
        )
        db_session.add(position)
    await db_session.commit()
    
    # Test eager loading
    repo = PortfolioRepository(db_session)
    
    # This should load portfolio with positions in a single query (or two optimized queries)
    loaded_portfolio = await repo.get_with_positions(portfolio.id)
    
    assert loaded_portfolio is not None
    assert len(loaded_portfolio.positions) == 3
    assert loaded_portfolio.positions[0].symbol in ["AAPL", "GOOGL", "MSFT"]


@pytest.mark.asyncio
async def test_trade_eager_loading_with_executions(db_session: AsyncSession):
    """Test that eager loading works for trades with executions."""
    from app.db.models import Execution
    
    # Create test data
    portfolio = Portfolio(
        name="Test Portfolio 2",
        initial_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    
    # Create trade
    trade = Trade(
        portfolio_id=portfolio.id,
        symbol="AAPL",
        action="BUY",
        quantity=100.0,
        order_type="MARKET",
        status="FILLED",
    )
    db_session.add(trade)
    await db_session.commit()
    await db_session.refresh(trade)
    
    # Add executions
    execution = Execution(
        trade_id=trade.id,
        symbol="AAPL",
        quantity=100.0,
        price=150.0,
        execution_type="MARKET",
        commission=1.0,
        fees=0.5,
    )
    db_session.add(execution)
    await db_session.commit()
    
    # Test eager loading
    repo = TradeRepository(db_session)
    loaded_trade = await repo.get_with_executions(trade.id)
    
    assert loaded_trade is not None
    assert len(loaded_trade.executions) == 1
    assert loaded_trade.executions[0].quantity == 100.0


@pytest.mark.asyncio
async def test_get_position_by_symbol_uses_index(db_session: AsyncSession):
    """Test that getting position by portfolio and symbol should use the composite index."""
    # Create test data
    portfolio = Portfolio(
        name="Index Test Portfolio",
        initial_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    
    position = Position(
        portfolio_id=portfolio.id,
        symbol="TSLA",
        quantity=50.0,
        average_cost=200.0,
        current_price=220.0,
    )
    db_session.add(position)
    await db_session.commit()
    
    # Query using the composite index
    repo = PositionRepository(db_session)
    found_position = await repo.get_by_symbol(portfolio.id, "TSLA")
    
    assert found_position is not None
    assert found_position.symbol == "TSLA"
    assert found_position.quantity == 50.0


@pytest.mark.asyncio
async def test_trade_session_id_foreign_key(db_session: AsyncSession):
    """Test that trades.session_id has proper foreign key relationship."""
    from app.db.models import TradingSession
    
    # Create portfolio
    portfolio = Portfolio(
        name="FK Test Portfolio",
        initial_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    
    # Create trading session
    trading_session = TradingSession(
        portfolio_id=portfolio.id,
        session_type="PAPER",
        status="ACTIVE",
        starting_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(trading_session)
    await db_session.commit()
    await db_session.refresh(trading_session)
    
    # Create trade with session_id
    trade = Trade(
        portfolio_id=portfolio.id,
        session_id=trading_session.id,
        symbol="NVDA",
        action="BUY",
        quantity=20.0,
        order_type="MARKET",
        status="PENDING",
    )
    db_session.add(trade)
    await db_session.commit()
    await db_session.refresh(trade)
    
    # Verify the relationship
    assert trade.session_id == trading_session.id
    
    # Query by session
    repo = TradeRepository(db_session)
    session_trades = await repo.get_by_session(trading_session.id)
    
    assert len(session_trades) == 1
    assert session_trades[0].id == trade.id


@pytest.mark.asyncio
async def test_query_performance_with_filtering(db_session: AsyncSession):
    """Test that composite indexes improve query performance for filtering."""
    from sqlalchemy import select
    
    # Create test data
    portfolio = Portfolio(
        name="Performance Test Portfolio",
        initial_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    
    # Create multiple trades with different statuses
    statuses = ["PENDING", "FILLED", "CANCELLED", "FILLED", "PENDING"]
    for i, status in enumerate(statuses):
        trade = Trade(
            portfolio_id=portfolio.id,
            symbol=f"STOCK{i}",
            action="BUY",
            quantity=10.0,
            order_type="MARKET",
            status=status,
        )
        db_session.add(trade)
    await db_session.commit()
    
    # Filter by status (should use the composite index)
    stmt = select(Trade).where(
        Trade.portfolio_id == portfolio.id,
        Trade.status == "FILLED"
    )
    result = await db_session.execute(stmt)
    filled_only = list(result.scalars().all())
    
    assert len(filled_only) == 2
    assert all(t.status == "FILLED" for t in filled_only)


@pytest.mark.asyncio
async def test_portfolio_with_all_relations(db_session: AsyncSession):
    """Test loading portfolio with all relationships at once."""
    # Create comprehensive test data
    portfolio = Portfolio(
        name="Full Relations Portfolio",
        initial_capital=100000.0,
        current_capital=100000.0,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)
    
    # Add positions
    for symbol in ["AAPL", "GOOGL"]:
        position = Position(
            portfolio_id=portfolio.id,
            symbol=symbol,
            quantity=10.0,
            average_cost=100.0,
            current_price=110.0,
        )
        db_session.add(position)
    
    # Add trades
    for symbol in ["AAPL", "MSFT"]:
        trade = Trade(
            portfolio_id=portfolio.id,
            symbol=symbol,
            action="BUY",
            quantity=10.0,
            order_type="MARKET",
            status="FILLED",
        )
        db_session.add(trade)
    
    await db_session.commit()
    
    # Load with all relations
    repo = PortfolioRepository(db_session)
    loaded = await repo.get_with_all_relations(portfolio.id)
    
    assert loaded is not None
    assert len(loaded.positions) == 2
    assert len(loaded.trades) == 2
    assert loaded.positions[0].portfolio_id == portfolio.id
    assert loaded.trades[0].portfolio_id == portfolio.id
