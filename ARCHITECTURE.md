# SAGE ONE — ARCHITECTURE

## Vision

SAGE ONE is a personal AI mentor and execution partner designed around a cloud-first, background-first architecture.

The user's laptop should be a control surface, not the main AI compute engine.

## High-Level Architecture

```text
                    ┌─────────────────────────┐
                    │       SAGE CLOUD        │
                    │                         │
                    │ AI inference             │
                    │ Research workers         │
                    │ Web processing           │
                    │ Synthesis                │
                    │ Verification             │
                    │ Memory                   │
                    │ Task workers             │
                    └────────────┬────────────┘
                                 │
                              Internet
                                 │
                    ┌────────────▼────────────┐
                    │      USER DEVICES       │
                    │                          │
                    │ Mobile UI                │
                    │ Desktop UI               │
                    │ Voice                    │
                    │ Local agent              │
                    │ Lightweight integrations │
                    └──────────────────────────┘
```

## Core Pipeline

```text
User request
    ↓
Orchestrator
    ↓
Task classification
    ↓
┌─────────────┬──────────────┬─────────────┐
│ LIGHT       │ MEDIUM       │ HEAVY       │
│             │              │             │
│ Fast cloud  │ Cloud worker │ Background  │
│ execution   │              │ cloud worker│
└─────────────┴──────────────┴─────────────┘
    ↓
Result
    ↓
Memory / response / notification
```

## Research OS

```text
SEARCH
  ↓
WEB READER
  ↓
EXTRACTION
  ↓
EVIDENCE
  ↓
CROSS-CHECK
  ↓
SYNTHESIS
  ↓
CITATIONS
  ↓
REPORT
```

Search discovers sources. Web Reader retrieves/reads them. Extraction converts content into useful passages. Evidence stores traceable facts. Cross-check compares claims. Synthesis produces the answer. Citations preserve provenance.

## Durable Task Execution

```text
Task created
    ↓
Atomic claim
    ↓
Worker lease
    ↓
Heartbeat
    ↓
Execute
    ├── Success → completed
    ├── Retryable failure → delayed retry
    └── Permanent/exhausted failure → failed/dead
```

If a worker disappears:
- lease expires
- task becomes recoverable
- another worker may claim it

Execution should be idempotent so recovery does not create harmful duplicate side effects.

## Cloud-First Provider Routing

Preferred:

```text
Request
  ↓
Provider router
  ↓
Cloud provider A
  ↓ failure
Cloud provider B
  ↓ failure
Cloud provider C
  ↓ failure
Queue / explicit failure
```

Avoid:

```text
Cloud failure
  ↓
Automatically start local LLM
  ↓
Laptop CPU 100%
```

Local models may remain available for deliberate low-load/local use, but must not be an uncontrolled fallback for heavy work.

## Resource Guard

Target:

```text
Local CPU
<40%      SAFE
40–70%    BUSY
70–85%    HEAVY
>85%      CRITICAL
```

At high load:
- avoid starting additional local heavy tasks
- pause/defer optional work
- prefer cloud workers
- maintain interactive responsiveness

These thresholds are initial design targets and should be validated experimentally.

## Research Concurrency

Independent work can eventually be parallelized:

```text
             Research
                ↓
       ┌────────┼────────┐
       ↓        ↓        ↓
    Search A  Search B  Search C
       ↓        ↓        ↓
       └────────┼────────┘
                ↓
           Deduplicate
                ↓
          Relevant evidence
                ↓
            Synthesis
                ↓
           Verification
```

Concurrency should be primarily cloud-side.

## Data Minimization

Do not move or process more data than needed.

Apply limits to:
- sources
- page size
- extracted text
- evidence
- claims
- context
- output

This improves:
- CPU usage
- memory usage
- API cost
- latency
- reliability

## Design Principles

1. Cloud-first for heavy intelligence.
2. Background-first for long tasks.
3. Laptop remains responsive.
4. Durable workers over fragile synchronous jobs.
5. Evidence must remain traceable to sources.
6. Working components are not rebuilt.
7. Failures are explicit, not hidden.
8. Provider fallback should be controlled.
9. Heavy tasks should be observable.
10. Permission boundaries must be respected.
