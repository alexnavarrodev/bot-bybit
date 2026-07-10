# Bot Bybit (Python + CCXT)

Bot de trading algorítmico para Bybit (BTC/USDT y ETH/USDT perpetuos), con:

- **Datos y ejecución** vía [CCXT](https://github.com/ccxt/ccxt) (Bybit).
- **Base de datos** PostgreSQL (self-hosted en el VPS vía Docker, o Supabase/otro Postgres externo) o SQLite (local/desarrollo), vía SQLAlchemy — se cambia con una sola variable de entorno.
- **Alertas por Telegram** (señales, aperturas/cierres de trade, errores).
- **Dashboard web** con el rendimiento y las operaciones en vivo (ver sección 8).
- **3 modos de ejecución**: `backtest` (histórico), `shadow` (paper trading 24/7 con precios reales, sin arriesgar capital) y `live` (órdenes reales).
- **5 estrategias** listas para comparar en BTC y ETH.
- Configuración de despliegue para VPS (Docker Compose todo-en-uno o systemd).

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
  dashboard/                 # App FastAPI de solo lectura (rendimiento y operaciones)
scripts/
  run_backtest.py   # Descarga histórico y compara las 5 estrategias
  run_shadow.py      # Paper trading 24/7 con datos reales
  run_live.py        # Trading real (requiere --i-understand-the-risk)
deploy/
  Dockerfile, docker-compose.yml (postgres + shadow-bot + dashboard), *.service (systemd)
  vps_setup.sh        # Instalación todo-en-uno en un VPS limpio
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

**Opción A — Postgres self-hosted en el VPS (recomendado para producción, incluida en `docker-compose.yml`):**

El propio `docker-compose.yml` levanta un contenedor `postgres:16-alpine` con volumen persistente. Solo tienes que rellenar en `.env`:
```
POSTGRES_USER=botbybit
POSTGRES_PASSWORD=elige-una-contraseña-fuerte
POSTGRES_DB=botbybit
DATABASE_URL=postgresql+psycopg2://botbybit:elige-una-contraseña-fuerte@postgres:5432/botbybit
```
(el host `postgres` es el nombre del servicio dentro de la red de Docker Compose; no cambia aunque cambie la IP del VPS).

**Opción B — SQLite (más simple, un solo archivo, para desarrollo local):**
```
DATABASE_URL=sqlite:///data/bot.db
```

**Opción C — Supabase u otro Postgres externo:**
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

## 8. Despliegue en VPS (Docker, todo-en-uno)

Script de instalación automática (`deploy/vps_setup.sh`): instala Docker si falta, levanta Postgres + el shadow trader + el dashboard, y abre el puerto del dashboard en el firewall si `ufw` está activo.

```bash
ssh root@TU_IP_VPS
git clone https://github.com/alexnavarrodev/bot-bybit.git
cd bot-bybit
cp .env.example .env
nano .env   # rellena TELEGRAM_*, POSTGRES_PASSWORD, DASHBOARD_PASSWORD, estrategia, símbolos...
bash deploy/vps_setup.sh
```

Al terminar, el script imprime la URL del dashboard (`http://TU_IP_VPS:8080`). **Recuerda abrir el puerto 8080 también en el firewall del panel de Hostinger** (VPS → Firewall) si el tráfico no llega — `ufw` solo cubre el firewall del propio sistema operativo.

Para pasar a real más adelante, descomenta el servicio `live-bot` en `deploy/docker-compose.yml` y ejecútalo con `docker compose -f deploy/docker-compose.yml up -d --build live-bot` (revisa antes con testnet).

**Alternativa — systemd (sin Docker):**
```bash
sudo useradd -r -s /bin/false botbybit
sudo mkdir -p /opt/bot-bybit /var/log/bot-bybit
sudo chown botbybit:botbybit /var/log/bot-bybit
# copia el repo a /opt/bot-bybit, crea el venv e instala requirements ahí
# (necesitarás además una instancia de Postgres/SQLite propia, systemd no la gestiona)
sudo cp deploy/bot-bybit-shadow.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bot-bybit-shadow
sudo journalctl -u bot-bybit-shadow -f
```

## 9. Dashboard — seguir el rendimiento en vivo

`src/dashboard/app.py` (FastAPI) sirve una página con:
- Equity actual y posición abierta por símbolo/estrategia.
- Curva de equity (gráfico).
- Últimas operaciones (con PnL) y últimas señales generadas.

Se actualiza sola cada 30s y está protegida con **HTTP Basic Auth** (`DASHBOARD_USER` / `DASHBOARD_PASSWORD` en `.env` — cambia el valor por defecto antes de desplegar). En el VPS queda disponible en `http://TU_IP_VPS:8080` una vez corres `deploy/vps_setup.sh` (o `docker compose up -d dashboard`).

Para probarlo en local:
```bash
uvicorn src.dashboard.app:app --reload --port 8080
```

## 10. Tests

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
