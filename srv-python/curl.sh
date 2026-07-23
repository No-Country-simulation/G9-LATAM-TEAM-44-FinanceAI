#!/usr/bin/env bash
# Ejemplos del contrato contra el servicio local (uvicorn en :8000)
B=http://localhost:8000
curl -s $B/health && echo
curl -s $B/modelo/info && echo
curl -s -X POST $B/clasificar -H 'Content-Type: application/json' -d '{
  "transacciones": [
    {"descripcion": "Supermercado", "valor": 420},
    {"descripcion": "Combustible", "valor": 300},
    {"descripcion": "Streaming", "valor": 40}
  ]}' && echo
curl -s -X POST $B/perfil -H 'Content-Type: application/json' -d '{
  "ingreso_mensual": 4500,
  "nivel_endeudamiento": 25,
  "frecuencia_ahorro": "Media",
  "resumen_gastos": {"alimentacion": 420, "transporte": 300, "ocio": 40}
}' && echo
