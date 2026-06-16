#!/usr/bin/env python3
"""
FIFA World Cup 2026 — Live Data Fetcher
Runs hourly via GitHub Actions.
Fetches from api-football.com (free tier: 100 calls/day).
Writes data.json which the HTML page reads on load.
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.error

# ── CONFIG ────────────────────────────────────────────────────────────
API_KEY      = os.environ.get("FOOTBALL_API_KEY", "")
API_HOST     = "v3.football.api-sports.io"
WC_2026_ID   = 1                 # FIFA World Cup
WC_2026_YEAR = 2026

# All 12 group names and their teams (static — set by FIFA draw)
GROUPS_STATIC = {
    "A": ["Mexico", "South Korea", "Czechia", "South Africa"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["United States", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curaçao"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Colombia", "DR Congo", "Uzbekistan"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

# Fixed R32 bracket structure (FIFA published, never changes)
R32_BRACKET = [
    # LEFT HALF
    {"id": "M73", "venue": "Los Angeles · Jun 28", "slot1": "2A", "slot2": "2B", "side": "left"},
    {"id": "M74", "venue": "Boston · Jun 29",      "slot1": "1E", "slot2": "3rd-ABCDF", "side": "left"},
    {"id": "M75", "venue": "Monterrey · Jun 29",   "slot1": "1F", "slot2": "2C", "side": "left"},
    {"id": "M76", "venue": "Houston · Jun 29",     "slot1": "1C", "slot2": "2F", "side": "left"},
    {"id": "M77", "venue": "New York · Jun 30",    "slot1": "1I", "slot2": "3rd-CDFGH", "side": "left"},
    {"id": "M78", "venue": "Dallas · Jun 30",      "slot1": "2E", "slot2": "2I", "side": "left"},
    {"id": "M79", "venue": "Mexico City · Jun 30", "slot1": "1A", "slot2": "3rd-CEFHI", "side": "left"},
    {"id": "M80", "venue": "Atlanta · Jul 1",      "slot1": "1L", "slot2": "3rd-EHIJK", "side": "left"},
    # RIGHT HALF
    {"id": "M81", "venue": "San Francisco · Jul 1","slot1": "1D", "slot2": "3rd-BEFIJ", "side": "right"},
    {"id": "M82", "venue": "Seattle · Jul 1",      "slot1": "1G", "slot2": "3rd-AEHIJ", "side": "right"},
    {"id": "M83", "venue": "Toronto · Jul 2",      "slot1": "2K", "slot2": "2L", "side": "right"},
    {"id": "M84", "venue": "Los Angeles · Jul 2",  "slot1": "1H", "slot2": "2J", "side": "right"},
    {"id": "M85", "venue": "Vancouver · Jul 2",    "slot1": "1B", "slot2": "3rd-EFGIJ", "side": "right"},
    {"id": "M86", "venue": "Miami · Jul 3",        "slot1": "1J", "slot2": "2H", "side": "right"},
    {"id": "M87", "venue": "Kansas City · Jul 3",  "slot1": "1K", "slot2": "3rd-DEIJL", "side": "right"},
    {"id": "M88", "venue": "Dallas · Jul 3",       "slot1": "2D", "slot2": "2G", "side": "right"},
]

# Pre-tournament win probability estimates (from betting markets, Dec 2025)
# These are the BASE priors — updated by current standing bonus
WIN_PROBS = {
    "France": 12.0, "Argentina": 11.5, "England": 10.5, "Brazil": 9.5,
    "Spain": 9.0,   "Germany": 8.5,    "Portugal": 7.0, "Netherlands": 6.5,
    "USA": 4.5,     "Belgium": 3.5,    "Uruguay": 3.0,  "Colombia": 3.0,
    "Croatia": 2.5, "Mexico": 2.5,     "Norway": 2.5,   "Switzerland": 2.0,
    "Sweden": 1.8,  "Australia": 1.5,  "Ecuador": 1.5,  "Canada": 1.5,
    "Japan": 1.5,   "Senegal": 1.5,    "Morocco": 1.8,  "Scotland": 1.2,
    "Algeria": 1.0, "Austria": 1.0,    "South Korea": 1.2, "Egypt": 0.8,
    "Czechia": 0.8, "Iran": 0.7,       "Saudi Arabia": 0.7,"Bosnia and Herzegovina": 0.6,
    "Qatar": 0.5,   "Tunisia": 0.5,    "Ghana": 0.5,    "Panama": 0.4,
    "Paraguay": 0.6,"Türkiye": 1.2,    "DR Congo": 0.4, "Uzbekistan": 0.3,
    "Jordan": 0.3,  "Iraq": 0.4,       "Ivory Coast": 0.8,"Haiti": 0.2,
    "New Zealand": 0.3, "Cape Verde": 0.3, "South Africa": 0.4, "Curaçao": 0.1,
}

# ── API CALLS ─────────────────────────────────────────────────────────

def api_get(endpoint, params=None):
    """Call api-football.com and return parsed JSON."""
    if not API_KEY:
        return None
    url = f"https://{API_HOST}/{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": API_HOST,
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"API error ({endpoint}): {e}", file=sys.stderr)
        return None


def fetch_standings():
    """Returns dict: group_letter -> list of team standing dicts."""
    data = api_get("standings", {"league": WC_2026_ID, "season": WC_2026_YEAR})
    if not data or not data.get("response"):
        return None
    groups = {}
    for league in data["response"]:
        for standing_group in league.get("league", {}).get("standings", []):
            if not standing_group:
                continue
            letter = None
            for team_entry in standing_group:
                grp = team_entry.get("group", "")
                # e.g. "Group A"
                if "Group " in grp:
                    letter = grp.split("Group ")[-1].strip()
                    break
            if not letter:
                continue
            teams = []
            for entry in standing_group:
                t = entry.get("team", {})
                all_stats = entry.get("all", {})
                goals = all_stats.get("goals", {})
                teams.append({
                    "name": t.get("name", ""),
                    "logo": t.get("logo", ""),
                    "played": all_stats.get("played", 0),
                    "win":    all_stats.get("win", 0),
                    "draw":   all_stats.get("draw", 0),
                    "lose":   all_stats.get("lose", 0),
                    "gf":     goals.get("for", 0),
                    "ga":     goals.get("against", 0),
                    "gd":     entry.get("goalsDiff", 0),
                    "points": entry.get("points", 0),
                    "rank":   entry.get("rank", 0),
                })
            groups[letter] = sorted(teams, key=lambda x: x["rank"])
    return groups if groups else None


def fetch_fixtures():
    """Returns list of all WC 2026 fixtures with scores."""
    data = api_get("fixtures", {"league": WC_2026_ID, "season": WC_2026_YEAR})
    if not data or not data.get("response"):
        return []
    fixtures = []
    for f in data["response"]:
        fix   = f.get("fixture", {})
        teams = f.get("teams", {})
        goals = f.get("goals", {})
        score = f.get("score", {})
        status = fix.get("status", {}).get("short", "")
        fixtures.append({
            "id":       fix.get("id"),
            "date":     fix.get("date", ""),
            "venue":    fix.get("venue", {}).get("name", ""),
            "status":   status,
            "home":     teams.get("home", {}).get("name", ""),
            "away":     teams.get("away", {}).get("name", ""),
            "home_goals": goals.get("home"),
            "away_goals": goals.get("away"),
            "finished": status in ("FT", "AET", "PEN"),
            "live":     status in ("1H", "HT", "2H", "ET", "P"),
        })
    return fixtures


# ── PROBABILITY CALCULATION ───────────────────────────────────────────

def calc_qualify_prob(team_name, rank_in_group, played, points, remaining):
    """
    Estimate probability (0-100) that this team qualifies from their
    current position (1st or 2nd = auto qualify, 3rd = possible best third).
    Simple model: base prior × position bonus × points momentum.
    """
    base = WIN_PROBS.get(team_name, 0.5)

    if played == 0:
        # Not started — use pre-tournament rank in group
        bonuses = {1: 1.4, 2: 1.0, 3: 0.7, 4: 0.4}
        multiplier = bonuses.get(rank_in_group, 0.5)
        raw = base * multiplier
    else:
        # Points-based: 3pts = win, momentum bonus
        pts_per_game = points / max(played, 1)
        projected_pts = points + pts_per_game * remaining

        if rank_in_group == 1:
            raw = base * (1.5 + min(projected_pts / 9, 1.0) * 0.5)
        elif rank_in_group == 2:
            raw = base * (1.0 + min(projected_pts / 9, 0.8) * 0.4)
        elif rank_in_group == 3:
            raw = base * (0.5 + min(projected_pts / 9, 0.5) * 0.3)
        else:
            raw = base * 0.2

    # Normalise to 0-99 range
    prob = min(99, max(1, round(raw * 6)))
    return prob


def build_group_data(standings, fixtures):
    """
    Merge API standings with static group data.
    Returns list of group dicts ready for the frontend.
    """
    groups_out = []
    for letter, static_teams in GROUPS_STATIC.items():
        # Get live standings for this group if available
        live = standings.get(letter, []) if standings else []
        live_map = {t["name"]: t for t in live}

        teams_out = []
        for i, tname in enumerate(static_teams):
            live_t = live_map.get(tname, {})
            played  = live_t.get("played", 0)
            points  = live_t.get("points", 0)
            rank    = live_t.get("rank", i + 1)
            remaining = 3 - played

            teams_out.append({
                "name":    tname,
                "played":  played,
                "win":     live_t.get("win", 0),
                "draw":    live_t.get("draw", 0),
                "lose":    live_t.get("lose", 0),
                "gf":      live_t.get("gf", 0),
                "ga":      live_t.get("ga", 0),
                "gd":      live_t.get("gd", 0),
                "points":  points,
                "rank":    rank,
                "qualify_prob": calc_qualify_prob(tname, rank, played, points, remaining),
            })

        # Sort by rank (from API) or points
        teams_out.sort(key=lambda x: (x["rank"], -x["points"], -x["gd"], -x["gf"]))

        # Get results and upcoming for this group from fixtures
        group_fixtures = [
            f for f in fixtures
            if f["home"] in static_teams and f["away"] in static_teams
        ]
        results  = [f for f in group_fixtures if f["finished"]]
        upcoming = [f for f in group_fixtures if not f["finished"] and not f["live"]]
        live_now = [f for f in group_fixtures if f["live"]]

        groups_out.append({
            "letter":   letter,
            "teams":    teams_out,
            "results":  [{"home": f["home"], "away": f["away"],
                          "score": f"{f['home_goals']}–{f['away_goals']}",
                          "date": f["date"][:10]} for f in results],
            "upcoming": [{"home": f["home"], "away": f["away"],
                          "date": f["date"][:10]} for f in upcoming[:4]],
            "live":     [{"home": f["home"], "away": f["away"],
                          "home_goals": f["home_goals"],
                          "away_goals": f["away_goals"]} for f in live_now],
        })

    return groups_out


def resolve_r32_slot(slot, groups_out):
    """
    Given a slot like '1A', '2B', '3rd-ABCDF', resolve to team name + prob.
    """
    if slot.startswith("3rd"):
        return {"name": None, "label": slot.replace("3rd-", "3rd ").replace("-", "/"),
                "status": "tbd", "prob": None}

    pos_str = slot[0]   # '1' or '2'
    letter  = slot[1:]  # 'A', 'B', etc.
    pos     = int(pos_str) - 1  # 0-indexed

    group = next((g for g in groups_out if g["letter"] == letter), None)
    if not group or not group["teams"]:
        return {"name": None, "label": slot, "status": "tbd", "prob": None}

    teams = group["teams"]
    if pos >= len(teams):
        return {"name": None, "label": slot, "status": "tbd", "prob": None}

    team = teams[pos]
    # Determine status
    any_played = any(t["played"] > 0 for t in teams)
    if not any_played:
        status = "likely"
    elif team["played"] > 0:
        status = "confirmed"
    else:
        status = "likely"

    return {
        "name":   team["name"],
        "label":  slot,
        "status": status,
        "prob":   team["qualify_prob"],
    }


def build_bracket(groups_out):
    """Build R32 bracket with resolved teams."""
    bracket = []
    for match in R32_BRACKET:
        t1 = resolve_r32_slot(match["slot1"], groups_out)
        t2 = resolve_r32_slot(match["slot2"], groups_out)
        bracket.append({
            "id":     match["id"],
            "venue":  match["venue"],
            "side":   match["side"],
            "slot1":  match["slot1"],
            "slot2":  match["slot2"],
            "t1":     t1,
            "t2":     t2,
        })
    return bracket


# ── FALLBACK DATA (used when API unavailable) ─────────────────────────
# Hard-coded MD1 results as of June 16 2026

FALLBACK_GROUPS = [
    {"letter":"A","teams":[
        {"name":"Mexico","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":0,"gd":2,"points":3,"rank":1,"qualify_prob":72},
        {"name":"South Korea","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":1,"gd":1,"points":3,"rank":2,"qualify_prob":58},
        {"name":"Czechia","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":2,"gd":-1,"points":0,"rank":3,"qualify_prob":35},
        {"name":"South Africa","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":2,"gd":-2,"points":0,"rank":4,"qualify_prob":22},
    ],"results":[{"home":"Mexico","away":"South Africa","score":"2–0","date":"2026-06-11"},{"home":"South Korea","away":"Czechia","score":"2–1","date":"2026-06-11"}],
    "upcoming":[{"home":"Czechia","away":"South Africa","date":"2026-06-18"},{"home":"Mexico","away":"South Korea","date":"2026-06-18"}],"live":[]},

    {"letter":"B","teams":[
        {"name":"Switzerland","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":1,"qualify_prob":52},
        {"name":"Canada","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":48},
        {"name":"Qatar","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":3,"qualify_prob":30},
        {"name":"Bosnia and Herzegovina","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":4,"qualify_prob":28},
    ],"results":[{"home":"Canada","away":"Bosnia and Herzegovina","score":"1–1","date":"2026-06-12"},{"home":"Qatar","away":"Switzerland","score":"1–1","date":"2026-06-14"}],
    "upcoming":[{"home":"Switzerland","away":"Bosnia and Herzegovina","date":"2026-06-18"},{"home":"Canada","away":"Qatar","date":"2026-06-19"}],"live":[]},

    {"letter":"C","teams":[
        {"name":"Scotland","played":1,"win":1,"draw":0,"lose":0,"gf":1,"ga":0,"gd":1,"points":3,"rank":1,"qualify_prob":44},
        {"name":"Brazil","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":70},
        {"name":"Morocco","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":3,"qualify_prob":58},
        {"name":"Haiti","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":1,"gd":-1,"points":0,"rank":4,"qualify_prob":12},
    ],"results":[{"home":"Scotland","away":"Haiti","score":"1–0","date":"2026-06-14"},{"home":"Brazil","away":"Morocco","score":"1–1","date":"2026-06-14"}],
    "upcoming":[{"home":"Morocco","away":"Scotland","date":"2026-06-20"},{"home":"Brazil","away":"Haiti","date":"2026-06-20"}],"live":[]},

    {"letter":"D","teams":[
        {"name":"United States","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":0,"gd":2,"points":3,"rank":1,"qualify_prob":78},
        {"name":"Australia","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":52},
        {"name":"Paraguay","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":38},
        {"name":"Türkiye","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":2,"gd":-2,"points":0,"rank":4,"qualify_prob":34},
    ],"results":[{"home":"United States","away":"Türkiye","score":"2–0","date":"2026-06-12"}],
    "upcoming":[{"home":"Australia","away":"Paraguay","date":"2026-06-13"},{"home":"United States","away":"Australia","date":"2026-06-19"}],"live":[]},

    {"letter":"E","teams":[
        {"name":"Ecuador","played":1,"win":1,"draw":0,"lose":0,"gf":4,"ga":1,"gd":3,"points":3,"rank":1,"qualify_prob":62},
        {"name":"Germany","played":1,"win":1,"draw":0,"lose":0,"gf":3,"ga":0,"gd":3,"points":3,"rank":2,"qualify_prob":60},
        {"name":"Ivory Coast","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":4,"gd":-3,"points":0,"rank":3,"qualify_prob":28},
        {"name":"Curaçao","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":3,"gd":-3,"points":0,"rank":4,"qualify_prob":8},
    ],"results":[{"home":"Germany","away":"Curaçao","score":"3–0","date":"2026-06-13"},{"home":"Ecuador","away":"Ivory Coast","score":"4–1","date":"2026-06-13"}],
    "upcoming":[{"home":"Germany","away":"Ivory Coast","date":"2026-06-20"},{"home":"Ecuador","away":"Curaçao","date":"2026-06-20"}],"live":[]},

    {"letter":"F","teams":[
        {"name":"Sweden","played":1,"win":1,"draw":0,"lose":0,"gf":5,"ga":1,"gd":4,"points":3,"rank":1,"qualify_prob":65},
        {"name":"Netherlands","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":2,"qualify_prob":72},
        {"name":"Japan","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":3,"qualify_prob":42},
        {"name":"Tunisia","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":5,"gd":-4,"points":0,"rank":4,"qualify_prob":14},
    ],"results":[{"home":"Sweden","away":"Tunisia","score":"5–1","date":"2026-06-14"},{"home":"Netherlands","away":"Japan","score":"2–2","date":"2026-06-14"}],
    "upcoming":[{"home":"Netherlands","away":"Sweden","date":"2026-06-20"},{"home":"Tunisia","away":"Japan","date":"2026-06-20"}],"live":[]},

    {"letter":"G","teams":[
        {"name":"Belgium","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":1,"qualify_prob":48},
        {"name":"Egypt","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":40},
        {"name":"Iran","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":3,"qualify_prob":32},
        {"name":"New Zealand","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":4,"qualify_prob":24},
    ],"results":[{"home":"Belgium","away":"Egypt","score":"1–1","date":"2026-06-15"},{"home":"Iran","away":"New Zealand","score":"2–2","date":"2026-06-15"}],
    "upcoming":[{"home":"Belgium","away":"Iran","date":"2026-06-21"},{"home":"New Zealand","away":"Egypt","date":"2026-06-21"}],"live":[]},

    {"letter":"H","teams":[
        {"name":"Spain","played":1,"win":0,"draw":1,"lose":0,"gf":0,"ga":0,"gd":0,"points":1,"rank":1,"qualify_prob":55},
        {"name":"Saudi Arabia","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":36},
        {"name":"Uruguay","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":3,"qualify_prob":44},
        {"name":"Cape Verde","played":1,"win":0,"draw":1,"lose":0,"gf":0,"ga":0,"gd":0,"points":1,"rank":4,"qualify_prob":22},
    ],"results":[{"home":"Spain","away":"Cape Verde","score":"0–0","date":"2026-06-15"},{"home":"Saudi Arabia","away":"Uruguay","score":"1–1","date":"2026-06-15"}],
    "upcoming":[{"home":"Spain","away":"Saudi Arabia","date":"2026-06-21"},{"home":"Uruguay","away":"Cape Verde","date":"2026-06-21"}],"live":[]},

    {"letter":"I","teams":[
        {"name":"France","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":1,"qualify_prob":82},
        {"name":"Senegal","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":55},
        {"name":"Norway","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":65},
        {"name":"Iraq","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":18},
    ],"results":[],
    "upcoming":[{"home":"France","away":"Senegal","date":"2026-06-16"},{"home":"Iraq","away":"Norway","date":"2026-06-16"}],"live":[]},

    {"letter":"J","teams":[
        {"name":"Argentina","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":1,"qualify_prob":86},
        {"name":"Algeria","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":45},
        {"name":"Austria","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":38},
        {"name":"Jordan","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":15},
    ],"results":[],
    "upcoming":[{"home":"Argentina","away":"Algeria","date":"2026-06-16"},{"home":"Austria","away":"Jordan","date":"2026-06-17"}],"live":[]},

    {"letter":"K","teams":[
        {"name":"Portugal","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":1,"qualify_prob":84},
        {"name":"Colombia","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":60},
        {"name":"DR Congo","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":28},
        {"name":"Uzbekistan","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":18},
    ],"results":[],
    "upcoming":[{"home":"Portugal","away":"DR Congo","date":"2026-06-17"},{"home":"Uzbekistan","away":"Colombia","date":"2026-06-17"}],"live":[]},

    {"letter":"L","teams":[
        {"name":"England","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":1,"qualify_prob":76},
        {"name":"Croatia","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":55},
        {"name":"Ghana","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":32},
        {"name":"Panama","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":20},
    ],"results":[],
    "upcoming":[{"home":"England","away":"Croatia","date":"2026-06-17"},{"home":"Ghana","away":"Panama","date":"2026-06-18"}],"live":[]},
]


# ── MAIN ──────────────────────────────────────────────────────────────

def main():
    print("Fetching World Cup 2026 data...")
    now = datetime.datetime.utcnow().isoformat() + "Z"

    # Try live API first
    groups_out = None
    fixtures   = []

    if API_KEY:
        print("API key found — fetching live data...")
        standings = fetch_standings()
        fixtures  = fetch_fixtures() or []
        if standings:
            groups_out = build_group_data(standings, fixtures)
            print(f"Live data fetched: {len(groups_out)} groups, {len(fixtures)} fixtures")
        else:
            print("Standings API returned nothing — using fallback", file=sys.stderr)
    else:
        print("No API key set — using fallback data", file=sys.stderr)

    if not groups_out:
        groups_out = FALLBACK_GROUPS

    bracket = build_bracket(groups_out)

    output = {
        "updated_at": now,
        "source": "live" if API_KEY and fixtures else "fallback",
        "groups": groups_out,
        "bracket": bracket,
    }

    out_path = os.path.join(os.path.dirname(__file__), "data.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Written to {out_path}")
    print(f"Source: {output['source']} | Updated: {now}")


if __name__ == "__main__":
    main()
