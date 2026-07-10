"""Notificador simple de Telegram vía Bot API (requests, sin dependencias pesadas)."""
from __future__ import annotations

import logging

import requests

from src.config import settings

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token if bot_token is not None else settings.telegram_bot_token
        self.chat_id = chat_id if chat_id is not None else settings.telegram_chat_id
        self.enabled = bool(self.bot_token and self.chat_id)
        if not self.enabled:
            logger.warning("Telegram no configurado (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID vacíos); alertas solo por log.")

    def send(self, message: str) -> None:
        if not self.enabled:
            logger.info("[telegram-disabled] %s", message)
            return
        url = _API_BASE.format(token=self.bot_token)
        try:
            resp = requests.post(
                url,
                json={"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Fallo enviando alerta de Telegram: %s", exc)

    def notify_signal(self, strategy: str, symbol: str, signal: str, price: float, mode: str) -> None:
        emoji = {"LONG": "🟢", "SHORT": "🔴", "FLAT": "⚪"}.get(signal, "ℹ️")
        self.send(
            f"{emoji} <b>{signal}</b> señal\n"
            f"Estrategia: {strategy}\n"
            f"Símbolo: {symbol}\n"
            f"Precio: {price:.2f}\n"
            f"Modo: {mode}"
        )

    def notify_trade_closed(self, strategy: str, symbol: str, side: str, pnl: float, pnl_pct: float, mode: str) -> None:
        emoji = "✅" if pnl >= 0 else "❌"
        self.send(
            f"{emoji} Trade cerrado ({mode})\n"
            f"Estrategia: {strategy} | {symbol} | {side}\n"
            f"PnL: {pnl:.2f} USDT ({pnl_pct:.2f}%)"
        )

    def notify_error(self, context: str, error: str) -> None:
        self.send(f"⚠️ Error en {context}:\n<code>{error}</code>")
