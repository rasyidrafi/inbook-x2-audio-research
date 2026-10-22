#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
{
  python3 -m unittest discover -s tests -p 'test_*.py' -v
  python3 tests/test_driver.py
  if [[ -f inputs/windows/ESAuDriverTDMMode.sys &&
        -f inputs/windows/esaudrivertdmmode.inf &&
        -f inputs/firmware/ES8326-DSM-function-returns.csv &&
        -f analysis/decompiled/functions.tsv ]]; then
    python3 scripts/analyze-driver.py
  else
    echo 'Skipped private Windows analysis: inputs are not included in the public repository.'
  fi
} 2>&1 | tee validation/tests.log
