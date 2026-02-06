"""产业链相关的 Pydantic Schema 定义"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============ 产业链列表 ============

class ChainSegmentCounts(BaseModel):
    """产业链环节数量"""
    upstream: int = Field(..., description="上游数量")
    midstream: int = Field(..., description="中游数量")
    downstream: int = Field(..., description="下游数量")


class ChainSummary(BaseModel):
    """产业链概要"""
    id: str = Field(..., description="产业链 ID")
    name: str = Field(..., description="产业链名称")
    description: str = Field(..., description="描述")
    total_companies: int = Field(..., description="公司总数")
    segments: ChainSegmentCounts = Field(..., description="各环节数量")


class ChainListResponse(BaseModel):
    """产业链列表响应"""
    chains: List[ChainSummary] = Field(default_factory=list, description="产业链列表")
    total: int = Field(..., description="总数量")
    timestamp: str = Field(..., description="时间戳")


# ============ 产业链图谱 ============

class GraphNode(BaseModel):
    """图谱节点"""
    id: str = Field(..., description="节点 ID")
    type: str = Field(..., description="节点类型: chain / segment / company")
    label: str = Field(..., description="显示标签")
    position: str = Field(..., description="位置: center / upstream / midstream / downstream")
    symbol: Optional[str] = Field(None, description="股票代码")
    code: Optional[str] = Field(None, description="代码")
    segment: Optional[str] = Field(None, description="所属环节")
    price: Optional[float] = Field(None, description="当前价格")
    change_pct: Optional[float] = Field(None, description="涨跌幅")


class GraphEdge(BaseModel):
    """图谱边"""
    source: str = Field(..., description="源节点 ID")
    target: str = Field(..., description="目标节点 ID")
    relation: str = Field(..., description="关系描述")
    style: Optional[str] = Field(None, description="样式")


class ChainGraphStats(BaseModel):
    """图谱统计"""
    total_nodes: int = Field(..., description="节点总数")
    total_edges: int = Field(..., description="边总数")
    upstream_count: int = Field(..., description="上游数量")
    midstream_count: int = Field(..., description="中游数量")
    downstream_count: int = Field(..., description="下游数量")


class ChainGraphResponse(BaseModel):
    """产业链图谱响应"""
    chain_id: str = Field(..., description="产业链 ID")
    chain_name: str = Field(..., description="产业链名称")
    description: str = Field(..., description="描述")
    nodes: List[GraphNode] = Field(default_factory=list, description="节点列表")
    edges: List[GraphEdge] = Field(default_factory=list, description="边列表")
    stats: ChainGraphStats = Field(..., description="统计数据")
    timestamp: str = Field(..., description="时间戳")


# ============ 个股产业链位置 ============

class ChainPosition(BaseModel):
    """个股产业链位置"""
    chain_id: str = Field(..., description="产业链 ID")
    chain_name: str = Field(..., description="产业链名称")
    position: str = Field(..., description="位置")
    segment: str = Field(..., description="环节")
    full_name: str = Field(..., description="公司全名")


class StockChainPositionResponse(BaseModel):
    """个股产业链位置响应"""
    symbol: str = Field(..., description="股票代码")
    found: bool = Field(..., description="是否找到")
    chains: Optional[List[ChainPosition]] = Field(None, description="所属产业链")
    chain_count: Optional[int] = Field(None, description="产业链数量")
    industry_info: Optional[Dict[str, Any]] = Field(None, description="行业信息")
    suggestion: Optional[str] = Field(None, description="建议")
    timestamp: Optional[str] = Field(None, description="时间戳")


# ============ 产业链传导效应 ============

class SupplyChainImpactAnalysis(BaseModel):
    """传导效应分析"""
    upstream_risk: str = Field(..., description="上游风险")
    downstream_demand: str = Field(..., description="下游需求")
    position_advantage: str = Field(..., description="位置优势")


class SupplyChainImpact(BaseModel):
    """产业链传导效应"""
    chain_id: str = Field(..., description="产业链 ID")
    chain_name: str = Field(..., description="产业链名称")
    position: str = Field(..., description="位置")
    segment: str = Field(..., description="环节")
    upstream_companies: List[str] = Field(default_factory=list, description="上游公司")
    downstream_companies: List[str] = Field(default_factory=list, description="下游公司")
    impact_analysis: SupplyChainImpactAnalysis = Field(..., description="传导分析")


class SupplyChainImpactResponse(BaseModel):
    """产业链传导效应响应"""
    symbol: str = Field(..., description="股票代码")
    analyses: List[SupplyChainImpact] = Field(default_factory=list, description="分析结果")
    timestamp: str = Field(..., description="时间戳")
