"""Métricas de evaluación para curvas de equity y listas de trades."""
from __future__ import annotations

import numpy as np
import pandas as pd


def total_return_pct(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] == 0:
        return 0.0
    return (equity.iloc[-1] / equity.iloc[0] - 1) * 100


def max_drawdown_pct(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max.replace(0, np.nan)
    return float(drawdown.min() * 100) if not drawdown.empty else 0.0


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 365 * 24) -> float:
    """Sharpe anualizado a partir de retornos por barra (asume tasa libre de riesgo = 0)."""
    if returns.std(ddof=0) == 0 or returns.empty:
        return 0.0
    return float(returns.mean() / returns.std(ddof=0) * np.sqrt(periods_per_year))


def win_rate_pct(trade_pnls: list[float]) -> float:
    if not trade_pnls:
        return 0.0
    wins = sum(1 for p in trade_pnls if p > 0)
    return wins / len(trade_pnls) * 100


def profit_factor(trade_pnls: list[float]) -> float:
    gains = sum(p for p in trade_pnls if p > 0)
    losses = abs(sum(p for p in trade_pnls if p < 0))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def summarize(equity: pd.Series, returns: pd.Series, trade_pnls: list[float], periods_per_year: int) -> dict:
    return {
        "total_return_pct": total_return_pct(equity),
        "max_drawdown_pct": max_drawdown_pct(equity),
        "sharpe_ratio": sharpe_ratio(returns, periods_per_year),
        "win_rate_pct": win_rate_pct(trade_pnls),
        "num_trades": len(trade_pnls),
        "profit_factor": profit_factor(trade_pnls),
    }
