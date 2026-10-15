# SAGE ONE — Consent-Driven Memory Learning

## Contract

Automatic memory learning may persist only when the authenticated profile has enabled memory_consent.

The learning boundary receives classified candidates, not raw conversation transcripts. Candidate classification must identify one of the supported memory types:

- fact
- interest
- inference
- skill
- skill_evidence
- goal
- preference
- experience

## Safety rules

1. Consent is a persisted profile setting and is checked at the learning boundary.
2. Consent allows persistence but does not make a candidate a confirmed fact.
3. Auto-learned memories are stored with confirmed=false and source=auto_learning.
4. Existing equivalent content is skipped rather than duplicated.
5. Unsupported memory types, invalid confidence/importance, empty content, and oversized candidates are rejected.
6. Secret-like credential material is rejected.
7. Raw conversation text is not stored by this pipeline.
8. Existing profile-scoped view/update/delete controls remain the user's correction and removal boundary.

## Lifecycle

observe → classify candidate → consent check → safety validation → deduplicate → persist unconfirmed memory → user review/correction

The conversation/agent layer remains responsible for producing classified candidates. This module is deliberately not an LLM extractor; extraction can be connected later without weakening the storage boundary.
