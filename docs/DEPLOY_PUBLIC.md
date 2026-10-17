# Put SAGE ONE on the internet (free) and share it

Two parts: the **website** (free, GitHub Pages) and the **server** (free, Render). Secrets go into the Render dashboard only, never into GitHub.

What other people can do: anyone can open the public website and read about SAGE. Only **you** can sign in to the app: the server refuses every other Google account. (Opening it to others is a later, separate decision.)

## 1. Website: turn on GitHub Pages (2 minutes)
1. Open the repository `officialoroe-crypto/sage-one-bot` > **Settings** > **Pages**.
2. Under **Source** choose **GitHub Actions**.
3. Open the **Actions** tab, pick **Publish website (sage-one-bot)** and press **Run workflow** (it also runs on every push).
4. Your public link: `https://officialoroe-crypto.github.io/sage-one-bot/`. Share that.

## 2. Database: free Postgres so nothing is lost on restart
1. Create a free account at neon.tech (or supabase.com) and create a project.
2. Copy the connection string (starts with `postgresql://`). This is your `SAGE_DATABASE_URL`.

## 3. Google sign-in
1. Google Cloud Console > APIs & Services > **Credentials** > Create credentials > **OAuth client ID** > Web application.
2. Authorised JavaScript origins: `https://officialoroe-crypto.github.io` (and `http://localhost:8123` if you test locally).
3. Copy the **Client ID**. This is `GOOGLE_CLIENT_ID`. (It is public by design; there is no secret to copy.)

## 4. Server on Render
1. render.com > **New** > **Blueprint** > pick `sage-one-bot` (it reads `render.yaml`).
2. Fill the values it asks for: `GOOGLE_CLIENT_ID`, `SAGE_DATABASE_URL`, `SAGE_OWNER_AUTH_SUBJECT` (type `pending` for now), and at least one AI key (`GEMINI_API_KEY` is free).
3. Deploy. Your server address is shown on the service page, normally `https://sage-one-api.onrender.com`. If it differs, tell Claude or edit `apiBase` in `website/site-config.js` and the API host in the CSP of `website/chat/index.html` and `website/mobile/index.html`.

## 5. Tell the server who you are
1. Open `https://officialoroe-crypto.github.io/sage-one-bot/chat/` and sign in with Google. It will say this server is private.
2. In Render > your service > **Logs** find the line `Sign-in refused: Google subject=NUMBER ...`.
3. Put that NUMBER in `SAGE_OWNER_AUTH_SUBJECT`, save (Render restarts), and sign in again. You are now the owner.

## Free-tier facts
- Render free servers sleep after ~15 minutes idle; the first request after that takes up to a minute. The page says "Connecting..." meanwhile.
- Google sign-in lasts about an hour; sign in again when asked.
- Voice uses the browser's own speech tools (Chrome or Edge on Android/desktop work best; Nepali recognition depends on the device).
