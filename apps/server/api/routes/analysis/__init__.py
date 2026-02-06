from fastapi import APIRouter
from . import analyze, sentiment, macro, central_bank, policy, reflection, model_racing, vision, supply_chain

router = APIRouter()

router.include_router(analyze.router)
router.include_router(sentiment.router)
router.include_router(macro.router)
router.include_router(central_bank.router)
router.include_router(policy.router)
router.include_router(reflection.router)
router.include_router(model_racing.router)
router.include_router(vision.router)
router.include_router(supply_chain.router)
