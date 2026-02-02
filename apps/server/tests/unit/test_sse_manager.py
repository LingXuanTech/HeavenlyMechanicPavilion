"""
SSE Manager 单元测试

覆盖:
1. SSEManager.create_event()
2. SSEManager.stream_text_chunks()
3. stream_text_as_sse() 函数
"""
import json
import pytest
import asyncio
from typing import List

from api.sse import SSEManager, stream_text_as_sse, sse_manager


# =============================================================================
# SSEManager.create_event 测试
# =============================================================================

class TestSSEManagerCreateEvent:
    """create_event 方法测试"""

    @pytest.mark.asyncio
    async def test_create_event_basic(self):
        """创建基础事件"""
        event = await SSEManager.create_event(
            event_type="test_event",
            data={"message": "Hello"}
        )

        parsed = json.loads(event)
        assert parsed["event"] == "test_event"
        assert parsed["data"]["message"] == "Hello"

    @pytest.mark.asyncio
    async def test_create_event_complex_data(self):
        """创建复杂数据事件"""
        data = {
            "stage": "analysis",
            "progress": 45.5,
            "details": {
                "analyst": "market",
                "status": "completed"
            },
            "items": [1, 2, 3]
        }

        event = await SSEManager.create_event("progress", data)

        parsed = json.loads(event)
        assert parsed["event"] == "progress"
        assert parsed["data"]["stage"] == "analysis"
        assert parsed["data"]["progress"] == 45.5
        assert parsed["data"]["details"]["analyst"] == "market"
        assert parsed["data"]["items"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_create_event_empty_data(self):
        """创建空数据事件"""
        event = await SSEManager.create_event("heartbeat", {})

        parsed = json.loads(event)
        assert parsed["event"] == "heartbeat"
        assert parsed["data"] == {}


# =============================================================================
# SSEManager.stream_text_chunks 测试
# =============================================================================

class TestSSEManagerStreamTextChunks:
    """stream_text_chunks 方法测试"""

    @pytest.mark.asyncio
    async def test_stream_short_text(self):
        """流式传输短文本"""
        text = "Hello"
        chunks = []

        async for chunk in SSEManager.stream_text_chunks(
            text,
            event_type="msg",
            chunk_size=2,
            delay_ms=0,
        ):
            chunks.append(chunk)

        # "Hello" 以 chunk_size=2 分割: "He", "ll", "o" + 完成事件 = 4 个
        assert len(chunks) == 4

        # 验证第一个块
        assert chunks[0]["event"] == "msg"
        data0 = json.loads(chunks[0]["data"])
        assert data0["chunk"] == "He"
        assert data0["progress"] == 40.0  # 2/5 * 100
        assert data0["is_complete"] is False

        # 验证最后一个数据块
        data2 = json.loads(chunks[2]["data"])
        assert data2["chunk"] == "o"
        assert data2["progress"] == 100.0
        assert data2["is_complete"] is True

        # 验证完成事件
        assert chunks[3]["event"] == "msg_complete"
        data3 = json.loads(chunks[3]["data"])
        assert data3["total_length"] == 5

    @pytest.mark.asyncio
    async def test_stream_with_metadata(self):
        """流式传输带元数据"""
        text = "Test"
        chunks = []

        async for chunk in SSEManager.stream_text_chunks(
            text,
            event_type="content",
            chunk_size=2,
            delay_ms=0,
            metadata={"stage": "reasoning", "task_id": "123"}
        ):
            chunks.append(chunk)

        # 验证元数据被包含
        data0 = json.loads(chunks[0]["data"])
        assert data0["stage"] == "reasoning"
        assert data0["task_id"] == "123"

        # 完成事件也包含元数据
        complete_data = json.loads(chunks[-1]["data"])
        assert complete_data["stage"] == "reasoning"
        assert complete_data["task_id"] == "123"

    @pytest.mark.asyncio
    async def test_stream_empty_text(self):
        """流式传输空文本"""
        text = ""
        chunks = []

        async for chunk in SSEManager.stream_text_chunks(
            text,
            chunk_size=5,
            delay_ms=0,
        ):
            chunks.append(chunk)

        # 只有完成事件
        assert len(chunks) == 1
        assert chunks[0]["event"] == "text_chunk_complete"

    @pytest.mark.asyncio
    async def test_stream_exact_chunk_size(self):
        """文本长度正好是 chunk_size 的倍数"""
        text = "ABCD"  # 4 字符，chunk_size=2
        chunks = []

        async for chunk in SSEManager.stream_text_chunks(
            text,
            chunk_size=2,
            delay_ms=0,
        ):
            chunks.append(chunk)

        # "AB", "CD", complete = 3
        assert len(chunks) == 3

        data0 = json.loads(chunks[0]["data"])
        assert data0["chunk"] == "AB"
        assert data0["progress"] == 50.0

        data1 = json.loads(chunks[1]["data"])
        assert data1["chunk"] == "CD"
        assert data1["progress"] == 100.0
        assert data1["is_complete"] is True

    @pytest.mark.asyncio
    async def test_stream_single_char_chunks(self):
        """逐字符流式传输"""
        text = "Hi"
        chunks = []

        async for chunk in SSEManager.stream_text_chunks(
            text,
            chunk_size=1,
            delay_ms=0,
        ):
            chunks.append(chunk)

        # "H", "i", complete = 3
        assert len(chunks) == 3

        data0 = json.loads(chunks[0]["data"])
        assert data0["chunk"] == "H"

        data1 = json.loads(chunks[1]["data"])
        assert data1["chunk"] == "i"

    @pytest.mark.asyncio
    async def test_stream_unicode_text(self):
        """流式传输 Unicode 文本"""
        text = "你好世界"  # 4 个中文字符
        chunks = []

        async for chunk in SSEManager.stream_text_chunks(
            text,
            chunk_size=2,
            delay_ms=0,
        ):
            chunks.append(chunk)

        # "你好", "世界", complete = 3
        assert len(chunks) == 3

        data0 = json.loads(chunks[0]["data"])
        assert data0["chunk"] == "你好"

        data1 = json.loads(chunks[1]["data"])
        assert data1["chunk"] == "世界"


# =============================================================================
# stream_text_as_sse 函数测试
# =============================================================================

class TestStreamTextAsSSE:
    """stream_text_as_sse 函数测试"""

    @pytest.mark.asyncio
    async def test_stream_format(self):
        """验证 SSE 格式"""
        text = "Test"
        events = []

        async for event in stream_text_as_sse(
            text,
            stage="test_stage",
            chunk_size=2,
            delay_ms=0,
        ):
            events.append(event)

        # 验证格式: "data: {json}\n\n"
        for event in events:
            assert event.startswith("data: ")
            assert event.endswith("\n\n")

        # 解析第一个事件
        json_str = events[0][6:-2]  # 去掉 "data: " 和 "\n\n"
        parsed = json.loads(json_str)
        assert parsed["event"] == "text_chunk"
        assert parsed["data"]["stage"] == "test_stage"
        assert parsed["data"]["chunk"] == "Te"

    @pytest.mark.asyncio
    async def test_stream_progress_calculation(self):
        """验证进度计算"""
        text = "ABCDE"  # 5 字符
        events = []

        async for event in stream_text_as_sse(
            text,
            chunk_size=1,
            delay_ms=0,
        ):
            events.append(event)

        # 5 个块
        assert len(events) == 5

        # 检查进度
        expected_progress = [20.0, 40.0, 60.0, 80.0, 100.0]
        for i, event in enumerate(events):
            json_str = event[6:-2]
            parsed = json.loads(json_str)
            assert parsed["data"]["progress"] == expected_progress[i]

    @pytest.mark.asyncio
    async def test_stream_is_complete_flag(self):
        """验证 is_complete 标志"""
        text = "AB"
        events = []

        async for event in stream_text_as_sse(
            text,
            chunk_size=1,
            delay_ms=0,
        ):
            events.append(event)

        # 第一个块不完成
        json1 = json.loads(events[0][6:-2])
        assert json1["data"]["is_complete"] is False

        # 最后一个块完成
        json2 = json.loads(events[1][6:-2])
        assert json2["data"]["is_complete"] is True

    @pytest.mark.asyncio
    async def test_stream_custom_stage(self):
        """自定义 stage 参数"""
        text = "X"
        events = []

        async for event in stream_text_as_sse(
            text,
            stage="custom_stage",
            chunk_size=1,
            delay_ms=0,
        ):
            events.append(event)

        parsed = json.loads(events[0][6:-2])
        assert parsed["data"]["stage"] == "custom_stage"

    @pytest.mark.asyncio
    async def test_stream_default_stage(self):
        """默认 stage 为 'reasoning'"""
        text = "X"
        events = []

        async for event in stream_text_as_sse(
            text,
            chunk_size=1,
            delay_ms=0,
        ):
            events.append(event)

        parsed = json.loads(events[0][6:-2])
        assert parsed["data"]["stage"] == "reasoning"


# =============================================================================
# 全局单例测试
# =============================================================================

class TestSSEManagerSingleton:
    """sse_manager 单例测试"""

    def test_singleton_exists(self):
        """全局单例存在"""
        assert sse_manager is not None
        assert isinstance(sse_manager, SSEManager)


# =============================================================================
# 延迟测试
# =============================================================================

class TestStreamDelay:
    """流式传输延迟测试"""

    @pytest.mark.asyncio
    async def test_delay_applied(self):
        """验证延迟被应用"""
        text = "ABC"
        start_time = asyncio.get_event_loop().time()

        events = []
        async for event in stream_text_as_sse(
            text,
            chunk_size=1,
            delay_ms=50,  # 50ms 延迟
        ):
            events.append(event)

        elapsed = asyncio.get_event_loop().time() - start_time

        # 3 个块，2 次延迟（最后一个块后不延迟）
        # 期望至少 100ms (2 * 50ms)
        assert elapsed >= 0.08  # 留一点余量

    @pytest.mark.asyncio
    async def test_no_delay_last_chunk(self):
        """最后一个块后无延迟"""
        text = "AB"
        start_time = asyncio.get_event_loop().time()

        events = []
        async for event in stream_text_as_sse(
            text,
            chunk_size=1,
            delay_ms=100,  # 100ms 延迟
        ):
            events.append(event)

        elapsed = asyncio.get_event_loop().time() - start_time

        # 2 个块，只有 1 次延迟（第一个块后）
        # 期望大约 100ms，而非 200ms
        assert elapsed < 0.2

    @pytest.mark.asyncio
    async def test_zero_delay(self):
        """零延迟快速完成"""
        text = "ABCDEFGHIJ"  # 10 字符
        start_time = asyncio.get_event_loop().time()

        events = []
        async for event in stream_text_as_sse(
            text,
            chunk_size=1,
            delay_ms=0,
        ):
            events.append(event)

        elapsed = asyncio.get_event_loop().time() - start_time

        # 应该几乎立即完成
        assert elapsed < 0.1
        assert len(events) == 10
