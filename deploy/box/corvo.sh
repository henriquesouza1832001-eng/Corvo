#!/bin/sh
# Comando único do CORVO na caixa, só por terminal.  Uso:  sh deploy/box/corvo.sh <comando>
#   status    estado do coletor, último ciclo, contagens, preços e memória
#   on        (ou start) liga o coletor em segundo plano (se já estiver ligado, não duplica)
#   off       (ou stop) desliga o coletor
#   restart   desliga e liga
#   logs [n]  últimas n linhas do log (padrão 20)
#   painel    painel ao vivo no terminal (feed da API: pressão do orçamento e últimas notícias); Ctrl+C sai
#   enviar    pede o token (digitação oculta), grava em deploy/box/.env e passa a ENVIAR à API
#   seco      modo --dry-run (decide e guarda só local; não envia nada; o token continua guardado)
#   envio     volta a ENVIAR à API (precisa do token, gravado uma vez por `enviar`)
#   intervalo N  segundos entre ciclos (300 a 3600)
#   agente    liga o agente que recebe os comandos do app no celular
#   ciclo     roda um ciclo de coleta agora
#   precos    atualiza os preços agora
#   limpar    libera espaço (corpus velho, logs grandes, cache)
#   instalar  cria o comando curto `corvo` (depois: corvo on, corvo off, corvo status, corvo painel)
#   atualizar baixa a versão nova do repositório (git pull) e reinicia
cd "$(dirname "$0")/../.." || exit 1
ROOT=$(pwd); ENVF="$ROOT/deploy/box/.env"; DATA="$ROOT/engine/data/corvo_corpus"; LOG="$DATA/caixa.log"
setvar() { # setvar CHAVE VALOR: troca ou acrescenta uma linha no .env, preservando o resto
  umask 077; touch "$ENVF"; grep -v "^$1=" "$ENVF" > "$ENVF.tmp" 2>/dev/null; printf '%s=%s
' "$1" "$2" >> "$ENVF.tmp"; mv "$ENVF.tmp" "$ENVF"
}
rodando() { ps -ef 2>/dev/null | grep '[d]eploy/box/run.sh' >/dev/null; }
agente_ligado() { ps -ef 2>/dev/null | grep '[d]eploy/box/agente.sh' >/dev/null; }

case "$1" in
  status)
    if rodando; then echo "coletor: LIGADO"; else echo "coletor: DESLIGADO"; fi
    if agente_ligado; then echo "agente (comandos do app): LIGADO"; else echo "agente (comandos do app): DESLIGADO"; fi
    if [ -f "$ENVF" ] && grep -q '^CORVO_INGEST_TOKEN=.\{8,\}' "$ENVF" && ! grep -q '^CORVO_MODO=seco' "$ENVF"; then echo "modo: ENVIA à API"; else echo "modo: SECO (não envia)"; fi
    echo "intervalo: $(grep '^CORVO_INTERVALO=' "$ENVF" 2>/dev/null | cut -d= -f2 | grep . || echo 900)s"
    echo "último ciclo:"; grep '"feeds"' "$LOG" 2>/dev/null | tail -1 | cut -c1-200
    [ -f "$DATA/corpus.jsonl" ] && echo "itens no corpus local: $(wc -l < "$DATA/corpus.jsonl")"
    [ -f "$DATA/precos.csv" ] && echo "linhas de preço: $(( $(wc -l < "$DATA/precos.csv") - 1 ))"
    grep -E 'MemAvailable' /proc/meminfo 2>/dev/null | head -1
    df -h "$DATA" 2>/dev/null | tail -1 | awk '{print "disco livre: "$4" ("$5" usado)"}'
    ;;
  start|on)
    if rodando; then echo "já está ligado"; else termux-wake-lock 2>/dev/null; nohup sh deploy/box/run.sh >/dev/null 2>&1 & sleep 1; echo "ligado"; fi
    ;;
  stop|off)
    pkill -f 'deploy/box/run.sh' 2>/dev/null; pkill -f 'corvo_engine.collect --once' 2>/dev/null; echo "desligado"
    ;;
  agente) if agente_ligado; then echo "agente já está ligado"; else nohup sh deploy/box/agente.sh >/dev/null 2>&1 & sleep 1; echo "agente ligado"; fi ;;
  restart) sh "$0" stop; sleep 2; sh "$0" start ;;
  painel) shift; PYTHONPATH="$ROOT/engine" python -m corvo_engine.collect.painel "$@" ;;
  logs) tail -n "${2:-20}" "$LOG" ;;
  enviar)
    printf "Cole o token (não aparece na tela) e tecle Enter: "; stty -echo 2>/dev/null; read -r TOK; stty echo 2>/dev/null; echo
    [ ${#TOK} -ge 8 ] || { echo "token curto demais; nada mudou"; exit 1; }
    setvar CORVO_API_URL https://corvo-api.henriquesouza.workers.dev; setvar CORVO_INGEST_TOKEN "$TOK"; setvar CORVO_MODO envia
    echo "gravado em deploy/box/.env (fora do Git). Reiniciando em modo ENVIO..."; sh "$0" restart ;;
  seco) setvar CORVO_MODO seco; echo "modo seco (o token continua guardado)"; sh "$0" restart ;;
  envio)
    grep -q '^CORVO_INGEST_TOKEN=.\{8,\}' "$ENVF" 2>/dev/null || { echo "sem token: use 'corvo enviar' uma vez"; exit 1; }
    setvar CORVO_MODO envia; echo "modo envio"; sh "$0" restart ;;
  intervalo)
    case "$2" in ''|*[!0-9]*) echo "uso: corvo intervalo 300..3600"; exit 1 ;; esac
    [ "$2" -ge 300 ] && [ "$2" -le 3600 ] || { echo "intervalo fora de 300..3600"; exit 1; }
    setvar CORVO_INTERVALO "$2"; echo "intervalo $2s"; sh "$0" restart ;;
  ciclo)
    # roda UM ciclo de coleta agora, fora do intervalo (mesmas regras do laço: respeita modo seco e token)
    [ -f "$ENVF" ] && set -a && . "$ENVF" && set +a
    export PYTHONPATH="$ROOT/engine"
    MODO="--dry-run --quiet --dump $DATA/corpus.jsonl"
    [ -n "$CORVO_API_URL" ] && [ -n "$CORVO_INGEST_TOKEN" ] && [ "$CORVO_MODO" != "seco" ] && MODO="--dump $DATA/corpus.jsonl"
    python -m corvo_engine.collect --once $MODO --state "$DATA/seen.sqlite" 2>&1 | tail -2 ;;
  precos) PYTHONPATH="$ROOT/engine" python -m corvo_engine.collect.prices --out "$DATA/precos.csv" 2>&1 | tail -1 ;;
  limpar)
    antes=$(df -k "$DATA" | tail -1 | awk '{print $4}')
    rm -f "$DATA/corpus.velho.jsonl" "$DATA"/*.tmp
    for f in "$LOG" "$DATA/agente.log"; do
      [ -f "$f" ] && [ "$(wc -c < "$f")" -gt 200000 ] && tail -c 100000 "$f" > "$f.tmp" && mv "$f.tmp" "$f"
    done
    apt clean 2>/dev/null
    depois=$(df -k "$DATA" | tail -1 | awk '{print $4}')
    echo "livre agora: $((depois / 1024)) MB (liberou $(((depois - antes) / 1024)) MB)" ;;
  atualizar) git pull -q && echo "atualizado" && sh "$0" restart ;;
  *) sed -n '2,20p' "$0" ;;
esac
