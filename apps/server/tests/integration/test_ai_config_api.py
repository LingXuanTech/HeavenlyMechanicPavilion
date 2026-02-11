"""AI 配置 API 集成测试。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from api.routes.system.ai_config import router as ai_config_router


def _create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(ai_config_router, prefix="/api")
    return TestClient(app)


class TestAIConfigRoutes:
    """校验 AI 配置路由的关键行为。"""

    def test_models_endpoint_returns_single_handler_payload(self):
        """/api/ai/models 应返回统一 schema：{"configs": [...]}。"""
        client = _create_test_client()

        mocked_configs = [
            {
                "config_key": "quick_think",
                "provider_id": 1,
                "provider_name": "OpenAI Official",
                "model_name": "gpt-4o-mini",
                "is_active": True,
                "updated_at": "2026-02-11T00:00:00",
            }
        ]

        with patch(
            "api.routes.system.ai_config.ai_config_service.get_model_configs",
            new=AsyncMock(return_value=mocked_configs),
        ):
            response = client.get("/api/ai/models")

        assert response.status_code == 200
        data = response.json()
        assert "configs" in data
        assert isinstance(data["configs"], list)
        assert data["configs"][0]["config_key"] == "quick_think"

    def test_test_provider_endpoint_has_single_behavior(self):
        """/api/ai/providers/{id}/test 应返回带 success 字段的统一结构。"""
        client = _create_test_client()

        mocked_result = {
            "success": True,
            "model": "gpt-4o-mini",
            "response_preview": "OK",
            "error": None,
        }

        with patch(
            "api.routes.system.ai_config.ai_config_service.test_provider",
            new=AsyncMock(return_value=mocked_result),
        ):
            response = client.post("/api/ai/providers/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["model"] == "gpt-4o-mini"
        assert "error" in data
