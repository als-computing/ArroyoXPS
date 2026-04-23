# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ArroyoXPS is a real-time streaming data analysis service for X-ray Photoelectron Spectroscopy (XPS) at the Advanced Light Source (ALS) beamline. It ingests ZMQ messages from LabVIEW instruments, processes detector frames (peak fitting, FFT analysis), and publishes results over WebSocket to a React frontend and to a Tiled data server.

## Commands

### Python Backend

```bash
# Install with dev dependencies (uses uv or pip)
pip install ".[dev]"

# Run tests
python -m pytest

# Run a single test file
python -m pytest src/_tests/test_processor.py -v

# Linting (pre-commit runs flake8, black, isort)
pre-commit run --all-files
```

Max line length is 115 (configured in `.flake8`).

### Frontend

```bash
cd frontend
npm install
npm start        # dev server at http://localhost:3000
npm run build
```

### Running Locally (Docker)

```bash
# One-time setup
docker network create mle_net
cp .env.example .env  # then set TILED_SINGLE_USER_API_KEY

# Start all services
docker-compose up -d

# With LabVIEW simulator instead of real hardware
docker-compose -f docker-compose-simulator.yaml up -d
```

Services: Frontend at `:8080`, Tiled at `:8000`, Jaeger at `:16686`, Prometheus at `:9090`, Grafana at `:3000`.

### Running Without Docker

```bash
# Start the LabVIEW frame simulator
python -m tr_ap_xps.simulator
```

## Architecture

### Data Flow

```
LabVIEW (ZMQ PUB) → XPSLabviewZMQListener → XPSOperator → XPSProcessor
                                                                 ↓
                                              XPSWSResultPublisher (WebSocket)
                                              TiledPublisher (Tiled server)
```

**Message lifecycle:**
1. LabVIEW sends three message types over ZMQ: `start` (scan metadata), `event` (detector frame), `stop`
2. `labview.py` parses raw ZMQ messages into Pydantic models (`XPSStart`, `XPSRawEvent`, `XPSStop`)
3. `XPSOperator` (`pipeline/xps_operator.py`) orchestrates the processing pipeline using the Arroyopy framework
4. `XPSProcessor` (`pipeline/xps_processor.py`) does the computation: frame integration, rolling mean/std, peak fitting, FFT
5. Results (`XPSResult`) are published to WebSocket clients and Tiled

### Key Components

- **`src/tr_ap_xps/`** — main package
  - `schemas.py` — all Pydantic message models; LabVIEW JSON field names mapped via aliases
  - `labview.py` — ZMQ listener; handles BigEndian binary frame buffers from LabVIEW
  - `websockets.py` — WebSocket publisher; uses msgpack binary protocol for efficiency
  - `tiled.py` — Tiled server integration for data persistence
  - `config.py` — Dynaconf configuration (env vars prefixed `DYNACONF_`, override via `.secrets.yaml`)
  - `pipeline/xps_operator.py` — Arroyopy `Operator` subclass; async `process()` entry point
  - `pipeline/xps_processor.py` — core XPS computation (horizontal integration, rolling stats)
  - `pipeline/peak_fitting.py` — Bayesian blocks peak detection + Astropy Gaussian fitting
  - `pipeline/fft.py` — vertical FFT + inverse FFT filtering with configurable repeat factors
  - `simulator/` — LabVIEW simulators for local development

- **`frontend/src/`** — React 18 frontend
  - WebSocket connection managed via custom hooks
  - Plotly.js for heatmaps and scatter plots
  - msgpack decoding of binary WebSocket frames

### Framework: Arroyopy

The backend is built on [Arroyopy](https://github.com/als-computing/arroyo), an async ZMQ pub/sub framework. Key base classes:
- `Operator` — processes incoming messages, calls `process()` for each
- `Publisher` — sends results to an output sink

### Observability

- OpenTelemetry tracing via `@traced` decorators; Jaeger collects traces
- Prometheus metrics endpoint (configured in `config/prometheus.yml`)
- Grafana dashboards pre-configured in `config/grafana-dashboard.json`

## Serialization Notes

- LabVIEW frames arrive as BigEndian binary buffers; `DATATYPE_MAP` in `labview.py` handles type conversion
- WebSocket results use msgpack (binary) for efficiency, not JSON
- Zarr format used for Tiled data storage
