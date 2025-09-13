PCS LiveStats → Pushover Notifier

Small CLI to poll ProCyclingStats LiveStats pages and push updates to your phone via Pushover.

- Uses the `procyclingstats` Python package to fetch the LiveStats HTML
- Extracts the embedded `var data = {...}` JSON and detects changes
- Notifies only on: race start, 100 km to‑go, 50 km to‑go, 10 km to‑go, and finish

Quick Start

1) Create and activate a virtualenv, then install deps:

`python3 -m venv .venv`
`. .venv/bin/activate`
`pip install -r requirements.txt`

2) Set Pushover credentials (or use a `.env` file):

`export PUSHOVER_TOKEN=your_app_token`
`export PUSHOVER_USER=your_user_key`

3) Run the poller, pointing at a PCS LiveStats page (relative URL preferred):

`python -m pcs_pushover.cli \
  --race "race/tour-de-france/2024/stage-1/live" \
  --interval 30`

Or with a full URL (e.g., Vuelta):

`python -m pcs_pushover.cli \
  --race "https://www.procyclingstats.com/race/vuelta-a-espana/2025/stage-20/live" \
  --interval 30`

Auto Mode (discover and track live races)

- Automatically discovers live trackers from the PCS homepage and tracks each race with the same notification rules (start, 100/50/10 km, finish):

`python -m pcs_pushover.cli --auto --interval 30`

- Optional: adjust discovery frequency (default 120 seconds):

`python -m pcs_pushover.cli --auto --interval 30 --discovery-interval 90`

Deployment (Raspberry Pi self‑hosted runner)

- Build and run in Docker locally:

`docker build -t pcs-pushover:latest .`
`docker run -d --name pcs-pushover --restart unless-stopped \
  -e PUSHOVER_TOKEN=your_app_token \
  -e PUSHOVER_USER=your_user_key \
  pcs-pushover:latest`

- GitHub Actions deploy (self‑hosted runner):
  - Register your Raspberry Pi as a GitHub Actions self‑hosted runner (with Docker installed).
  - Add repo secrets `PUSHOVER_TOKEN`, `PUSHOVER_USER` (and optional `PCS_ARGS`, e.g. `--auto --interval 30`).
  - On push to `main`/`master`, `.github/workflows/deploy.yml` will build and (re)start the container on the Pi.


- `--race` accepts a relative PCS path (`race/.../live`) or a full URL.
- `--interval` is the polling interval in seconds.

4) Optional: run once to inspect data without looping:

`python -m pcs_pushover.cli --race "race/tour-de-france/2024/stage-1/live" --once --debug`

What Gets Notified

- Only these events:
  - Race starts (transition to live/running)
  - 100 km to‑go (crossing from above to at/below)
  - 50 km to‑go (crossing from above to at/below)
  - 10 km to‑go (crossing from above to at/below)
  - Finished

Notes

- LiveStats pages differ by race/stage. Not all keys are always present. The tool is defensive and logs when data is missing.
- State is kept in `.cache/state.json` per race so you don’t get duplicate notifications across restarts. Km notifications trigger only when crossing from above to below a marker during the current run; they aren’t backfilled if you start mid‑stage.
- If a page is temporarily unavailable, retries continue without crashing.

Configuration

- Env vars: `PUSHOVER_TOKEN`, `PUSHOVER_USER`
- CLI flags: see `python -m pcs_pushover.cli --help`

Safety

- This tool only reads public PCS pages and posts to Pushover. No scraping beyond what `procyclingstats` already does + extracting the embedded LiveStats JSON blob the page exposes.
