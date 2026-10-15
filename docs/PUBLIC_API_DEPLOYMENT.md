# Public SAGE ONE API deployment

The GitHub Pages site is static. The FastAPI service must run separately at a public HTTPS URL.

## 1. Deploy the API service

The backend entry point is `app.main:app` and the repository root has `requirements.txt`.

Use a Python web-service host that supports FastAPI. Configure:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check:** `/health`
- **Environment:** `SAGE_ENV=production`, `SAGE_PRIVATE_MODE=false`, `SAGE_DEV_MODE=false`
- **Google sign-in:** set `GOOGLE_CLIENT_ID` to the Web application OAuth client ID in the host's private environment settings. Never commit credentials.
- **Database:** set `SAGE_DATABASE_URL` to a persistent PostgreSQL database URL before using this service for real user data. The default SQLite database may be ephemeral on cloud hosts; do not treat it as durable production storage.
- Add any model-provider API keys only as private environment variables if the corresponding features are needed.

The service must expose HTTPS and `GET /health` and `GET /identity/config` must respond successfully. Set `SAGE_CORS_ORIGINS=https://officialoroe-crypto.github.io` in the host's environment settings (or confirm the default list still includes this origin). CORS must allow the public Pages origin.

Free service plans may sleep, limit resources, or have storage restrictions. Confirm the host's current limits before relying on it for persistent data or always-on availability.

## 2. Point the public web build at the backend

After the service is deployed and its HTTPS URL has been tested:

1. Open the repository's **Settings → Secrets and variables → Actions → Variables**.
2. Create a repository variable named `SAGE_API_URL`.
3. Set its value to the base HTTPS URL of the API, without a trailing slash. Example format only: `https://your-service.example.com`. Do not use localhost.
4. Run the **SAGE ONE Public Website and Web App** workflow from **Actions → Run workflow**, or push a change to `main`.

The workflow now refuses to deploy the public app when `SAGE_API_URL` is missing or not HTTPS. Pull-request builds still run without production configuration.

## 3. Verify before announcing launch

- `GET https://YOUR_API_HOST/health` returns HTTP 200.
- `GET https://YOUR_API_HOST/identity/config` returns HTTP 200 without exposing any secret.
- Browser developer tools show API requests going to the configured HTTPS host, not `localhost`.
- Complete Google sign-in and onboarding in the public app.
- Confirm database writes survive a service restart before storing real user data.

This document does not mean the service has already been deployed. Hosting account setup, database provisioning, and the actual API URL are required before the public app can pass end-to-end verification.
