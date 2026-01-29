"""
TTS 语音合成服务

支持多个 TTS 提供商：
- OpenAI TTS (tts-1, tts-1-hd)
- Google Gemini TTS
- Edge TTS (免费备选)
"""

import asyncio
import hashlib
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
import structlog

logger = structlog.get_logger(__name__)


class TTSProvider(str, Enum):
    """TTS 提供商"""
    OPENAI = "openai"
    GEMINI = "gemini"
    EDGE = "edge"


class TTSVoice(str, Enum):
    """预定义的语音"""
    # OpenAI 语音
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"

    # Edge TTS 中文语音
    XIAOXIAO = "zh-CN-XiaoxiaoNeural"
    XIAOYI = "zh-CN-XiaoyiNeural"
    YUNYANG = "zh-CN-YunyangNeural"
    YUNXI = "zh-CN-YunxiNeural"

    # Edge TTS 英文语音
    JENNY = "en-US-JennyNeural"
    GUY = "en-US-GuyNeural"
    ARIA = "en-US-AriaNeural"


@dataclass
class TTSConfig:
    """TTS 配置"""
    provider: TTSProvider = TTSProvider.EDGE
    voice: str = TTSVoice.XIAOXIAO.value
    speed: float = 1.0
    pitch: str = "+0Hz"
    # OpenAI 特定
    model: str = "tts-1"  # tts-1 or tts-1-hd
    response_format: str = "mp3"


@dataclass
class TTSResult:
    """TTS 结果"""
    audio_data: bytes
    format: str
    duration_ms: Optional[int] = None
    provider: str = ""
    voice: str = ""
    text_length: int = 0


class BaseTTSProvider(ABC):
    """TTS 提供商基类"""

    @abstractmethod
    async def synthesize(self, text: str, config: TTSConfig) -> TTSResult:
        """合成语音"""
        pass

    @abstractmethod
    async def get_voices(self) -> List[Dict[str, Any]]:
        """获取可用语音列表"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查提供商是否可用"""
        pass


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS 提供商"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI()
            except ImportError:
                logger.warning("OpenAI package not installed")
                return None
        return self._client

    def is_available(self) -> bool:
        import os
        return bool(os.getenv("OPENAI_API_KEY"))

    async def synthesize(self, text: str, config: TTSConfig) -> TTSResult:
        client = self._get_client()
        if not client:
            raise RuntimeError("OpenAI client not available")

        try:
            response = await client.audio.speech.create(
                model=config.model,
                voice=config.voice,
                input=text,
                response_format=config.response_format,
                speed=config.speed,
            )

            audio_data = response.content

            return TTSResult(
                audio_data=audio_data,
                format=config.response_format,
                provider="openai",
                voice=config.voice,
                text_length=len(text),
            )
        except Exception as e:
            logger.error("OpenAI TTS failed", error=str(e))
            raise

    async def get_voices(self) -> List[Dict[str, Any]]:
        return [
            {"id": "alloy", "name": "Alloy", "language": "en", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "language": "en", "gender": "male"},
            {"id": "fable", "name": "Fable", "language": "en", "gender": "neutral"},
            {"id": "onyx", "name": "Onyx", "language": "en", "gender": "male"},
            {"id": "nova", "name": "Nova", "language": "en", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "language": "en", "gender": "female"},
        ]


class EdgeTTSProvider(BaseTTSProvider):
    """Edge TTS 提供商（免费）"""

    def is_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    async def synthesize(self, text: str, config: TTSConfig) -> TTSResult:
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts package not installed. Run: pip install edge-tts")

        voice = config.voice
        # 如果使用 OpenAI 风格的语音名，转换为 Edge TTS 格式
        voice_mapping = {
            "alloy": "zh-CN-XiaoxiaoNeural",
            "echo": "zh-CN-YunxiNeural",
            "fable": "zh-CN-XiaoyiNeural",
            "onyx": "zh-CN-YunyangNeural",
            "nova": "en-US-JennyNeural",
            "shimmer": "en-US-AriaNeural",
        }
        voice = voice_mapping.get(voice, voice)

        try:
            communicate = edge_tts.Communicate(
                text,
                voice,
                rate=f"{int((config.speed - 1) * 100):+d}%",
                pitch=config.pitch,
            )

            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            return TTSResult(
                audio_data=audio_data,
                format="mp3",
                provider="edge",
                voice=voice,
                text_length=len(text),
            )
        except Exception as e:
            logger.error("Edge TTS failed", error=str(e))
            raise

    async def get_voices(self) -> List[Dict[str, Any]]:
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [
                {
                    "id": v["ShortName"],
                    "name": v["FriendlyName"],
                    "language": v["Locale"],
                    "gender": v["Gender"],
                }
                for v in voices
                if v["Locale"].startswith(("zh-", "en-"))  # 只返回中英文
            ]
        except Exception as e:
            logger.error("Failed to list Edge TTS voices", error=str(e))
            return []


