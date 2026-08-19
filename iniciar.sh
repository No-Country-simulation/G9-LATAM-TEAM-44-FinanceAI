#!/usr/bin/env bash
# ============================================================================
#  FinanceAI - lanzador para Linux y macOS
#
#    ./iniciar.sh
#
#  Levanta los tres servicios en segundo plano y deja los logs en .logs/.
#  Ctrl+C los para todos.
# ============================================================================
set -u

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ"

PY="$RAIZ/.venv/bin/python"

if [ ! -x "$PY" ]; then
  cat <<EOF

  No existe el entorno virtual .venv

  Crealo con estos dos comandos y vuelve a ejecutar ./iniciar.sh:

    python3 -m venv .venv
    .venv/bin/python -m pip install -r srv-python/requirements.txt

EOF
  exit 1
fi

if ! command -v java >/dev/null 2>&1; then
  echo "  No se encuentra Java en el PATH. Hace falta JDK 25."
  exit 1
fi

mkdir -p .logs

# Al salir se paran los tres; si no, quedan ocupando sus puertos.
pids=()
limpiar() {
  echo
  echo "  Parando FinanceAI..."
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  exit 0
}
trap limpiar INT TERM

echo
echo "  Levantando FinanceAI..."

( cd srv-python && "$PY" -m uvicorn app.main:app --port 8000 ) > .logs/ml-service.log 2>&1 &
pids+=($!)

( cd srv-java && ./mvnw spring-boot:run ) > .logs/api.log 2>&1 &
pids+=($!)

( cd web && "$PY" -m http.server 8081 ) > .logs/web.log 2>&1 &
pids+=($!)

cat <<EOF

    ml-service  http://localhost:8000/docs
    API         http://localhost:8080/swagger-ui.html
    Frontend    http://localhost:8081

  Logs en .logs/  ·  Ctrl+C para parar

EOF

# Espera a que la API responda en vez de dormir un tiempo fijo.
for _ in $(seq 1 90); do
  if curl -sf -o /dev/null http://localhost:8080/api/v1/health 2>/dev/null; then
    echo "  API lista."
    break
  fi
  sleep 2
done

wait
