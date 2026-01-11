#!/usr/bin/env bash
set -euo pipefail
out=diagnostics/monitoring-baseline
mkdir -p "$out"

kubectl get svc -n monitoring -o wide > "$out/svcs.txt"
kubectl get pods -n monitoring -o wide > "$out/pods.txt"
kubectl get endpoints -n monitoring -o wide > "$out/endpoints.txt"

# Try to find the Prometheus service name
PROM_SVC=$(kubectl get svc -n monitoring -o jsonpath='{range .items[*]}{.metadata.name} {.metadata.labels.app.kubernetes.io/name}{"\n"}{end}' 2>/dev/null | awk '/prometheus/ {print $1; exit}' || true)
if [ -z "$PROM_SVC" ]; then
  PROM_SVC=$(kubectl get svc -n monitoring -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' 2>/dev/null | grep -i prometheus | head -n1 || true)
fi

if [ -z "$PROM_SVC" ]; then
  echo "Prometheus service not found in monitoring namespace" >&2
  exit 1
fi

kubectl port-forward svc/"$PROM_SVC" -n monitoring 9090:9090 --address 127.0.0.1 &
PF_PID=$!
sleep 2

curl -s "http://127.0.0.1:9090/api/v1/query?query=sum%28rate%28container_cpu_usage_seconds_total%7Bnamespace%3D%22monitoring%22%7D%5B5m%5D%29%29" > "$out/total_cpu.json"
curl -s "http://127.0.0.1:9090/api/v1/query?query=topk%2810%2Csum%20by%20%28pod%29%20%28rate%28container_cpu_usage_seconds_total%7Bnamespace%3D%22monitoring%22%7D%5B5m%5D%29%29%29" > "$out/top_cpu.json"
curl -s "http://127.0.0.1:9090/api/v1/query?query=sum%28container_memory_working_set_bytes%7Bnamespace%3D%22monitoring%22%7D%29" > "$out/total_mem.json"
curl -s "http://127.0.0.1:9090/api/v1/query?query=topk%2810%2Csum%20by%20%28pod%29%20%28container_memory_working_set_bytes%7Bnamespace%3D%22monitoring%22%7D%29%29" > "$out/top_mem.json"
curl -s "http://127.0.0.1:9090/api/v1/query?query=prometheus_tsdb_head_series" > "$out/tsdb_series.json"
curl -s "http://127.0.0.1:9090/api/v1/query?query=prometheus_engine_query_duration_seconds_sum" > "$out/query_duration.json"

kill ${PF_PID} || true

echo "Captured baseline artifacts to $out"
