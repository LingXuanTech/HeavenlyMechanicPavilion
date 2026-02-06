"""Vision 分析相关的 Pydantic Schema 定义"""

from typing import List, Optional
from pydantic import BaseModel, Field


class VisionKeyDataPoint(BaseModel):
    """Vision 关键数据点"""
    label: str = Field(..., description="标签")
    value: str = Field(..., description="值")


class VisionAnalysisResult(BaseModel):
    """Vision 分析结果"""
    chart_type: str = Field(..., description="图表类型")
    time_range: Optional[str] = Field(None, description="时间范围")
    key_data_points: Optional[List[VisionKeyDataPoint]] = Field(None, description="关键数据点")
    trend: str = Field(..., description="趋势方向")
    trend_description: Optional[str] = Field(None, description="趋势描述")
    patterns: Optional[List[str]] = Field(None, description="识别到的模式")
    support_levels: Optional[List[float]] = Field(None, description="支撑位")
    resistance_levels: Optional[List[float]] = Field(None, description="阻力位")
    anomalies: Optional[List[str]] = Field(None, description="异常点")
    signals: Optional[List[str]] = Field(None, description="交易信号")
    summary: str = Field(..., description="分析摘要")
    recommendation: Optional[str] = Field(None, description="建议")
    confidence: float = Field(..., ge=0, le=100, description="置信度")
    raw_analysis: Optional[str] = Field(None, description="原始分析文本")


class VisionAnalysisResponse(BaseModel):
    """Vision 分析响应"""
    success: bool = Field(..., description="是否成功")
    symbol: str = Field(..., description="关联股票代码")
    description: str = Field(..., description="图片描述")
    analysis: VisionAnalysisResult = Field(..., description="分析结果")
    timestamp: str = Field(..., description="时间戳")
    image_size: int = Field(..., description="原始图片大小")
    processed_size: int = Field(..., description="处理后大小")
    error: Optional[str] = Field(None, description="错误信息")
