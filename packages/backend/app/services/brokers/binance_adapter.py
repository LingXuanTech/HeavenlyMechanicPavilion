"""Binance 券商适配器实现 (加密货币交易)."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

# 注意：实际项目中需要安装 python-binance
# 这里提供一个基于通用接口的实现框架
try:
    from binance.client import Client
    from binance.enums import *
except ImportError:
    Client = None

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


class BinanceBrokerAdapter(BrokerAdapter):
    """Binance 券商适配器 - 支持加密货币现货交易."""
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        testnet: bool = True,
    ):
        """初始化 Binance 适配器.
        
        Args:
            api_key: Binance API Key
            secret_key: Binance Secret Key
            testnet: 是否使用测试网 (Testnet)
        """
        if Client is None:
            raise ImportError("请安装 python-binance 以使用 Binance 适配器")
            
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        
        # 初始化客户端
        self.client = Client(api_key, secret_key, testnet=testnet)
        
        # 验证连接
        try:
            account = self.client.get_account()
            logger.info(
                f"Binance 连接成功 ({'Testnet' if testnet else 'Mainnet'}) - "
                f"账户类型: {account['accountType']}"
            )
        except Exception as e:
            logger.error(f"Binance 连接失败: {e}")
            raise ExternalServiceError(f"无法连接到 Binance: {e}")
    
    async def submit_order(self, order: OrderRequest) -> OrderResponse:
        """提交订单到 Binance."""
        try:
            side = SIDE_BUY if order.action in [OrderAction.BUY, OrderAction.COVER] else SIDE_SELL
            
            # Binance 订单参数
            params = {
                "symbol": order.symbol,
                "side": side,
                "quantity": order.quantity,
            }
            
            if order.order_type == OrderType.MARKET:
                params["type"] = ORDER_TYPE_MARKET
            elif order.order_type == OrderType.LIMIT:
                if order.limit_price is None:
                    raise ValidationError("LIMIT 订单需要限制价格")
                params["type"] = ORDER_TYPE_LIMIT
                params["price"] = str(order.limit_price)
                params["timeInForce"] = TIME_IN_FORCE_GTC
            
            # 提交订单 (同步调用，建议在生产环境中使用 run_in_executor)
            binance_order = self.client.create_order(**params)
            
            return self._map_order_response(binance_order)
            
        except Exception as e:
            logger.error(f"Binance 订单提交失败: {e}")
            raise ExternalServiceError(f"Binance 订单提交失败: {e}")
    
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """取消订单."""
        # 注意：Binance 通常需要 symbol 才能取消订单
        # 这里假设 order_id 编码了 symbol 或者需要从本地数据库查找
        raise NotImplementedError("Binance 取消订单需要 symbol 参数，请通过 get_order_status 扩展实现")
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """查询订单状态."""
        # 同样需要 symbol
        raise NotImplementedError("Binance 查询订单需要 symbol 参数")
    
    async def get_market_price(self, symbol: str) -> MarketPrice:
        """获取实时价格."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            return MarketPrice(
                symbol=symbol,
                bid=price, # 简化处理
                ask=price,
                last=price,
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            raise ExternalServiceError(f"获取 Binance 价格失败: {e}")
    
    async def get_buying_power(self) -> float:
        """获取可用余额 (以 USDT 为例)."""
        try:
            asset = self.client.get_asset_balance(asset='USDT')
            return float(asset['free'])
        except Exception as e:
            return 0.0
            
    async def get_positions(self) -> List[Dict]:
        """获取所有非零余额资产."""
        try:
            account = self.client.get_account()
            balances = account.get('balances', [])
            positions = []
            for b in balances:
                free = float(b['free'])
                locked = float(b['locked'])
                total = free + locked
                if total > 0:
                    positions.append({
                        "symbol": b['asset'],
                        "quantity": total,
                        "free": free,
                        "locked": locked,
                        "position_type": "LONG"
                    })
            return positions
        except Exception as e:
            raise ExternalServiceError(f"获取 Binance 余额失败: {e}")

    async def get_position(self, symbol: str) -> Optional[Dict]:
        """获取特定资产余额."""
        try:
            asset = self.client.get_asset_balance(asset=symbol)
            if not asset: return None
            total = float(asset['free']) + float(asset['locked'])
            return {
                "symbol": symbol,
                "quantity": total,
                "position_type": "LONG"
            }
        except Exception:
            return None

    def _map_order_response(self, b_order: Dict) -> OrderResponse:
        """映射 Binance 响应到内部格式."""
        status_map = {
            "NEW": OrderStatus.PENDING,
            "PARTIALLY_FILLED": OrderStatus.PARTIAL,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.CANCELLED,
        }
        
        return OrderResponse(
            order_id=str(b_order['orderId']),
            status=status_map.get(b_order['status'], OrderStatus.REJECTED),
            symbol=b_order['symbol'],
            action=OrderAction.BUY if b_order['side'] == 'BUY' else OrderAction.SELL,
            quantity=float(b_order['origQty']),
            filled_quantity=float(b_order['executedQty']),
            average_fill_price=float(b_order.get('price', 0)) or None,
            submitted_at=datetime.fromtimestamp(b_order['transactTime'] / 1000) if 'transactTime' in b_order else None
        )