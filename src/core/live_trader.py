"""Live trading: ejecuta órdenes REALES en Bybit. Requiere confirmación explícita."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.config import settings
from src.database.db import session_scope
from src.database.models import Trade
from src.strategies.base import PositionSignal
from src.core.trading_engine import OpenPosition, TradingEngine

logger = logging.getLogger(__name__)


class LiveTrader(TradingEngine):
    mode = "live"

    def __init__(self, *args, confirm_live: bool = False, **kwargs):
        if not confirm_live:
            raise RuntimeError(
                "LiveTrader requiere confirm_live=True explícito. Este modo envía órdenes "
                "reales a Bybit. Verifica bien la estrategia en shadow/backtest antes de usarlo."
            )
        settings.validate_for_live()
        super().__init__(*args, **kwargs)
        if settings.bybit_testnet:
            logger.warning("BYBIT_TESTNET=true: las órdenes 'reales' se ejecutarán en testnet, no en producción.")

    def _execute_entry(self, symbol: str, signal: PositionSignal, price: float, sizing) -> int | None:
        side = "buy" if signal == PositionSignal.LONG else "sell"
        order = self.client.create_market_order(symbol, side, sizing.quantity)
        fill_price = float(order.get("average") or order.get("price") or price)
        fee = float(sizing.quantity) * fill_price * 0.00055

        with session_scope() as session:
            trade = Trade(
                mode=self.mode,
                strategy=self.strategy.name,
                symbol=symbol,
                side=signal.value,
                entry_price=fill_price,
                quantity=sizing.quantity,
                stop_loss=sizing.stop_loss,
                take_profit=sizing.take_profit,
                fees=fee,
                is_open=True,
                exchange_order_id=str(order.get("id", "")),
            )
            session.add(trade)
            session.flush()
            return trade.id

    def _execute_exit(self, symbol: str, position: OpenPosition, price: float, reason: str) -> tuple[float, float]:
        close_side = "sell" if position.side == "LONG" else "buy"
        order = self.client.create_market_order(symbol, close_side, position.quantity, params={"reduceOnly": True})
        fill_price = float(order.get("average") or order.get("price") or price)

        direction = 1 if position.side == "LONG" else -1
        pnl_pct = direction * (fill_price / position.entry_price - 1) * 100
        fee = position.quantity * fill_price * 0.00055
        pnl = position.quantity * position.entry_price * (pnl_pct / 100) - fee

        logger.info("[LIVE] Cierre %s %s precio=%.2f motivo=%s pnl=%.2f", position.side, symbol, fill_price, reason, pnl)

        if position.trade_id is not None:
            with session_scope() as session:
                trade = session.get(Trade, position.trade_id)
                if trade is not None:
                    trade.exit_price = fill_price
                    trade.pnl = pnl
                    trade.pnl_pct = pnl_pct
                    trade.fees = (trade.fees or 0.0) + fee
                    trade.is_open = False
                    trade.closed_at = datetime.now(timezone.utc)

        return pnl, pnl_pct
