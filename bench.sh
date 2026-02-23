#!/usr/bin/env bash
set -euo pipefail

N="${1:-20}"
ok=0
fail=0
retry=0
lat_file="$(mktemp)"
MAX_POLLS="${MAX_POLLS:-120}"
POLL_SLEEP_SECONDS="${POLL_SLEEP_SECONDS:-0.1}"

for i in $(seq 1 "$N"); do
  start_ms=$(date +%s%3N)

  job_id=$(curl -s -X POST http://localhost:8000/v1/inference \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"message-$i\"}" | jq -r '.job_id')
  echo "[$i/$N] submitted job_id=$job_id"

  terminal=0
  for poll in $(seq 1 "$MAX_POLLS"); do
    body=$(curl -s "http://localhost:8000/v1/jobs/$job_id")
    status=$(echo "$body" | jq -r '.status')
    echo "[$i/$N] poll=$poll status=$status"
    if [ "$status" = "succeeded" ] || [ "$status" = "failed" ]; then
      end_ms=$(date +%s%3N)
      dur=$((end_ms - start_ms))
      echo "$dur" >> "$lat_file"
      terminal=1

      if [ "$status" = "succeeded" ]; then ok=$((ok+1)); else fail=$((fail+1)); fi

      rc=$(echo "$body" | jq -r '.retry_count // 0')
      if [ "$rc" -gt 0 ]; then retry=$((retry+1)); fi
      echo "[$i/$N] completed status=$status duration_ms=$dur retries=$rc"
      break
    fi
    sleep "$POLL_SLEEP_SECONDS"
  done

  if [ "$terminal" -eq 0 ]; then
    fail=$((fail+1))
    echo "[$i/$N] timeout waiting for terminal status after $MAX_POLLS polls"
  fi
done

sort -n "$lat_file" -o "$lat_file"
count=$(wc -l < "$lat_file")
p50="n/a"
p95="n/a"
if [ "$count" -gt 0 ]; then
  p50_idx=$(( (count + 1) / 2 ))
  p95_idx=$(( (95 * count + 99) / 100 ))
  p50=$(sed -n "${p50_idx}p" "$lat_file")
  p95=$(sed -n "${p95_idx}p" "$lat_file")
fi
success_rate=$(awk -v o="$ok" -v n="$N" 'BEGIN { printf "%.2f", (o/n)*100 }')
retry_rate=$(awk -v r="$retry" -v n="$N" 'BEGIN { printf "%.2f", (r/n)*100 }')

echo "N=$N"
echo "success=$ok failed=$fail"
echo "success_rate_percent=$success_rate"
echo "completed_jobs_for_latency=$count"
echo "p50_ms=$p50"
echo "p95_ms=$p95"
echo "retry_rate_percent=$retry_rate"

rm -f "$lat_file"
