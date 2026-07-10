import numpy as np

from src.indicators import atr, bollinger_bands, donchian_channel, ema, macd, rsi, sma


def test_sma_matches_pandas(synthetic_ohlcv):
    result = sma(synthetic_ohlcv["close"], 10)
    expected = synthetic_ohlcv["close"].rolling(10).mean()
    assert np.allclose(result.dropna(), expected.dropna())


def test_ema_no_lookahead_and_bounded(synthetic_ohlcv):
    result = ema(synthetic_ohlcv["close"], 20)
    valid = result.dropna()
    assert len(valid) == len(synthetic_ohlcv) - 19
    assert valid.between(synthetic_ohlcv["close"].min() * 0.5, synthetic_ohlcv["close"].max() * 1.5).all()


def test_rsi_bounded_0_100(synthetic_ohlcv):
    result = rsi(synthetic_ohlcv["close"], 14).dropna()
    assert (result >= 0).all() and (result <= 100).all()


def test_macd_columns(synthetic_ohlcv):
    result = macd(synthetic_ohlcv["close"])
    assert set(result.columns) == {"macd", "signal", "histogram"}
    valid = result.dropna()
    assert np.allclose(valid["histogram"], valid["macd"] - valid["signal"])


def test_bollinger_bands_ordering(synthetic_ohlcv):
    bb = bollinger_bands(synthetic_ohlcv["close"], 20, 2.0).dropna()
    assert (bb["upper"] >= bb["mid"]).all()
    assert (bb["mid"] >= bb["lower"]).all()


def test_donchian_channel_ordering(synthetic_ohlcv):
    dc = donchian_channel(synthetic_ohlcv["high"], synthetic_ohlcv["low"], 20).dropna()
    assert (dc["upper"] >= dc["mid"]).all()
    assert (dc["mid"] >= dc["lower"]).all()


def test_atr_non_negative(synthetic_ohlcv):
    result = atr(synthetic_ohlcv["high"], synthetic_ohlcv["low"], synthetic_ohlcv["close"], 14).dropna()
    assert (result >= 0).all()
