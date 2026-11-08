#!/bin/sh
# Confere que nada dentro das pastas protegidas vai para o GitHub em texto puro. Rode antes de commitar segredos.
# Uso:  sh scripts/gitcrypt_check.sh
set -e
cd "$(git rev-parse --show-toplevel)"
fail=0
# 1) tudo que casa com os padrões do .gitattributes precisa estar marcado como cifrado
for f in $(git ls-files -- 'secrets' 'docs/private' '*.secret' '*.secret.*'); do
  case "$f" in secrets/.gitkeep) continue ;; esac
  head=$(git cat-file -p ":$f" | head -c 9 | tr -d '\000')
  if [ "$head" != "GITCRYPT" ]; then
    echo "PLANO NO ÍNDICE (não cifrado): $f"
    fail=1
  fi
done
# 2) arquivos de segredo conhecidos nunca podem estar versionados em texto puro
for f in $(git ls-files | grep -E '(^|/)(\.env|\.dev\.vars)$|\.pem$|\.key$' || true); do
  echo "SEGREDO VERSIONADO: $f"
  fail=1
done
if [ "$fail" -eq 0 ]; then echo "ok: nenhum segredo em texto puro no índice"; else echo "FALHOU: não faça commit"; fi
exit $fail
