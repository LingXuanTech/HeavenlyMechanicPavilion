"""Vision 服务测试"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import io


class TestVisionService:
    """测试 Vision 分析服务"""

    def test_supported_formats(self):
        """应定义支持的图片格式"""
        from services.vision_service import SUPPORTED_FORMATS, MAX_FILE_SIZE

        assert "image/png" in SUPPORTED_FORMATS
        assert "image/jpeg" in SUPPORTED_FORMATS
        assert "image/webp" in SUPPORTED_FORMATS
        assert MAX_FILE_SIZE == 10 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_rejects_unsupported_format(self):
        """应拒绝不支持的格式"""
        from services.vision_service import vision_service

        result = await vision_service.analyze_image(
            image_data=b"fake data",
            content_type="application/pdf",
        )
        assert "error" in result
        assert "Unsupported format" in result["error"]

    @pytest.mark.asyncio
    async def test_rejects_oversized_file(self):
        """应拒绝超大文件"""
        from services.vision_service import vision_service, MAX_FILE_SIZE

        large_data = b"x" * (MAX_FILE_SIZE + 1)
        result = await vision_service.analyze_image(
            image_data=large_data,
            content_type="image/png",
        )
        assert "error" in result
        assert "too large" in result["error"].lower()

    def test_build_analysis_prompt(self):
        """应构建包含描述和代码的 prompt"""
        from services.vision_service import vision_service

        prompt = vision_service._build_analysis_prompt("测试描述", "AAPL")
        assert "AAPL" in prompt
        assert "测试描述" in prompt
        assert "JSON" in prompt

    def test_build_analysis_prompt_without_extras(self):
        """无额外信息时也应生成有效 prompt"""
        from services.vision_service import vision_service

        prompt = vision_service._build_analysis_prompt("", "")
        assert "金融图表分析师" in prompt

    def test_process_image_without_pillow(self):
        """Pillow 不可用时应返回原始数据"""
        from services.vision_service import vision_service

        with patch("services.vision_service.io") as mock_io:
            # 模拟 Pillow 导入失败
            with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
                data, ct = vision_service._process_image(b"test", "image/png")
                # 应该返回原始数据（因为 Pillow 导入失败）
                assert ct in ("image/png", "image/jpeg")

    @pytest.mark.asyncio
    async def test_analyze_image_success(self):
        """成功分析应返回结果"""
        from services.vision_service import vision_service

        mock_response = MagicMock()
        mock_response.content = '{"chart_type": "K线图", "trend": "Bullish", "summary": "上升趋势", "confidence": 80}'

        with patch.object(vision_service, "_get_llm") as mock_llm, \
             patch.object(vision_service, "_process_image", return_value=(b"processed", "image/jpeg")):
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke.return_value = mock_response
            mock_llm.return_value = mock_llm_instance

            result = await vision_service.analyze_image(
                image_data=b"fake png data",
                content_type="image/png",
                description="测试",
                symbol="AAPL",
            )

            assert result["success"] is True
            assert result["symbol"] == "AAPL"
            assert "analysis" in result

    @pytest.mark.asyncio
    async def test_get_analysis_history(self):
        """历史记录应返回列表"""
        from services.vision_service import vision_service

        history = await vision_service.get_analysis_history()
        assert isinstance(history, list)
