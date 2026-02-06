"""
Analyze API 集成测试

测试内容：
1. POST /analyze/{symbol} - 触发分析任务
2. GET /analyze/stream/{task_id} - SSE 流式进度（简化测试）
3. GET /analyze/latest/{symbol} - 获取最新分析
4. GET /analyze/history/{symbol} - 获取历史记录
5. GET /analyze/status/{task_id} - 查询任务状态
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, date

from db.models import AnalysisResult


class TestTriggerAnalysis:
    """测试触发分析任务"""

    def test_trigger_analysis_returns_task_id(self, client):
        """成功触发分析任务返回 task_id"""
        # Mock 背景任务，不实际执行分析
        with patch("api.routes.analyze.run_analysis_task"):
            response = client.post("/api/analyze/AAPL")

            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["symbol"] == "AAPL"
            assert data["status"] == "accepted"
            assert data["task_id"].startswith("task_AAPL_")

    def test_trigger_analysis_with_custom_date(self, client):
        """指定日期触发分析"""
        with patch("api.routes.analyze.run_analysis_task"):
            response = client.post("/api/analyze/AAPL?trade_date=2026-01-15")

            assert response.status_code == 200

    def test_trigger_analysis_cn_stock(self, client):
        """触发 A 股分析"""
        with patch("api.routes.analyze.run_analysis_task"):
            response = client.post("/api/analyze/600519.SH")

            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "600519.SH"


class TestGetLatestAnalysis:
    """测试获取最新分析结果"""

    def test_get_latest_analysis_success(self, client, db_session):
        """成功获取最新分析结果"""
        # 添加测试数据
        analysis = AnalysisResult(
            symbol="AAPL",
            date="2026-01-28",
            signal="Strong Buy",
            confidence=85,
            full_report_json=json.dumps({
                "signal": "Strong Buy",
                "confidence": 85,
                "summary": "Test analysis",
            }),
            anchor_script="Test anchor script",
            task_id="test-task-123",
            status="completed",
            elapsed_seconds=45.2,
        )
        db_session.add(analysis)
        db_session.commit()

        response = client.get("/api/analyze/latest/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["signal"] == "Strong Buy"
        assert data["confidence"] == 85
        assert "full_report" in data
        assert data["full_report"]["summary"] == "Test analysis"

    def test_get_latest_analysis_not_found(self, client):
        """股票无分析记录返回 404"""
        response = client.get("/api/analyze/latest/NONEXISTENT")

        assert response.status_code == 404

    def test_get_latest_analysis_excludes_failed(self, client, db_session):
        """只返回完成的分析，排除失败的"""
        # 添加一条失败的记录
        failed = AnalysisResult(
            symbol="AAPL",
            date="2026-01-28",
            signal="Error",
            confidence=0,
            full_report_json="{}",
            anchor_script="",
            task_id="failed-task",
            status="failed",
            error_message="Test error",
        )
        db_session.add(failed)
        db_session.commit()

        response = client.get("/api/analyze/latest/AAPL")

        assert response.status_code == 404


class TestGetAnalysisHistory:
    """测试获取历史分析记录"""

    def test_get_history_success(self, client, db_session):
        """成功获取历史记录"""
        # 添加多条测试数据
        for i in range(5):
            analysis = AnalysisResult(
                symbol="AAPL",
                date=f"2026-01-{20 + i:02d}",
                signal="Buy" if i % 2 == 0 else "Hold",
                confidence=70 + i * 5,
                full_report_json="{}",
                anchor_script="",
                task_id=f"task-{i}",
                status="completed",
            )
            db_session.add(analysis)
        db_session.commit()

        response = client.get("/api/analyze/history/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 5
        assert data["offset"] == 0
        assert data["limit"] == 10
        # 验证按创建时间降序排列
        assert all("date" in item for item in data["items"])

    def test_get_history_with_limit(self, client, db_session):
        """限制返回数量"""
        for i in range(10):
            analysis = AnalysisResult(
                symbol="AAPL",
                date=f"2026-01-{10 + i:02d}",
                signal="Buy",
                confidence=75,
                full_report_json="{}",
                anchor_script="",
                task_id=f"task-{i}",
                status="completed",
            )
            db_session.add(analysis)
        db_session.commit()

        response = client.get("/api/analyze/history/AAPL?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 10
        assert data["limit"] == 3

    def test_get_history_empty(self, client):
        """无历史记录返回空数组"""
        response = client.get("/api/analyze/history/NEWSTOCK")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_history_includes_failed(self, client, db_session):
        """历史记录包含失败的任务"""
        # 添加一条成功和一条失败的
        success = AnalysisResult(
            symbol="AAPL",
            date="2026-01-28",
            signal="Buy",
            confidence=80,
            full_report_json="{}",
            anchor_script="",
            task_id="success-task",
            status="completed",
        )
        failed = AnalysisResult(
            symbol="AAPL",
            date="2026-01-27",
            signal="Error",
            confidence=0,
            full_report_json="{}",
            anchor_script="",
            task_id="failed-task",
            status="failed",
        )
        db_session.add(success)
        db_session.add(failed)
        db_session.commit()

        response = client.get("/api/analyze/history/AAPL")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        statuses = [item["status"] for item in data["items"]]
        assert "completed" in statuses
        assert "failed" in statuses


class TestGetTaskStatus:
    """测试查询任务状态"""

    def test_get_status_from_cache(self, client):
        """从缓存中获取正在运行的任务状态"""
        import asyncio
        from services.cache_service import cache_service

        # 通过 cache_service 设置任务状态
        asyncio.get_event_loop().run_until_complete(
            cache_service.set_task("test-task-cache", {"status": "running", "symbol": "AAPL", "progress": 50})
        )

        try:
            response = client.get("/api/analyze/status/test-task-cache")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-cache"
            assert data["status"] == "running"
            assert data["source"] == "cache"
        finally:
            asyncio.get_event_loop().run_until_complete(
                cache_service.delete_task("test-task-cache")
            )

    def test_get_status_from_database(self, client, db_session):
        """从数据库获取已完成任务状态"""
        analysis = AnalysisResult(
            symbol="AAPL",
            date="2026-01-28",
            signal="Buy",
            confidence=80,
            full_report_json="{}",
            anchor_script="",
            task_id="test-task-db",
            status="completed",
        )
        db_session.add(analysis)
        db_session.commit()

        response = client.get("/api/analyze/status/test-task-db")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-db"
        assert data["status"] == "completed"
        assert data["source"] == "database"
        assert data["symbol"] == "AAPL"

    def test_get_status_not_found(self, client):
        """任务不存在返回 404"""
        response = client.get("/api/analyze/status/nonexistent-task")

        assert response.status_code == 404


class TestSSEStream:
    """测试 SSE 流式接口"""

    def test_stream_not_found_task(self, client):
        """不存在的任务返回 404"""
        response = client.get("/api/analyze/stream/nonexistent-task")
        assert response.status_code == 404

    def test_stream_existing_task_with_events(self, client):
        """存在的任务可以连接 SSE 并接收事件"""
        import asyncio
        from services.cache_service import cache_service

        task_id = "test-sse-task-001"

        # 设置任务状态和 SSE 事件
        async def setup_sse_events():
            # 初始化 SSE 任务
            await cache_service.init_sse_task(task_id, "AAPL")

            # 推送模拟的分析阶段事件
            await cache_service.push_sse_event(task_id, "stage_analyst", {
                "node": "Market Analyst",
                "stage": "stage_analyst",
                "status": "completed",
                "message": "Market analyst completed"
            })
            await cache_service.push_sse_event(task_id, "stage_analyst", {
                "node": "News Analyst",
                "stage": "stage_analyst",
                "status": "completed",
                "message": "News analyst completed"
            })
            await cache_service.push_sse_event(task_id, "stage_debate", {
                "node": "Bull Researcher",
                "stage": "stage_debate",
                "status": "completed",
                "message": "Bull researcher completed"
            })
            await cache_service.push_sse_event(task_id, "stage_risk", {
                "node": "Risk Judge",
                "stage": "stage_risk",
                "status": "completed",
                "message": "Risk assessment completed"
            })
            await cache_service.push_sse_event(task_id, "stage_final", {
                "signal": "Strong Buy",
                "confidence": 78,
                "summary": "Test analysis completed"
            })

            # 设置任务完成状态
            await cache_service.set_sse_status(task_id, "completed")

        asyncio.get_event_loop().run_until_complete(setup_sse_events())

        try:
            # 请求 SSE 流
            response = client.get(f"/api/analyze/stream/{task_id}")

            # 验证响应状态
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")

            # 解析 SSE 事件
            events = []
            for line in response.iter_lines():
                if line:
                    line_str = line.decode() if isinstance(line, bytes) else line
                    if line_str.startswith("data:"):
                        event_data = json.loads(line_str[5:].strip())
                        events.append(event_data)

            # 验证收到了预期的事件
            assert len(events) >= 5

            # 验证事件序列包含各阶段
            stages = [e.get("stage") for e in events if "stage" in e]
            assert "stage_analyst" in stages
            assert "stage_debate" in stages
            assert "stage_risk" in stages

        finally:
            # 清理测试数据
            asyncio.get_event_loop().run_until_complete(
                cache_service.cleanup_sse_task(task_id)
            )
            asyncio.get_event_loop().run_until_complete(
                cache_service.delete_task(task_id)
            )

    def test_stream_event_format(self, client):
        """验证 SSE 事件格式正确"""
        import asyncio
        from services.cache_service import cache_service

        task_id = "test-sse-format-001"

        async def setup_events():
            await cache_service.init_sse_task(task_id, "TSLA")
            await cache_service.push_sse_event(task_id, "stage_analyst", {
                "node": "Macro Analyst",
                "stage": "stage_analyst",
                "status": "completed",
                "message": "Macro analyst completed",
                "payload": {"market_report": "Test macro report content"}
            })
            await cache_service.set_sse_status(task_id, "completed")

        asyncio.get_event_loop().run_until_complete(setup_events())

        try:
            response = client.get(f"/api/analyze/stream/{task_id}")
            assert response.status_code == 200

            # 解析第一个事件
            for line in response.iter_lines():
                if line:
                    line_str = line.decode() if isinstance(line, bytes) else line
                    if line_str.startswith("data:"):
                        event_data = json.loads(line_str[5:].strip())
                        # 验证事件格式
                        assert "node" in event_data or "signal" in event_data
                        if "node" in event_data:
                            assert "stage" in event_data
                            assert "status" in event_data
                        break

        finally:
            asyncio.get_event_loop().run_until_complete(
                cache_service.cleanup_sse_task(task_id)
            )


class TestAnalysisIntegration:
    """端到端集成测试（需要 Mock LLM）"""

    @pytest.mark.asyncio
    async def test_full_analysis_flow_mocked(self, async_client, db_session):
        """完整分析流程（Mock LLM）"""
        from tests.fixtures.mock_llm_responses import get_sample_synthesized_analysis

        # Mock TradingAgentsGraph 和相关依赖
        mock_analysis_result = get_sample_synthesized_analysis()

        with patch("api.routes.analysis.analyze.TradingAgentsGraph") as mock_graph_class, \
             patch("api.routes.analysis.analyze.synthesizer") as mock_synthesizer, \
             patch("api.routes.analysis.analyze.memory_service") as mock_memory, \
             patch("api.routes.analysis.analyze.accuracy_tracker") as mock_tracker, \
             patch("api.routes.analysis.analyze.layered_memory") as mock_layered:

            # 配置 mock
            mock_memory.is_available.return_value = False

            # Mock synthesizer 返回预设结果
            mock_synthesizer.synthesize = AsyncMock(return_value=mock_analysis_result)

            # Mock accuracy_tracker
            mock_tracker.record_prediction = AsyncMock()

            # Mock layered_memory
            mock_layered.store_layered_analysis = AsyncMock()

            # Mock graph 执行
            mock_graph_instance = MagicMock()
            mock_graph_class.return_value = mock_graph_instance

            # 模拟 graph.stream 返回的迭代器
            def mock_stream(*args, **kwargs):
                yield {"Market Analyst": {"market_report": "Test market report"}}
                yield {"News Analyst": {"news_report": "Test news report"}}
                yield {"Bull Researcher": {"bull_report": "Test bull case"}}
                yield {"Bear Researcher": {"bear_report": "Test bear case"}}
                yield {"Risk Judge": {"risk_report": "Test risk assessment"}}
                yield {"Trader": {"final_decision": "Buy"}}

            mock_graph_instance.graph.stream = mock_stream
            mock_graph_instance.propagator.create_initial_state.return_value = {}
            mock_graph_instance.propagator.get_graph_args.return_value = {}

            # 触发分析
            response = await async_client.post("/api/analyze/AAPL")

            assert response.status_code == 200
            data = response.json()

            # 验证返回的 task_id 格式
            assert "task_id" in data
            assert data["task_id"].startswith("task_AAPL_")
            assert data["symbol"] == "AAPL"
            assert data["status"] == "accepted"

            # 验证分析师配置
            assert "analysts" in data
            assert isinstance(data["analysts"], list)

    def test_trigger_analysis_with_custom_analysts(self, client):
        """测试自定义分析师配置"""
        with patch("api.routes.analysis.analyze.run_analysis_task"):
            # 指定特定分析师
            response = client.post(
                "/api/analyze/AAPL",
                json={
                    "analysts": ["market", "news", "macro"],
                    "analysis_level": "L1",
                    "use_planner": False
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["analysis_level"] == "L1"
            assert data["use_planner"] == False
            assert set(data["analysts"]) == {"market", "news", "macro"}

    def test_trigger_analysis_with_exclude_analysts(self, client):
        """测试排除分析师配置"""
        with patch("api.routes.analysis.analyze.run_analysis_task"):
            response = client.post(
                "/api/analyze/600519.SH",
                json={
                    "exclude_analysts": ["social"],
                    "analysis_level": "L2"
                }
            )

            assert response.status_code == 200
            data = response.json()
            # 验证 social 分析师被排除
            assert "social" not in data["analysts"]

    def test_quick_scan_endpoint(self, client):
        """测试快速扫描端点"""
        with patch("api.routes.analysis.analyze.run_analysis_task"):
            response = client.post("/api/analyze/quick/MSFT")

            assert response.status_code == 200
            data = response.json()
            assert data["analysis_level"] == "L1"
            assert data["task_id"].startswith("quick_MSFT_")
            assert set(data["analysts"]) == {"market", "news", "macro"}
            assert "estimated_time_seconds" in data

    def test_task_status_transitions(self, client, db_session):
        """测试任务状态转换"""
        import asyncio
        from services.cache_service import cache_service

        task_id = "test-status-transition-001"

        # 设置初始状态为 running
        asyncio.get_event_loop().run_until_complete(
            cache_service.set_task(task_id, {"status": "running", "symbol": "GOOG", "progress": 25})
        )

        try:
            # 查询 running 状态
            response = client.get(f"/api/analyze/status/{task_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "running"

            # 更新为 completed
            asyncio.get_event_loop().run_until_complete(
                cache_service.set_task(task_id, {"status": "completed", "symbol": "GOOG"})
            )

            response = client.get(f"/api/analyze/status/{task_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

        finally:
            asyncio.get_event_loop().run_until_complete(
                cache_service.delete_task(task_id)
            )


class TestAnalysisEdgeCases:
    """边缘情况测试"""

    def test_special_characters_in_symbol(self, client):
        """带特殊字符的股票代码"""
        with patch("api.routes.analyze.run_analysis_task"):
            response = client.post("/api/analyze/600519.SH")
            assert response.status_code == 200

            response = client.post("/api/analyze/0700.HK")
            assert response.status_code == 200

    def test_limit_validation(self, client):
        """历史记录 limit 参数验证"""
        # 超过最大值
        response = client.get("/api/analyze/history/AAPL?limit=101")
        assert response.status_code == 422  # Validation error

        # 小于最小值
        response = client.get("/api/analyze/history/AAPL?limit=0")
        assert response.status_code == 422

        # 有效值
        response = client.get("/api/analyze/history/AAPL?limit=50")
        assert response.status_code == 200
