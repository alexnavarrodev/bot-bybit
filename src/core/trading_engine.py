"""Loop de trading compartido entre shadow (paper) y live (real).

Cada ciclo: obtiene velas recientes, calcula la señal de la estrategia, abre/cierra
posiciones según la señal y el stop-loss/take-profit, y persiste todo en la BD +
Telegram. Las subclases solo difieren en cómo se ejecutan las entradas/salidas
(simuladas vs. órdenes reales en Bybit).
"""
from __future__ import annotations

import abc
import logging
import time

from src.config import settings
from src.database.db import init_db, session_scope
from src.database.models import EquitySnapshot, Signal as SignalModel, Trade
from src.exchange.bybit_client import BybitClient
from src.indicators import atr
from src.notifications.telegram_notifier import TelegramNotifier
from src.strategies import get_strategy
from src.strategies.base import PositionSignal
from src.core.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class OpenPosition:
    def __init__(self, side: str, entry_price: float, quantity: float, stop_loss: float, take_profit: float, trade_id: int | None):
        self.side = side
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.trade_id = trade_id


class TradingEngine(abc.ABC):
    mode: str = "shadow"

    def __init__(
        self,
        strategy_name: str | None = None,
        symbols: list[str] | None = None,
        timeframe: str | None = None,
        poll_interval: int | None = None,
        initial_balance: float | None = None,
    ):
        self.strategy = get_strategy(strategy_name or settings.strategy)
        self.symbols = symbols or settings.symbols
        self.timeframe = timeframe or settings.timeframe
        self.poll_interval = poll_interval or settings.poll_interval_seconds
        self.client = BybitClient()
        self.notifier = TelegramNotifier()
        self.risk_manager = RiskManager(risk_per_trade=settings.risk_per_trade, max_leverage=settings.leverage)
        # INITIAL_BALANCE es el capital TOTAL de la cuenta, repartido a partes iguales
        # entre los símbolos (cada símbolo opera con su propia porción del bote).
        total_capital = initial_balance if initial_balance is not None else settings.initial_balance
        per_symbol = total_capital / len(self.symbols) if self.symbols else total_capital
        self.balances: dict[str, float] = {s: per_symbol for s in self.symbols}
        self.open_positions: dict[str, OpenPosition] = {}
        init_db()

    def run_forever(self) -> None:
        logger.info(
            "Arrancando %s | estrategia=%s | símbolos=%s | timeframe=%s | intervalo=%ss",
            self.mode, self.strategy.name, self.symbols, self.timeframe, self.poll_interval,
        )
        self.notifier.send(
            f"🚀 Bot iniciado en modo <b>{self.mode}</b>\nEstrategia: {self.strategy.name}\nSímbolos: {', '.join(self.symbols)}"
        )
        while True:
            for symbol in self.symbols:
                try:
                    self.process_symbol(symbol)
                except Exception as exc:  # noqa: BLE001 - el loop no debe morir por un símbolo
                    logger.exception("Error procesando %s", symbol)
                    self.notifier.notify_error(f"{self.mode}:{symbol}", str(exc))
            time.sleep(self.poll_interval)

    def process_symbol(self, symbol: str) -> None:
        needed = max(self.strategy.min_bars + 50, 200)
        df = self.client.fetch_ohlcv_df(symbol, timeframe=self.timeframe, limit=needed)
        if len(df) < self.strategy.min_bars:
            logger.warning("Datos insuficientes para %s (%d velas)", symbol, len(df))
            return

        indicators_df = self.strategy.compute_indicators(df)
        signal = self.strategy.latest_signal(df)
        price = float(df["close"].iloc[-1])
        atr_value = float(atr(df["high"], df["low"], df["close"]).iloc[-1])

        self._persist_signal(symbol, signal, price)

        position = self.open_positions.get(symbol)

        if position is None:
            if signal in (PositionSignal.LONG, PositionSignal.SHORT):
                self._open_position(symbol, signal, price, atr_value)
            return

        hit_sl, hit_tp = self._check_stops(position, price)
        flipped = signal != PositionSignal.FLAT and signal.value != position.side
        should_flatten = signal == PositionSignal.FLAT and False  # una señal FLAT no cierra por sí sola; solo SL/TP o giro

        if hit_sl or hit_tp or flipped:
            reason = "stop_loss" if hit_sl else "take_profit" if hit_tp else "reverse_signal"
            self._close_position(symbol, position, price, reason)
            if flipped:
                self._open_position(symbol, signal, price, atr_value)

    def _check_stops(self, position: OpenPosition, price: float) -> tuple[bool, bool]:
        if position.side == "LONG":
            return price <= position.stop_loss, price >= position.take_profit
        return price >= position.stop_loss, price <= position.take_profit

    def _persist_signal(self, symbol: str, signal: PositionSignal, price: float) -> None:
        with session_scope() as session:
            session.add(
                SignalModel(
                    mode=self.mode,
                    strategy=self.strategy.name,
                    symbol=symbol,
                    timeframe=self.timeframe,
                    signal=signal.value,
                    price=price,
                )
            )

    def _open_position(self, symbol: str, signal: PositionSignal, price: float, atr_value: float) -> None:
        balance = self.balances.get(symbol, settings.initial_balance)
        sizing = self.risk_manager.size_position(balance, price, atr_value, signal.value)
        if sizing.quantity <= 0:
            return

        trade_id = self._execute_entry(symbol, signal, price, sizing)
        self.open_positions[symbol] = OpenPosition(
            side=signal.value,
            entry_price=price,
            quantity=sizing.quantity,
            stop_loss=sizing.stop_loss,
            take_profit=sizing.take_profit,
            trade_id=trade_id,
        )
        self.notifier.notify_signal(self.strategy.name, symbol, signal.value, price, self.mode)

    def _close_position(self, symbol: str, position: OpenPosition, price: float, reason: str) -> None:
        pnl, pnl_pct = self._execute_exit(symbol, position, price, reason)
        self.balances[symbol] = self.balances.get(symbol, settings.initial_balance) + pnl
        self.notifier.notify_trade_closed(self.strategy.name, symbol, position.side, pnl, pnl_pct, self.mode)
        with session_scope() as session:
            session.add(EquitySnapshot(mode=self.mode, strategy=self.strategy.name, symbol=symbol, equity=self.balances[symbol]))
        del self.open_positions[symbol]

    @abc.abstractmethod
    def _execute_entry(self, symbol: str, signal: PositionSignal, price: float, sizing) -> int | None:
        """Debe registrar el Trade (BD) y devolver su id. En live, además envía la orden real."""

    @abc.abstractmethod
    def _execute_exit(self, symbol: str, position: OpenPosition, price: float, reason: str) -> tuple[float, float]:
        """Debe cerrar el Trade (BD) y devolver (pnl_absoluto, pnl_pct)."""
