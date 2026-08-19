#!/usr/bin/env bash
# Ejemplos contra el ml-service local (uvicorn en :8000).
#
# Para probar la API que consume un cliente real (:8080), usa:
#   python docs/ejemplos.py
set -u
B=${1:-http://localhost:8000}

echo "== GET /health =="
curl -s "$B/health" && echo

echo
echo "== GET /modelo/info (versión, origen y métricas) =="
curl -s "$B/modelo/info" && echo

echo
echo "== POST /clasificar — solo transacciones, sin ingreso ni deuda =="
curl -s -X POST "$B/clasificar" -H 'Content-Type: application/json' -d '{
  "transacciones": [
    {"descripcion": "Supermercado Exito", "valor": 420},
    {"descripcion": "TRF/POS Gasolinera Terpel REF88213", "valor": 300},
    {"descripcion": "Netflix Streaming", "valor": 40},
    {"descripcion": "### farmacia cruz verde", "valor": 85},
    {"descripcion": "zxqw plfj mmnb", "valor": 25}
  ]}' && echo

echo
echo "== POST /perfil — solo agregados, sin descripciones =="
curl -s -X POST "$B/perfil" -H 'Content-Type: application/json' -d '{
  "ingreso_mensual": 4500,
  "nivel_endeudamiento": 25,
  "frecuencia_ahorro": "Media",
  "resumen_gastos": {"alimentacion": 420, "transporte": 300, "ocio": 40, "vivienda": 900}
}' && echo

echo
echo "== POST /perfil — frecuencia inválida, debe responder 422 =="
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST "$B/perfil" \
  -H 'Content-Type: application/json' -d '{
  "ingreso_mensual": 4500, "nivel_endeudamiento": 25,
  "frecuencia_ahorro": "Siempre", "resumen_gastos": {"ocio": 10}
}'
