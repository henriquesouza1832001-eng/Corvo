#!/bin/sh
# Comando único do CORVO na caixa, só por terminal.  Uso:  sh deploy/box/corvo.sh <comando>
#   status    estado do coletor, último ciclo, contagens, preços e memória
#   on        (ou start) liga o coletor em segundo plano (se já estiver ligado, não duplica)
#   off       (ou stop) desliga o coletor
#   restart   desliga e liga
#   logs [n]  últimas n linhas do log (padrão 20)
#   painel    painel ao vivo no terminal (feed da API: pressão do orçamento e últimas notícias); Ctrl+C sai
#   enviar    pede o token (digitação oculta), grava em deploy/box/.env e passa a ENVIAR à API
#   seco      volta ao modo --dry-run (decide e guarda só local; não envia nada)
#   instalar  cria o comando curto `corvo` (depois: corvo on, corvo off, corvo status, corvo painel)
#   atualizar baixa a versão nova do repositório (git pull) e reinicia
cd "$(dirname "$0")/../.." || exit 1
ROOT=$(pwd); ENVF="$ROOT/deploy/box/.env"; DATA="$ROOT/engine/data/corvo_corpus"; LOG="$DATA/caixa.log"
rodando() { ps -ef 2>/dev/null | grep '[d]eploy/box/run.sh' >/dev/null; }

case "$1" in
  status)
    if rodando; then echo "coletor: LIGADO"; else echo "coletor: DESLIGADO"; fi
    if [ -f "$ENVF" ] && grep -q '^CORVO_INGEST_TOKEN=.\{8,\}' "$ENVF"; then echo "modo: ENVIA à API"; else echo "modo: SECO (não envia)"; fi
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
    pkill -f 'deploy/box/run.sh' 2>/dev/null; pkill -f 'corvo_engine.collect' 2>/dev/null; echo "desligado"
    ;;
  restart) sh "$0" stop; sleep 2; sh "$0" start ;;
  painel) shift; PYTHONPATH="$ROOT/engine" python -m corvo_engine.collect.painel "$@" ;;
  logs) tail -n "${2:-20}" "$LOG" ;;
  enviar)
    printf "Cole o token (não aparece na tela) e tecle Enter: "; stty -echo 2>/dev/null; read -r TOK; stty echo 2>/dev/null; echo
    [ ${#TOK} -ge 8 ] || { echo "token curto demais; nada mudou"; exit 1; }
    INT=$(grep '^CORVO_INTERVALO=' "$ENVF" 2>/dev/null | cut -d= -f2); INT=${INT:-900}
    umask 077
    printf 'CORVO_API_URL=https://corvo-api.henriquesouza.workers.dev\nCORVO_INGEST_TOKEN=%s\nCORVO_INTERVALO=%s\n' "$TOK" "$INT" > "$ENVF"
    echo "gravado em deploy/box/.env (fora do Git). Reiniciando em modo ENVIO..."; sh "$0" restart ;;
  seco)
    INT=$(grep '^CORVO_INTERVALO=' "$ENVF" 2>/dev/null | cut -d= -f2); echo "CORVO_INTERVALO=${INT:-900}" > "$ENVF"; echo "modo seco"; sh "$0" restart ;;
  instalar)
    printf '#!/bin/sh
exec sh "%s/deploy/box/corvo.sh" "$@"
' "$ROOT" > "$PREFIX/bin/corvo" && chmod +x "$PREFIX/bin/corvo" && echo "comando corvo instalado" ;;
  atualizar) git pull -q && echo "atualizado" && sh "$0" restart ;;
  *) sed -n '2,13p' "$0" ;;
esac
