from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from db.models import Watchlist, get_session
from services.data_router import MarketRouter
import structlog

router = APIRouter(prefix="/watchlist", tags=["Watchlist"])
logger = structlog.get_logger()

@router.get("/", response_model=List[Watchlist])
async def get_watchlist(session: Session = Depends(get_session)):
    statement = select(Watchlist)
    results = session.exec(statement).all()
    return results

@router.post("/{symbol}")
async def add_to_watchlist(symbol: str, session: Session = Depends(get_session)):
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
        try:
            fund = await MarketRouter.get_fundamentals(symbol)
            name = fund.name
        except:
            name = symbol

        new_item = Watchlist(symbol=symbol, name=name, market=market)
        session.add(new_item)
        session.commit()
        session.refresh(new_item)
        return new_item
    except Exception as e:
        logger.error("Failed to add to watchlist", symbol=symbol, error=str(e))
        raise HTTPException(status_code=400, detail=f"Could not add symbol: {str(e)}")

@router.delete("/{symbol}")
async def remove_from_watchlist(symbol: str, session: Session = Depends(get_session)):
    statement = select(Watchlist).where(Watchlist.symbol == symbol)
    item = session.exec(statement).first()
    if not item:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist")
    
    session.delete(item)
    session.commit()
    return {"message": f"Removed {symbol} from watchlist"}
