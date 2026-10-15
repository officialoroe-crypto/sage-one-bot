# SAGE ONE development rules

SAGE ONE is a personal AI mentor and execution system. Preserve its core principle: **capability does not equal permission**.

## Repository

The backend is Python/FastAPI and is organized into app, brain, memory, tasks, agents, tools, permissions, projects, research, execution, missions, database, and web subsystems. The long-term clients are mobile and desktop, with cloud-first execution and an offline Ollama path.

## Development style

- Prefer coherent bulk changes over repetitive micro-patches.
- Inspect existing interfaces before creating new ones.
- Preserve working behavior and backwards compatibility unless a deliberate breaking change is required.
- Use complete implementations, not placeholder architecture.
- Never hard-code API keys or secrets. Never read, print, modify, or commit `.env` files.
- Heavy AI inference and research should be cloud-first. Ollama is the offline/local fallback and must not be used for heavy online research by default.
- Local execution must remain lightweight enough for the owner's older laptop.
- Long-running work belongs in background workers rather than blocking HTTP requests.
- Expensive live API/web tests should be separate from cheap static/unit tests.
- Do not claim a test passed unless it was actually run.

## Testing

Use static checks and unit tests first. Integration/live provider tests should be run only when the change requires them. Avoid unnecessary full research calls during development.

## Security and authority

Never silently expand permissions. Never spend money, deploy, publish packages, push remote Git changes, or delete important data without explicit owner authorization. Development automation may inspect, create, and replace approved source/test files, but remote Git operations remain an approval boundary.


## Shared owner memory contract

- Read `memory/CHATGPT_OS.md` and `memory/OWNER_MEMORY_MODEL.md` when work involves owner interaction behavior, memory, continuity, or user identity.
- SAGE ONE is currently private-first and owner-scoped. Owner preferences and memories must never be treated as global defaults for future users.
- The public repository stores the memory contract/schema, not raw private conversations, secrets, credentials, or sensitive owner data.
- Runtime memory must enforce user/owner scope at the data-access boundary.
