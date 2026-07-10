from src.strategies.base import BaseStrategy, PositionSignal
from src.strategies.sma_crossover import SmaCrossoverStrategy
from src.strategies.rsi_mean_reversion import RsiMeanReversionStrategy
from src.strategies.macd_trend import MacdTrendStrategy
from src.strategies.bollinger_breakout import BollingerBreakoutStrategy
from src.strategies.donchian_breakout import DonchianBreakoutStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "sma_crossover": SmaCrossoverStrategy,
    "rsi_mean_reversion": RsiMeanReversionStrategy,
    "macd_trend": MacdTrendStrategy,
    "bollinger_breakout": BollingerBreakoutStrategy,
    "donchian_breakout": DonchianBreakoutStrategy,
}


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    if name not in STRATEGY_REGISTRY:
        raise ValueError(f"Estrategia desconocida: {name}. Disponibles: {list(STRATEGY_REGISTRY)}")
    return STRATEGY_REGISTRY[name](**kwargs)


__all__ = [
    "BaseStrategy",
    "PositionSignal",
    "STRATEGY_REGISTRY",
    "get_strategy",
]
