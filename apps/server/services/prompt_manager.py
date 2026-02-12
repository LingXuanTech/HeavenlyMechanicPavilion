import re
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
                # 使用 regex 安全替换：只替换 {key} 中 key 为合法标识符且存在于 context 中的变量
                # 避免误匹配 JSON 中的 {"symbol": ...} 等文本
                def _safe_sub(template: str) -> str:
                    def replacer(m: re.Match) -> str:
                        key = m.group(1)
                        if key in context:
                            return str(context[key])
                        return m.group(0)  # 不在 context 中则原样保留
                    return re.sub(r'\{([a-zA-Z_]\w*)\}', replacer, template)

                system_prompt = _safe_sub(system_tmpl)
                user_prompt = _safe_sub(user_tmpl)
            except Exception as e:
                logger.warning("Failed to render prompt", role=role, error=str(e))
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
