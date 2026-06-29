# Stage 1 Evaluation Report

**Generated:** 2026-06-29T09:21:09.994669+00:00

## Scope

This report evaluates retrieval quality and system performance for the Stage 1 RAG parking chatbot.

## Environment

| Item | Value |
|---|---|
| Python | 3.11.5 |
| LangChain | 1.3.11 |
| LLM model | gpt-4o-mini |
| Embedding model | text-embedding-3-small |
| Weaviate collection | ParkingInfo |

## Retrieval quality

Evaluated 7 labelled queries at K=3.

| Metric | Result |
|---|---:|
| Average Recall@3 | 1.000 |
| Average Precision@3 | 0.333 |

### Per-query results

| Query | Expected | Retrieved | Recall | Precision |
|---|---|---|---:|---:|
| Where are you located? | location-1 | location-1, details-2, general-1 | 1.00 | 0.33 |
| What documents are required to make a reservation? | booking-1 | booking-1, booking-2, policy-1 | 1.00 | 0.33 |
| Can I cancel my reservation? | booking-2 | booking-2, booking-1, policy-1 | 1.00 | 0.33 |
| Do you have electric vehicle charging? | details-2 | details-2, details-1, general-1 | 1.00 | 0.33 |
| What parking zones do you have? | details-1 | details-1, details-2, general-1 | 1.00 | 0.33 |
| Do you share my personal data with anyone? | policy-1 | policy-1, booking-1, general-1 | 1.00 | 0.33 |
| Tell me about your facility security. | general-1 | general-1, details-2, details-1 | 1.00 | 0.33 |

## Performance

| Metric | Result |
|---|---:|
| Requests attempted | 15 |
| Requests successful | 15 |
| Success rate | 100.0% |
| Throughput | 0.291 requests/s |
| Total test duration | 51.496 s |

### Retrieval latency

| Metric | Result |
|---|---:|
| Mean | 0.263 s |
| P50 | 0.169 s |
| P90 | 0.403 s |
| P95 | 0.706 s |
| Maximum | 1.184 s |

### Full answer latency

| Metric | Result |
|---|---:|
| Mean | 3.170 s |
| P50 | 2.804 s |
| P90 | 4.638 s |
| P95 | 5.191 s |
| Maximum | 5.538 s |

## Interpretation

- Recall@3 measures whether the expected source appears among the top 3 retrieved documents.
- Precision@3 measures how many retrieved documents are labelled relevant.
- With one labelled relevant source and K=3, one correct result gives precision 0.333.
- Retrieval latency measures vector search only.
- Full answer latency includes retrieval, SQL context, LangChain agent execution, model generation and PII filtering.

## Conclusion

All requests completed successfully in this run.

## Reproduction

```bash
python -m evaluation.generate_report
```
