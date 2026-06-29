# AI_Engineering_Practical_Task (Stage 4)

Stage 4 integrates the RAG chatbot, administrator workflow, and MCP recording service into one LangGraph pipeline

## Implemented functionality

- LangGraph orchestration of all previous stages
- RAG chatbot with Weaviate, PostgreSQL, and PII filtering
- Human-in-the-loop administrator approval with `interrupt()` and resume
- Authenticated MCP recording for approved reservations
- PostgreSQL workflow checkpoints and history
- Retry support for failed MCP recording
- REST API, CLI, integration tests, evaluation, and load testing

## Workflow

```text
User -> RAG chatbot -> Reservation created -> Administrator approval -> MCP recording -> Completed
```

Refused reservations are finalized without MCP recording.

## Project structure (added/changed files)

```text
src/
  orchestration/
    state.py       # shared workflow state
    nodes.py       # chatbot, approval, MCP, and finalization nodes
    routing.py     # conditional routing
    graph.py       # LangGraph definition
    service.py     # start, resume, retry, state, and history operations
  workflow_api.py  # Stage 4 REST API
  workflow_cli.py  # unified CLI
evaluation/
  eval_orchestrated_workflow.py
load_tests/
  locustfile.py
langgraph.json
```

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Fill the credentials in `.env`


### 4. Seed PostgreSQL and Weaviate

```bash
python -m src.ingest --reset
```

### 5. Generate an MCP access token

```bash
python -m src.mcp_token
```

Copy the generated JWT into `.env`:

```env
MCP_ACCESS_TOKEN=<generated-token>
```

The generated token is short-lived. Generate a new one if the MCP server returns `401 Unauthorized`.

## Run

Open separate terminals with the virtual environment activated.

### MCP server

```bash
python -m src.mcp_server
```

Default endpoint: `http://127.0.0.1:8001/mcp`

### Administrator API

```bash
uvicorn src.admin_api:app --host 127.0.0.1 --port 8000
```

### LangGraph workflow API

```bash
uvicorn src.workflow_api:app --host 127.0.0.1 --port 8002
```

### Unified workflow CLI

```bash
python -m src.workflow_cli
```

Main API endpoints:

```text
POST /workflows
POST /workflows/{workflow_id}/admin-decision
POST /workflows/{workflow_id}/retry
GET  /workflows/{workflow_id}
GET  /workflows/{workflow_id}/history
```

## Tests

```bash
python -m pytest -v
```

The complete project contains 88 automated tests covering all four stages and the integrated workflow.

## Evaluation

```bash
python -m evaluation.eval_orchestrated_workflow
```

Results are stored in:

```text
evaluation/results/stage4_results.json
```

Latest run:

- 3/3 successful workflows
- 100% success rate
- Mean latency: 11.3692 s
- P50 latency: 9.9895 s
- Maximum latency: 14.4842 s

## Load testing

Start the workflow API, then run:

```bash
locust -f load_tests/locustfile.py --host http://127.0.0.1:8002
```

Open `http://127.0.0.1:8089` to run the test.

## Reliability and security

- Administrator actions require a bearer token
- MCP writes require a scoped JWT
- Approved reservations only are written to storage
- PostgreSQL checkpoints preserve workflow state
- Failed MCP steps can be retried without repeating previous steps
- Idempotent recording prevents duplicate entries