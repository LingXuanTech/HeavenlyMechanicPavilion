
# 任务 1.1 实施指南：事件历史持久化到数据库

## 📋 概述

本文档说明如何将新创建的事件持久化功能集成到现有系统中。

## ✅ 已完成的工作

### 1. 数据库模型
✅ **文件**: `packages/backend/app/db/models/session_event.py`
- 创建了 `SessionEvent` 模型
- 包含所有必要字段：id, session_id, event_type, message, payload, sequence_number, timestamp
- 添加了复合索引以优化查询性能

### 2. 数据访问层
✅ **文件**: `packages/backend/app/repositories/session_event.py`
- 实现了 `SessionEventRepository`
- 提供了以下方法：
  - `get_by_session()` - 分页查询会话事件
  - `get_by_session_and_type()` - 按类型过滤
  - `count_by_session()` - 统计事件总数
  - `get_next_sequence_number()` - 获取下一个序列号
  - `bulk_create()` - 批量创建事件
  - `delete_by_session()` - 删除会话事件

### 3. 增强的事件管理器
✅ **文件**: `packages/backend/app/services/events_enhanced.py`
- 创建了 `EnhancedSessionEventManager`
- 保持向后兼容性（内存缓冲 + 数据库持久化）
- 异步、非阻塞的数据库写入
- 线程安全操作

### 4. 增强的 API 端点
✅ **文件**: `packages/backend/app/api/streams_enhanced.py`
- 扩展了事件历史端点，支持分页
- 添加了数据源选择（db 或 memory）
- 支持事件类型过滤
- 添加了删除事件端点

### 5. 数据库迁移
✅ **文件**: `packages/backend/alembic/versions/add_session_events_table.py`
- 创建 `session_events` 表
- 添加所有必要的索引
- 提供了 upgrade 和 downgrade 方法

## 🔧 集成步骤

### 步骤 1: 更新数据库模型导入

编辑 `packages/backend/app/db/models/__init__.py`：

```python
# 添加新模型导入
from .session_event import SessionEvent

# 更新 __all__
__all__ = [
    # ... 现有模型 ...
    "SessionEvent",
]
```

### 步骤 2: 更新仓储层导入

编辑 `packages/backend/app/repositories/__init__.py`：

```python
# 添加新仓储导入
from .session_event import SessionEventRepository

# 更新 __all__
__all__ = [
    # ... 现有仓储 ...
    "SessionEventRepository",
]
```

### 步骤 3: 运行数据库迁移

```bash
cd packages/backend

# 检查迁移状态
alembic current

# 更新迁移脚本中的 down_revision
# 编辑 alembic/versions/add_session_events_table.py
# 将 down_revision = None 改为最新的迁移 ID

# 运行迁移
alembic upgrade head

# 验证表已创建
# PostgreSQL:
psql -d tradingagents -c "\d session_events"

# SQLite:
sqlite3 data/tradingagents.db ".schema session_events"
```

### 步骤 4: 更新依赖注入

编辑 `packages/backend/app/dependencies/__init__.py`：

```python
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from ..services.events_enhanced import EnhancedSessionEventManager
from ..db.database import get_db

# 创建数据库会话工厂
@asynccontextmanager
async def get_db_session():
    async with get_db() as session:
        yield session

# 更新或创建事件管理器依赖
def get_enhanced_event_manager() -> EnhancedSessionEventManager:
    """Get enhanced event manager with database persistence."""
    return EnhancedSessionEventManager(
        db_session_factory=get_db_session,
        max_buffer_size=100,
        persist_to_db=True,
    )

# 为了向后兼容，保留原有的 get_event_manager
# 但让它返回增强版本
def get_event_manager():
    """Backward compatible event manager getter."""
    return get_enhanced_event_manager()
```

### 步骤 5: 更新路由注册

编辑 `packages/backend/app/main.py` 或路由配置文件：

```python
from .api import streams_enhanced

# 方案 A: 替换现有路由（推荐）
app.include_router(
    streams_enhanced.router,
    prefix="/api/sessions",
    tags=["sessions", "streaming"],
)

# 方案 B: 同时保留旧路由（用于渐进式迁移）
from .api import streams, streams_enhanced

app.include_router(
    streams.router,
    prefix="/api/sessions",
    tags=["sessions", "streaming-legacy"],
)

app.include_router(
    streams_enhanced.router,
    prefix="/api/v2/sessions",
    tags=["sessions", "streaming-v2"],
)
```

### 步骤 6: 更新事件发布调用

在 `TradingGraphService` 或其他发布事件的地方，更新 `publish()` 调用以包含元数据：

```python
# 旧方式（仍然支持）
event_manager.publish(session_id, event_data)

# 新方式（推荐，提供更多上下文）
event_manager.publish(
    session_id=session_id,
    event=event_data,
    event_type="agent_complete",  # 事件类型
    message="Technical analysis completed",  # 人类可读消息
    agent_name="technical_analyst",  # 智能体名称
    status="success",  # 状态
)
```

### 步骤 7: 配置环境变量

编辑 `.env` 文件：

