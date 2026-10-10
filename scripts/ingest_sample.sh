#!/usr/bin/env bash
# Ingestão de amostra real do PNCP para desenvolvimento.
# Uso: ./scripts/ingest_sample.sh [DATA_INICIAL] [DATA_FINAL] [MODALIDADE]
set -euo pipefail

DATA_INICIAL="${1:-2026-01-05}"
DATA_FINAL="${2:-2026-01-05}"
MODALIDADE="${3:-6}"

echo "→ Seed de dados de referência..."
python -m app.cli seed

echo "→ Ingestão de contratações (${DATA_INICIAL} a ${DATA_FINAL}, modalidade ${MODALIDADE})..."
python -m app.cli ingest pncp \
  --data-inicial "${DATA_INICIAL}" \
  --data-final "${DATA_FINAL}" \
  --modalidades "${MODALIDADE}" \
  --max-paginas 1

echo "→ Estatísticas da base:"
python -m app.cli stats

echo "✓ Concluído."
