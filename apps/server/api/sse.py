import asyncio
import json
from typing import AsyncGenerator, Optional
from sse_starlette.sse import EventSourceResponse


class SSEManager:
    """SSE 事件管理器"""

    @staticmethod
    async def create_event(event_type: str, data: dict) -> str:
        return json.dumps({
            "event": event_type,
            "data": data
        })

    @staticmethod
    async def stream_events(generator: AsyncGenerator) -> EventSourceResponse:
        return EventSourceResponse(generator)

    @staticmethod
    async def stream_text_chunks(
        text: str,
        event_type: str = "text_chunk",
        chunk_size: int = 5,
        delay_ms: int = 20,
        metadata: Optional[dict] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        将文本分块为 SSE 事件流

        Args:
            text: 要流式发送的文本
            event_type: 事件类型
            chunk_size: 每个块的字符数
            delay_ms: 每个块之间的延迟（毫秒）
            metadata: 附加的元数据

        Yields:
            SSE 事件数据字典
        """
        total_length = len(text)
        sent_length = 0

        while sent_length < total_length:
            chunk = text[sent_length:sent_length + chunk_size]
            sent_length += len(chunk)

            yield {
                "event": event_type,
                "data": json.dumps({
                    "chunk": chunk,
                    "progress": round(sent_length / total_length * 100, 1),
                    "is_complete": sent_length >= total_length,
                    **(metadata or {})
                })
            }

            if delay_ms > 0 and sent_length < total_length:
                await asyncio.sleep(delay_ms / 1000)

        # 发送完成事件
        yield {
            "event": f"{event_type}_complete",
            "data": json.dumps({
                "total_length": total_length,
                **(metadata or {})
            })
        }


async def stream_text_as_sse(
    text: str,
    stage: str = "reasoning",
    chunk_size: int = 5,
    delay_ms: int = 15,
) -> AsyncGenerator[str, None]:
    """
    将文本流式输出为 SSE 格式的字符串

    Args:
        text: 要流式发送的文本
        stage: 当前阶段名称
        chunk_size: 每个块的字符数
        delay_ms: 每个块之间的延迟（毫秒）

    Yields:
        SSE 格式的事件字符串
    """
    total = len(text)
    sent = 0

    while sent < total:
        chunk = text[sent:sent + chunk_size]
        sent += len(chunk)

        event_data = {
            "event": "text_chunk",
            "data": {
                "stage": stage,
                "chunk": chunk,
                "progress": round(sent / total * 100, 1),
                "is_complete": sent >= total,
            }
        }
        yield f"data: {json.dumps(event_data)}\n\n"

        if delay_ms > 0 and sent < total:
            await asyncio.sleep(delay_ms / 1000)


sse_manager = SSEManager()
