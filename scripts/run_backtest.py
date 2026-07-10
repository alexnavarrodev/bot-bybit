#!/usr/bin/env python3
"""Descarga histórico de Bybit y compara las 5 estrategias en BTC/USDT y ETH/USDT.

Uso:
    python scripts/run_backtest.py --symbols "BTC/USDT:USDT,ETH/USDT:USDT" \
        --timeframe 4h --bars 2000
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.backtest.engine import Backtester
from src.database.db import init_db, session_scope
from src.database.models import BacktestRun
from src.exchange.bybit_client import BybitClient
from src.logging_setup import setup_logging
from src.strategies import STRATEGY_REGISTRY

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backtest comparativo de estrategias")
    parser.add_argument("--symbols", default="BTC/USDT:USDT,ETH/USDT:USDT")
    parser.add_argument("--timeframe", default="4h")
    parser.add_argument("--bars", type=int, default=2000, help="Número de velas históricas a descargar")
    parser.add_argument("--initial-balance", type=float, default=10_000.0)
    parser.add_argument("--save-csv", default="data/backtest_results.csv")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    client = BybitClient()
    backtester = Backtester(initial_balance=args.initial_balance)
    init_db()

    rows = []
    for symbol in symbols:
        logger.info("Descargando histórico de %s (%s, %d velas)...", symbol, args.timeframe, args.bars)
        df = client.fetch_ohlcv_history(symbol, timeframe=args.timeframe, max_bars=args.bars)
        if df.empty:
            logger.warning("Sin datos para %s, se omite", symbol)
            continue

        for strategy_name, strategy_cls in STRATEGY_REGISTRY.items():
            strategy = strategy_cls()
            try:
                result = backtester.run(df, strategy, symbol=symbol, timeframe=args.timeframe)
            except ValueError as exc:
                logger.warning("Omitiendo %s/%s: %s", strategy_name, symbol, exc)
                continue

            m = result.metrics
            rows.append(
                {
                    "symbol": symbol,
                    "strategy": strategy_name,
                    "return_%": round(m["total_return_pct"], 2),
                    "max_dd_%": round(m["max_drawdown_pct"], 2),
                    "sharpe": round(m["sharpe_ratio"], 2),
                    "win_rate_%": round(m["win_rate_pct"], 2),
                    "trades": m["num_trades"],
                    "profit_factor": round(m["profit_factor"], 2) if m["profit_factor"] != float("inf") else "inf",
                    "final_balance": round(m["final_balance"], 2),
                }
            )

            with session_scope() as session:
                session.add(
                    BacktestRun(
                        strategy=strategy_name,
                        symbol=symbol,
                        timeframe=args.timeframe,
                        start=df.index[0].to_pydatetime(),
                        end=df.index[-1].to_pydatetime(),
                        initial_balance=args.initial_balance,
                        final_balance=m["final_balance"],
                        total_return_pct=m["total_return_pct"],
                        max_drawdown_pct=m["max_drawdown_pct"],
                        sharpe_ratio=m["sharpe_ratio"],
                        win_rate_pct=m["win_rate_pct"],
                        num_trades=m["num_trades"],
                        profit_factor=0.0 if m["profit_factor"] == float("inf") else m["profit_factor"],
                    )
                )

    if not rows:
        logger.error("No se generó ningún resultado.")
        return

    results_df = pd.DataFrame(rows).sort_values(["symbol", "return_%"], ascending=[True, False])
    Path(args.save_csv).parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.save_csv, index=False)

    pd.set_option("display.width", 160)
    print("\n=== Resultados de backtest (ordenado por retorno) ===\n")
    print(results_df.to_string(index=False))
    print(f"\nGuardado en {args.save_csv} y en la tabla backtest_runs de la base de datos.")


if __name__ == "__main__":
    main()
