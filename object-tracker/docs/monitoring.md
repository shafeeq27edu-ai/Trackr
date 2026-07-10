# Production Monitoring Guide — Trackr v1.0

Monitoring and alerting are essential for maintaining reliability, tracking processing throughput, and observing resource usage on Trackr v1.0 instances.

---

## 1. Metrics Collector & Architecture

Trackr utilizes **Prometheus** for metrics collection and exposing data points. The FastAPI application is instrumented using `prometheus-fastapi-instrumentator`.

* **Metrics Endpoint**: `GET http://localhost:8000/metrics`
* **Default Scrape Interval**: `15s`

---

## 2. Key Performance Indicators (KPIs) to Monitor

### 2.1 API Availability & Latency
* **Metric**: `http_requests_total` & `http_request_duration_seconds`
* **Description**: Measures request counts, HTTP status code distributions (2xx vs 5xx), and API response latency.
* **Critical Path**: Watch for increases in `500 Internal Server Error` responses and p99 response times exceeding 2.0s.

### 2.2 Video Processing Throughput
* **Metric**: Average FPS during batch job processing. Exposed on completed jobs in the database (`average_fps` and `processing_throughput` fields).
* **Target**: 
  - CPU: >= 10 FPS (YOLOv8n)
  - GPU (T4/V100/A10G): >= 60 FPS (YOLOv8n)

### 2.3 System Job Execution Queues
* **Metric**: Active jobs list and duration.
* **Failed Jobs Ratio**: Track failed vs completed jobs. A spike in failed jobs indicates issues with input codecs, database writes, or VRAM OOM.

### 2.4 Compute & VRAM Resource Consumption
* **Metric**: CPU utilization percent, RAM usage, and GPU/VRAM allocation.
* **Exposed endpoint**: `/api/v1/system/resources` returns JSON metrics dynamically.
* **Thresholds**: 
  - Memory Usage > 90% (High risk of Out Of Memory crash)
  - VRAM Utilization > 92% (High risk of CUDA OOM)

---

## 3. Recommended Prometheus Alert Rules

Configure your Prometheus Alertmanager with these rules:

```yaml
groups:
  - name: trackr_alerts
    rules:
      - alert: TrackrApiHighErrorRate
        expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100 > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High API error rate detected (exceeds 5%)"
          description: "Trackr API is returning 5xx status codes for over 5% of requests in the last 2 minutes."

      - alert: TrackrSlowApiResponse
        expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow API responses on p99 (exceeds 2s)"
          description: "99% of Trackr API responses are taking longer than 2.0 seconds to execute."

      - alert: HostCpuSaturation
        expr: psutil_cpu_percent > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Host CPU saturation (>90%)"
          description: "Host CPU has been saturated above 90% for more than 5 minutes."

      - alert: HighJobFailureRate
        expr: rate(trackr_job_failures_total[10m]) > 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Elevated video processing failures"
          description: "More than 2 jobs have failed within the last 10 minutes."
```

---

## 4. Operational Dashboards

It is recommended to deploy Grafana and import templates for FastAPI/Uvicorn metrics. Configure panels for:
1. **API Traffic**: Request rate (RPS), status code breakdown, WebSocket active connection counts.
2. **Batch Queue**: Number of active files processing, average queue time.
3. **Computer Vision Stats**: Average processing FPS per file, GPU VRAM allocation over time.
4. **Host metrics**: Disk space, CPU, Memory.
