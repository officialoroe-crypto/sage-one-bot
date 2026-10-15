# Premium Spark Task — Local Migration & Smoke Test

This runbook is for the private SAGE ONE development environment. It does not authorize deployment or production database changes.

## 1. Stop the running backend

Stop the SAGE ONE API/worker process before applying the schema migration. This avoids a worker using the task table while columns are being added.

## 2. Run the additive migration

Open PowerShell and run the command from the canonical repository directory:

```powershell
cd C:\SageOne\sage_core
C:\SageOne\Backend\venv\Scripts\python.exe -m database.migrate
```

The migration adds missing columns to the existing `tasks` table, including `owner_key` and `premium_work_key`. It is designed to be repeatable: columns already present should be reported as `SKIP`.

Run the command a second time to confirm it reports no new changes. Do not delete or recreate the database to apply this migration.

## 3. Start the backend again

From `C:\SageOne\sage_core`:

```powershell
C:\SageOne\Backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
```

## 4. Premium task smoke-test checklist

Before testing premium execution, confirm:

- The authenticated session is the configured SAGE owner.
- The owner's Spark wallet has enough balance for the selected catalog work type.
- The premium task is created through `POST /tasks/premium`; do not pass a price or owner key from the client.
- The durable worker is enabled and running.
- The task reaches a terminal state and the Spark transaction becomes `settled` on success or `refunded` after terminal failure/cancellation.
- A repeated worker cycle does not charge or refund the same operation twice.

## Current verification boundary

CI covers the additive migration's repeatability on an isolated SQLite database and an isolated API-to-worker success path. The migration has **not** been run against the user's local database in this session, and no live provider-backed premium job has been executed.
