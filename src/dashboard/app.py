"""Dashboard web de solo lectura: rendimiento y operaciones del bot (shadow/live/backtest).

Sirve una página HTML (equity curve, posiciones abiertas, trades y señales recientes)
protegida con HTTP Basic Auth. Lee directamente de la misma base de datos que usa el bot.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import select

from src.config import settings
from src.database.db import get_session_factory, init_db
from src.database.models import EquitySnapshot, Signal, Trade

app = FastAPI(title="Bot Bybit - Dashboard")
security = HTTPBasic()


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _check_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    valid_user = secrets.compare_digest(credentials.username, settings.dashboard_user)
    valid_pass = secrets.compare_digest(credentials.password, settings.dashboard_password)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=401, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Basic"})


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


@app.get("/api/summary")
def api_summary(_: None = Depends(_check_auth)) -> JSONResponse:
    Session = get_session_factory()
    with Session() as session:
        open_trades = session.scalars(select(Trade).where(Trade.is_open.is_(True))).all()
        latest_by_key: dict[tuple[str, str, str], EquitySnapshot] = {}
        for snap in session.scalars(select(EquitySnapshot).order_by(EquitySnapshot.created_at.asc())):
            latest_by_key[(snap.mode, snap.strategy, snap.symbol)] = snap

        summary = []
        for key, snap in latest_by_key.items():
            mode, strategy, symbol = key
            open_trade = next((t for t in open_trades if t.mode == mode and t.strategy == strategy and t.symbol == symbol), None)
            summary.append(
                {
                    "mode": mode,
                    "strategy": strategy,
                    "symbol": symbol,
                    "equity": snap.equity,
                    "updated_at": _iso(snap.created_at),
                    "open_position": (
                        {
                            "side": open_trade.side,
                            "entry_price": open_trade.entry_price,
                            "quantity": open_trade.quantity,
                            "stop_loss": open_trade.stop_loss,
                            "take_profit": open_trade.take_profit,
                            "opened_at": _iso(open_trade.opened_at),
                        }
                        if open_trade
                        else None
                    ),
                }
            )
        return JSONResponse(summary)


@app.get("/api/equity")
def api_equity(limit: int = 500, _: None = Depends(_check_auth)) -> JSONResponse:
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(
            select(EquitySnapshot).order_by(EquitySnapshot.created_at.desc()).limit(limit)
        ).all()
        rows.reverse()
        return JSONResponse(
            [
                {
                    "mode": r.mode,
                    "strategy": r.strategy,
                    "symbol": r.symbol,
                    "equity": r.equity,
                    "created_at": _iso(r.created_at),
                }
                for r in rows
            ]
        )


@app.get("/api/trades")
def api_trades(limit: int = 100, _: None = Depends(_check_auth)) -> JSONResponse:
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(select(Trade).order_by(Trade.opened_at.desc()).limit(limit)).all()
        return JSONResponse(
            [
                {
                    "id": r.id,
                    "mode": r.mode,
                    "strategy": r.strategy,
                    "symbol": r.symbol,
                    "side": r.side,
                    "entry_price": r.entry_price,
                    "exit_price": r.exit_price,
                    "quantity": r.quantity,
                    "pnl": r.pnl,
                    "pnl_pct": r.pnl_pct,
                    "is_open": r.is_open,
                    "opened_at": _iso(r.opened_at),
                    "closed_at": _iso(r.closed_at),
                }
                for r in rows
            ]
        )


@app.get("/api/signals")
def api_signals(limit: int = 100, _: None = Depends(_check_auth)) -> JSONResponse:
    Session = get_session_factory()
    with Session() as session:
        rows = session.scalars(select(Signal).order_by(Signal.created_at.desc()).limit(limit)).all()
        return JSONResponse(
            [
                {
                    "id": r.id,
                    "mode": r.mode,
                    "strategy": r.strategy,
                    "symbol": r.symbol,
                    "timeframe": r.timeframe,
                    "signal": r.signal,
                    "price": r.price,
                    "created_at": _iso(r.created_at),
                }
                for r in rows
            ]
        )


@app.get("/", response_class=HTMLResponse)
def index(_: None = Depends(_check_auth)) -> str:
    return _DASHBOARD_HTML


_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bot Bybit - Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3"></script>
<style>
  :root { color-scheme: dark; }
  body { background:#0f1117; color:#e6e6e6; font-family:-apple-system,Segoe UI,Roboto,sans-serif; margin:0; padding:24px; }
  h1 { font-size:1.4rem; margin-bottom:4px; }
  .subtitle { color:#9aa0ac; margin-bottom:24px; font-size:0.9rem; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px,1fr)); gap:16px; margin-bottom:24px; }
  .card { background:#171a21; border:1px solid #262b36; border-radius:10px; padding:16px; }
  .card h3 { margin:0 0 8px 0; font-size:0.95rem; color:#c9cdd6; }
  .equity { font-size:1.6rem; font-weight:600; }
  .pos-long { color:#3ecf8e; } .pos-short { color:#ef5b5b; } .pos-flat { color:#9aa0ac; }
  table { width:100%; border-collapse:collapse; font-size:0.85rem; }
  th, td { text-align:left; padding:6px 8px; border-bottom:1px solid #262b36; }
  th { color:#9aa0ac; font-weight:500; }
  .pnl-pos { color:#3ecf8e; } .pnl-neg { color:#ef5b5b; }
  .section { margin-bottom:32px; }
  canvas { max-height:320px; }
  .tag { display:inline-block; padding:1px 8px; border-radius:999px; font-size:0.75rem; background:#262b36; }
</style>
</head>
<body>
  <h1>🤖 Bot Bybit — Dashboard</h1>
  <div class="subtitle">Rendimiento y operaciones en vivo. Se actualiza cada 30s.</div>

  <div class="grid" id="summary-grid"></div>

  <div class="section card">
    <h3>Curva de equity</h3>
    <canvas id="equityChart"></canvas>
  </div>

  <div class="section card">
    <h3>Últimas operaciones</h3>
    <table id="trades-table">
      <thead><tr><th>Fecha</th><th>Símbolo</th><th>Estrategia</th><th>Lado</th><th>Entrada</th><th>Salida</th><th>PnL</th><th>Estado</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="section card">
    <h3>Últimas señales</h3>
    <table id="signals-table">
      <thead><tr><th>Fecha</th><th>Símbolo</th><th>Estrategia</th><th>Señal</th><th>Precio</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

<script>
let chart;

function fmt(n, d=2) { return (n === null || n === undefined) ? '-' : Number(n).toFixed(d); }
function fmtDate(s) { return s ? new Date(s).toLocaleString() : '-'; }

async function refresh() {
  const [summary, equity, trades, signals] = await Promise.all([
    fetch('/api/summary').then(r => r.json()),
    fetch('/api/equity?limit=1000').then(r => r.json()),
    fetch('/api/trades?limit=50').then(r => r.json()),
    fetch('/api/signals?limit=50').then(r => r.json()),
  ]);

  const grid = document.getElementById('summary-grid');
  grid.innerHTML = summary.map(s => {
    const pos = s.open_position;
    const posClass = pos ? (pos.side === 'LONG' ? 'pos-long' : 'pos-short') : 'pos-flat';
    const posText = pos
      ? `${pos.side} @ ${fmt(pos.entry_price)} (qty ${fmt(pos.quantity, 6)})`
      : 'Sin posición abierta';
    return `<div class="card">
      <h3>${s.symbol} <span class="tag">${s.strategy}</span> <span class="tag">${s.mode}</span></h3>
      <div class="equity">${fmt(s.equity)} USDT</div>
      <div class="${posClass}">${posText}</div>
    </div>`;
  }).join('') || '<div class="card">Aún no hay datos. Espera al primer ciclo del bot.</div>';

  const bySymbol = {};
  equity.forEach(e => {
    const key = `${e.symbol} (${e.strategy})`;
    if (!bySymbol[key]) bySymbol[key] = [];
    bySymbol[key].push({ x: e.created_at, y: e.equity });
  });
  const datasets = Object.entries(bySymbol).map(([label, data], i) => ({
    label, data, borderWidth: 2, pointRadius: 0, tension: 0.15,
    borderColor: ['#3ecf8e', '#5b8def', '#ef5b5b', '#e6b800', '#b06bde'][i % 5],
  }));

  if (chart) chart.destroy();
  chart = new Chart(document.getElementById('equityChart'), {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      scales: { x: { type: 'time', time: { unit: 'hour' }, ticks: { color: '#9aa0ac' } }, y: { ticks: { color: '#9aa0ac' } } },
      plugins: { legend: { labels: { color: '#e6e6e6' } } },
    },
  });

  document.querySelector('#trades-table tbody').innerHTML = trades.map(t => `
    <tr>
      <td>${fmtDate(t.opened_at)}</td>
      <td>${t.symbol}</td>
      <td>${t.strategy}</td>
      <td>${t.side}</td>
      <td>${fmt(t.entry_price)}</td>
      <td>${fmt(t.exit_price)}</td>
      <td class="${(t.pnl ?? 0) >= 0 ? 'pnl-pos' : 'pnl-neg'}">${t.pnl !== null ? fmt(t.pnl) + ' (' + fmt(t.pnl_pct) + '%)' : '-'}</td>
      <td>${t.is_open ? 'Abierta' : 'Cerrada'}</td>
    </tr>`).join('');

  document.querySelector('#signals-table tbody').innerHTML = signals.map(s => `
    <tr>
      <td>${fmtDate(s.created_at)}</td>
      <td>${s.symbol}</td>
      <td>${s.strategy}</td>
      <td>${s.signal}</td>
      <td>${fmt(s.price)}</td>
    </tr>`).join('');
}

refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>
"""
