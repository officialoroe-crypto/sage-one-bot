# SAGE WORKFLOW

Status: FOUNDATION SPECIFICATION — 2026-09-22

SAGE WORKFLOW is the connective layer between a user's intent, projects, assets, actions, publishing and feedback. It prevents SAGE from behaving like a collection of disconnected chats.

## Core model

REQUEST → PLAN → EXECUTE → RESULT → VERIFY → EVIDENCE → SETTLE → ACHIEVEMENT → EVOLUTION → HISTORY

WORKFLOW adds persistent relationships around that execution chain:

WORKSPACE → PROJECT → ASSET GRAPH → WORKFLOW → MISSION → EXECUTION → PUBLISH → ANALYTICS → IMPROVE

## Product hierarchy

- Workspaces
  - OROE
  - Dhun Barsa
  - SAGE ONE
  - Personal
- Projects
- Assets
- Workflows
- Missions
- Execution
- Memory
- Intelligence
- Economy
- Evolution
- History

## Content workflow

IDEA
→ SCRIPT
→ MUSIC / AUDIO
→ IMAGES
→ VIDEO CLIPS
→ EDIT
→ THUMBNAIL
→ CAPTION
→ HASHTAGS
→ PLATFORM VERSIONS
→ PUBLISH
→ ANALYZE
→ IMPROVE

Every derived asset should retain a relationship to its source asset and project. Platform variants should remain variants of one canonical content project rather than independent uploads.

## Asset graph

Asset types:
- image
- video
- audio
- document
- text
- project file
- thumbnail
- caption
- export

Relationship examples:
- derived_from
- version_of
- contains
- references
- selected_for
- published_as
- generated_by
- verified_by

## Workflow execution rules

1. SAGE should understand the desired outcome before choosing tools.
2. Planning should produce explicit steps and dependencies.
3. Independent work may execute in parallel within resource limits.
4. External/destructive actions require the applicable permission boundary.
5. Results must be verified before dependent steps proceed.
6. Evidence and provenance must remain attached to important outputs.
7. Failures should produce recovery actions instead of silently disappearing.
8. Premium work must integrate with Spark settlement once the premium execution billing path is wired.
9. User memory and public World Intelligence remain separate.
10. History must retain enough context to explain what SAGE did and why.

## Publishing model

A content project has one canonical source. Platform publishing creates platform-specific versions and publication records.

Future integrations:
- YouTube
- Instagram
- Facebook
- TikTok
- X
- other user-authorized platforms

SAGE must never publish externally merely because a workflow reached the final step. Publishing remains an explicit permissioned action unless the user has created an automation rule that authorizes that exact class of action.

## Mobile UX

Primary daily destinations:
- Home
- Chat
- Research
- Create
- Execute
- Spark
- Memory
- Profile

The command center is the starting point, not the entire product. A user should be able to move from an idea to a project, attach/create assets, execute a workflow, review evidence, publish with permission, and return later to the same project.

## Implementation sequence

1. Design the mobile workflow model in Figma.
2. Implement reusable Flutter workflow primitives.
3. Add project/asset relationship models without breaking existing mission/task APIs.
4. Build Create around a persistent Content Project.
5. Build Execute around existing durable missions/tasks.
6. Add platform-version records.
7. Add permissioned publishing adapters.
8. Feed analytics back into Improve.
9. Connect Spark/Evolution settlement to completed premium workflows.

## Non-goals

- Do not replace the durable mission/task engine.
- Do not make the UI the source of truth for execution state.
- Do not treat generated assets as untraceable files.
- Do not silently publish content.
- Do not merge personal memory with World Intelligence.
