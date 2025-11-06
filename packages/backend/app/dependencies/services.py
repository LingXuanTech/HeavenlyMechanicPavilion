"""统一的服务依赖注入管理."""

from fastapi import Depends

from ..config.settings import Settings, get_settings
from ..services.alerting import AlertingService
from ..services.auto_trading_orchestrator import AutoTradingOrchestrator
from ..services.broker_adapter import BrokerAdapter, SimulatedBroker
from ..services.brokers.alpaca_adapter import AlpacaBrokerAdapter
from ..services.execution import ExecutionService
from ..services.graph import TradingGraphService
from ..services.market_data import MarketDataService
from ..services.monitoring import MonitoringService
from ..services.position_sizing import PositionSizingMethod, PositionSizingService
from ..services.risk_management import RiskConstraints, RiskManagementService
from ..services.trading_session import TradingSessionService
from ..services.events import SessionEventManager

# ============= 应用级单例服务 =============

_market_data_service: MarketDataService | None = None


def get_market_data_service() -> MarketDataService:
    """获取行情数据服务实例 (应用级单例)."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service


def get_alerting_service(settings: Settings = Depends(get_settings)) -> AlertingService:
    """获取告警服务实例 (应用级单例).

    Args:
        settings: 应用配置

    Returns:
        AlertingService 实例
    """
    return AlertingService(settings)


def get_monitoring_service() -> MonitoringService:
    """获取监控服务实例 (应用级单例).

    Returns:
        MonitoringService 实例
    """
    return MonitoringService()


# ============= 会话级服务 =============


def get_broker_adapter(
    settings: Settings = Depends(get_settings),
    session_type: str = "PAPER",
    initial_capital: float = 100000.0,
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> BrokerAdapter:
    """获取券商适配器实例 (会话级).

    Args:
        settings: 应用配置
        session_type: 会话类型 (PAPER/LIVE)
        initial_capital: 初始资金
        market_data_service: 行情数据服务实例

    Returns:
        BrokerAdapter 实例

    Raises:
        ValueError: 如果配置无效
        NotImplementedError: 如果券商类型未实现
    """
    broker_type = settings.broker_type.lower()
    
    if session_type == "PAPER":
        # Paper trading - 优先使用配置的券商类型，否则使用模拟器
        if broker_type == "alpaca":
            # 使用 Alpaca Paper Trading
            if not settings.alpaca_api_key or not settings.alpaca_api_secret:
                raise ValueError(
                    "Alpaca API key and secret are required. "
                    "Please set ALPACA_API_KEY and ALPACA_API_SECRET environment variables."
                )
            return AlpacaBrokerAdapter(
                api_key=settings.alpaca_api_key,
                api_secret=settings.alpaca_api_secret,
                base_url=settings.alpaca_base_url,
                paper_trading=True,
            )
        else:
            # 默认使用模拟器
            return SimulatedBroker(
                initial_capital=initial_capital,
                commission_per_trade=0.0,
                slippage_percent=0.001,
                market_data_service=market_data_service,
            )
    else:
        # Live trading
        if broker_type == "alpaca":
            if not settings.alpaca_api_key or not settings.alpaca_api_secret:
                raise ValueError(
                    "Alpaca API key and secret are required for live trading. "
                    "Please set ALPACA_API_KEY and ALPACA_API_SECRET environment variables."
                )
            # 实盘交易需要明确设置 base_url 为实盘地址
            live_base_url = "https://api.alpaca.markets"
            return AlpacaBrokerAdapter(
                api_key=settings.alpaca_api_key,
                api_secret=settings.alpaca_api_secret,
                base_url=live_base_url,
                paper_trading=False,
            )
        else:
            raise NotImplementedError(
                f"Live trading with broker type '{broker_type}' is not yet implemented. "
                "Currently supported: alpaca"
            )


def get_position_sizing_service(
    method: PositionSizingMethod = PositionSizingMethod.FIXED_PERCENTAGE,
) -> PositionSizingService:
    """获取仓位管理服务实例.

    Args:
        method: 仓位计算方法

    Returns:
        PositionSizingService 实例
    """
    return PositionSizingService(method=method)


def get_risk_management_service(
    max_position_weight: float = 0.20,
    max_portfolio_exposure: float = 1.0,
    default_stop_loss_pct: float = 0.10,
    default_take_profit_pct: float = 0.20,
) -> RiskManagementService:
    """获取风险管理服务实例.

    Args:
        max_position_weight: 最大单个持仓权重
        max_portfolio_exposure: 最大组合敞口
        default_stop_loss_pct: 默认止损百分比
        default_take_profit_pct: 默认止盈百分比

    Returns:
        RiskManagementService 实例
    """
    constraints = RiskConstraints(
        max_position_weight=max_position_weight,
        max_portfolio_exposure=max_portfolio_exposure,
        default_stop_loss_pct=default_stop_loss_pct,
        default_take_profit_pct=default_take_profit_pct,
    )
    return RiskManagementService(constraints=constraints)


def get_execution_service(
    broker: BrokerAdapter = Depends(get_broker_adapter),
    position_sizing: PositionSizingService = Depends(get_position_sizing_service),
    risk_management: RiskManagementService = Depends(get_risk_management_service),
) -> ExecutionService:
    """获取执行服务实例.

    Args:
        broker: 券商适配器
        position_sizing: 仓位管理服务
        risk_management: 风险管理服务

    Returns:
        ExecutionService 实例
    """
    return ExecutionService(broker, position_sizing, risk_management)


def get_trading_session_service() -> TradingSessionService:
    """获取交易会话服务实例.

    Returns:
        TradingSessionService 实例
    """
    return TradingSessionService()


# ============= 自动交易协调器 =============

# 应用级单例
_auto_trading_orchestrator: AutoTradingOrchestrator | None = None


def get_auto_trading_orchestrator(
    graph_service: TradingGraphService = Depends(lambda: None),  # Will be injected in API
    trading_session_service: TradingSessionService = Depends(get_trading_session_service),
    event_manager: SessionEventManager = Depends(lambda: None),  # Will be injected in API
) -> AutoTradingOrchestrator:
    """获取自动交易协调器实例 (应用级单例).
    
    Note: graph_service and event_manager need to be properly injected in the API layer
    as they require additional initialization.
    
    Args:
        graph_service: Agent 图谱服务
        trading_session_service: 交易会话服务
        event_manager: 事件管理器
        
    Returns:
        AutoTradingOrchestrator 实例
    """
    global _auto_trading_orchestrator
    if _auto_trading_orchestrator is None:
        # This will be properly initialized in the API startup
        # For now, create a placeholder that will be replaced
        if graph_service and event_manager:
            _auto_trading_orchestrator = AutoTradingOrchestrator(
                graph_service=graph_service,
                trading_session_service=trading_session_service,
                event_manager=event_manager,
            )
    return _auto_trading_orchestrator
