#!/usr/bin/env bash
# Instalación todo-en-uno en un VPS limpio (Ubuntu/Debian): Docker + Postgres +
# shadow trading + dashboard web. Ejecutar como root desde la raíz del repo:
#
#   git clone https://github.com/alexnavarrodev/bot-bybit.git
#   cd bot-bybit && git checkout claude/brave-turing-umnv0z
#   cp .env.example .env && nano .env   # rellena TELEGRAM_*, contraseñas, estrategia...
#   bash deploy/vps_setup.sh
#
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Ejecuta este script como root (o con sudo)." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "No existe .env en $(pwd). Copia .env.example a .env y rellénalo antes de continuar." >&2
  exit 1
fi

if grep -qE '^(POSTGRES_PASSWORD|DASHBOARD_PASSWORD)=changeme$' .env; then
  echo "ERROR: cambia POSTGRES_PASSWORD y DASHBOARD_PASSWORD en .env (siguen en 'changeme')." >&2
  exit 1
fi

echo "==> Instalando Docker (si no está presente)..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

echo "==> Construyendo y levantando los servicios (postgres + shadow-bot + dashboard)..."
docker compose -f deploy/docker-compose.yml up -d --build postgres shadow-bot dashboard

echo "==> Abriendo el puerto 8080 en el firewall local (ufw), si está activo..."
if command -v ufw &>/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 8080/tcp || true
fi

PUBLIC_IP=$(curl -4 -fsSL --max-time 5 ifconfig.me || hostname -I | awk '{print $1}')

echo ""
echo "======================================================================"
echo " Listo. Estado de los contenedores:"
docker compose -f deploy/docker-compose.yml ps
echo ""
echo " Dashboard:  http://${PUBLIC_IP}:8080"
echo "   Usuario:    $(grep -E '^DASHBOARD_USER=' .env | cut -d= -f2)"
echo "   Contraseña: la que pusiste en DASHBOARD_PASSWORD (.env)"
echo ""
echo " IMPORTANTE: abre el puerto 8080 también en el firewall del panel de"
echo " Hostinger (VPS -> Firewall) si el tráfico no llega."
echo ""
echo " Logs en vivo del shadow trader:  docker compose -f deploy/docker-compose.yml logs -f shadow-bot"
echo "======================================================================"
