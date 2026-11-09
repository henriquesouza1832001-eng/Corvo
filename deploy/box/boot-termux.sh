#!/data/data/com.termux/files/usr/bin/sh
# Copie para ~/.termux/boot/corvo.sh (precisa do app Termux:Boot, também do F-Droid). Liga o coletor quando a caixa liga.
termux-wake-lock
cd "$HOME/Corvo" || exit 1
nohup sh deploy/box/run.sh >/dev/null 2>&1 &
nohup sh deploy/box/agente.sh >/dev/null 2>&1 &
