from fastapi import APIRouter
from . import auth, oauth, passkey, admin, settings, health, prompts, ai_config, tts

router = APIRouter()

router.include_router(auth.router)
router.include_router(oauth.router)
router.include_router(passkey.router)
router.include_router(admin.router)
router.include_router(settings.router)
router.include_router(health.router)
router.include_router(prompts.router)
router.include_router(ai_config.router)
router.include_router(tts.router)
