# CORVO numa caixa pequena (MXQ Pro 5G ou parecida)

Coletor que liga junto com o aparelho e fica o dia todo: lê os feeds, passa pelo portão, grava preços a cada hora e (se configurado) envia o aprovado à API. **Sem navegador**; só Python padrão.

## Instalação no Android (Termux): não apaga nada, dá para desinstalar depois
1. Instale **F-Droid** e, por ele, **Termux** e **Termux:Boot** (não use a versão da Play Store).
2. Abra o Termux uma vez e rode: `pkg install python git`
3. `git clone https://github.com/henriquesouza1832001-eng/Corvo.git ~/Corvo`
4. (opcional, para enviar à API) crie `~/Corvo/deploy/box/.env`:
   ```
   CORVO_API_URL=https://corvo-api.henriquesouza.workers.dev
   CORVO_INGEST_TOKEN=cole-o-token-aqui
   ```
   Sem esse arquivo ele roda em `--dry-run` (decide e guarda localmente, não envia nada).
5. Teste: `sh ~/Corvo/deploy/box/run.sh` (Ctrl+C para parar; veja `engine/data/corvo_corpus/caixa.log`).
6. Ligar sozinho com a caixa: `mkdir -p ~/.termux/boot && cp ~/Corvo/deploy/box/boot-termux.sh ~/.termux/boot/corvo.sh`, abra o Termux:Boot uma vez, e nas configurações do Android **desative a otimização de bateria** do Termux e do Termux:Boot.
7. Atualizar: `cd ~/Corvo && git pull`.

## Voltar ao Android puro
Termux é só um aplicativo: **desinstale-o** e o aparelho volta ao que era. Nenhum passo acima mexe no sistema.

## Se um dia quiser Linux de verdade (Armbian)
Só **a partir de cartão microSD ou pendrive**, mantendo o Android intacto na memória interna (tire o cartão e ele volta a ser Android). **Não grave na memória interna** sem antes salvar a imagem original: o modelo exato do processador varia entre caixas "MXQ" e uma imagem errada pode inutilizar o aparelho.

## Cuidados
- Memória: o laço guarda no máximo 50 MB de corpus e 2 MB de log.
- Segredos só no `.env` do aparelho (está no `.gitignore`); nunca no Git.
- Fontes novas (por exemplo outras redes) entram no coletor como adaptadores, cada uma com ficha em `docs/sources/SOURCES.md`, respeitando os termos de uso.