```bash
# 事件持久化配置
EVENT_PERSISTENCE_ENABLED=true
EVENT_BUFFER_SIZE=100

# 数据库配置（如果还没有）
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/tradingagents
# 或 SQLite
# DATABASE_URL=sqlite+aiosqlite:///./data/tradingagents.db
```

## 🧪 测试

### 1. 单元测试

创建 `packages/backend/tests/unit/test_session_event_persistence.py`：

```python
import pytest
from app.db.models.session_event import SessionEvent
from app.repositories.session_event import SessionEventRepository

@pytest.mark.asyncio
async def test_create_session_event(db_session):
    repo = SessionEventRepository(db_session)
    
    event = SessionEvent(
        session_id="test-session-123",
        event_type="test_event",
        message="Test message",
        payload={"data": "test"},
        sequence_number=0,
    )
    
    created = await repo.create(event)
    assert created.id is not None
    assert created.session_id == "test-session-123"

@pytest.mark.asyncio
async def test_get_events_paginated(db_session):
    repo = SessionEventRepository(db_session)
    session_id = "test-session-456"
    
    # 创建多个事件
    for i in range(10):
        event = SessionEvent(
            session_id=session_id,
            event_type="test",
            message=f"Event {i}",
            payload={},
            sequence_number=i,
        )
        await repo.create(event)
    
    # 测试分页
    events = await repo.get_by_session(session_id, skip=0, limit=5)
    assert len(events) == 5
    
    events_page2 = await repo.get_by_session(session_id, skip=5, limit=5)
    assert len(events_page2) == 5
    
    # 测试计数
    total = await repo.count_by_session(session_id)
    assert total == 10
```

### 2. 集成测试

创建 `packages/backend/tests/integration/test_event_streaming_persistence.py`：

```python
import pytest
from fastapi.testclient import TestClient

def test_get_events_from_database(client: TestClient, auth_headers):
    session_id = "test-session-789"
    
    # 获取数据库中的事件
    response = client.get(
        f"/api/sessions/{session_id}/events-history?source=db&limit=50",
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "total" in data
    assert "has_more" in data
    assert data["source"] == "database"

def test_pagination(client: TestClient, auth_headers):
    session_id = "test-session-pagination"
    
    # 第一页
    response1 = client.get(
        f"/api/sessions/{session_id}/events-history?skip=0&limit=10",
        headers=auth_headers,
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    # 第二页
    response2 = client.get(
        f"/api/sessions/{session_id}/events-history?skip=10&limit=10",
        headers=auth_headers,
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    # 确保不重复
    event_ids_1 = [e["sequence_number"] for e in data1["events"]]
    event_ids_2 = [e["sequence_number"] for e in data2["events"]]
    assert len(set(event_ids_1) & set(event_ids_2)) == 0
```

### 3. 手动测试

```bash
# 1. 启动服务
cd packages/backend
uv run uvicorn app.main:app --reload

# 2. 创建测试会话（通过 POST /sessions 或 CLI）
pnpm cli

# 3. 查询事件历史
curl -X GET "http://localhost:8000/api/sessions/{session_id}/events-history?limit=50&source=db" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 对比内存和数据库
# 内存（快速，最近 100 个）
curl -X GET "http://localhost:8000/api/sessions/{session_id}/events-history?source=memory" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 数据库（完整历史）
curl -X GET "http://localhost:8000/api/sessions/{session_id}/events-history?source=db&limit=1000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📊 性能考虑

### 1. 数据库索引
已创建的索引：
- `session_id` - 主要查询字段
- `event_type` - 过滤查询
- `sequence_number` - 排序
- `timestamp` - 时间范围查询
- 复合索引 `(session_id, sequence_number)` - 最常用的查询模式

### 2. 异步写入
- 事件持久化是异步的，不会阻塞实时流
- 使用 `asyncio.create_task()` 后台写入
- 失败不影响流式传输

### 3. 内存缓冲
- 保留内存缓冲用于快速访问最近事件
- 默认 100 个事件，可配置
- 对于需要完整历史的场景，使用数据库查询

### 4. 批量操作
- `bulk_create()` 方法支持批量插入
- 适用于导入历史数据或批处理场景

## 🔄 迁移现有数据（可选）

如果需要将现有内存中的事件迁移到数据库：

```python
# 创建迁移脚本：packages/backend/scripts/migrate_events_to_db.py

import asyncio
from app.dependencies import get_db_session
from app.repositories.session_event import SessionEventRepository
from app.services.events import SessionEventManager
from app.db.models.session_event import SessionEvent

async def migrate_events():
    """Migrate in-memory events to database."""
    old_manager = SessionEventManager()
    
    async with get_db_session() as db:
        repo = SessionEventRepository(db)
        
        # 遍历所有会话
        for session_id, buffer in old_manager._event_buffers.items():
            events_to_create = []
            
            for seq_num, timestamped_event in enumerate(buffer):
                event = SessionEvent(
                    session_id=session_id,
                    event_type="migrated",
                    message="Migrated from memory",
                    payload=timestamped_event.event,
                    sequence_number=seq_num,
                    timestamp=timestamped_event.timestamp,
                )
                events_to_create.append(event)
            
            