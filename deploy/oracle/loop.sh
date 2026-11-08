#!/bin/sh
# Publica cada arquivo da caixa de entrada pelo portão do CORVO. Falha não apaga o arquivo: tenta de novo no próximo minuto.
mkdir -p /state/done
while true; do
  for f in /inbox/*.jsonl; do
    [ -e "$f" ] || continue
    if python -m corvo_engine.oracle "$f"; then
      cp "$f" "/state/done/$(basename "$f")"
    else
      echo "falha ao publicar $f; tentando de novo no próximo ciclo"
    fi
  done
  sleep 60
done
