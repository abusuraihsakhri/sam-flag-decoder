# SAM Flag Decoder

> **Domain:** Clinical Decision Support & Biomedical Computing

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## Overview

SAM Flag Decoder decodes SAM bitwise FLAG values to human-readable alignment properties. It provides a stdlib parser/mapper with batch CSV processing and single-lookup capabilities, plus a multi-agent enterprise analytical suite for clinical decision support.

---

## Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/sam-flag-decoder.git
cd sam-flag-decoder

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Docker

```bash
docker build -t sam-flag-decoder .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret-key sam-flag-decoder
```

### Docker Compose

```bash
# Set your audit secret key
export AUDIT_SECRET_KEY=your-production-secret-key

docker-compose up -d
```

---

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Description | Required |
|:---------|:------------|:---------|
| `AUDIT_SECRET_KEY` | Secret key for HMAC-SHA256 audit trail signing | Yes |
| `MODEL_PROVIDER` | LLM provider: `mock`, `ollama`, `claude`, `openai` | No (default: `mock`) |

---

## Usage

### CLI Commands

#### Single Lookup
```bash
python sam_flag.py single creatinine
python sam_flag.py single --query hemoglobin
```

#### Batch CSV Processing
```bash
python sam_flag.py batch --input sample.csv --output results.csv
```

#### Enterprise Audit (agents module)
```bash
# Run single task evaluation
python cli.py audit --task-id TASK-001 --primary 28.5 --secondary 14.2

# Batch process records
python cli.py batch -i sample.csv -o results.csv

# Verify audit trail integrity
python cli.py verify-audit

# Start REST API server
python cli.py serve --host 127.0.0.1 --port 8000
```

### Python API

```python
from sam_flag import lookup, process_csv

# Single lookup
result = lookup("creatinine")
print(result["top_hit"], result["score"])

# Batch CSV processing
results = process_csv("input.csv", "output.csv")
```

### REST API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health check |
| `/metrics` | GET | Operational metrics |
| `/api/audit` | POST | Process task payload |
| `/api/chat` | POST | Supervisory chat query |
| `/api/audit/logs` | GET | Retrieve and verify audit trail |

---

## Testing

```bash
# Run full test suite
pytest -v

# Run with coverage
pytest -v --cov=. --cov-report=term-missing
```

The test suite includes:
- Core function tests (`tests/test_core_functions.py`)
- Security tests (`tests/test_security.py`)
- PHI guard enforcement tests
- Multi-agent consensus and audit tests
- Enrichment module tests

---

## Architecture

### Core Module (`sam_flag.py`)
- **`lookup(query)`** — Single lookup with token overlap + substring scoring
- **`process_csv(input, output)`** — Batch CSV processing with column auto-detection
- **`main()`** — CLI entry point

### Agents Module (`agents/`)
- **`base.py`** — PHI guard, HMAC-SHA256 audit trail, security exceptions
- **`models.py`** — Pydantic schemas for tasks, alerts, and dossiers
- **`supervisor.py`** — Multi-agent orchestrator with consensus logic
- **`workers.py`** — Specialized domain workers (QC, Safety, Conformance)
- **`api.py`** — FastAPI REST endpoints
- **`llm_factory.py`** — Pluggable LLM provider adapter

### Security Features
- **Zero-PHI Outbound Guard** — AST and regex inspection blocking SSNs, MRNs, phone numbers, emails
- **HMAC-SHA256 Audit Trail** — Cryptographically chained, tamper-evident logging
- **Required Secret Key** — No hardcoded defaults; `AUDIT_SECRET_KEY` must be configured

---

## Project Structure

```
sam-flag-decoder/
├── sam_flag.py           # Core FLAG decoder and CSV processor
├── cli.py                # Enterprise CLI entry point
├── enrichment.py         # Domain enrichment engines
├── simulator.py          # Load testing simulator
├── requirements.txt      # Python dependencies
├── conftest.py           # Pytest configuration
├── Dockerfile            # Container build
├── docker-compose.yml    # Multi-service orchestration
├── agents/               # Enterprise agent module
│   ├── base.py           # Security, PHI guard, audit trail
│   ├── models.py         # Pydantic data models
│   ├── supervisor.py     # Task orchestrator
│   ├── workers.py        # Domain workers
│   ├── api.py            # FastAPI endpoints
│   └── ...
├── tests/                # Test suite
│   ├── test_core_functions.py
│   ├── test_security.py
│   ├── test_enrichment.py
│   └── test_sam_flag_decoder.py
└── web/                  # Operations console UI
```

---

## License

[MIT](LICENSE)
