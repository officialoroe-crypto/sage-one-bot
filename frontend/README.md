# SAGE ONE Flutter Frontend

First mobile command-center slice for SAGE ONE.

## Design direction

- Premium dark interface
- One primary command surface
- Background execution is visible but does not block the user
- Research, Tasks, Projects, and Agent are first-class modules
- Minimal chrome; the command is the product

## Backend connection

Defaults are platform-aware:

- Flutter Web / Windows desktop: `http://localhost:8010`
- Android emulator: `http://10.0.2.2:8010`
- Other devices: override with `--dart-define=SAGE_API_URL=http://YOUR_BACKEND_HOST:8010`

## Google authentication

SAGE verifies Google ID tokens on the backend. The web client obtains the non-secret Google OAuth client ID from `GET /identity/config`, so it does not need to be embedded in the Flutter build.

For local web development, configure the same Google OAuth web client ID in the backend environment as `GOOGLE_CLIENT_ID`. Add the exact local origin you use to the OAuth client's Authorized JavaScript origins, for example `http://localhost:8080`.

The web implementation uses Google's official rendered sign-in button and the authentication event stream; it does not call `authenticate()` from a custom Flutter button on web.

## Local web preview

1. Start the SAGE backend on port `8010`.
2. Build the Flutter web app from this directory.
3. Serve `build/web` from `http://localhost:8080` (or another configured origin).

## Current integration points

- `GET /identity/config`
- `POST /identity/google`
- `GET /identity/me`
- `GET /identity/onboarding/options`
- `POST /identity/onboarding`
- `POST /identity/phone/send`
- `POST /identity/phone/verify`
- `GET /brain/routing`
- `POST /execute/background`
- `GET /tasks/{task_id}`
