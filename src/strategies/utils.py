"""Utilidades compartidas entre estrategias con estado (histéresis de entrada/salida)."""
from __future__ import annotations

import pandas as pd

from src.strategies.base import PositionSignal


def build_stateful_position(
    long_entry: pd.Series,
    long_exit: pd.Series,
    short_entry: pd.Series,
    short_exit: pd.Series,
    allow_short: bool = True,
) -> pd.Series:
    """Construye una serie de posición con memoria: permanece en LONG/SHORT hasta que
    se cumpla la condición de salida correspondiente. Evita lookahead: en la fila `i`
    solo se usan valores ya calculados en `i`.
    """
    state = PositionSignal.FLAT
    out = []
    for i in range(len(long_entry)):
        if state == PositionSignal.FLAT:
            if bool(long_entry.iloc[i]):
                state = PositionSignal.LONG
            elif allow_short and bool(short_entry.iloc[i]):
                state = PositionSignal.SHORT
        elif state == PositionSignal.LONG:
            if bool(long_exit.iloc[i]):
                state = PositionSignal.FLAT
        elif state == PositionSignal.SHORT:
            if bool(short_exit.iloc[i]):
                state = PositionSignal.FLAT
        out.append(state.value)
    return pd.Series(out, index=long_entry.index)
