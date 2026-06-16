# FIFA World Cup 2026 — Live Tracker

A self-updating World Cup bracket and group stage tracker hosted on GitHub Pages.
Data refreshes **every hour** via GitHub Actions — no server needed.

---

## How it works

```
GitHub Actions (every hour)
  └── fetch_data.py          ← fetches live scores from api-football.com
        └── data.json        ← committed back to repo
              └── index.html ← reads data.json on every page load
                    └── GitHub Pages serves it to the world
```

- **`fetch_data.py`** — Python script that calls the api-football.com API, computes
  qualification probabilities, and writes `data.json`. Falls back to hardcoded
  MD1 data if the API is unavailable.
- **`data.json`** — The live data file. Committed to the repo by the Action so
  visitors always get data ≤1 hour old without any API calls from their browser.
- **`index.html`** — Fully self-contained page. Loads `data.json` on visit,
  renders the mirrored bracket + group tables, and auto-refreshes every hour.
- **`.github/workflows/update.yml`** — Runs `fetch_data.py` every hour on cron,
  commits any changes to `data.json`.

---

## Setup (5 minutes)

### 1. Fork / create repo

Create a new GitHub repository and push these files to the `main` branch:

```
worldcup2026/
├── .github/
│   └── workflows/
│       └── update.yml
├── index.html
├── fetch_data.py
├── data.json          ← initial fallback data, updated by Action
└── README.md
```

### 2. Get a free API key

1. Go to [api-football.com](https://www.api-football.com/) (RapidAPI)
2. Sign up for the **free tier** — 100 requests/day (plenty for hourly updates)
3. Copy your API key

### 3. Add the secret to GitHub

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `FOOTBALL_API_KEY`
4. Value: your api-football.com key
5. Click **Add secret**

Without the secret, the page still works using the built-in fallback data —
it just won't fetch live scores until the secret is added.

### 4. Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)`
4. Click **Save**

Your page will be live at:
`https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/`

### 5. Trigger the first data update

Go to **Actions** → **Update World Cup Data** → **Run workflow** → **Run workflow**

This fetches live data immediately without waiting for the next hourly cron.

---

## Costs

| Resource | Usage | Cost |
|---|---|---|
| GitHub Actions | ~720 runs × ~15s each ≈ 3 hrs/month | Free (2,000 min/month free) |
| GitHub Pages | Static hosting | Free |
| api-football.com | ~24 calls/day × 39 days ≈ 936 calls | Free (100/day limit — enough) |

**Total cost: $0**

---

## Updating data manually

```bash
FOOTBALL_API_KEY=your_key_here python3 fetch_data.py
```

Then commit and push `data.json`.

---

## Tech stack

- Pure HTML/CSS/JS — zero dependencies, no build step
- Python 3 stdlib only — no pip installs needed
- GitHub Actions for scheduling
- GitHub Pages for hosting
- api-football.com for live World Cup data
