# AI_Engineering_Practical_Task (Stage 3)

Stage 3 extends the RAG chatbot and human-in-the-loop administrator workflow with an MCP server that records approved reservations in a text file

## Implemented functionality

- RAG chatbot built with LangChain
- Weaviate for static parking information
- PostgreSQL for dynamic data, reservations, and administrator reviews
- PII filtering with Microsoft Presidio
- LangChain administrator agent with human approval or refusal
- FastMCP server for recording approved reservations
- JWT authentication with the `reservations:write` scope
- Retry, timeout, file locking, atomic index updates, and idempotent writes

## Workflow

```text
User -> RAG chatbot -> Reservation created -> Administrator review -> approved -> Authenticated MCP tool -> approved_reservations.txt
```

Refused or unreviewed reservations are not written to the file.

## Output format

```text
Name Surname | Car Number | Start Time to End Time | Approval Time
```

Example:

```text
Anna Ponomarenko | AA5678AA | 2026-07-12T12:00:00 to 2026-07-12T14:00:00 | 2026-07-01T14:44:02+00:00
```

## Project structure (added/changed files)

```text
src/
  chatbot.py                    # user-facing RAG chatbot
  admin_agent.py                # administrator LangChain agent
  admin_api.py                  # secured administrator REST API
  admin_cli.py                  # administrator console
  mcp_server.py                 # FastMCP server
  mcp_client.py                 # LangChain MCP adapter client
  approved_reservation_store.py # text-file storage
  mcp_token.py                  # JWT generator
  record_approved.py            # manual retry command
evaluation/
  eval_mcp_workflow.py
tests/
storage/
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

Fill the credentials in `.env` (use a random secret of at least 32 characters for `MCP_JWT_SECRET`)


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

### User chatbot

```bash
python -m src.main
```

### Administrator console

```bash
python -m src.admin_cli
```

Available commands:

```text
list
list pending
list all
open <reservation-id>
quit
```

After the administrator approves a reservation, the administrator agent invokes the authenticated MCP tool and writes the record to:

```text
storage/approved_reservations.txt
```

A failed MCP write can be retried without duplicating the entry:

```bash
python -m src.record_approved <reservation-id>
```

## Tests

```bash
python -m pytest -v
```

The Stage 3 contains 74 automated tests covering the chatbot, guardrails, database, administrator workflow, MCP authentication/integration, file formatting, and idempotency.

## Evaluation

Run the MCP workflow evaluation while PostgreSQL, the administrator API, and the MCP server are available:

```bash
python -m evaluation.eval_mcp_workflow
```

The generated report is saved to:

```text
evaluation/results/mcp_workflow_results.json
```

Stage 1 RAG and Stage 2 administrator workflow results are retained under `evaluation/results/`.

## Security

- The MCP endpoint requires a signed HS256 JWT
- The token must contain the `reservations:write` scope
- The server verifies that the reservation was approved before writing
- Reservation IDs are stored in a separate index to prevent duplicate writes
- File locking protects concurrent writes
- The index is replaced atomically, and the text file is flushed with `fsync`
- The MCP client uses configurable timeout and retry settings