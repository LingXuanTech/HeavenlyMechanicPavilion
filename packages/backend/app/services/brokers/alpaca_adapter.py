"""Alpaca 券商适配器实现."""

import logging
from datetime import datetime
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType as AlpacaOrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

from ..broker_adapter import (
    BrokerAdapter,
    MarketPrice,
    OrderAction,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    OrderType,
)
from ...core.errors import (
    ExternalServiceError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter(BrokerAdapter):
    """Alpaca 券商适配器 - 支持美股实盘和模拟交易."""
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper_trading: bool = True,
    ):
        """初始化 Alpaca 适配器.
        
        Args:
            api_key: Alpaca API Key
            secret_key: Alpaca Secret Key
            paper_trading: 是否使用模拟账户 (Paper Trading)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper_trading = paper_trading
        
        # 初始化交易客户端
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper_trading,
        )
        
        # 初始化行情数据客户端
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key,
        )
        
        # 验证连接
        try:
            account = self.trading_client.get_account()
            logger.info(
                f"Alpaca 连接成功 ({'Paper' if paper_trading else 'Live'} Trading) - "
                f"账户状态: {account.status}, "
                f"购买力: ${float(account.buying_power):,.2f}"
            )
        except Exception as e:
            logger.error(f"Alpaca 连接失败: {e}")
            raise ExternalServiceError(
                f"无法连接到 Alpaca: {e}",
                details={"paper_trading": paper_trading}
            )
    
    async def submit_order(self, order: OrderRequest) -> OrderResponse:
        """提交订单到 Alpaca.
        
        Args:
            order: 订单请求
            
        Returns:
            订单响应
            
        Raises:
            ValidationError: 订单参数验证失败
            ExternalServiceError: Alpaca API 调用失败
        """
        try:
            # 转换订单方向
            side = self._convert_order_side(order.action)
            
            # 转换订单类型并提交
            if order.order_type == OrderType.MARKET:
                alpaca_order = MarketOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                )
            elif order.order_type == OrderType.LIMIT:
                if order.limit_price is None:
                    raise ValidationError(
                        "Limit price required for LIMIT orders",
                        details={"symbol": order.symbol}
                    )
                alpaca_order = LimitOrderRequest(
                    symbol=order.symbol,
                    qty=order.quantity,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=order.limit_price,
                )
            else:
                raise ValidationError(
                    f"Unsupported order type: {order.order_type}",
                    details={"order_type": order.order_type.value}
                )
            
            # 提交订单
            alpaca_response = self.trading_client.submit_order(alpaca_order)
            
            logger.info(
                f"订单已提交到 Alpaca: {alpaca_response.id} - "
                f"{side.value} {order.quantity} {order.symbol}"
            )
            
            # 转换状态
            status = self._convert_order_status(alpaca_response.status)
            
            # 构建响应
            return OrderResponse(
                order_id=alpaca_response.id,
                status=status,
                symbol=alpaca_response.symbol,
                action=order.action,
                quantity=float(alpaca_response.qty),
                filled_quantity=float(alpaca_response.filled_qty or 0),
                average_fill_price=float(alpaca_response.filled_avg_price) if alpaca_response.filled_avg_price else None,
                commission=0.0,  # Alpaca 免佣金
                fees=0.0,
                message=None,
                submitted_at=alpaca_response.submitted_at,
                filled_at=alpaca_response.filled_at,
            )
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Alpaca 订单提交失败: {e}")
            raise ExternalServiceError(
                f"订单提交失败: {e}",
                details={
                    "symbol": order.symbol,
                    "action": order.action.value,
                    "order_type": order.order_type.value
                }
            )
    
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """取消订单.
        
        Args:
            order_id: 订单ID
            
        Returns:
            更新后的订单响应
        """
        try:
            # 取消订单
            self.trading_client.cancel_order_by_id(order_id)
            
            # 获取更新后的订单状态
            return await self.get_order_status(order_id)
            
        except Exception as e:
            logger.error(f"取消订单失败 ({order_id}): {e}")
            raise ExternalServiceError(
                f"取消订单失败: {e}",
                details={"order_id": order_id}
            )
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """查询订单状态.
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单响应
        """
        try:
            alpaca_order = self.trading_client.get_order_by_id(order_id)
            
            # 转换状态
            status = self._convert_order_status(alpaca_order.status)
            
            # 转换订单方向
            action = self._convert_to_order_action(alpaca_order.side)
            
            return OrderResponse(
                order_id=alpaca_order.id,
                status=status,
                symbol=alpaca_order.symbol,
                action=action,
                quantity=float(alpaca_order.qty),
                filled_quantity=float(alpaca_order.filled_qty or 0),
                average_fill_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
                commission=0.0,
                fees=0.0,
                message=None,
                submitted_at=alpaca_order.submitted_at,
                filled_at=alpaca_order.filled_at,
            )
            
        except Exception as e:
            logger.error(f"查询订单状态失败 ({order_id}): {e}")
            raise ResourceNotFoundError(
                f"订单未找到或查询失败: {e}",
                details={"order_id": order_id}
            )
    
    async def get_market_price(self, symbol: str) -> MarketPrice:
        """获取实时市场价格.
        
        Args:
            symbol: 股票代码
            
        Returns:
            市场价格数据
        """
        try:
            # 获取最新报价
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            
            if symbol not in quotes:
                raise ResourceNotFoundError(
                    f"未找到股票报价: {symbol}",
                    details={"symbol": symbol}
                )
            
            quote = quotes[symbol]
            
            return MarketPrice(
                symbol=symbol,
                bid=float(quote.bid_price),
                ask=float(quote.ask_price),
                last=(float(quote.bid_price) + float(quote.ask_price)) / 2,  # 使用买卖中间价
                timestamp=datetime.utcnow(),
            )
            
        except ResourceNotFoundError:
            raise
        except Exception as e:
            logger.error(f"获取价格失败 ({symbol}): {e}")
            raise ExternalServiceError(
                f"无法获取价格: {e}",
                details={"symbol": symbol}
            )
    
    async def get_buying_power(self) -> float:
        """获取可用购买力.
        
        Returns:
            可用购买力
        """
        try:
            account = self.trading_client.get_account()
            return float(account.buying_power)
            
        except Exception as e:
            logger.error(f"获取购买力失败: {e}")
            raise ExternalServiceError(
                "无法获取账户信息",
                details={"error": str(e)}
            )
    
    def _convert_order_side(self, action: OrderAction) -> OrderSide:
        """转换订单方向到 Alpaca 格式.
        
        Args:
            action: 订单动作
            
        Returns:
            Alpaca 订单方向
        """
        mapping = {
            OrderAction.BUY: OrderSide.BUY,
            OrderAction.SELL: OrderSide.SELL,
            OrderAction.SHORT: OrderSide.SELL,  # Alpaca 只有 BUY/SELL
            OrderAction.COVER: OrderSide.BUY,
        }
        return mapping[action]
    
    def _convert_to_order_action(self, side: OrderSide) -> OrderAction:
        """转换 Alpaca 订单方向到内部格式.
        
        Args:
            side: Alpaca 订单方向
            
        Returns:
            内部订单动作
        """
        mapping = {
            OrderSide.BUY: OrderAction.BUY,
            OrderSide.SELL: OrderAction.SELL,
        }
        return mapping.get(side, OrderAction.BUY)
    
    def _convert_order_status(self, alpaca_status: str) -> OrderStatus:
        """转换 Alpaca 订单状态到内部状态.
        
        Args:
            alpaca_status: Alpaca 订单状态
            
        Returns:
            内部订单状态
        """
        # Alpaca 订单状态映射
        # https://alpaca.markets/docs/api-references/trading-api/orders/#order-status
        status_map = {
            'new': OrderStatus.PENDING,
            'partially_filled': OrderStatus.PARTIAL,
            'filled': OrderStatus.FILLED,
            'done_for_day': OrderStatus.CANCELLED,
            'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.CANCELLED,
            'replaced': OrderStatus.CANCELLED,
            'pending_cancel': OrderStatus.PENDING,
            'pending_replace': OrderStatus.PENDING,
            'accepted': OrderStatus.SUBMITTED,
            'pending_new': OrderStatus.PENDING,
            'accepted_for_bidding': OrderStatus.SUBMITTED,
            'stopped': OrderStatus.CANCELLED,
            'rejected': OrderStatus.REJECTED,
            'suspended': OrderStatus.CANCELLED,
            'calculated': OrderStatus.PENDING,
        }
        
        # 转换为小写进行匹配
        status_lower = str(alpaca_status).lower()
        return status_map.get(status_lower, OrderStatus.REJECTED)