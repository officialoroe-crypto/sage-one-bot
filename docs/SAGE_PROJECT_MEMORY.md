# SAGE ONE — Project Memory / Canonical Source of Truth

> GitHub is the canonical shared project memory for SAGE ONE. Backend and frontend chats must read this file and the linked project-state documents before making architectural changes.

## Operating Model
- Backend chat owns backend architecture, APIs, database, authentication, memory, economy, activity verification, workers, integrations, CI, security and production contracts.
- Frontend chat owns screens, navigation, UX, visual design, theme, animations, responsive behavior and frontend QA.
- Both sides coordinate through documented API contracts and this repository. Neither side invents the other's behavior.
- Every meaningful architectural decision is recorded in GitHub documentation/commits.
- The repository is the canonical source of truth; chat memory is supplementary.

## Immediate Priority
1. Make the existing SAGE ONE application actually runnable end-to-end.
2. Connect frontend to real backend functionality.
3. Verify every route, button, link, API contract, loading/error/empty state.
4. Keep CI green and reduce unnecessary laptop load.
5. Prepare a private working/demo deployment.
6. Only after stability, build Owner Developer Mode and its separate secured development server.

## Product Vision
SAGE ONE is the user's personal AI execution platform. The user should eventually be able to use SAGE itself for research, content creation, video workflows, marketing, business discovery, portfolio generation, WhatsApp outreach links and other creator/business work.

## Owner Developer Mode
- Owner-only.
- Never hardcode the owner email/password in source control.
- Credentials/secrets live in secure server configuration.
- Accessible from any authorized device through a separate secured developer environment.
- Default workflow: diagnose -> branch -> modify -> test -> preview -> owner approval -> merge -> deploy.
- Production, authentication, authorization, payment and destructive database changes require elevated approval.
- SAGE may not grant itself owner privileges or alter its own authorization rules.

## Economy
- Every new account starts with Spark = 0.
- Owner also starts with Spark = 0.
- No hidden welcome Spark.
- Spark and Evolution are separate systems.
- Activity Center may award verified rewards such as 5/10/15+ Spark based on useful activity difficulty.
- Rewards are server-verified, ledgered and idempotent; users cannot farm a one-time quest repeatedly.
- Spark is the SAGE platform currency at a fixed rate of 1 Spark = NPR 1 (owner decision 2026-10-11). It is not a cryptocurrency, investment or security. Real-rupee cash-out stays disabled until a payment provider is configured, the owner opts in, and a legal review is done.
- Spend Trust Ladder (provisional): SAGE earns first, a savings lock and percentage rules limit each spend, and the owner approves every spend. See docs/SAGE_MASTER_BLUEPRINT.md.

## Activity Center
Examples:
- First command: +5 Spark
- First useful research: +10 Spark
- First project: +10 Spark
- First completed task: +15 Spark
- Higher-difficulty useful missions: larger rewards
Rewards must be configured by backend rules and recorded in the economy ledger.

## Shared Work Split
Backend: API, database, auth, memory, Spark ledger, activity verification, research/task services, workers, CI, security, deployment contracts.
Frontend: UI, routes, screens, design system, animations, responsive behavior, frontend interaction states.
Integration: both sides jointly verify end-to-end behavior.

## Launch Principle
Do not block customer value on finishing every future SAGE feature. First make a working demo/product that can be used to deliver real work. The user already has a first potential customer/business and wants SAGE to generate the demo/video and business materials.

## Future Developer Brain
SAGE should eventually connect securely to GitHub and AI model providers so the owner can say things like “this is not working, fix it” or “change the logo/theme/font.” The system must inspect, propose, branch, modify, test and obtain approval before production deployment by default.

## Current Constraint
The immediate objective is a stable runnable SAGE ONE core and a usable demo. Avoid adding placeholder screens when real backend functionality can be implemented instead.


## 2026-10-08 Build Directive
- Start building now in bulk/full-speed mode; do not pause for tiny implementation steps.
- The first acceptance target is a **working SAGE-only demo workflow**, not another collection of placeholder screens.
- The owner wants to use SAGE itself for the work: research -> content creation -> video creation/workflow -> portfolio/business materials -> WhatsApp-ready outreach.
- The first real-world validation target is the owner's existing family-business customer, **Calvert Hardware Suppliers**. Existing business information can be used to create the first demo.
- Business discovery is a later SAGE capability: SAGE should be able to find businesses in real time whose online presence needs improvement (for example weak/inconsistent Instagram, weak video content, poor branding, missing reels, outdated websites or weak Google presence) and turn findings into actionable sales/work opportunities.
- Do not make manual prospecting the immediate blocker; the owner already has a first customer target.
- Build order remains: stabilize core -> connect real backend/frontend -> complete one end-to-end customer workflow -> owner testing/private demo -> then expand automation and Owner Developer Mode.
- GitHub remains the canonical shared memory for both backend and frontend chats.

## 2026-10-08 Role Boundary Correction — LOCKED
- The backend chat's job is to **build and maintain the system**, not to personally perform SAGE's future customer-facing work.
- SAGE Sales is a future SAGE capability/agent. When we say SAGE should create videos, research businesses, make portfolios, generate outreach, or perform sales work, that means **we must code SAGE so SAGE can perform those jobs**.
- Backend chat must therefore prioritize the infrastructure, APIs, orchestration, tools, permissions, data models, workers, integrations and tests that enable those SAGE capabilities.
- Do NOT mistake a desired SAGE capability for an instruction for the backend chat to manually perform that capability.
- Example: “SAGE Sales should create the customer's video” means build the sales/content/video capability into SAGE; it does **not** mean the backend chat should switch its engineering work into manually creating a customer video.
- Do not let an individual feature such as video generation hijack the roadmap. Features must serve the agreed product architecture and launch priorities.
- Before implementing a feature, determine: **Who performs this action? SAGE, backend infrastructure, frontend, or the owner?** Keep those responsibilities separate.
- Current engineering priority: make the existing app runnable end-to-end, connect real backend/frontend behavior, verify routes/buttons/links/contracts, keep CI green, prepare the private demo, then expand SAGE Sales/business discovery and Owner Developer Mode in the agreed order.
- Work in bulk/full-speed mode, but do not make unrelated changes just to show activity.

