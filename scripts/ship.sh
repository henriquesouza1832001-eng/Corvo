#!/bin/bash
# Leva a hen para a main por PR comum (a decisão de rodar é do dono ou de quem ele mandar).
# Uso:  bash scripts/ship.sh
# Faz: confere que a hen está empurrada, abre o PR (se não houver) e mescla SOMENTE com CI verde (scripts/merge_when_green.sh).
# Auto-merge por workflow está só PROPOSTO em docs/corvo/propostas/; enquanto o dono não habilitar, é este script.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
branch=$(git branch --show-current)
[ "$branch" = "hen" ] || { echo "rode na branch hen (atual: $branch)" >&2; exit 1; }
git fetch -q origin
if [ -n "$(git log origin/hen..hen --oneline)" ]; then echo "há commits locais não enviados: git push origin hen" >&2; exit 1; fi
if [ "$(git rev-list --count origin/main..origin/hen)" = "0" ]; then echo "a main já tem tudo da hen"; exit 0; fi
pr=$(gh pr list --head hen --base main --state open --json number --jq '.[0].number // empty')
if [ -z "$pr" ]; then
  gh pr create --base main --head hen --title "chore: levar hen para a main" --body "Sincronização da hen com a main.

🤖 Generated with [Claude Code](https://claude.com/claude-code)" >/dev/null
  pr=$(gh pr list --head hen --base main --state open --json number --jq '.[0].number')
fi
echo "PR #$pr"
bash scripts/merge_when_green.sh "$pr"
git fetch -q origin
git merge --no-edit origin/main || { echo "conflito ao trazer a main para a hen: resolva e rode de novo" >&2; exit 1; }
echo "hen e main sincronizadas"
