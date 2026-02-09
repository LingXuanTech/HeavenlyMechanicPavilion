"""Vision 分析路由

提供图片上传和 Vision 分析的 API 端点。
"""

import structlog
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from typing import Optional, List

from api.schemas.vision import VisionAnalysisResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/vision", tags=["Vision Analysis"])


@router.post("/analyze", response_model=VisionAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(..., description="图片文件（PNG/JPG/WebP）"),
    description: str = Form("", description="用户描述（可选）"),
    symbol: str = Form("", description="关联股票代码（可选）"),
):
    """上传图片并进行 Vision 分析

    支持财报截图、K线图、技术指标图等金融图表的智能识别和分析。

    - **file**: 图片文件（支持 PNG、JPG、WebP、GIF，最大 10MB）
    - **description**: 用户对图片的补充说明
    - **symbol**: 关联的股票代码（用于上下文增强）
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Missing content type")

    from services.vision_service import vision_service, SUPPORTED_FORMATS

    if file.content_type not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {file.content_type}. Supported: {', '.join(SUPPORTED_FORMATS)}",
        )

    # 读取文件内容
    image_data = await file.read()

    if len(image_data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    logger.info(
        "Vision analysis requested",
        filename=file.filename,
        content_type=file.content_type,
        size=len(image_data),
        symbol=symbol,
    )

    result = await vision_service.analyze_image(
        image_data=image_data,
        content_type=file.content_type,
        description=description,
        symbol=symbol,
        file_name=file.filename,
    )

    if not result.get("success") and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@router.post("/analyze-batch")
async def analyze_batch(
    files: List[UploadFile] = File(..., description="多个图片文件"),
    description: str = Form("", description="共享的用户描述"),
    symbol: str = Form("", description="关联股票代码"),
):
    """批量上传图片进行 Vision 分析

    支持同时上传多张图片，并行分析（最大并发 3）。
    所有图片共享同一个 batch_id。

    - **files**: 多个图片文件
    - **description**: 共享的用户描述
    - **symbol**: 关联的股票代码
    """
    from services.vision_service import vision_service, SUPPORTED_FORMATS

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    # 预处理文件
    file_infos = []
    for f in files:
        if not f.content_type or f.content_type not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format for {f.filename}: {f.content_type}",
            )
        data = await f.read()
        if len(data) == 0:
            continue
        file_infos.append({
            "image_data": data,
            "content_type": f.content_type,
            "filename": f.filename,
        })

    if not file_infos:
        raise HTTPException(status_code=400, detail="All files are empty")

    logger.info("Batch vision analysis requested", count=len(file_infos), symbol=symbol)

    result = await vision_service.analyze_batch(
        files=file_infos,
        description=description,
        symbol=symbol,
    )

    return result


@router.get("/history")
async def get_vision_history(
    symbol: Optional[str] = None,
    content_type: Optional[str] = Query(None, description="筛选内容类型: image | audio"),
    limit: int = Query(default=10, ge=1, le=100),
):
    """获取 Vision 分析历史记录

    Args:
        symbol: 筛选股票代码（可选）
        content_type: 筛选内容类型（可选）
        limit: 返回数量
    """
    from services.vision_service import vision_service

    history = await vision_service.get_analysis_history(
        symbol=symbol or "", limit=limit, content_type=content_type
    )
    return {"history": history, "total": len(history)}
