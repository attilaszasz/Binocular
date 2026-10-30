#!/usr/bin/env bash
set -u
ROOT=/workspace/Binocular
OUT="$ROOT/artifacts/00037-qc"
run() {
  local name="$1"; shift
  { printf 'cwd=%s\ncommand=' "$PWD"; printf '%q ' "$@"; printf '\nstarted=%s\n' "$(date -Iseconds)"; "$@"; rc=$?; printf '\nexit=%s\nfinished=%s\n' "$rc" "$(date -Iseconds)"; } >"$OUT/$name.log" 2>&1
  printf '%s\t%s\n' "$name" "$rc" >>"$OUT/${GROUP}-status.tsv"
  return "$rc"
}
GROUP="$1"
case "$GROUP" in
backend)
 cd "$ROOT/backend"
 run backend-compile uv run python -m compileall -q src tests
 run backend-mypy uv run mypy --strict .; types=$?
 run backend-ruff uv run ruff check .
 run backend-pip-audit uv run pip-audit
 if [ "$types" -eq 0 ]; then
  run backend-pytest uv run pytest -W error --cov=binocular --cov-report=term-missing --cov-report=xml:../artifacts/00037-qc/backend-coverage.xml --cov-fail-under=80
  run backend-performance uv run pytest -W error tests/db/test_catalog_performance.py -v --durations=10
  run backend-security uv run pytest -W error tests/db/test_catalog_security.py -q
  run backend-official-fixtures bash -c 'uv run pytest -W error tests/test_official* -q'
 fi
 ;;
frontend)
 cd "$ROOT/frontend"
 run frontend-typecheck npm run typecheck; types=$?
 run frontend-lint npm run lint
 run frontend-audit npm audit --json
 if [ "$types" -eq 0 ]; then
  run frontend-vitest npm test -- --run --coverage
  cp coverage/clover.xml "$OUT/frontend-coverage.xml"
  cp coverage/coverage-final.json "$OUT/frontend-coverage-final.json"
  run frontend-build npm run build
  export LD_LIBRARY_PATH="$PWD/node_modules/.cache/playwright-deps/root/usr/lib/x86_64-linux-gnu:$PWD/node_modules/.cache/playwright-deps/root/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export FONTCONFIG_FILE="$PWD/node_modules/.cache/playwright-deps/fonts.conf"
  run playwright npx playwright test
  tar -czf "$OUT/playwright-evidence.tar.gz" test-results
 fi
 ;;
image)
 cd "$ROOT"
 run docker-build docker build --load -t binocular:qc-check -f Dockerfile .; built=$?
 if [ "$built" -eq 0 ]; then
  run docker-image-inspect docker image inspect binocular:qc-check
  run trivy trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 binocular:qc-check
 fi
 ;;
esac
