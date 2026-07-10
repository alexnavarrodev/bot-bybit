"""4) Bollinger Bands Breakout: entra en la ruptura de volatilidad, sale en la reversión a la media."""
from __future__ import annotations

import pandas as pd

from src.indicators import bollinger_bands
from src.strategies.base import BaseStrategy
from src.strategies.utils import build_stateful_position


class BollingerBreakoutStrategy(BaseStrategy):
    name = "bollinger_breakout"

    def __init__(self, period: int = 20, num_std: float = 2.0, allow_short: bool = True):
        self.period = period
        self.num_std = num_std
        self.allow_short = allow_short
        self.min_bars = period + 10

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        bb = bollinger_bands(out["close"], self.period, self.num_std)
        out["bb_mid"] = bb["mid"]
        out["bb_upper"] = bb["upper"]
        out["bb_lower"] = bb["lower"]
        return out

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        out = self.compute_indicators(df)
        long_entry = out["close"] > out["bb_upper"]
        long_exit = out["close"] < out["bb_mid"]
        short_entry = out["close"] < out["bb_lower"]
        short_exit = out["close"] > out["bb_mid"]
        return build_stateful_position(long_entry, long_exit, short_entry, short_exit, self.allow_short)
