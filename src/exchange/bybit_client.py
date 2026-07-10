"""Wrapper delgado sobre ccxt.bybit: OHLCV, ticker, balance y órdenes."""
from __future__ import annotations

import logging

import ccxt
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

logger = logging.getLogger(__name__)


class BybitClient:
    """Cliente CCXT genérico. Por defecto Bybit, pero el exchange es configurable
    (EXCHANGE en .env) para poder usar una fuente de datos accesible desde regiones
    donde Bybit está bloqueado (p. ej. Binance.US o Kraken desde EE.UU.)."""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None, testnet: bool | None = None):
        self.testnet = settings.bybit_testnet if testnet is None else testnet
        exchange_class = getattr(ccxt, settings.exchange_id)
        self.exchange = exchange_class(
            {
                "apiKey": api_key if api_key is not None else settings.bybit_api_key,
                "secret": api_secret if api_secret is not None else settings.bybit_api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": settings.market_type},
            }
        )
        # El modo sandbox/testnet solo aplica a exchanges que lo soportan (Bybit).
        if self.testnet and self.exchange.has.get("sandbox"):
            try:
                self.exchange.set_sandbox_mode(True)
            except Exception:  # noqa: BLE001 - algunos exchanges no lo implementan
                logger.warning("El exchange %s no soporta modo sandbox; usando producción.", settings.exchange_id)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ohlcv_df(self, symbol: str, timeframe: str = "1h", limit: int = 500, since: int | None = None) -> pd.DataFrame:
        """Devuelve un DataFrame OHLCV indexado por timestamp UTC."""
        raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, since=since)
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        return df

    def fetch_ohlcv_history(self, symbol: str, timeframe: str = "1h", since_ms: int | None = None, max_bars: int = 5000) -> pd.DataFrame:
        """Pagina fetch_ohlcv hacia atrás/adelante hasta acumular max_bars velas."""
        all_rows: list[list] = []
        limit = 1000
        cursor = since_ms
        while len(all_rows) < max_bars:
            batch = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, since=cursor)
            if not batch:
                break
            all_rows.extend(batch)
            cursor = batch[-1][0] + 1
            if len(batch) < limit:
                break
        df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df.drop_duplicates(subset="timestamp", inplace=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df.tail(max_bars)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_ticker_price(self, symbol: str) -> float:
        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker["last"])

    def fetch_balance(self, currency: str = "USDT") -> float:
        balance = self.exchange.fetch_balance()
        return float(balance.get(currency, {}).get("free", 0.0))

    def create_market_order(self, symbol: str, side: str, amount: float, params: dict | None = None):
        """side: 'buy' o 'sell'. Solo debe usarse en modo live."""
        logger.info("Creando orden de mercado %s %s %.6f", side, symbol, amount)
        return self.exchange.create_order(symbol, "market", side, amount, params=params or {})

    def create_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float):
        """side: lado de cierre ('sell' para cerrar long, 'buy' para cerrar short)."""
        params = {"stopLoss": stop_price, "reduceOnly": True}
        return self.exchange.create_order(symbol, "market", side, amount, params=params)
