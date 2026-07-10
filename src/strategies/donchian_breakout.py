"""5) Donchian Channel Breakout (estilo Turtle): entra en máximos/mínimos de N periodos,
sale en la ruptura del canal corto en sentido contrario."""
from __future__ import annotations

import pandas as pd

from src.indicators import donchian_channel
from src.strategies.base import BaseStrategy
from src.strategies.utils import build_stateful_position


class DonchianBreakoutStrategy(BaseStrategy):
    name = "donchian_breakout"

    def __init__(self, entry_period: int = 20, exit_period: int = 10, allow_short: bool = True):
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.allow_short = allow_short
        self.min_bars = entry_period + 10

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        entry_ch = donchian_channel(out["high"], out["low"], self.entry_period)
        exit_ch = donchian_channel(out["high"], out["low"], self.exit_period)
        # Se desplaza una posición para comparar el cierre actual contra el canal
        # formado por las velas ANTERIORES (evita usar la propia vela en su ruptura).
        out["donchian_entry_upper"] = entry_ch["upper"].shift(1)
        out["donchian_entry_lower"] = entry_ch["lower"].shift(1)
        out["donchian_exit_upper"] = exit_ch["upper"].shift(1)
        out["donchian_exit_lower"] = exit_ch["lower"].shift(1)
        return out

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        out = self.compute_indicators(df)
        long_entry = out["close"] > out["donchian_entry_upper"]
        long_exit = out["close"] < out["donchian_exit_lower"]
        short_entry = out["close"] < out["donchian_entry_lower"]
        short_exit = out["close"] > out["donchian_exit_upper"]
        return build_stateful_position(long_entry, long_exit, short_entry, short_exit, self.allow_short)
