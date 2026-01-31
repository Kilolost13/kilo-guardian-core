# Monitoring - Prometheus & Grafana (sample)

This folder contains sample config and dashboards for scraping AI Brain metrics.

Overview
- `prometheus-sample.yml` - sample scrape config that scrapes metrics from the gateway admin proxy (`/admin/ai_brain/metrics`).
- `grafana/ai_brain_dashboard.json` - minimal Grafana dashboard showing latency and request volume.

Security & Access
- Metrics are restricted to admin access only. The gateway exposes an admin proxy at `/admin/ai_brain/metrics` which requires a valid admin token.
- To generate an admin token (first token can be created without auth if DB empty):

  1. Create a token via the gateway: `curl -X POST http://<gateway>/admin/tokens` (if tokens exist, create with an existing admin token in header)
  2. Save the returned token into a file on the Prometheus host and mount it into the Prometheus container, then set `bearer_token_file` to reference that file (example in `prometheus-sample.yml`).

Notes
- For air-gapped deployments you must generate and manage tokens locally and provide them as files to Prometheus.
- Alternatively, you can use the static `LIBRARY_ADMIN_KEY` env var as a bootstrap token (gateway recognizes that), but creating and using a persistent admin token is recommended.

Next steps
- Add Prometheus container and mount scraped token file: `-v /path/to/token:/etc/prometheus/secrets/gateway_admin_token:ro`.
- Import the Grafana dashboard JSON into your Grafana instance.
