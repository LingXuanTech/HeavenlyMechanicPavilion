"""SubGraph 模块

将 LangGraph 工作流模块化为独立的子图：
- AnalystSubGraph: 分析师并行执行
- DebateSubGraph: Bull vs Bear 辩论
- RiskSubGraph: 风险评估三方辩论

每个 SubGraph 封装私有状态和内部逻辑，对外仅暴露输入/输出接口。
"""

from .analyst_subgraph import AnalystSubGraph
from .debate_subgraph import DebateSubGraph
from .risk_subgraph import RiskSubGraph

__all__ = [
    "AnalystSubGraph",
    "DebateSubGraph",
    "RiskSubGraph",
]