class TTSService:
    """
    TTS 服务

    自动选择可用的 TTS 提供商，支持降级。

    Usage:
        tts = TTSService()
        result = await tts.synthesize("Hello, world!")
        with open("output.mp3", "wb") as f:
            f.write(result.audio_data)
    """

    def __init__(self):
        self._providers: Dict[TTSProvider, BaseTTSProvider] = {}
        self._cache_dir: Optional[Path] = None
        self._init_providers()

    def _init_providers(self):
        """初始化可用的提供商"""
        # OpenAI
        openai_provider = OpenAITTSProvider()
        if openai_provider.is_available():
            self._providers[TTSProvider.OPENAI] = openai_provider
            logger.info("OpenAI TTS provider available")

        # Edge TTS (always try to add as fallback)
        edge_provider = EdgeTTSProvider()
        if edge_provider.is_available():
            self._providers[TTSProvider.EDGE] = edge_provider
            logger.info("Edge TTS provider available")

    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        return [p.value for p in self._providers.keys()]

    def get_default_provider(self) -> TTSProvider:
        """获取默认提供商（优先使用 OpenAI）"""
        if TTSProvider.OPENAI in self._providers:
            return TTSProvider.OPENAI
        if TTSProvider.EDGE in self._providers:
            return TTSProvider.EDGE
        raise RuntimeError("No TTS provider available")

    async def synthesize(
        self,
        text: str,
        provider: Optional[TTSProvider] = None,
        voice: Optional[str] = None,
        speed: float = 1.0,
        use_cache: bool = True,
    ) -> TTSResult:
        """
        合成语音

        Args:
            text: 要合成的文本
            provider: TTS 提供商（None 则自动选择）
            voice: 语音 ID
            speed: 语速（0.5-2.0）
            use_cache: 是否使用缓存

        Returns:
            TTSResult: 包含音频数据的结果
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        # 选择提供商
        if provider is None:
            provider = self.get_default_provider()

        if provider not in self._providers:
            # 尝试降级
            available = list(self._providers.keys())
            if not available:
                raise RuntimeError("No TTS provider available")
            provider = available[0]
            logger.warning(
                "Requested provider not available, falling back",
                requested=provider,
                fallback=provider.value
            )

        # 配置
        config = TTSConfig(
            provider=provider,
            voice=voice or (TTSVoice.ALLOY.value if provider == TTSProvider.OPENAI else TTSVoice.XIAOXIAO.value),
            speed=max(0.5, min(2.0, speed)),
        )

        # 缓存检查
        if use_cache:
            cache_key = self._get_cache_key(text, config)
            cached = await self._get_cached(cache_key)
            if cached:
                logger.debug("TTS cache hit", cache_key=cache_key[:16])
                return cached

        # 合成
        provider_instance = self._providers[provider]
        result = await provider_instance.synthesize(text, config)

        # 缓存结果
        if use_cache:
            await self._set_cached(cache_key, result)

        logger.info(
            "TTS synthesis completed",
            provider=result.provider,
            voice=result.voice,
            text_length=result.text_length,
            audio_size=len(result.audio_data),
        )

        return result

    async def get_voices(self, provider: Optional[TTSProvider] = None) -> List[Dict[str, Any]]:
        """获取可用语音列表"""
        if provider:
            if provider not in self._providers:
                return []
            return await self._providers[provider].get_voices()

        # 返回所有提供商的语音
        all_voices = []
        for p, instance in self._providers.items():
            voices = await instance.get_voices()
            for v in voices:
                v["provider"] = p.value
            all_voices.extend(voices)
        return all_voices

    def _get_cache_key(self, text: str, config: TTSConfig) -> str:
        """生成缓存键"""
        content = f"{text}|{config.provider.value}|{config.voice}|{config.speed}"
        return hashlib.md5(content.encode()).hexdigest()

    async def _get_cached(self, cache_key: str) -> Optional[TTSResult]:
        """从缓存获取"""
        if not self._cache_dir:
            return None

        cache_file = self._cache_dir / f"{cache_key}.mp3"
        if cache_file.exists():
            try:
                audio_data = cache_file.read_bytes()
                return TTSResult(
                    audio_data=audio_data,
                    format="mp3",
                    provider="cache",
                    voice="",
                )
            except Exception:
                pass
        return None

    async def _set_cached(self, cache_key: str, result: TTSResult):
        """设置缓存"""
        if not self._cache_dir:
            return

        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self._cache_dir / f"{cache_key}.mp3"
            cache_file.write_bytes(result.audio_data)
        except Exception as e:
            logger.warning("Failed to cache TTS result", error=str(e))

    def set_cache_dir(self, path: str):
        """设置缓存目录"""
        self._cache_dir = Path(path)
        self._cache_dir.mkdir(parents=True, exist_ok=True)


# 单例实例
tts_service = TTSService()
