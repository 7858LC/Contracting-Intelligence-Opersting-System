#!/usr/bin/env bash
# Wraps the Celery worker command so a startup crash backs off with
# increasing delay instead of Render restarting the container in a tight
# loop. This matters because kombu's redis transport raises a raw
# redis.exceptions.ResponseError (not a ConnectionError) when Redis rejects
# a command outright — e.g. Upstash's "max requests limit exceeded" — and
# that error isn't one Celery's own connection-retry logic treats as
# retryable, so the process just exits. Without backoff, Render restarting
# it immediately means every restart attempt opens a fresh Redis connection
# and adds to usage (and, on a metered plan, cost) while doing zero real
# work — exactly what turned one Redis outage into a climbing bill.
#
# Usage: worker-entrypoint.sh <celery command and args...>
set -u

min_backoff=5
max_backoff=300
healthy_run_seconds=60 # ran at least this long => treat the next crash as fresh, not part of a loop
backoff=$min_backoff
child_pid=""

forward_signal() {
  if [ -n "$child_pid" ]; then
    kill -TERM "$child_pid" 2>/dev/null
    wait "$child_pid" 2>/dev/null
  fi
  exit 0
}
trap forward_signal TERM INT

while true; do
  start=$(date +%s)
  "$@" &
  child_pid=$!
  wait "$child_pid"
  status=$?
  child_pid=""
  elapsed=$(($(date +%s) - start))

  if [ "$elapsed" -ge "$healthy_run_seconds" ]; then
    backoff=$min_backoff
  fi

  echo "cios-worker exited (status=$status, ran ${elapsed}s) — retrying in ${backoff}s" >&2
  sleep "$backoff" &
  wait $!

  if [ "$backoff" -lt "$max_backoff" ]; then
    backoff=$((backoff * 2))
    if [ "$backoff" -gt "$max_backoff" ]; then
      backoff=$max_backoff
    fi
  fi
done
