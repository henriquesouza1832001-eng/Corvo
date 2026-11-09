#!/bin/sh
# Coletor 24 h do CORVO para uma caixa pequena (Termux/Android ou Linux leve). Só biblioteca padrão do Python; ~100-250 MB de RAM.
# Uso:  sh deploy/box/run.sh        (de dentro do repositório; lê deploy/box/.env, que NUNCA vai para o Git)
# Sem CORVO_API_URL/CORVO_INGEST_TOKEN no .env ele coleta em --dry-run (só decide e guarda localmente, não envia nada).
# O .env é relido A CADA CICLO: trocar camada de fontes (CORVO_TIER), intervalo ou modo vale no ciclo seguinte, sem reiniciar.
cd "$(dirname "$0")/../.." || exit 1
ROOT=$(pwd)
export PYTHONPATH="$ROOT/engine" PYTHONUNBUFFERED=1
DATA="$ROOT/engine/data/corvo_corpus"; mkdir -p "$DATA"
LOG="$DATA/caixa.log"
echo "$(date -u +%FT%TZ) inicio" >> "$LOG"
ULT_PRECO=0
while :; do
  unset CORVO_API_URL CORVO_INGEST_TOKEN CORVO_MODO CORVO_TIER CORVO_INTERVALO
  [ -f deploy/box/.env ] && set -a && . deploy/box/.env && set +a
  MODO="--dry-run --quiet --dump $DATA/corpus.jsonl"
  # Em modo ENVIO também grava o corpus completo (decisão de cada item, inclusive descartes), como o laço de treino: serve para auditar e treinar o portão.
  [ -n "$CORVO_API_URL" ] && [ -n "$CORVO_INGEST_TOKEN" ] && [ "$CORVO_MODO" != "seco" ] && MODO="--dump $DATA/corpus.jsonl"
  # a linha "<hora UTC> ciclo" antecede o resumo de cada ciclo: é dela que o agente tira os indicadores por hora
  echo "$(date -u +%FT%TZ) ciclo" >> "$LOG"
  # um ciclo de notícias; se o Python cair, o laço apenas tenta de novo no próximo
  python -m corvo_engine.collect --once $MODO --state "$DATA/seen.sqlite" >> "$LOG" 2>&1
  AGORA=$(date +%s)
  # preços a cada hora (idempotente)
  if [ $((AGORA - ULT_PRECO)) -ge 3600 ]; then
    (cd engine && python -m corvo_engine.collect.prices --out "$DATA/precos.csv" >> "$LOG" 2>&1) && ULT_PRECO=$AGORA
  fi
  # o log não cresce sem fim (o disco da caixa é pequeno)
  [ "$(wc -c < "$LOG")" -gt 2000000 ] && tail -c 500000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  [ -f "$DATA/corpus.jsonl" ] && [ "$(wc -c < "$DATA/corpus.jsonl")" -gt 50000000 ] && mv "$DATA/corpus.jsonl" "$DATA/corpus.velho.jsonl"
  sleep "${CORVO_INTERVALO:-600}"
done
