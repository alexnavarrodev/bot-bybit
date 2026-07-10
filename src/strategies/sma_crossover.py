"""1) SMA Crossover: seguimiento de tendencia clásico (cruce dorado / cruce de la muerte)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.indicators import sma
from src.strategies.base import BaseStrategy, PositionSignal


class SmaCrossoverStrategy(BaseStrategy):
    name = "sma_crossover"

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.min_bars = slow_period + 5

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["sma_fast"] = sma(out["close"], self.fast_period)
        out["sma_slow"] = sma(out["close"], self.slow_period)
        return out

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        out = self.compute_indicators(df)
        position = np.where(
            out["sma_fast"] > out["sma_slow"],
            PositionSignal.LONG.value,
            np.where(out["sma_fast"] < out["sma_slow"], PositionSignal.SHORT.value, PositionSignal.FLAT.value),
        )
        signals = pd.Series(position, index=out.index)
        signals[out["sma_slow"].isna()] = PositionSignal.FLAT.value
        return signals
