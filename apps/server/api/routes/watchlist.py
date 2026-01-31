from fastapi import APIRouter, Depends, Path
from sqlmodel import Session, select
from typing import List
import re
from db.models import Watchlist, get_session
from services.data_router import MarketRouter
from api.exceptions import (
    ValidationError,
    InvalidSymbolError,
    ResourceNotFoundError,
    DataSourceError as AppDataSourceError,
)
import structlog

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])
logger = structlog.get_logger()

# Symbol validation pattern:
# - US stocks: 1-5 uppercase letters (e.g., AAPL, GOOGL)
# - A-shares: 6 digits + .SH or .SZ (e.g., 600519.SH, 000001.SZ)
# - HK stocks: 5 digits + .HK (e.g., 00700.HK)
SYMBOL_PATTERN = re.compile(
    r'^(?:'
    r'[A-Z]{1,5}'                    # US stocks: 1-5 uppercase letters
    r'|[0-9]{6}\.(SH|SZ)'            # A-shares: 6 digits + .SH or .SZ
    r'|[0-9]{5}\.HK'                 # HK stocks: 5 digits + .HK
    r')$',
    re.IGNORECASE
)


def validate_symbol(symbol: str) -> str:
    """Validate and normalize stock symbol.

    Args:
        symbol: Stock symbol to validate

    Returns:
        Normalized uppercase symbol

    Raises:
        ValidationError / InvalidSymbolError: If symbol format is invalid
    """
    symbol = symbol.strip().upper()

    if not symbol:
        raise ValidationError("Symbol cannot be empty", field="symbol")

    if len(symbol) > 12:
        raise ValidationError("Symbol too long (max 12 characters)", field="symbol")

    if not SYMBOL_PATTERN.match(symbol):
        raise InvalidSymbolError(symbol)

    return symbol

@router.get("/", response_model=List[Watchlist])
async def get_watchlist(session: Session = Depends(get_session)):
    statement = select(Watchlist)
    results = session.exec(statement).all()
    return results

@router.post("/{symbol}")
async def add_to_watchlist(
    symbol: str = Path(..., min_length=1, max_length=12, description="Stock symbol"),
    session: Session = Depends(get_session)
):
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)

    # Check if already exists
    statement = select(Watchlist).where(Watchlist.symbol == symbol)
    existing = session.exec(statement).first()
    if existing:
        return existing

    try:
        # Fetch basic info to get the name
        price_info = await MarketRouter.get_stock_price(symbol)
        market = MarketRouter.get_market(symbol)

        # For now, we don't have a full name lookup in MarketRouter,
        # but we can add it or use symbol as name for now.
        # Let's try to get fundamentals if possible
        name = symbol
        try:
            fund = await MarketRouter.get_fundamentals(symbol)
            name = fund.name
        except Exception as e:
            logger.debug("Could not fetch fundamentals, using symbol as name", symbol=symbol, error=str(e))

        new_item = Watchlist(symbol=symbol, name=name, market=market)
        session.add(new_item)
        session.commit()
        session.refresh(new_item)

        logger.info("Added symbol to watchlist", symbol=symbol, name=name, market=market)
        return new_item
    except AppDataSourceError:
        raise  # 已是 AppException 子类，交给全局 handler
    except Exception as e:
        logger.error("Failed to add to watchlist", symbol=symbol, error=str(e))
        raise AppDataSourceError("watchlist", f"Could not add symbol {symbol}: {str(e)}")

@router.delete("/{symbol}")
async def remove_from_watchlist(
    symbol: str = Path(..., min_length=1, max_length=12, description="Stock symbol"),
    session: Session = Depends(get_session)
):
    # Validate and normalize symbol
    symbol = validate_symbol(symbol)

    statement = select(Watchlist).where(Watchlist.symbol == symbol)
    item = session.exec(statement).first()
    if not item:
        raise ResourceNotFoundError("Watchlist", symbol)

    session.delete(item)
    session.commit()

    logger.info("Removed symbol from watchlist", symbol=symbol)
    return {"message": f"Removed {symbol} from watchlist"}
