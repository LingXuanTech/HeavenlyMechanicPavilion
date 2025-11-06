"""自动交易相关的 Schema 定义."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class StartAutoTradingRequest(BaseModel):
    """启动自动交易请求."""
    
    portfolio_id: int = Field(..., description="投资组合ID")
    symbols: List[str] = Field(..., description="要交易的股票列表")
    interval_minutes: int = Field(
        30, 
        ge=5, 
        le=1440,
        description="执行间隔(分钟), 5分钟到24小时"
    )
    trading_hours_only: bool = Field(
        True, 
        description="是否仅在交易时间内运行"
    )
    trading_session_id: Optional[int] = Field(
        None,
        description="关联的交易会话ID（可选）"
    )


class AutoTradingStatusResponse(BaseModel):
    """自动交易状态响应."""
    
    status: str = Field(..., description="状态: running | stopped")
    portfolio_id: int
    symbols: Optional[List[str]] = None
    interval_minutes: Optional[int] = None
    started_at: Optional[datetime] = None


class RunOnceRequest(BaseModel):
    """单次执行请求."""
    
    portfolio_id: int = Field(..., description="投资组合ID")
    symbols: List[str] = Field(..., description="要交易的股票列表")
    trading_session_id: Optional[int] = Field(
        None,
        description="关联的交易会话ID（可选）"
    )


class TradingCycleResult(BaseModel):
    """单个标的的交易周期结果."""
    
    symbol: str
    decision: Optional[str] = None  # BUY/SELL/HOLD
    status: str  # executed | filtered | no_action | error | timeout
    trade_id: Optional[int] = None
    price: Optional[float] = None
    quantity: Optional[float] = None
    error: Optional[str] = None
    reason: Optional[str] = None


class RunOnceResponse(BaseModel):
    """单次执行响应."""
    
    portfolio_id: int
    results: List[TradingCycleResult]
    executed_at: datetime
    summary: Optional[Dict[str, int]] = Field(
        None,
        description="执行摘要统计"
    )


class StopAutoTradingRequest(BaseModel):
    """停止自动交易请求."""
    
    portfolio_id: int = Field(..., description="投资组合ID")