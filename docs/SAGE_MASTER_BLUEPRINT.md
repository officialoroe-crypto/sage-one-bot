# SAGE ONE — Master Blueprint

Written: 2026-10-11. Source of truth for where SAGE starts, how it grows, and where it ends.
Verified items are marked **[verified]**; items that are decisions not yet built are marked **[planned]**.
Numbers marked **PROVISIONAL** are the owner's first draft and must be confirmed before they are treated as final.

---

## 1. What SAGE is

A private personal AI mentor and execution partner. It talks, researches, creates, executes work, earns, and
evolves. The owner is the final authority on every action: **capability is not permission**.

Long-term, the owner may give the same system, on a separate server, to people who do not have family support.
That is a later phase and needs its own security, legal and multi-user work (see section 7).

---

## 2. Where we start (state on 2026-10-11)

**[verified] from the repository:**

- Backend (about 29,000 lines of Python, FastAPI): durable background worker, mission planner, Research OS with
  evidence and verification, provider router (Groq, Cerebras, Gemini, local Ollama), memory with a consent review
  queue, Permission Engine (fail-closed), Developer Mode with approve-before-apply, Sales Engine (never sends
  outreach by itself), Spark wallet with reserve / settle / refund and an audited ledger.
- Flutter app (about 14,000 lines of Dart): splash, onboarding, command center, chat, research, tasks, projects,
  memory, evolution, voice, wallet, jobs/marketplace, owner console and more.
- CI: Python tests and Flutter analysis/tests; Android APK/AAB build; GitHub Pages workflow.
- Backend test suite: 243 tests pass on the Spark-currency branch.

**[verified] still open (from `PROJECT_STATE.md`):**

- Google Sign-In has not been confirmed on a physical Android phone.
- The Render backend is on the free tier with temporary storage; not safe for real user data.
- The public website and Pages deployment were still waiting on checks.
- No real SMS/OTP provider, no payment provider, no external integrations such as Meta ads or Shopify.
- No manual end-to-end device walkthrough.

---

## 3. How it grows (in order, not dates)

**Stage A — Make the private core real.** Fix Google Sign-In on the phone, move the backend to storage that
survives restarts, verify the website, walk every screen on a real device.

**Stage B — SAGE earns its first Spark through real work.** Use the Sales Engine and content workflow for the
owner's first real customer. Earnings are recorded as verified, idempotent ledger entries and trigger the
earning animations (section 5). SAGE is never funded by the owner.

**Stage C — The Spend Trust Ladder goes live (section 6).** SAGE may *propose* spending within its limits;
the owner approves every spend. First adapters must be permissioned, one at a time (for example, one ad
platform), each with a spend ceiling and a kill switch.

**Stage D — Mentor depth.** Voice-first mentor personality, memory of the owner, honest pushback and
accountability. The owner decides how strict it should be.

**Stage E — Share the server (optional).** Multi-user isolation, privacy and security review, payments and
cash-out compliance, support. Not started until A to C are stable.

---

## 4. Where it ends

SAGE is finished when all of this is true:

1. The owner can talk to SAGE and it acts like a mentor that remembers, pushes back, and helps run businesses.
2. SAGE earns Spark from verified real work and spends only inside the ladder, with the owner approving each spend.
3. Every action is traceable: request, plan, permission, tool, execution, verification, evidence, result.
4. Nothing external (ads, posts, messages, money) happens without owner approval.
5. If shared with others, each person's data and money are isolated and the legal requirements are met.

---

## 5. Design system (from the repo, locked unless the owner changes it)

**Brand.** Canonical logo is the orbital metallic S in a thin ring with a travelling orb; wordmark SAGE, sub-mark
ONE, line "YOUR PERSONAL AI MENTOR & EXECUTION PARTNER". Do not redraw or replace it. The logo image is
`docs/design/img-assets/content-(81) (1).png`.

**Look.** Near-black foundation; cyan, blue and violet for intelligence; gold only for Spark, economy and premium;
green success; red/orange failure; purple/blue recovery. Restraint over neon. Status never relies on colour alone.

**Evolution (LOCKED, 2026-10-01).** 13 ranks x 3 intensities (Low / Mid / High): Bronze, Silver, Gold, Platinum,
Jade, Ruby, Sapphire, Emerald, Diamond Sovereign, Black Opal Realm, Painite Core, Void Matter, Californium Overlord.
Rank is skill-driven and never reduced by spending or withdrawing Spark. The UI layout stays the same; only the
SAGE Core, particles, edge highlights and badge change. Permanent environment: Everest, moon, golden Buddha, stars.

**Earning animations.** Small, medium, major and legendary tiers, by rupee amount:

