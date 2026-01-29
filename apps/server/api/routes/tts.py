"""
TTS 语音合成 API 路由

提供文本转语音功能：
- POST /api/tts/synthesize - 合成语音
- GET /api/tts/voices - 获取可用语音列表
- GET /api/tts/status - 获取服务状态
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
import structlog

from services.tts_service import tts_service, TTSProvider, TTSResult

router = APIRouter(prefix="/tts", tags=["TTS"])
logger = structlog.get_logger()


class TTSSynthesizeRequest(BaseModel):
    """TTS 合成请求"""
    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    provider: Optional[str] = Field(None, description="TTS 提供商: openai, gemini, edge")
    voice: Optional[str] = Field(None, description="语音 ID")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="语速 (0.5-2.0)")
    use_cache: bool = Field(True, description="是否使用缓存")


class TTSVoiceInfo(BaseModel):
    """语音信息"""
    id: str
    name: str
    language: str
    gender: str
    provider: Optional[str] = None


class TTSStatusResponse(BaseModel):
    """TTS 状态响应"""
    available: bool
    providers: List[str]
    default_provider: Optional[str]


@router.post("/synthesize", summary="合成语音")
async def synthesize(request: TTSSynthesizeRequest):
    """
    将文本合成为语音

    返回 MP3 格式的音频数据
    """
    try:
        # 解析提供商
        provider = None
        if request.provider:
            try:
                provider = TTSProvider(request.provider.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {request.provider}. Available: {tts_service.get_available_providers()}"
                )

        # 合成
        result = await tts_service.synthesize(
            text=request.text,
            provider=provider,
            voice=request.voice,
            speed=request.speed,
            use_cache=request.use_cache,
        )

        # 返回音频数据
        return Response(
            content=result.audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "X-TTS-Provider": result.provider,
                "X-TTS-Voice": result.voice,
                "X-TTS-Text-Length": str(result.text_length),
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("TTS synthesis failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.get("/voices", response_model=List[TTSVoiceInfo], summary="获取可用语音列表")
async def get_voices(
    provider: Optional[str] = Query(None, description="筛选特定提供商的语音")
):
    """
    获取可用的语音列表

    可以按提供商筛选
    """
    try:
        p = None
        if provider:
            try:
                p = TTSProvider(provider.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {provider}"
                )

        voices = await tts_service.get_voices(p)
        return voices

    except Exception as e:
        logger.error("Failed to get voices", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=TTSStatusResponse, summary="获取服务状态")
async def get_status():
    """
    获取 TTS 服务状态

    包括可用的提供商和默认提供商
    """
    providers = tts_service.get_available_providers()
    default_provider = None

    if providers:
        try:
            default_provider = tts_service.get_default_provider().value
        except RuntimeError:
            pass

    return TTSStatusResponse(
        available=len(providers) > 0,
        providers=providers,
        default_provider=default_provider,
    )


@router.post("/briefing/{symbol}", summary="生成股票播报")
async def generate_briefing(
    symbol: str,
    voice: Optional[str] = Query(None, description="语音 ID"),
    speed: float = Query(1.0, ge=0.5, le=2.0, description="语速"),
):
    """
    根据股票分析结果生成语音播报

    自动获取最新分析结果并生成 TTS 播报
    """
    from sqlmodel import Session, select
    from db.models import AnalysisResult, engine

    try:
        # 获取最新分析结果
        with Session(engine) as session:
            statement = (
                select(AnalysisResult)
                .where(AnalysisResult.symbol == symbol.upper())
                .order_by(AnalysisResult.created_at.desc())
                .limit(1)
            )
            result = session.exec(statement).first()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail=f"No analysis found for {symbol}"
                )

            # 使用存储的 anchor_script 或生成默认脚本
            if result.anchor_script:
                script = result.anchor_script
            else:
                # 生成简单的播报脚本
                signal = result.signal or "Hold"
                confidence = result.confidence or 50
                reasoning_summary = (result.reasoning or "")[:200]

                script = f"""
                {symbol} 分析播报。
                信号：{signal}，置信度 {confidence}%。
                {reasoning_summary}
                """

        # 合成语音
        tts_result = await tts_service.synthesize(
            text=script.strip(),
            voice=voice,
            speed=speed,
        )

        return Response(
            content=tts_result.audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename={symbol}_briefing.mp3",
                "X-TTS-Provider": tts_result.provider,
                "X-TTS-Voice": tts_result.voice,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate briefing", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
