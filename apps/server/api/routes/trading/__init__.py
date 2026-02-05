from fastapi import APIRouter
from . import watchlist, portfolio, backtest, chat, memory, discover, news, news_aggregator

router = APIRouter()

router.include_router(watchlist.router)
router.include_router(portfolio.router)
router.include_router(backtest.router)
router.include_router(chat.router)
router.include_router(memory.router)
router.include_router(discover.router)
router.include_router(news.router)
router.include_router(news_aggregator.router)
