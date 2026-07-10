"""Modelos ORM (SQLAlchemy 2.0) compartidos por backtest, shadow y live trading."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Float, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Signal(Base):
    """Señal generada por una estrategia (LONG/SHORT/FLAT), con o sin ejecución."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    mode: Mapped[str] = mapped_column(String(16))  # backtest | shadow | live
    strategy: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32))
    timeframe: Mapped[str] = mapped_column(String(8))
    signal: Mapped[str] = mapped_column(String(8))  # LONG | SHORT | FLAT
    price: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Trade(Base):
    """Operación (real o simulada) abierta y/o cerrada por el bot."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mode: Mapped[str] = mapped_column(String(16))  # backtest | shadow | live
    strategy: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))  # LONG | SHORT
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    exchange_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class EquitySnapshot(Base):
    """Punto de la curva de equity (usado en backtest y shadow trading)."""

    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    mode: Mapped[str] = mapped_column(String(16))
    strategy: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32))
    equity: Mapped[float] = mapped_column(Float)


class BacktestRun(Base):
    """Resumen de una ejecución de backtest (para comparar estrategias)."""

    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    strategy: Mapped[str] = mapped_column(String(64))
    symbol: Mapped[str] = mapped_column(String(32))
    timeframe: Mapped[str] = mapped_column(String(8))
    start: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    initial_balance: Mapped[float] = mapped_column(Float)
    final_balance: Mapped[float] = mapped_column(Float)
    total_return_pct: Mapped[float] = mapped_column(Float)
    max_drawdown_pct: Mapped[float] = mapped_column(Float)
    sharpe_ratio: Mapped[float] = mapped_column(Float)
    win_rate_pct: Mapped[float] = mapped_column(Float)
    num_trades: Mapped[int] = mapped_column(Integer)
    profit_factor: Mapped[float] = mapped_column(Float)
