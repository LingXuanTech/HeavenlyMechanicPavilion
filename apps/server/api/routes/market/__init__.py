from fastapi import APIRouter
from . import market, north_money, lhb, jiejin, unlock, cross_asset, market_watcher, alternative

router = APIRouter()

router.include_router(market.router)
router.include_router(north_money.router)
router.include_router(lhb.router)
router.include_router(jiejin.router)
router.include_router(unlock.router)
router.include_router(cross_asset.router)
router.include_router(market_watcher.router)
router.include_router(alternative.router)