| Tier | Earned (NPR) |
|---|---|
| Small | 500 to 2,000 |
| Medium | 2,001 to 10,000 |
| Major milestone | 10,001 to 100,000 |
| Legendary | over 100,000 |

**Two conflicts between older mockups and the locked decisions (locked decisions win):**

- The 2026-09-19 mockup shows a different 13-rank set (Beginner to Transcendent) with XP. The locked Evolution
  document replaced it.
- The 2026-09-22 mockup shows "SAGE Coin (SSG)" and "2,580 credits = NPR 5,800". The approved name is
  **SAGE Spark** and the rate is now **1 Spark = NPR 1** (so that balance would show NPR 2,580).

---

## 6. SAGE Spark currency and the Spend Trust Ladder

### 6.1 Currency rule (owner decision, 2026-10-11)

- **1 SAGE Spark = NPR 1.** Defined once in `economy/currency.py`.
- Spark amounts are whole numbers. Converting rupees to Spark rounds down.
- New accounts, including the owner's, start with 0 Spark. There is no hidden welcome balance.
- This **replaces** the earlier rule that Spark is "an internal credit, not cash." The wallet, ledger, premium
  reserve / settle / refund logic and Evolution separation are unchanged.
- **Cash-out is switched off.** A quote can be requested, but real rupee payout needs both a payment provider
  and `SAGE_SPARK_CASH_OUT_ENABLED=true`. Until then the app reports payout as unavailable.

> **Legal check before cash-out.** A balance that users can redeem for money at a fixed rate is generally treated
> as stored value or e-money, and payment-system rules (in Nepal, Nepal Rastra Bank licensing) may apply. Get
> proper local legal advice before enabling payout or offering Spark to other people. This blueprint is not legal advice.

### 6.2 Spend Trust Ladder (PROVISIONAL)

This is the **Money Upgrade** path in the locked Evolution system. It limits spending only; it does not change
the skill-based Evolution rank.

1. SAGE earns first. The owner never funds it.
2. Levels: Bronze, Silver, Gold, each with Low / Mid / High. A level is reached when lifetime earnings reach its threshold.
3. **Savings lock.** Earnings up to the current level's threshold are locked as savings and are never spendable.
   Only the surplus above that is spendable. Example: earn 60 at the 50 level, 50 is locked, at most 10 is spendable.
4. **Percentage rule.** One spend may be at most a share of lifetime earnings, and the share shrinks as earnings grow.
5. **Absolute ceiling.** No single spend may exceed the ceiling, however large the balance.
6. **Owner approval on every spend.** A passing check only means the amount may be shown to the owner.
7. **Fail closed.** Unknown levels, zero or negative amounts are refused.

The smaller of the surplus, the percentage cap and the ceiling is the limit for one spend.

| Setting | Current value (PROVISIONAL) |
|---|---|
| Bronze Low / Mid / High thresholds | 1 / 10 / 50 Spark |
| Silver and Gold | **not set yet**; limits stay at Bronze High until set |
| Percentage of lifetime earnings per spend | 10% up to 100, 5% up to 1,000, 2% up to 10,000, 1% above |
| Absolute ceiling per spend | 200 Spark |

Code: `economy/spend_ladder.py`. Tests: `tests/test_spark_currency.py`. API (owner-authenticated):
`GET /economy/currency`, `GET /economy/cash-out/quote?spark=N`, `GET /economy/spend-limit`.

### 6.3 Decisions the owner still needs to make

1. **Units.** The Bronze caps (1, 10, 50) and the ceiling were first spoken in dollars. They are currently read as
   Spark, which means NPR 1, 10 and 50 (very small). Should they stay as Spark, or be restated in rupees (for example
   NPR 140, 1,400, 7,000)?
2. **Silver and Gold** thresholds for Low / Mid / High.
3. **Ceiling.** 200 Spark now (the safer end of the owner's 200 to 500 range). Raise to 500?
4. **Percentage bands.** 10 / 5 / 2 / 1 is an interpretation of the owner's examples.
5. **How the level cap and the percentage rule combine.** Currently the stricter one wins. In the 60-earned example
   that gives 6, not 10.

---

## 7. Risks to keep in front of us

- **Autonomous ad spending** can lose money quickly and platforms suspend accounts that look automated. Hence the ladder and approval.
- **Screen, file and message access** is a large privacy and security surface. Keep it opt-in, scoped and logged.
- **Public repository.** No keys, tokens, OAuth IDs or private chats go in GitHub. A scan on 2026-10-11 found none in the current tree.
- **Reselling the system** adds multi-user isolation, payments law and support obligations.
- **Free-tier limits.** Free AI providers and free hosting have quotas and can disappear; plan fallbacks.
