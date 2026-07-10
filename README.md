# Bot Bybit (Python + CCXT)

Bot de trading algorítmico para Bybit (BTC/USDT y ETH/USDT perpetuos), con:

- **Datos y ejecución** vía [CCXT](https://github.com/ccxt/ccxt) (Bybit).
- **Base de datos** SQLite (local/desarrollo) o PostgreSQL/[Supabase](https://supabase.com) (producción), vía SQLAlchemy — se cambia con una sola variable de entorno.
- **Alertas por Telegram** (señales, aperturas/cierres de trade, errores).
- **3 modos de ejecución**: `backtest` (histórico), `shadow` (paper trading 24/7 con precios reales, sin arriesgar capital) y `live` (órdenes reales).
- **5 estrategias** listas para comparar en BTC y ETH.
- Configuración de despliegue para VPS (systemd o Docker).

## Estructura

```
src/
  config.py                # Variables de entorno (.env)
  indicators.py             # SMA, EMA, RSI, MACD, Bollinger, Donchian, ATR
  exchange/bybit_client.py  # Wrapper de ccxt.bybit
  database/                 # Modelos SQLAlchemy + engine (SQLite / Postgres)
  notifications/             # Telegram
  strategies/                # Las 5 estrategias + interfaz base
  backtest/                  # Motor de backtesting + métricas
  core/                      # Loop compartido, shadow trader, live trader, risk manager
scripts/
  run_backtest.py   # Descarga histórico y compara las 5 estrategias
  run_shadow.py      # Paper trading 24/7 con datos reales
  run_live.py        # Trading real (requiere --i-understand-the-risk)
deploy/
  Dockerfile, docker-compose.yml, *.service (systemd)
```

## 1. Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # y rellena las claves
```

## 2. Configurar Bybit

1. Crea claves API en Bybit (empieza en **testnet**: https://testnet.bybit.com).
2. En `.env`:
   ```
   BYBIT_API_KEY=...
   BYBIT_API_SECRET=...
   BYBIT_TESTNET=true
   ```
3. Para producción, cambia `BYBIT_TESTNET=false` y usa claves de la cuenta real (con permisos mínimos: **solo trading de derivados**, sin retiros).

## 3. Base de datos

**Opción A — SQLite (por defecto, recomendado para shadow/backtest local):**
```
DATABASE_URL=sqlite:///data/bot.db
```

**Opción B — Supabase (Postgres, recomendado para producción/VPS):**
1. Crea un proyecto en https://supabase.com.
2. En *Project Settings → Database* copia la cadena de conexión (usa el **connection pooler**, puerto 6543, para evitar agotar conexiones).
3. En `.env`:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:TU_PASSWORD@db.xxxxx.supabase.co:5432/postgres
   ```

Las tablas (`trades`, `signals`, `equity_snapshots`, `backtest_runs`) se crean automáticamente al arrancar cualquier script (`init_db()`).

## 4. Telegram

1. Habla con [@BotFather](https://t.me/BotFather), crea un bot y copia el token.
2. Escribe al bot y visita `https://api.telegram.org/bot<TOKEN>/getUpdates` para obtener tu `chat_id`.
3. En `.env`:
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```

Si se dejan vacíos, el bot sigue funcionando y solo registra las alertas en el log.

## 5. Backtesting — compara las 5 estrategias

```bash
python scripts/run_backtest.py --symbols "BTC/USDT:USDT,ETH/USDT:USDT" --timeframe 4h --bars 3000
```

Descarga histórico real de Bybit, corre las 5 estrategias sobre BTC y ETH, imprime una tabla comparativa (retorno, drawdown, Sharpe, win rate, nº de trades, profit factor), la guarda en `data/backtest_results.csv` y en la tabla `backtest_runs`.

Ajusta periodos/parámetros por estrategia editando `src/strategies/*.py` o instanciando con kwargs propios.

## 6. Shadow trading (paso obligatorio antes de ir en real)

Corre 24/7 con **precios reales** de Bybit, genera señales y simula la posición (sin enviar órdenes). Registra trades simulados en la BD y avisa por Telegram en cada apertura/cierre.

```bash
python scripts/run_shadow.py --strategy sma_crossover --symbols "BTC/USDT:USDT,ETH/USDT:USDT" --timeframe 1h
```

Recomendación: deja el shadow corriendo **varias semanas** en distintos regímenes de mercado antes de considerar ir a real.

## 7. Live trading (dinero real)

Solo cuando el shadow haya validado la estrategia:

```bash
python scripts/run_live.py --strategy sma_crossover --i-understand-the-risk
```

- Requiere `BYBIT_API_KEY`/`SECRET` válidos y el flag `--i-understand-the-risk`.
- Usa el mismo `RiskManager` (tamaño de posición por ATR, SL/TP) que el shadow trader.
- Empieza con `BYBIT_TESTNET=true` y capital simbólico antes de pasar a producción.

## 8. Despliegue en VPS

**Opción A — Docker (recomendado):**
```bash
cd deploy
docker compose up -d --build shadow-bot
docker compose logs -f shadow-bot
```

**Opción B — systemd (sin Docker):**
```bash
sudo useradd -r -s /bin/false botbybit
sudo mkdir -p /opt/bot-bybit /var/log/bot-bybit
sudo chown botbybit:botbybit /var/log/bot-bybit
# copia el repo a /opt/bot-bybit, crea el venv e instala requirements ahí
sudo cp deploy/bot-bybit-shadow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bot-bybit-shadow
sudo journalctl -u bot-bybit-shadow -f
```

Cuando quieras pasar a real, usa `bot-bybit-live.service` (mismo procedimiento) — revisa el archivo, ejecuta primero en testnet.

## 9. Tests

```bash
pytest tests/ -q
```

Cubren indicadores, las 5 estrategias (señales válidas, comportamiento con datos insuficientes) y el motor de backtest, todo con datos sintéticos (no requieren red).

## Las 5 estrategias

| # | Nombre | Tipo | Lógica |
|---|--------|------|--------|
| 1 | `sma_crossover` | Tendencia | SMA rápida (20) vs. lenta (50): LONG si rápida > lenta, SHORT si rápida < lenta |
| 2 | `rsi_mean_reversion` | Reversión a la media | LONG si RSI(14) < 30, SHORT si RSI > 70, sale al cruzar RSI 50 |
| 3 | `macd_trend` | Tendencia/momentum | LONG si línea MACD > señal, SHORT si MACD < señal |
| 4 | `bollinger_breakout` | Ruptura de volatilidad | LONG si cierre rompe banda superior, SHORT si rompe banda inferior, sale en la media móvil central |
| 5 | `donchian_breakout` | Ruptura (estilo Turtle) | LONG en máximo de 20 periodos, SHORT en mínimo de 20 periodos, sale con canal de 10 periodos |

Todas comparten la misma interfaz (`BaseStrategy`), por lo que añadir una estrategia nueva es tan simple como crear una clase en `src/strategies/` y registrarla en `src/strategies/__init__.py`.

## Notas de riesgo importantes

- Nunca subas tu `.env` ni tus claves API a git (ya está en `.gitignore`).
- Usa claves de API **sin permiso de retiro**.
- El backtest incluido es una simplificación (una posición por símbolo, sin slippage explícito más allá de la comisión) — sirve para comparar estrategias entre sí, no como garantía de resultados en real.
- Rendimiento pasado (backtest o shadow) no garantiza resultados futuros.
