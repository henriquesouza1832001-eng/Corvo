#!/bin/sh
# Instalador de UM COMANDO do CORVO na caixa (Termux, Android). Pode rodar de novo: é idempotente (atualiza em vez de duplicar).
#   pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/henriquesouza1832001-eng/Corvo/main/deploy/box/instalar.sh | sh
# Faz: instala Python e Git, baixa/atualiza o projeto, cria o comando `corvo`, liga o início automático (precisa do app Termux:Boot),
# liga o coletor e o agente de comandos. NÃO pergunta nem grava segredo: o token é colocado depois, uma vez, com `corvo enviar`.
set -e
REPO="https://github.com/henriquesouza1832001-eng/Corvo.git"
DIR="$HOME/Corvo"

echo "[1/6] pacotes (python, git)"
pkg install -y python git >/dev/null 2>&1 || pkg update -y && pkg install -y python git

echo "[2/6] projeto"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q --depth 1 "$REPO" "$DIR"; fi

echo "[3/6] comando 'corvo'"
sh "$DIR/deploy/box/corvo.sh" instalar

echo "[4/6] início automático"
mkdir -p "$HOME/.termux/boot"
cp "$DIR/deploy/box/boot-termux.sh" "$HOME/.termux/boot/corvo.sh" && chmod +x "$HOME/.termux/boot/corvo.sh"

echo "[5/6] ligando coletor e agente"
termux-wake-lock 2>/dev/null || true
sh "$DIR/deploy/box/corvo.sh" on
sh "$DIR/deploy/box/corvo.sh" agente

echo "[6/6] estado"
sh "$DIR/deploy/box/corvo.sh" status

cat <<'MSG'

Pronto. Falta só uma vez (para a caixa ENVIAR ao banco e aceitar comandos do celular):
    corvo enviar        (cole o token de envio; ele não aparece na tela)
Também, nas configurações do Android: desative a otimização de bateria do Termux e abra o Termux:Boot uma vez.
Comandos: corvo status | corvo painel | corvo logs | corvo on | corvo off
MSG
