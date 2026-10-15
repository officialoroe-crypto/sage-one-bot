# SAGE ONE Website

The `website/` directory is the public-facing SAGE ONE landing surface.

## Boundaries

- This site explains SAGE ONE, SAGE WORKFLOW, Intelligence, Spark and Evolution.
- It does not expose authenticated workspace data.
- It does not pretend that publishing, social connections, research or execution are available from the public landing page.
- The authenticated product remains the Flutter application and SAGE Core APIs.

## Local preview

Serve this directory with any static HTTP server. For example:

```text
python -m http.server 8080 --directory website
```

Then open `http://127.0.0.1:8080`.

## Deployment

`.github/workflows/sage-one-god-mode-pages.yml` builds the Flutter app and publishes one combined Pages artifact: the marketing site at `/sage-one/` and the app at `/sage-one/app/`. Pushes to `main` that change `website/**` or `frontend/**` trigger deployment; a manual workflow dispatch is also available. Repository Pages must be configured to use GitHub Actions.

## Contents

Hero with the canonical logo, the Learn-to-Evolution flow, the two progression paths, an Evolution explorer (13 ranks, Low/Mid/High, transition preview), the Spark converter (1 Spark = NPR 1), a spend-limit calculator that mirrors `economy/spend_ladder.py`, and the roadmap from `docs/SAGE_MASTER_BLUEPRINT.md`. Images in `assets/` are web-sized copies of the owner's design assets in `docs/design/`. The calculator numbers are provisional until the owner confirms them.

## Design direction

The website follows the SAGE ONE cinematic system: near-black foundation, cyan/blue/violet intelligence accents, gold for economy/premium signals, orbital-core motifs, restrained motion and responsive layouts. The landing page describes the product direction without claiming that unfinished integrations are already live.
