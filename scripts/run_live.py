#!/usr/bin/env python3
"""Arranca el trading EN VIVO (órdenes reales en Bybit). Requiere --i-understand-the-risk.

No lo uses hasta haber validado la estrategia con backtest y, sobre todo, con varias
semanas de shadow trading. Empieza siempre con BYBIT_TESTNET=true.

Uso:
    python scripts/run_live.py --strategy sma_crossover --i-understand-the-risk
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.core.live_trader import LiveTrader
from src.logging_setup import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live trading (órdenes reales en Bybit)")
    parser.add_argument("--strategy", default=settings.strategy)
    parser.add_argument("--symbols", default=",".join(settings.symbols))
    parser.add_argument("--timeframe", default=settings.timeframe)
    parser.add_argument("--poll-interval", type=int, default=settings.poll_interval_seconds)
    parser.add_argument("--initial-balance", type=float, default=settings.initial_balance)
    parser.add_argument(
        "--i-understand-the-risk",
        action="store_true",
        help="Confirmación explícita obligatoria: este modo envía órdenes reales.",
    )
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    if not args.i_understand_the_risk:
        print("Debes pasar --i-understand-the-risk para operar con dinero real. Abortando.")
        sys.exit(1)

    trader = LiveTrader(
        strategy_name=args.strategy,
        symbols=symbols,
        timeframe=args.timeframe,
        poll_interval=args.poll_interval,
        initial_balance=args.initial_balance,
        confirm_live=True,
    )
    trader.run_forever()


if __name__ == "__main__":
    main()
