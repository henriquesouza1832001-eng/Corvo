#!/bin/sh
# Supervisor do agente da caixa: mantém `corvo_engine.collect.agente` vivo (reinicia se ele sair, p. ex. depois de "update").
# É ele que recebe os comandos do app (ligar, desligar, reiniciar, atualizar). Não depende do coletor estar ligado.
cd "$(dirname "$0")/../.." || exit 1
ROOT=$(pwd)
export PYTHONPATH="$ROOT/engine" PYTHONUNBUFFERED=1
LOG="$ROOT/engine/data/corvo_corpus/agente.log"; mkdir -p "$(dirname "$LOG")"
while :; do
  python -m corvo_engine.collect.agente >> "$LOG" 2>&1
  [ "$(wc -c < "$LOG")" -gt 500000 ] && tail -c 100000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
  sleep 5
done
