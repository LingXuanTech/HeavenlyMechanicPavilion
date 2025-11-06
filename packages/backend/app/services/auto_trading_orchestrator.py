"""自动交易协调器 - 连接 Agent 决策和订单执行的自动化系统."""

import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import ExternalServiceError, ResourceNotFoundError
from ..repositories import PortfolioRepository
from .events import SessionEventManager
from .execution import ExecutionService
from .graph import TradingGraphService
from .market_calendar import MarketCalendarService
from .trading_session import TradingSessionService
from ..dependencies.services import get_market_data_service

logger = logging.getLogger(__name__)


class AutoTradingOrchestrator:
    """自动交易协调器 - 实现端到端自动化交易流程."""
    
    def __init__(
        self,
        graph_service: TradingGraphService,
        trading_session_service: TradingSessionService,
        event_manager: SessionEventManager,
        market_calendar: Optional[MarketCalendarService] = None,
    ):
        """初始化自动交易协调器.
        
        Args:
            graph_service: Agent 图谱服务
            trading_session_service: 交易会话服务
            event_manager: 事件管理器
            market_calendar: 市场日历服务（可选）
        """
        self.graph = graph_service
        self.sessions = trading_session_service
        self.events = event_manager
        self.market_calendar = market_calendar
        
        # 自动交易状态管理
        self.is_running: Dict[int, bool] = {}
        self.active_tasks: Dict[int, asyncio.Task] = {}
        
        logger.info("Initialized AutoTradingOrchestrator")
    
    async def run_single_cycle(
        self,
        db: AsyncSession,
        portfolio_id: int,
        symbols: List[str],
        trading_session_id: Optional[int] = None,
    ) -> List[Dict]:
        """运行单次完整的分析+交易周期.
        
        Args:
            db: 数据库会话
            portfolio_id: 投资组合ID
            symbols: 股票代码列表
            trading_session_id: 交易会话ID（可选）
            
        Returns:
            每个标的的执行结果列表
        """
        logger.info(
            f"开始自动交易周期 - Portfolio: {portfolio_id}, "
            f"Symbols: {symbols}, Session: {trading_session_id}"
        )
        
        results = []
        
        for symbol in symbols:
            try:
                # 1. 运行 Agent 分析
                logger.info(f"[{symbol}] 启动 Agent 分析...")
                
                analysis_metadata = await self.graph.run_session(
                    ticker=symbol,
                    trade_date=datetime.now().date(),
                    selected_analysts=["market", "news", "fundamentals", "social"],
                )
                
                session_id = analysis_metadata["session_id"]
                
                # 2. 等待分析完成
                logger.info(f"[{symbol}] 等待 Agent 分析完成...")
                final_state = await self._wait_for_analysis_completion(
                    session_id, 
                    timeout=300
                )
                
                if not final_state:
                    logger.warning(f"[{symbol}] 分析未完成或超时")
                    results.append({
                        "symbol": symbol,
                        "status": "timeout",
                        "error": "Analysis timeout",
                    })
                    continue
                
                # 3. 提取决策和置信度
                processed_signal = final_state.get("processed_signal", "HOLD")
                confidence_score = final_state.get("confidence_score", 0.7)
                decision_rationale = final_state.get("final_trade_decision", "")
                
                logger.info(
                    f"[{symbol}] Agent 决策: {processed_signal} "
                    f"(置信度: {confidence_score:.2f})"
                )
                
                # 4. 发送决策事件到前端
                await self._emit_event({
                    "type": "agent_decision",
                    "symbol": symbol,
                    "decision": processed_signal,
                    "confidence": confidence_score,
                    "rationale": decision_rationale[:200],  # 限制长度
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
                # 5. 如果不是 HOLD，自动执行交易
                if processed_signal != "HOLD":
                    logger.info(f"[{symbol}] 准备执行 {processed_signal} 订单...")
                    
                    # 获取当前市场价格
                    current_price = await self._get_current_price(symbol)
                    
                    # 获取执行服务
                    execution_service = self.sessions.get_execution_service(
                        trading_session_id
                    )
                    
                    if not execution_service:
                        logger.error(
                            f"[{symbol}] 无法获取执行服务 "
                            f"(session_id={trading_session_id})"
                        )
                        results.append({
                            "symbol": symbol,
                            "decision": processed_signal,
                            "status": "error",
                            "error": "Execution service not available",
                        })
                        continue
                    
                    # 执行交易
                    trade = await execution_service.execute_signal(
                        session=db,
                        portfolio_id=portfolio_id,
                        symbol=symbol,
                        signal=processed_signal,
                        current_price=current_price,
                        decision_rationale=decision_rationale,
                        confidence_score=confidence_score,
                        session_id=trading_session_id,
                    )
                    
                    if trade:
                        logger.info(
                            f"[{symbol}] 订单执行成功 - "
                            f"Trade ID: {trade.id}, Status: {trade.status}"
                        )
                        
                        # 发送交易执行事件
                        await self._emit_event({
                            "type": "trade_executed",
                            "symbol": symbol,
                            "action": processed_signal,
                            "trade_id": trade.id,
                            "quantity": trade.quantity,
                            "price": trade.average_fill_price or current_price,
                            "status": trade.status,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        
                        results.append({
                            "symbol": symbol,
                            "decision": processed_signal,
                            "trade_id": trade.id,
                            "status": "executed",
                            "price": trade.average_fill_price or current_price,
                            "quantity": trade.quantity,
                        })
                    else:
                        logger.info(
                            f"[{symbol}] 订单被过滤 (风险检查未通过或其他原因)"
                        )
                        results.append({
                            "symbol": symbol,
                            "decision": processed_signal,
                            "status": "filtered",
                            "reason": "Risk check failed or insufficient funds",
                        })
                else:
                    logger.info(f"[{symbol}] 决策为 HOLD，无需操作")
                    results.append({
                        "symbol": symbol,
                        "decision": "HOLD",
                        "status": "no_action",
                    })
                
            except Exception as e:
                logger.error(
                    f"[{symbol}] 处理失败: {e}", 
                    exc_info=True
                )
                results.append({
                    "symbol": symbol,
                    "status": "error",
                    "error": str(e),
                })
                
                # 发送错误事件
                await self._emit_event({
                    "type": "trading_error",
                    "symbol": symbol,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
        
        logger.info(
            f"自动交易周期完成 - 处理了 {len(results)} 个标的，"
            f"成功: {sum(1 for r in results if r['status'] == 'executed')}"
        )
        
        return results
    
    async def start_continuous_trading(
        self,
        db: AsyncSession,
        portfolio_id: int,
        symbols: List[str],
        interval_minutes: int = 30,
        trading_hours_only: bool = True,
        trading_session_id: Optional[int] = None,
    ):
        """启动连续自动交易（后台任务）.
        
        Args:
            db: 数据库会话
            portfolio_id: 投资组合ID
            symbols: 股票代码列表
            interval_minutes: 执行间隔（分钟）
            trading_hours_only: 是否仅在交易时间内运行
            trading_session_id: 交易会话ID（可选）
        """
        self.is_running[portfolio_id] = True
        
        logger.info(
            f"启动连续自动交易 - Portfolio: {portfolio_id}, "
            f"Interval: {interval_minutes}分钟, "
            f"TradingHoursOnly: {trading_hours_only}"
        )
        
        try:
            while self.is_running.get(portfolio_id, False):
                # 检查是否在交易时间内
                if trading_hours_only:
                    is_open = await self._check_market_status()
                    if not is_open:
                        logger.debug("当前不在交易时间，等待...")
                        await asyncio.sleep(60)  # 1分钟后重新检查
                        continue
                
                # 运行交易周期
                try:
                    results = await self.run_single_cycle(
                        db=db,
                        portfolio_id=portfolio_id,
                        symbols=symbols,
                        trading_session_id=trading_session_id,
                    )
                    
                    logger.info(
                        f"周期完成 - Portfolio: {portfolio_id}, "
                        f"Results: {len(results)} symbols processed"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"交易周期执行失败: {e}", 
                        exc_info=True
                    )
                
                # 等待下一个周期
                logger.info(
                    f"等待 {interval_minutes} 分钟后继续下一个周期..."
                )
                await asyncio.sleep(interval_minutes * 60)
                
        except asyncio.CancelledError:
            logger.info(
                f"自动交易任务被取消 - Portfolio: {portfolio_id}"
            )
        finally:
            self.is_running[portfolio_id] = False
            if portfolio_id in self.active_tasks:
                del self.active_tasks[portfolio_id]
            logger.info(
                f"连续自动交易已停止 - Portfolio: {portfolio_id}"
            )
    
    def stop_continuous_trading(self, portfolio_id: int):
        """停止连续自动交易.
        
        Args:
            portfolio_id: 投资组合ID
        """
        if portfolio_id in self.is_running:
            self.is_running[portfolio_id] = False
            logger.info(
                f"正在停止自动交易 - Portfolio: {portfolio_id}"
            )
        
        # 取消后台任务
        if portfolio_id in self.active_tasks:
            task = self.active_tasks[portfolio_id]
            if not task.done():
                task.cancel()
                logger.info(
                    f"已取消自动交易任务 - Portfolio: {portfolio_id}"
                )
    
    async def _wait_for_analysis_completion(
        self, 
        session_id: str, 
        timeout: int = 300
    ) -> Optional[Dict]:
        """等待 Agent 分析完成并返回最终状态.
        
        Args:
            session_id: 分析会话ID
            timeout: 超时时间（秒）
            
        Returns:
            最终状态字典，如果超时或失败则返回 None
        """
        start_time = datetime.utcnow()
        final_state = None
        
        try:
            # 获取事件流
            queue = await self.graph.ensure_session_stream(session_id)
            
            while (datetime.utcnow() - start_time).total_seconds() < timeout:
                try:
                    # 等待事件（5秒超时）
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    
                    if event is None:
                        # 流结束
                        logger.info(f"分析流结束: {session_id}")
                        break
                    
                    event_type = event.get("type")
                    
                    if event_type == "result":
                        # 保存最终结果
                        final_state = event
                        logger.debug(
                            f"收到分析结果: {session_id}, "
                            f"signal={event.get('processed_signal')}"
                        )
                    
                    elif event_type == "completed":
                        logger.info(f"分析完成: {session_id}")
                        break
                    
                    elif event_type == "error":
                        logger.error(
                            f"分析失败: {session_id}, "
                            f"error={event.get('message')}"
                        )
                        return None
                    
                except asyncio.TimeoutError:
                    # 继续等待
                    continue
            
            return final_state
            
        except Exception as e:
            logger.error(
                f"等待分析完成时出错: {e}", 
                exc_info=True
            )
            return None
    
    async def _get_current_price(self, symbol: str) -> float:
        """获取当前市场价格.
        
        Args:
            symbol: 股票代码
            
        Returns:
            当前价格
        """
        try:
            market_data_service = get_market_data_service()
            price_data = await market_data_service.get_latest_price(symbol)
            return price_data.get("price", 0.0)
        except Exception as e:
            logger.error(
                f"获取价格失败 ({symbol}): {e}"
            )
            # 返回默认值或抛出异常
            raise ValueError(f"Cannot get price for {symbol}")
    
    async def _check_market_status(self) -> bool:
        """检查市场是否开市.
        
        使用 MarketCalendarService 获取准确的市场状态，
        如果服务不可用则回退到简单的时间检查。
        
        Returns:
            是否在交易时间内
        """
        if self.market_calendar:
            try:
                # 使用 Alpaca Clock API 获取准确状态
                return await self.market_calendar.is_market_open()
            except ExternalServiceError as e:
                logger.warning(
                    f"无法从市场日历服务获取状态，使用简单时间检查: {e}"
                )
        
        # 回退到简单的时间检查
        return self._is_market_open_simple()
    
    def _is_market_open_simple(self) -> bool:
        """简单的市场开市检查（美股时间）.
        
        注意：这是简化版本，不考虑节假日。
        生产环境应使用 MarketCalendarService。
        
        Returns:
            是否在交易时间内
        """
        now = datetime.now()
        
        # 周末不交易
        if now.weekday() >= 5:  # 5=周六, 6=周日
            return False
        
        # 美股交易时间: 9:30 - 16:00 EST
        # 简化版本，实际应考虑时区转换
        current_time = now.time()
        market_open = time(9, 30)
        market_close = time(16, 0)
        
        return market_open <= current_time <= market_close
    
    async def _emit_event(self, event: Dict):
        """发送事件到前端（通过事件管理器）.
        
        Args:
            event: 事件数据
        """
        # 广播事件（可以扩展为支持特定会话）
        # 当前简化版本：直接记录日志
        logger.info(f"Event emitted: {event.get('type')} - {event.get('symbol', 'N/A')}")
        
        # TODO: 实现真正的事件推送到前端
        # 可以通过 WebSocket 或 SSE 推送