"""Gestión de riesgo: dimensionado de posición y niveles de stop-loss / take-profit."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionSizing:
    quantity: float
    stop_loss: float
    take_profit: float
    notional: float


class RiskManager:
    """Arriesga un porcentaje fijo del balance por operación, con stop basado en ATR
    y take-profit definido por un ratio riesgo/beneficio."""

    def __init__(
        self,
        risk_per_trade: float = 0.01,
        atr_multiplier_sl: float = 2.0,
        risk_reward_ratio: float = 2.0,
        max_leverage: float = 1.0,
    ):
        self.risk_per_trade = risk_per_trade
        self.atr_multiplier_sl = atr_multiplier_sl
        self.risk_reward_ratio = risk_reward_ratio
        self.max_leverage = max_leverage

    def size_position(self, balance: float, entry_price: float, atr_value: float, side: str) -> PositionSizing:
        if atr_value <= 0:
            atr_value = entry_price * 0.01  # fallback conservador si no hay ATR válido

        risk_amount = balance * self.risk_per_trade
        stop_distance = atr_value * self.atr_multiplier_sl

        if side == "LONG":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + stop_distance * self.risk_reward_ratio
        else:
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - stop_distance * self.risk_reward_ratio

        quantity = risk_amount / stop_distance if stop_distance > 0 else 0.0
        notional = quantity * entry_price
        max_notional = balance * self.max_leverage
        if notional > max_notional and entry_price > 0:
            quantity = max_notional / entry_price
            notional = max_notional

        return PositionSizing(
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            notional=notional,
        )
