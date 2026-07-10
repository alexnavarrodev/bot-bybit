import pytest

from src.strategies import STRATEGY_REGISTRY
from src.strategies.base import PositionSignal


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY.keys()))
def test_strategy_generates_valid_signals(synthetic_ohlcv, name):
    strategy = STRATEGY_REGISTRY[name]()
    signals = strategy.generate_signals(synthetic_ohlcv)

    assert len(signals) == len(synthetic_ohlcv)
    assert set(signals.unique()).issubset({s.value for s in PositionSignal})


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY.keys()))
def test_latest_signal_with_insufficient_data_is_flat(synthetic_ohlcv, name):
    strategy = STRATEGY_REGISTRY[name]()
    tiny_df = synthetic_ohlcv.head(5)
    assert strategy.latest_signal(tiny_df) == PositionSignal.FLAT


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY.keys()))
def test_latest_signal_with_full_data_returns_enum(synthetic_ohlcv, name):
    strategy = STRATEGY_REGISTRY[name]()
    signal = strategy.latest_signal(synthetic_ohlcv)
    assert isinstance(signal, PositionSignal)
