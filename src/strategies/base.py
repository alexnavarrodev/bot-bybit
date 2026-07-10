"""Interfaz común para todas las estrategias de trading."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

import pandas as pd


class PositionSignal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class BaseStrategy(ABC):
    """Toda estrategia recibe un DataFrame OHLCV y produce una serie de posiciones deseadas.

    `generate_signals` debe ser vectorizada y usar solo datos hasta la fila `t` (sin lookahead).
    El backtester/shadow trader se encarga de aplicar el desfase de ejecución (shift).
    """

    name: str = "base"
    min_bars: int = 50

    @abstractmethod
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Devuelve una copia de df con columnas de indicadores añadidas."""

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Devuelve una Serie alineada al índice de df con valores PositionSignal."""

    def latest_signal(self, df: pd.DataFrame) -> PositionSignal:
        """Conveniencia para shadow/live: última señal disponible con los datos actuales."""
        if len(df) < self.min_bars:
            return PositionSignal.FLAT
        signals = self.generate_signals(df)
        return PositionSignal(signals.iloc[-1])
