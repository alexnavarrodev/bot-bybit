"""Motor de backtesting vectorizado con comisiones, para comparar estrategias."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.backtest.metrics import summarize
from src.strategies.base import BaseStrategy

_TIMEFRAME_MINUTES = {
    "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "6h": 360, "12h": 720,
    "1d": 1440,
}


def _periods_per_year(timeframe: str) -> int:
    minutes = _TIMEFRAME_MINUTES.get(timeframe, 60)
    return int((365 * 24 * 60) / minutes)


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    returns: pd.Series
    trades: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


class Backtester:
    """Backtest de una sola posición (long/short/flat) por símbolo, sin apalancamiento
    compuesto por defecto: cada trade arriesga el 100% del capital inicial (simplificación
    para comparar estrategias entre sí, no para dimensionar tamaño de posición real)."""

    def __init__(self, initial_balance: float = 10_000.0, fee_rate: float = 0.00055):
        self.initial_balance = initial_balance
        self.fee_rate = fee_rate  # comisión taker de Bybit por operación (0.055%)

    def run(self, df: pd.DataFrame, strategy: BaseStrategy, symbol: str = "", timeframe: str = "1h") -> BacktestResult:
        clean = df.dropna(subset=["close"]).copy()
        if len(clean) < strategy.min_bars:
            raise ValueError(f"Se necesitan al menos {strategy.min_bars} velas, hay {len(clean)}")

        signals = strategy.generate_signals(clean)
        pos_map = {"LONG": 1, "SHORT": -1, "FLAT": 0}
        raw_pos = signals.map(pos_map).fillna(0)
        # La señal calculada con el cierre de la vela t se ejecuta en la vela t+1 (sin lookahead).
        executed_pos = raw_pos.shift(1).fillna(0)

        price_returns = clean["close"].pct_change().fillna(0)
        gross_returns = executed_pos * price_returns

        pos_change = executed_pos.diff().fillna(0).abs()
        fee_cost = pos_change * self.fee_rate
        net_returns = gross_returns - fee_cost

        equity = (1 + net_returns).cumprod() * self.initial_balance

        trades = self._extract_trades(clean, executed_pos, symbol)
        trade_pnls = [t["pnl"] for t in trades]

        metrics = summarize(equity, net_returns, trade_pnls, _periods_per_year(timeframe))
        metrics["final_balance"] = float(equity.iloc[-1]) if len(equity) else self.initial_balance
        metrics["initial_balance"] = self.initial_balance

        return BacktestResult(equity_curve=equity, returns=net_returns, trades=trades, metrics=metrics)

    def _extract_trades(self, df: pd.DataFrame, executed_pos: pd.Series, symbol: str) -> list[dict]:
        trades: list[dict] = []
        direction = 0
        entry_idx = None
        entry_price = None

        for i in range(len(executed_pos)):
            pos = executed_pos.iloc[i]
            if direction == 0 and pos != 0:
                direction = pos
                entry_idx = df.index[i]
                entry_price = float(df["close"].iloc[i])
            elif direction != 0 and pos != direction:
                exit_idx = df.index[i]
                exit_price = float(df["close"].iloc[i])
                pnl_pct = direction * (exit_price / entry_price - 1) * 100
                pnl = self.initial_balance * (pnl_pct / 100)
                trades.append(
                    {
                        "symbol": symbol,
                        "side": "LONG" if direction == 1 else "SHORT",
                        "entry_time": entry_idx,
                        "exit_time": exit_idx,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl_pct": float(pnl_pct),
                        "pnl": float(pnl),
                    }
                )
                if pos != 0:
                    direction = pos
                    entry_idx = df.index[i]
                    entry_price = float(df["close"].iloc[i])
                else:
                    direction = 0
                    entry_idx = None
                    entry_price = None

        return trades
