"""Vision 分析服务

支持用户上传财报截图/K线图，通过 Vision 模型提取关键信息。
"""

import base64
import io
import json
import uuid
import asyncio
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = structlog.get_logger(__name__)

# 支持的图片格式
SUPPORTED_FORMATS = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class VisionService:
    """Vision 分析服务

    处理图片上传、压缩和 Vision 模型调用。
    """

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        """延迟创建支持 Vision 的 LLM"""
        if self._llm is not None:
            return self._llm

        from config.settings import settings

        # 优先使用支持 Vision 的模型
        if settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model="gpt-4o",
                api_key=settings.OPENAI_API_KEY,
                max_tokens=4096,
            )
        elif settings.GOOGLE_API_KEY:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.GOOGLE_API_KEY,
            )
        else:
            raise RuntimeError("No Vision-capable LLM API key configured (OPENAI_API_KEY or GOOGLE_API_KEY)")

        return self._llm

    async def analyze_image(
        self,
        image_data: bytes,
        content_type: str,
        description: str = "",
        symbol: str = "",
        file_name: Optional[str] = None,
        batch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分析上传的图片

        Args:
            image_data: 图片二进制数据
            content_type: MIME 类型
            description: 用户描述（可选）
            symbol: 关联的股票代码（可选）
            file_name: 原始文件名（可选）
            batch_id: 批量分析 ID（可选）

        Returns:
            分析结果字典
        """
        # 验证
        if content_type not in SUPPORTED_FORMATS:
            return {"error": f"Unsupported format: {content_type}. Supported: {', '.join(SUPPORTED_FORMATS)}"}

        if len(image_data) > MAX_FILE_SIZE:
            return {"error": f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB"}

        try:
            # 压缩图片
            processed_data, processed_type = self._process_image(image_data, content_type)

            # 编码为 base64
            b64_image = base64.b64encode(processed_data).decode("utf-8")

            # 构建 prompt
            prompt = self._build_analysis_prompt(description, symbol)

            # 调用 Vision 模型
            result = await self._call_vision_model(b64_image, processed_type, prompt)

            analysis_result = {
                "success": True,
                "symbol": symbol,
                "description": description,
                "analysis": result,
                "timestamp": datetime.now().isoformat(),
                "image_size": len(image_data),
                "processed_size": len(processed_data),
            }

            # 持久化到数据库
            record_id = self._persist_analysis(
                analysis_result, symbol, description, file_name, len(image_data), batch_id
            )
            if record_id:
                analysis_result["record_id"] = record_id

            return analysis_result

        except Exception as e:
            logger.error("Vision analysis failed", error=str(e), symbol=symbol)
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
            }

    def _persist_analysis(
        self,
        result: Dict[str, Any],
        symbol: str,
        description: str,
        file_name: Optional[str],
        file_size: int,
        batch_id: Optional[str] = None,
    ):
        """持久化分析结果到数据库"""
        try:
            from sqlmodel import Session
            from db.models import VisionAnalysisRecord, engine

            analysis = result.get("analysis", {})

            record = VisionAnalysisRecord(
                symbol=symbol or None,
                content_type="image",
                file_name=file_name,
                file_size=file_size,
                description=description or None,
                analysis_json=json.dumps(analysis, ensure_ascii=False),
                chart_type=analysis.get("chart_type"),
                confidence=analysis.get("confidence"),
                batch_id=batch_id,
            )

            with Session(engine) as session:
                session.add(record)
                session.commit()
                session.refresh(record)

            logger.info("Vision analysis persisted", id=record.id, symbol=symbol)
            return record.id

        except Exception as e:
            logger.warning("Failed to persist vision analysis", error=str(e))
            return None

    async def analyze_batch(
        self,
        files: List[Dict[str, Any]],
        description: str = "",
        symbol: str = "",
    ) -> Dict[str, Any]:
        """批量分析多张图片

        Args:
            files: 文件列表，每个元素包含 image_data, content_type, filename
            description: 共享的用户描述
            symbol: 关联股票代码

        Returns:
            批量分析结果
        """
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        semaphore = asyncio.Semaphore(3)  # 限制并发数

        async def analyze_one(file_info: Dict[str, Any], index: int):
            async with semaphore:
                result = await self.analyze_image(
                    image_data=file_info["image_data"],
                    content_type=file_info["content_type"],
                    description=description,
                    symbol=symbol,
                    file_name=file_info.get("filename"),
                    batch_id=batch_id,
                )
                result["index"] = index
                result["filename"] = file_info.get("filename", f"file_{index}")
                return result

        results = await asyncio.gather(
            *[analyze_one(f, i) for i, f in enumerate(files)],
            return_exceptions=True,
        )

        # 处理异常
        processed_results = []
        for r in results:
            if isinstance(r, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(r),
                })
            else:
                processed_results.append(r)

        successes = sum(1 for r in processed_results if r.get("success"))

        return {
            "batch_id": batch_id,
            "total": len(files),
            "successes": successes,
            "failures": len(files) - successes,
            "results": processed_results,
        }

    def _process_image(self, image_data: bytes, content_type: str) -> tuple:
        """处理和压缩图片

        Args:
            image_data: 原始图片数据
            content_type: MIME 类型

        Returns:
            (处理后的数据, MIME 类型)
        """
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_data))

            # 如果图片太大，缩放
            max_dimension = 2048
            if max(img.size) > max_dimension:
                ratio = max_dimension / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info("Image resized", original=f"{img.size}", new=f"{new_size}")

            # 转换为 JPEG 以减小体积（除非是 PNG 且需要透明度）
            output = io.BytesIO()
            if img.mode == "RGBA":
                img.save(output, format="PNG", optimize=True)
                return output.getvalue(), "image/png"
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                img.save(output, format="JPEG", quality=85, optimize=True)
                return output.getvalue(), "image/jpeg"

        except ImportError:
            logger.warning("Pillow not installed, using raw image")
            return image_data, content_type
        except Exception as e:
            logger.warning("Image processing failed, using raw", error=str(e))
            return image_data, content_type

    def _build_analysis_prompt(self, description: str, symbol: str) -> str:
        """构建 Vision 分析 prompt"""
        base_prompt = """你是一位专业的金融图表分析师。请仔细分析这张图片，并提供结构化的分析报告。

## 分析要求

### 1. 图表类型识别
- 识别图表类型（K线图、折线图、柱状图、饼图、财务报表截图等）
- 识别时间范围和数据频率

### 2. 关键数据提取
- 提取图表中的关键数值（价格、成交量、财务指标等）
- 识别重要的数据标注和文字信息

### 3. 趋势分析
- 判断整体趋势方向（上升/下降/横盘）
- 识别关键支撑位和阻力位
- 标注重要的形态特征（头肩顶、双底、三角形等）

### 4. 异常标注
- 标注异常数据点（放量、跳空、极端值等）
- 识别可能的信号（金叉、死叉、背离等）

### 5. 投资建议
- 基于图表分析给出简要的投资建议
- 标注风险因素

请用 JSON 格式输出分析结果，包含以下字段：
{
  "chart_type": "图表类型",
  "time_range": "时间范围",
  "key_data_points": [{"label": "标签", "value": "值"}],
  "trend": "Bullish/Bearish/Neutral",
  "trend_description": "趋势描述",
  "patterns": ["识别到的形态"],
  "support_levels": [价格],
  "resistance_levels": [价格],
  "anomalies": ["异常标注"],
  "signals": ["技术信号"],
  "summary": "综合分析摘要",
  "recommendation": "投资建议",
  "confidence": 0-100
}

输出语言：简体中文。"""

        if symbol:
            base_prompt += f"\n\n关联股票代码: {symbol}"

        if description:
            base_prompt += f"\n\n用户补充说明: {description}"

        return base_prompt

    async def _call_vision_model(
        self, b64_image: str, content_type: str, prompt: str
    ) -> Dict[str, Any]:
        """调用 Vision 模型分析图片"""
        from langchain_core.messages import HumanMessage

        llm = self._get_llm()

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{b64_image}",
                        "detail": "high",
                    },
                },
            ]
        )

        logger.info("Calling Vision model", content_type=content_type)
        response = await llm.ainvoke([message])

        # 尝试解析 JSON
        content = response.content
        try:
            import json
            import re

            # 尝试提取 JSON 块
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_match:
                return json.loads(json_match.group(1))

            # 尝试直接解析
            return json.loads(content)

        except (json.JSONDecodeError, AttributeError):
            # 无法解析为 JSON，返回原始文本
            return {
                "raw_analysis": content,
                "chart_type": "unknown",
                "summary": content[:500],
                "confidence": 50,
            }

    async def get_analysis_history(
        self,
        symbol: str = "",
        limit: int = 10,
        content_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取 Vision 分析历史

        Args:
            symbol: 筛选股票代码（可选）
            limit: 返回数量
            content_type: 筛选内容类型 image|audio（可选）

        Returns:
            历史分析记录列表
        """
        try:
            from sqlmodel import Session, select, col
            from db.models import VisionAnalysisRecord, engine

            with Session(engine) as session:
                stmt = select(VisionAnalysisRecord)

                if symbol:
                    stmt = stmt.where(VisionAnalysisRecord.symbol == symbol)
                if content_type:
                    stmt = stmt.where(VisionAnalysisRecord.content_type == content_type)

                stmt = (
                    stmt.order_by(col(VisionAnalysisRecord.created_at).desc())
                    .limit(limit)
                )

                records = session.exec(stmt).all()

            return [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "content_type": r.content_type,
                    "file_name": r.file_name,
                    "file_size": r.file_size,
                    "description": r.description,
                    "analysis": json.loads(r.analysis_json) if r.analysis_json else {},
                    "chart_type": r.chart_type,
                    "confidence": r.confidence,
                    "batch_id": r.batch_id,
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ]

        except Exception as e:
            logger.error("Failed to get vision analysis history", error=str(e))
            return []


# 单例
vision_service = VisionService()
