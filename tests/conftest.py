import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    """Serie de precios sintética con tendencia + ruido, suficiente para todas las estrategias."""
    rng = np.random.default_rng(42)
    n = 500
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")

    trend = np.linspace(0, 30, n)
    cycle = 5 * np.sin(np.linspace(0, 12 * np.pi, n))
    noise = rng.normal(0, 1.5, n)
    close = 100 + trend + cycle + noise
    close = np.maximum(close, 1)

    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    open_ = close + rng.uniform(-0.5, 0.5, n)
    volume = rng.uniform(10, 100, n)

    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)
