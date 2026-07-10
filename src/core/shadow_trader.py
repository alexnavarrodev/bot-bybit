"""Shadow trading (paper trading): usa precios reales de Bybit pero NUNCA envía órdenes.
Ideal para validar una estrategia en vivo antes de arriesgar capital real."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.database.db import session_scope
from src.database.models import Trade
from src.strategies.base import PositionSignal
from src.core.trading_engine import OpenPosition, TradingEngine

logger = logging.getLogger(__name__)

FEE_RATE = 0.00055  # comisión taker aproximada de Bybit, aplicada en la simulación


class ShadowTrader(TradingEngine):
    mode = "shadow"

    def _execute_entry(self, symbol: str, signal: PositionSignal, price: float, sizing) -> int | None:
        fee = sizing.notional * FEE_RATE
        logger.info(
            "[SHADOW] Apertura %s %s qty=%.6f precio=%.2f SL=%.2f TP=%.2f",
            signal.value, symbol, sizing.quantity, price, sizing.stop_loss, sizing.take_profit,
        )
        with session_scope() as session:
            trade = Trade(
                mode=self.mode,
                strategy=self.strategy.name,
                symbol=symbol,
                side=signal.value,
                entry_price=price,
                quantity=sizing.quantity,
                stop_loss=sizing.stop_loss,
                take_profit=sizing.take_profit,
                fees=fee,
                is_open=True,
            )
            session.add(trade)
            session.flush()
            return trade.id

    def _execute_exit(self, symbol: str, position: OpenPosition, price: float, reason: str) -> tuple[float, float]:
        notional_exit = position.quantity * price
        fee = notional_exit * FEE_RATE
        direction = 1 if position.side == "LONG" else -1
        pnl_pct = direction * (price / position.entry_price - 1) * 100
        pnl = position.quantity * position.entry_price * (pnl_pct / 100) - fee

        logger.info("[SHADOW] Cierre %s %s precio=%.2f motivo=%s pnl=%.2f", position.side, symbol, price, reason, pnl)

        if position.trade_id is not None:
            with session_scope() as session:
                trade = session.get(Trade, position.trade_id)
                if trade is not None:
                    trade.exit_price = price
                    trade.pnl = pnl
                    trade.pnl_pct = pnl_pct
                    trade.fees = (trade.fees or 0.0) + fee
                    trade.is_open = False
                    trade.closed_at = datetime.now(timezone.utc)

        return pnl, pnl_pct
