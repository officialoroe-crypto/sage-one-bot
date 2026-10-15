# Backend ↔ Frontend Work Contract

## Backend owns
API contracts, authentication, authorization, database models/migrations, memory, research/task execution, Spark ledger, Activity Center reward validation, background workers, integrations, CI, security and deployment interfaces.

## Frontend owns
Screens, navigation, visual design, design tokens, typography, animations, responsive layouts, loading/error/empty states and user interaction presentation.

## Rules
1. Frontend consumes documented backend contracts; it must not invent server behavior.
2. Backend exposes stable versioned contracts and explicit error states.
3. Breaking API changes require updating this document and frontend consumers together.
4. End-to-end QA must test real backend calls, not only mocked success screens.
5. Every important route/button/link must have a verified destination/action.
6. Secrets never live in frontend source or GitHub.
