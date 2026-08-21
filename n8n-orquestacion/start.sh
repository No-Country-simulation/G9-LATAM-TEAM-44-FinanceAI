#!/bin/sh
set -eu

marker=/home/node/.n8n/.financeai-workflow-imported
workflow_name='FinanceAI Support Chat'

if [ ! -f "$marker" ]; then
  n8n import:workflow --input=/workflows/financeai-chat.json >/dev/null
  workflow_id="$(n8n list:workflow 2>/dev/null | awk -F'|' -v name="$workflow_name" '$2 == name {print $1; exit}')"
  if [ -n "$workflow_id" ]; then
    n8n publish:workflow --id="$workflow_id" >/dev/null
  fi
  touch "$marker"
fi

exec n8n start
