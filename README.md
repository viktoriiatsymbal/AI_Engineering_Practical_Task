# AI_Engineering_Practical_Task (Stage 1)

Stage 1 implements a parking assistant using RAG. It answers questions about the parking facility, collects reservation details, protects sensitive data, and evaluates retrieval quality and response latency.

## Features

- RAG-based answers using LangChain and OpenAI models
- Static parking information stored in Weaviate
- Dynamic availability, prices, working hours, and reservations stored in PostgreSQL
- Interactive reservation data collection
- Reservation validation for names, car numbers, dates, duration, opening hours, availability, and booking conflicts
- PII detection and redaction using Microsoft Presidio and LangChain middleware
- Retrieval and performance evaluation
- Automated tests with pytest

## Architecture

```text
User
->
  LangGraph chatbot
    ├── Information request -> Weaviate static data + PostgreSQL live data -> RAG answer
    └── Reservation request -> slot collection -> validation -> PostgreSQL reservation

Guardrails are applied during data ingestion and answer generation
```

## Data storage

- Weaviate: general info, location, parking details, policies, and booking instructions
- PostgreSQL: parking availability, prices, working hours, and reservations

## Project structure

```text
src/                    # application code
data/                   # static and dynamic seed data
evaluation/             # evaluation scripts and generated reports
tests/                  # automated tests
.env.example            # required env variables
requirements.txt        # python dependencies
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

Fill the OpenAI, Weaviate Cloud, and PostgreSQL credentials in `.env`.

### 4. Seed PostgreSQL and ingest static data into Weaviate

```bash
python -m src.ingest
```

To recreate the Weaviate collection before ingestion:

```bash
python -m src.ingest --reset
```

## Usage

Run the chatbot:

```bash
python -m src.main
```

Example reservation flow:

```text
I want to reserve a parking space
Anna
Ponomarenko
AA1234BB
2026-07-10 10:00
2026-07-10 12:00
```

The reservation is stored in PostgreSQL with `pending` status. Administrator approval is implemented in Stage 2.

## Evaluation

Generate the Stage 1 evaluation report:

```bash
python -m evaluation.generate_report
```

Generated artifacts:

- [`evaluation/results/evaluation_report.md`](evaluation/results/evaluation_report.md)
- [`evaluation/results/evaluation_results.json`](evaluation/results/evaluation_results.json)

Latest results:

| Metric | Result |
|---|---:|
| Labelled retrieval queries | 7 |
| Recall@3 | 1.000 |
| Precision@3 | 0.333 |
| Successful performance requests | 15/15 |
| Mean retrieval latency | 0.263 s |
| Mean full-answer latency | 3.170 s |

## Tests

Run all tests:

```bash
python -m pytest -v
```

The Stage 1 test suite contains 43 tests covering the chatbot, database, guardrails, RAG chain, reservation validation, vector storage, and evaluation logic.

## Security

- Sensitive data is redacted before static documents are stored in Weaviate
- User input and generated answers pass through PII middleware
- Secrets are loaded from `.env` and must not be committed to Git