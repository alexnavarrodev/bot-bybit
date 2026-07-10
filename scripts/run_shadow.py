#!/usr/bin/env python3
"""Arranca el shadow trader (paper trading 24/7 con datos reales de Bybit, sin órdenes reales).

Uso:
    python scripts/run_shadow.py --strategy sma_crossover --symbols "BTC/USDT:USDT,ETH/USDT:USDT"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.core.shadow_trader import ShadowTrader
from src.logging_setup import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shadow trading (paper trading en vivo)")
    parser.add_argument("--strategy", default=settings.strategy)
    parser.add_argument("--symbols", default=",".join(settings.symbols))
    parser.add_argument("--timeframe", default=settings.timeframe)
    parser.add_argument("--poll-interval", type=int, default=settings.poll_interval_seconds)
    parser.add_argument("--initial-balance", type=float, default=settings.initial_balance)
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    trader = ShadowTrader(
        strategy_name=args.strategy,
        symbols=symbols,
        timeframe=args.timeframe,
        poll_interval=args.poll_interval,
        initial_balance=args.initial_balance,
    )
    trader.run_forever()


if __name__ == "__main__":
    main()
