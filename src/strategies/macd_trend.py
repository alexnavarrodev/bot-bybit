"""3) MACD Trend Following: cruce de la línea MACD sobre su señal, confirmando tendencia."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.indicators import macd
from src.strategies.base import BaseStrategy, PositionSignal


class MacdTrendStrategy(BaseStrategy):
    name = "macd_trend"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.min_bars = slow + signal + 5

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        macd_df = macd(out["close"], self.fast, self.slow, self.signal)
        out["macd"] = macd_df["macd"]
        out["macd_signal"] = macd_df["signal"]
        out["macd_hist"] = macd_df["histogram"]
        return out

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        out = self.compute_indicators(df)
        position = np.where(
            out["macd"] > out["macd_signal"],
            PositionSignal.LONG.value,
            np.where(out["macd"] < out["macd_signal"], PositionSignal.SHORT.value, PositionSignal.FLAT.value),
        )
        signals = pd.Series(position, index=out.index)
        signals[out["macd_signal"].isna()] = PositionSignal.FLAT.value
        return signals
