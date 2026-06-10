#!/bin/sh
# Entrypoint integration test harness
# Usage: sh docker/test-entrypoint.sh

set -e
IMAGE="binocular-test:entrypoint"
PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
fail() { FAIL=$((FAIL+1)); echo "FAIL: $1"; }

echo "=== Building image ==="
docker build -t "$IMAGE" . >/dev/null 2>&1 || { echo "BUILD FAILED"; exit 1; }

echo "=== Default UID/GID ==="
R=$(docker run --rm "$IMAGE" id -u 2>/dev/null)
[ "$R" = "1000" ] && pass "default UID=1000" || fail "default UID=$R"

echo "=== Custom PUID=1001 PGID=1001 ==="
R=$(docker run --rm -e PUID=1001 -e PGID=1001 "$IMAGE" id -u 2>/dev/null)
[ "$R" = "1001" ] && pass "custom UID=1001" || fail "custom UID=$R"

echo "=== Root refusal PUID=0 ==="
docker run --rm -e PUID=0 "$IMAGE" true >/dev/null 2>&1; R=$?
[ "$R" = "1" ] && pass "PUID=0 exit 1" || fail "PUID=0 exit $R"

echo "=== Root refusal PGID=0 ==="
docker run --rm -e PUID=1001 -e PGID=0 "$IMAGE" true >/dev/null 2>&1; R=$?
[ "$R" = "1" ] && pass "PGID=0 exit 1" || fail "PGID=0 exit $R"

echo "=== Non-numeric fallback ==="
R=$(docker run --rm -e PUID=abc -e PGID=def "$IMAGE" id -u 2>/dev/null)
[ "$R" = "1000" ] && pass "non-numeric fallback UID=1000" || fail "non-numeric fallback UID=$R"

echo "=== Independent defaults (PUID=1500, no PGID) ==="
R=$(docker run --rm -e PUID=1500 "$IMAGE" sh -c 'id -u 2>&1' 2>/dev/null)
G=$(docker run --rm -e PUID=1500 "$IMAGE" sh -c 'id -g 2>&1' 2>/dev/null)
[ "$R" = "1500" ] && [ "$G" = "1000" ] && pass "independent defaults UID=1500 GID=1000" || fail "independent defaults UID=$R GID=$G"

echo "=== Volume ownership ==="
CID=$(docker run -d -e PUID=1001 -e PGID=1001 "$IMAGE" sleep 5)
sleep 2
D=$(docker exec "$CID" stat -c "%u:%g" /app/data 2>/dev/null)
M=$(docker exec "$CID" stat -c "%u:%g" /app/modules 2>/dev/null)
docker kill "$CID" >/dev/null 2>&1
docker rm "$CID" >/dev/null 2>&1
[ "$D" = "1001:1001" ] && pass "data volume ownership 1001:1001" || fail "data volume ownership $D"
[ "$M" = "1001:1001" ] && pass "modules volume ownership 1001:1001" || fail "modules volume ownership $M"

echo "=== Entrypoint and CMD ==="
docker inspect "$IMAGE" >/dev/null 2>&1
E=$(docker inspect "$IMAGE" | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['Config']['Entrypoint'][0])")
[ "$E" = "/entrypoint.sh" ] && pass "ENTRYPOINT /entrypoint.sh" || fail "ENTRYPOINT $E"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" = "0" ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED"
