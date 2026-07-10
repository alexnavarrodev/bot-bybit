"""2) RSI Mean Reversion: compra en sobreventa, vende en sobrecompra, salida en la zona neutra."""
from __future__ import annotations

import pandas as pd

from src.indicators import rsi
from src.strategies.base import BaseStrategy
from src.strategies.utils import build_stateful_position


class RsiMeanReversionStrategy(BaseStrategy):
    name = "rsi_mean_reversion"

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        exit_mid: float = 50.0,
        allow_short: bool = True,
    ):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.exit_mid = exit_mid
        self.allow_short = allow_short
        self.min_bars = period + 10

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["rsi"] = rsi(out["close"], self.period)
        return out

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        out = self.compute_indicators(df)
        long_entry = out["rsi"] < self.oversold
        long_exit = out["rsi"] > self.exit_mid
        short_entry = out["rsi"] > self.overbought
        short_exit = out["rsi"] < self.exit_mid
        return build_stateful_position(long_entry, long_exit, short_entry, short_exit, self.allow_short)
