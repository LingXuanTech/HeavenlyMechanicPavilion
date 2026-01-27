import yaml
import os
from typing import Dict, Any, Optional
import structlog
from config.settings import settings

logger = structlog.get_logger()

class PromptManager:
    _instance = None
    _prompts: Dict[str, Any] = {}
    _last_mtime: float = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptManager, cls).__new__(cls)
            cls._instance._load_prompts()
        return cls._instance

    def _load_prompts(self):
        path = settings.PROMPTS_YAML_PATH
        if not os.path.exists(path):
            logger.error("Prompts YAML file not found", path=path)
            return

        try:
            mtime = os.path.getmtime(path)
            if mtime > self._last_mtime:
                with open(path, 'r', encoding='utf-8') as f:
                    self._prompts = yaml.safe_load(f)
                self._last_mtime = mtime
                logger.info("Prompts loaded/reloaded", path=path)
        except Exception as e:
            logger.error("Failed to load prompts", error=str(e))

    def get_prompt(self, role: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        Get system and user prompts for a specific role.
        Injects context variables if provided.
        """
        self._load_prompts() # Check for updates
        
        role_config = self._prompts.get(role, {})
        system_tmpl = role_config.get("system", "")
        user_tmpl = role_config.get("user", "")

        if context:
            try:
                system_prompt = system_tmpl.format(**context)
                user_prompt = user_tmpl.format(**context)
            except KeyError as e:
                logger.warning("Missing context variable for prompt", role=role, missing=str(e))
                system_prompt = system_tmpl
                user_prompt = user_tmpl
        else:
            system_prompt = system_tmpl
            user_prompt = user_tmpl

        return {
            "system": system_prompt,
            "user": user_prompt
        }

prompt_manager = PromptManager()
