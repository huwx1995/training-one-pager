#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python3}"
"$PYTHON_BIN" -m compileall -q server.py document_parser.py bank_redaction_rules.py audio_transcriber.py http_runtime.py session_store.py docx_export.py term_index.py tests
"$PYTHON_BIN" -m unittest discover -s tests -q
"$PYTHON_BIN" scripts/smoke_local.py
if command -v deno >/dev/null 2>&1; then
  deno check prototype/redaction_workflow.js prototype/preview_rendering.js prototype/one_pager_rendering.js prototype/app.js
elif command -v node >/dev/null 2>&1; then
  node --check prototype/redaction_workflow.js
  node --check prototype/preview_rendering.js
  node --check prototype/one_pager_rendering.js
  node --check prototype/app.js
else
  echo '需要 Deno 或 Node.js 检查前端语法。' >&2
  exit 1
fi
git diff --check
