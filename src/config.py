"""Carga y validación de configuración desde variables de entorno (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _get_list(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [s.strip() for s in raw.split(",") if s.strip()]


@dataclass
class Settings:
    # Bybit
    bybit_api_key: str = field(default_factory=lambda: os.getenv("BYBIT_API_KEY", ""))
    bybit_api_secret: str = field(default_factory=lambda: os.getenv("BYBIT_API_SECRET", ""))
    bybit_testnet: bool = field(default_factory=lambda: _get_bool("BYBIT_TESTNET", True))
    bybit_account_type: str = field(default_factory=lambda: os.getenv("BYBIT_ACCOUNT_TYPE", "linear"))

    # Trading
    symbols: list[str] = field(default_factory=lambda: _get_list("SYMBOLS", "BTC/USDT:USDT,ETH/USDT:USDT"))
    timeframe: str = field(default_factory=lambda: os.getenv("TIMEFRAME", "1h"))
    mode: str = field(default_factory=lambda: os.getenv("MODE", "shadow"))
    strategy: str = field(default_factory=lambda: os.getenv("STRATEGY", "sma_crossover"))
    risk_per_trade: float = field(default_factory=lambda: float(os.getenv("RISK_PER_TRADE", "0.01")))
    leverage: float = field(default_factory=lambda: float(os.getenv("LEVERAGE", "1")))
    initial_balance: float = field(default_factory=lambda: float(os.getenv("INITIAL_BALANCE", "10000")))

    # Database
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///data/bot.db"))

    # Telegram
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # Loop
    poll_interval_seconds: int = field(default_factory=lambda: int(os.getenv("POLL_INTERVAL_SECONDS", "60")))

    # Dashboard
    dashboard_user: str = field(default_factory=lambda: os.getenv("DASHBOARD_USER", "admin"))
    dashboard_password: str = field(default_factory=lambda: os.getenv("DASHBOARD_PASSWORD", ""))

    def validate_for_live(self) -> None:
        if not self.bybit_api_key or not self.bybit_api_secret:
            raise ValueError("BYBIT_API_KEY / BYBIT_API_SECRET son obligatorios en modo live")
        if self.mode == "live" and self.bybit_testnet:
            # No es un error bloqueante, pero se advierte en el arranque del bot.
            pass


settings = Settings()
