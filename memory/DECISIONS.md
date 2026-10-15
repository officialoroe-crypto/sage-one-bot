# OWNER DECISIONS

This file records explicit durable decisions that affect future work.

## 2026-09-27 — Shared memory contract

Decision:
Build one memory/instruction contract that can be read by both ChatGPT-compatible workflows and SAGE ONE.

Requirements:
- It must describe how the AI should work with the owner.
- SAGE ONE must support owner-scoped personal memory.
- Additional users, if added later, must receive separate user memory scopes.
- Owner preferences must not become global preferences for other users.
- Public GitHub should contain the contract/schema, not private raw conversation history.

## 2026-10-11 — Spark becomes the platform currency (1 Spark = NPR 1)

Decision:
SAGE Spark is the platform currency. 1 Spark = NPR 1. This replaces the earlier rule that Spark is an internal credit and not cash.

Requirements:
- The rate lives in one place: `economy/currency.py`.
- Real-rupee cash-out stays disabled until a payment provider is configured, the owner sets `SAGE_SPARK_CASH_OUT_ENABLED`, and a legal review is done.
- Evolution stays separate from Spark and is never reduced by spending or withdrawal.
- SAGE earns first and is never funded by the owner. Spend limits follow the Spend Trust Ladder (savings lock, percentage rule, absolute ceiling) and the owner approves every spend.
- Ladder numbers are PROVISIONAL until the owner confirms them. Open questions are listed in `docs/SAGE_MASTER_BLUEPRINT.md`, section 6.3.
