#!/usr/bin/env bash
# Testes visuais do EconomIA: cada script sobe lojas falsas e o servidor do add-on (portas livres),
# abre a página no Chromium (Playwright), clica, digita e confere. Capturas em $E2E_TMP/shots, saídas em $E2E_TMP/logs.
#
#   tests/e2e/run.sh              todos
#   tests/e2e/run.sh ec_lista ...   só esses
#
# Precisa de python3 e playwright (pip install playwright; python3 -m playwright install chromium).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
export E2E_TMP="${E2E_TMP:-$(mktemp -d)}"
export TZ="${TZ:-America/Sao_Paulo}"
mkdir -p "$E2E_TMP/shots" "$E2E_TMP/logs"
if [ $# -gt 0 ]; then names=("$@"); else names=($(cd "$HERE" && ls ec_*.py | sed 's/\.py$//' | sort)); fi
pass=0; fail=0; bad=()
for t in "${names[@]}"; do
  f="$HERE/$t.py"
  [ -f "$f" ] || { echo "?? $t (não existe)"; bad+=("$t"); fail=$((fail+1)); continue; }
  (cd "$HERE" && timeout 400 python3 -u "$f" > "$E2E_TMP/logs/$t.txt" 2>&1)
  code=$?
  # tempo esgotado no Playwright (o GitHub às vezes fica lento): roda mais uma vez e deixa a 1ª falha no registro.
  # Uma conferência que falha (FAIL sem tempo esgotado) não repete.
  if [ $code -ne 0 ] && grep -q "TimeoutError" "$E2E_TMP/logs/$t.txt"; then
    mv "$E2E_TMP/logs/$t.txt" "$E2E_TMP/logs/$t.1.txt"
    echo "~~ $t: tempo esgotado, de novo ($(grep -h "TimeoutError" "$E2E_TMP/logs/$t.1.txt" | tail -1 | cut -c1-120))"
    (cd "$HERE" && timeout 400 python3 -u "$f" > "$E2E_TMP/logs/$t.txt" 2>&1)
    code=$?
  fi
  last=$(tail -1 "$E2E_TMP/logs/$t.txt")
  if [ $code -ne 0 ] || grep -q "^FAIL\|Traceback" "$E2E_TMP/logs/$t.txt"; then
    echo "XX $t: $last"; grep -h "^FAIL\|Error" "$E2E_TMP/logs/$t.txt" | head -5 | sed 's/^/     /'
    bad+=("$t"); fail=$((fail+1))
  else
    echo "ok $t: $last"; pass=$((pass+1))
  fi
done
echo
echo "$pass ok, $fail com falha · capturas e saídas em $E2E_TMP"
[ $fail -eq 0 ] || { echo "Falharam: ${bad[*]}"; exit 1; }
