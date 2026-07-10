import pytest

from src.backtest.engine import Backtester
from src.strategies import STRATEGY_REGISTRY


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY.keys()))
def test_backtester_runs_and_produces_metrics(synthetic_ohlcv, name):
    strategy = STRATEGY_REGISTRY[name]()
    backtester = Backtester(initial_balance=10_000.0)

    result = backtester.run(synthetic_ohlcv, strategy, symbol="BTC/USDT:USDT", timeframe="1h")

    assert len(result.equity_curve) == len(synthetic_ohlcv)
    assert result.equity_curve.iloc[0] > 0
    for key in ("total_return_pct", "max_drawdown_pct", "sharpe_ratio", "win_rate_pct", "num_trades", "profit_factor"):
        assert key in result.metrics


def test_backtester_raises_on_insufficient_data():
    from src.strategies.sma_crossover import SmaCrossoverStrategy
    import pandas as pd

    tiny_df = pd.DataFrame(
        {"open": [1, 2], "high": [1, 2], "low": [1, 2], "close": [1, 2], "volume": [1, 1]},
        index=pd.date_range("2024-01-01", periods=2, freq="1h", tz="UTC"),
    )
    backtester = Backtester()
    with pytest.raises(ValueError):
        backtester.run(tiny_df, SmaCrossoverStrategy())
