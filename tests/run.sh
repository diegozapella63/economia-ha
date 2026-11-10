#!/usr/bin/env bash
# Os testes unitários e de integração (só Python): tests/run.sh
# Com a cobertura de linhas do servidor (economia/app): tests/run.sh --cobertura   (python3 tools/cobertura.py --linhas)
set -u
cd "$(dirname "$0")/.."
export TZ="${TZ:-America/Sao_Paulo}"
if [ "${1:-}" = "--cobertura" ]; then exec python3 tools/cobertura.py --linhas; fi
exec python3 -m unittest discover -s tests -p "test_*.py"
