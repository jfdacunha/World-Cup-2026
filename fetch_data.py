#!/usr/bin/env python3
"""
FIFA World Cup 2026 - Live Data Fetcher
Uses api.football-data.org (free tier).
Runs every 30 min via GitHub Actions -> writes data.json.
"""
import json, os, sys, datetime, urllib.request, urllib.error

API_KEY  = os.environ.get("FOOTBALL_API_KEY", "")
BASE_URL = "https://api.football-data.org/v4"
WC_CODE  = "WC"

WIN_PROBS = {
    'France':11.5,'Argentina':11.0,'England':10.0,'Brazil':9.0,'Spain':8.5,
    'Germany':8.0,'Portugal':6.5,'Netherlands':6.0,'United States':4.0,'Belgium':3.2,
    'Uruguay':2.8,'Colombia':2.8,'Croatia':2.4,'Mexico':2.3,'Norway':2.3,
    'Switzerland':1.9,'Sweden':1.7,'Australia':1.4,'Ecuador':1.4,'Canada':1.4,
    'Japan':1.4,'Senegal':1.4,'Morocco':1.7,'Scotland':1.1,'Algeria':0.95,
    'Austria':0.95,'South Korea':1.1,'Egypt':0.75,'Czechia':0.75,'Iran':0.65,
    'Saudi Arabia':0.65,'Bosnia and Herzegovina':0.55,'Qatar':0.45,'Tunisia':0.45,
    'Ghana':0.45,'Panama':0.35,'Paraguay':0.55,'Türkiye':1.1,'DR Congo':0.35,
    'Uzbekistan':0.28,'Jordan':0.28,'Iraq':0.38,'Ivory Coast':0.75,'Haiti':0.18,
    'New Zealand':0.28,'Cape Verde':0.28,'South Africa':0.38,'Curaçao':0.08,
}

def team_raw_strength(t):
    """Raw knockout strength = pre-tournament odds base × group-stage multiplier."""
    base = WIN_PROBS.get(t.get("name", ""), 0.3)
    mult = 1.0
    if t.get("played", 0) > 0:
        ppg = t["points"] / t["played"]
        rank = t.get("rank", 2)
        if rank == 1:   mult = 1.0 + ppg * 0.18
        elif rank == 2: mult = 1.0 + ppg * 0.08
        elif rank == 3: mult = 1.0 - 0.10
        else:           mult = 1.0 - 0.30
    return max(0.05, base * mult)


R32_MATCHES = [
    # LEFT SIDE (per official FIFA bracket image)
    # M74+M77 → R16 M89 · M73+M75 → R16 M90 · M83+M84 → R16 M93 · M81+M82 → R16 M94
    {"id":"M74","venue":"Boston - Jun 29",      "side":"left", "s1":"1E","s2":"3rd-ABCDF","kickoff":"2026-06-29T20:30:00Z"},
    {"id":"M77","venue":"New York - Jun 30",    "side":"left", "s1":"1I","s2":"3rd-CDFGH","kickoff":"2026-06-30T21:00:00Z"},
    {"id":"M73","venue":"Los Angeles - Jun 28", "side":"left", "s1":"2A","s2":"2B","kickoff":"2026-06-28T19:00:00Z"},
    {"id":"M75","venue":"Monterrey - Jun 29",   "side":"left", "s1":"1F","s2":"2C","kickoff":"2026-06-30T01:00:00Z"},
    {"id":"M83","venue":"Toronto - Jul 2",      "side":"left", "s1":"2K","s2":"2L","kickoff":"2026-07-02T23:00:00Z"},
    {"id":"M84","venue":"Los Angeles - Jul 2",  "side":"left", "s1":"1H","s2":"2J","kickoff":"2026-07-02T19:00:00Z"},
    {"id":"M81","venue":"San Francisco - Jul 1","side":"left", "s1":"1D","s2":"3rd-BEFIJ","kickoff":"2026-07-02T00:00:00Z"},
    {"id":"M82","venue":"Seattle - Jul 1",      "side":"left", "s1":"1G","s2":"3rd-AEHIJ","kickoff":"2026-07-01T20:00:00Z"},
    # RIGHT SIDE (per official FIFA bracket image)
    # M76+M78 → R16 M91 · M79+M80 → R16 M92 · M86+M88 → R16 M95 · M85+M87 → R16 M96
    {"id":"M76","venue":"Houston - Jun 29",     "side":"right","s1":"1C","s2":"2F","kickoff":"2026-06-29T17:00:00Z"},
    {"id":"M78","venue":"Dallas - Jun 30",      "side":"right","s1":"2E","s2":"2I","kickoff":"2026-06-30T17:00:00Z"},
    {"id":"M79","venue":"Mexico City - Jun 30", "side":"right","s1":"1A","s2":"3rd-CEFHI","kickoff":"2026-07-01T01:00:00Z"},
    {"id":"M80","venue":"Atlanta - Jul 1",      "side":"right","s1":"1L","s2":"3rd-EHIJK","kickoff":"2026-07-01T16:00:00Z"},
    {"id":"M86","venue":"Miami - Jul 3",        "side":"right","s1":"1J","s2":"2H","kickoff":"2026-07-03T22:00:00Z"},
    {"id":"M88","venue":"Dallas - Jul 3",       "side":"right","s1":"2D","s2":"2G","kickoff":"2026-07-03T18:00:00Z"},
    {"id":"M85","venue":"Vancouver - Jul 2",    "side":"right","s1":"1B","s2":"3rd-EFGIJ","kickoff":"2026-07-03T03:00:00Z"},
    {"id":"M87","venue":"Kansas City - Jul 3",  "side":"right","s1":"1K","s2":"3rd-DEIJL","kickoff":"2026-07-04T01:30:00Z"},
]

SLOT_MAP = {
    "1A":("A",0),"2A":("A",1),"1B":("B",0),"2B":("B",1),
    "1C":("C",0),"2C":("C",1),"1D":("D",0),"2D":("D",1),
    "1E":("E",0),"2E":("E",1),"1F":("F",0),"2F":("F",1),
    "1G":("G",0),"2G":("G",1),"1H":("H",0),"2H":("H",1),
    "1I":("I",0),"2I":("I",1),"1J":("J",0),"2J":("J",1),
    "1K":("K",0),"2K":("K",1),"1L":("L",0),"2L":("L",1),
}

GROUPS_ORDER = list("ABCDEFGHIJKL")

STATIC_TEAMS = {
    "A":["Mexico","South Korea","Czechia","South Africa"],
    "B":["Switzerland","Canada","Qatar","Bosnia and Herzegovina"],
    "C":["Scotland","Brazil","Morocco","Haiti"],
    "D":["United States","Australia","Paraguay","Türkiye"],
    "E":["Ecuador","Germany","Ivory Coast","Curaçao"],
    "F":["Sweden","Netherlands","Japan","Tunisia"],
    "G":["Belgium","Egypt","Iran","New Zealand"],
    "H":["Spain","Saudi Arabia","Uruguay","Cape Verde"],
    "I":["France","Senegal","Norway","Iraq"],
    "J":["Argentina","Algeria","Austria","Jordan"],
    "K":["Portugal","Colombia","DR Congo","Uzbekistan"],
    "L":["England","Croatia","Ghana","Panama"],
}

NAME_MAP = {
    # USA / Turkey variants
    "USA":                      "United States",
    "Turkey":                   "Türkiye",
    # Africa
    "Congo DR":                 "DR Congo",
    "DR Congo":                 "DR Congo",
    "Cote d'Ivoire":            "Ivory Coast",
    "Côte d'Ivoire":            "Ivory Coast",
    "Ivory Coast":              "Ivory Coast",
    # Cape Verde — API uses "Cape Verde Islands"
    "Cape Verde Islands":       "Cape Verde",
    "Cabo Verde":               "Cape Verde",
    "Cape Verde":               "Cape Verde",
    # Bosnia — API uses "Bosnia-Herzegovina"
    "Bosnia-Herzegovina":       "Bosnia and Herzegovina",
    "Bosnia and Herzegovina":   "Bosnia and Herzegovina",
    # Korea
    "Korea Republic":           "South Korea",
    "South Korea":              "South Korea",
    # Others that may vary
    "Iran":                     "Iran",
    "IR Iran":                  "Iran",
}

def normalize(name):
    return NAME_MAP.get(name, name)

def api_get(path):
    if not API_KEY:
        return None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"X-Auth-Token": API_KEY, "Accept":"application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} on {path}: {body[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error on {path}: {e}", file=sys.stderr)
        return None

def qualify_prob(name, rank, played, points):
    """
    Fallback for rank-3 only (rank-1/2 are handled by gap_qualify_prob).
    """
    if points == 0 and played >= 2: return 5
    if points <= 1: return 10
    if points <= 3: return 30
    return 50


def gap_qualify_prob(rank, pts, rank3_pts, games_remaining):
    """
    Gap-aware qualify probability for rank-1 or rank-2 teams.
    Takes the actual points gap to rank-3 into account — the old function
    ignored this, producing absurd values like Portugal=47% with a 3-pt lead.

    With 1 game remaining:
      gap > max_catch : mathematically safe → 99%
      gap = max_catch : tied only if we lose all AND rank3 wins all → 96/93%
      gap 1 below mc  : rank3 can surpass with one game swing → 89/82%
      gap = 0         : equal points — genuine 50/50 battle → 80/68%
      gap < 0         : we are currently BEHIND rank-3 → 65/45%
    """
    if games_remaining == 0:
        return 99
    max_catch = games_remaining * 3
    gap = pts - rank3_pts

    if gap > max_catch:
        return 99

    if rank == 1:
        if gap >= max_catch:     return 96
        if gap >= max_catch - 3: return 89
        if gap >= max_catch - 6: return 82
        if gap >= 0:             return max(68, 68 + int(gap / max(max_catch,1) * 20))
        return                         max(50, 50 + int(gap / max(max_catch,1) * 20))
    else:  # rank 2
        if gap >= max_catch:     return 93
        if gap >= max_catch - 3: return 82
        if gap >= max_catch - 6: return 70
        if gap >= 0:             return max(58, 58 + int(gap / max(max_catch,1) * 25))
        return                         max(35, 35 + int(gap / max(max_catch,1) * 30))

def check_eliminated(teams):
    BEST3 = 4
    for t in teams:
        played = t["played"]; remaining = 3-played
        max_pts = t["points"]+remaining*3; rank = t["rank"]
        pts3 = teams[2]["points"] if len(teams)>2 else 0
        if played==3 and rank==4: t["eliminated"]="group"
        elif played==2 and rank==4 and max_pts<pts3: t["eliminated"]="group"
        elif played==2 and rank==4 and max_pts<BEST3: t["eliminated"]="group"
        else: t["eliminated"]=None
    return teams

def fetch_standings():
    data = api_get(f"/competitions/{WC_CODE}/standings")
    if not data: return None
    groups = {}
    for s in data.get("standings",[]):
        if s.get("type") != "TOTAL": continue
        raw_grp = s.get("group","")
        # API returns "Group A" or "GROUP_A" — normalise both
        grp = raw_grp.replace("GROUP_","").replace("Group ","").replace("GROUP ","").strip()
        if not grp or len(grp)>2: continue
        teams = []
        for e in s.get("table",[]):
            nm = normalize(e.get("team",{}).get("name",""))
            teams.append({
                "name":nm,"played":e.get("playedGames",0),
                "win":e.get("won",0),"draw":e.get("draw",0),"lose":e.get("lost",0),
                "gf":e.get("goalsFor",0),"ga":e.get("goalsAgainst",0),
                "gd":e.get("goalDifference",0),"points":e.get("points",0),
                "rank":e.get("position",0),
            })
        if teams: groups[grp] = sorted(teams, key=lambda x:x["rank"])
    return groups or None

def fetch_matches():
    data = api_get(f"/competitions/{WC_CODE}/matches")
    if not data: return []
    out = []
    for m in data.get("matches",[]):
        status = m.get("status","")
        grp = m.get("group","") or ""
        letter = grp.replace("GROUP_","").replace("Group ","").replace("GROUP ","").strip()
        sc = m.get("score",{}); ft = sc.get("fullTime",{}); ht = sc.get("halfTime",{})
        # Convert UTC kickoff time to ET date (UTC-4 in June)
        # Late US games (e.g. 9pm ET = 01:00 UTC next day) need this correction
        _utc_str = m.get("utcDate","")
        try:
            _utc_dt  = datetime.datetime.fromisoformat(_utc_str.replace("Z","+00:00"))
            _et_date = (_utc_dt - datetime.timedelta(hours=4)).strftime("%Y-%m-%d")
        except Exception:
            _et_date = _utc_str[:10]
        # Sanity check: only trust an "IN_PLAY"/"PAUSED"/"HALFTIME" status if
        # the match actually kicked off recently. football-data.org has been
        # observed returning stale "IN_PLAY" statuses for matches that
        # finished days ago (e.g. a match status that never updated to
        # FINISHED). A real World Cup match (with stoppage time, ET, etc.)
        # never runs longer than ~3.5 hours from kickoff.
        is_status_live = status in ("IN_PLAY", "PAUSED", "HALFTIME")
        hours_since_kickoff = None
        if is_status_live:
            try:
                _now_utc = datetime.datetime.now(datetime.timezone.utc)
                hours_since_kickoff = (_now_utc - _utc_dt).total_seconds() / 3600
            except Exception:
                hours_since_kickoff = None
        # Only treat as genuinely live if kickoff was 0-3.5 hours ago
        # (negative means it hasn't started yet — also not "live" in our UI)
        really_live = (
            is_status_live and
            hours_since_kickoff is not None and
            0 <= hours_since_kickoff <= 3.5
        )

        out.append({
            "date":_et_date,"group":letter,
            "stage":m.get("stage",""),"status":status,
            "home":normalize(m.get("homeTeam",{}).get("name","")),
            "away":normalize(m.get("awayTeam",{}).get("name","")),
            "home_goals":ft.get("home"),"away_goals":ft.get("away"),
            "finished":status=="FINISHED" or (is_status_live and not really_live and ft.get("home") is not None),
            "live":really_live,
        })
    return out

def build_groups(standings, matches):
    groups_out = []
    for letter in GROUPS_ORDER:
        static = STATIC_TEAMS[letter]
        lmap = {t["name"]:t for t in (standings or {}).get(letter,[])}

        # Compute which teams in this group are in a currently-LIVE match
        # BEFORE building teams_out, since that loop references this set.
        _gm_for_live = [m for m in matches if m["group"]==letter]
        live_team_names = {m["home"] for m in _gm_for_live if m["live"]} | \
                           {m["away"] for m in _gm_for_live if m["live"]}

        teams_out = []
        for i,name in enumerate(static):
            lt = lmap.get(name,{})
            played=lt.get("played",0); points=lt.get("points",0); rank=lt.get("rank",i+1)
            win=lt.get("win",0); draw=lt.get("draw",0); lose=lt.get("lose",0)
            gf=lt.get("gf",0); ga=lt.get("ga",0); gd=lt.get("gd",0)

            # If this team is in a currently-LIVE match, the /standings
            # endpoint may have already counted that match's in-progress
            # score as part of "played" stats (API behaviour varies).
            # We don't have a perfectly reliable way to know if standings
            # included the live match or not, so we keep the official
            # standings value, but flag it so the frontend can show a
            # "live in progress" note instead of treating it as final.
            is_live = name in live_team_names

            teams_out.append({
                "name":name,"played":played,"win":win,
                "draw":draw,"lose":lose,
                "gf":gf,"ga":ga,"gd":gd,
                "points":points,"rank":rank,
                "qualify_prob":qualify_prob(name,rank,played,points),
                "eliminated":None,
                "live_match":is_live,
            })
        # Sort by points desc, then GD desc, then GF desc (ignore API rank for ordering)
        teams_out.sort(key=lambda x:(-x["points"],-x["gd"],-x["gf"]))
        # Re-assign ranks based on our sort
        for _i,_t in enumerate(teams_out):
            _t["rank"] = _i + 1
        teams_out = check_eliminated(teams_out)
        # Eliminated teams cannot qualify — zero out their probability
        for _t in teams_out:
            if _t.get("eliminated"):
                _t["qualify_prob"] = 0

        # Override rank-1 and rank-2 qualify_prob with the gap-aware formula.
        # Now that teams_out is sorted and ranked we can see ALL 4 teams,
        # so we know the exact point gap between rank-2 and rank-3.
        _rank3_pts = next((t["points"] for t in teams_out if t["rank"]==3), 0)
        _games_rem = max(0, 3 - teams_out[0]["played"]) if teams_out else 0
        for _t in teams_out:
            if _t["rank"] in (1, 2) and not _t.get("eliminated"):
                _t["qualify_prob"] = gap_qualify_prob(
                    _t["rank"], _t["points"], _rank3_pts, _games_rem
                )

        # Lock confirmed qualifiers at 99% when group is fully complete
        _results_count = len([m for m in matches if m.get("score") and "None" not in str(m.get("score",""))])
        if _results_count >= 6:
            for _t in teams_out:
                if _t["rank"] <= 2 and not _t.get("eliminated"):
                    _t["qualify_prob"] = 99
        gm = [m for m in matches if m["group"]==letter]
        # Only treat as "finished" if it actually has valid numeric scores.
        # football-data.org occasionally flips status to FINISHED a moment
        # before the score fields are populated — treat those as still live
        # rather than showing a broken "None-None" result.
        def has_valid_score(m):
            return m["home_goals"] is not None and m["away_goals"] is not None

        results  = [m for m in gm if m["finished"] and has_valid_score(m)]
        live_now = [m for m in gm if m["live"] or (m["finished"] and not has_valid_score(m))]
        upcoming = [m for m in gm if not m["finished"] and not m["live"]]


        groups_out.append({
            "letter":letter,"teams":teams_out,
            "results":[{"home":r["home"],"away":r["away"],
                        "score":f"{r['home_goals']}-{r['away_goals']}","date":r["date"]}
                       for r in results],
            "upcoming":[{"home":u["home"],"away":u["away"],"date":u["date"]}
                        for u in upcoming[:4]],
            "live":[{"home":lv["home"],"away":lv["away"],
                     "home_goals":lv["home_goals"] or 0,"away_goals":lv["away_goals"] or 0}
                    for lv in live_now],
        })
    return groups_out

# ── 3RD PLACE RULES ─────────────────────────────────────────────────
# Fixed FIFA slot → eligible group combos for 3rd-place teams
# Official FIFA 2026 slot assignment: maps slot_code → group_letter
# Determined by which 8 groups qualify as best 3rd-place teams.
# For this tournament (qualifying groups: B,D,E,F,I,J,K,L):
OFFICIAL_SLOT_ASSIGNMENT = {
    "3rd-ABCDF": "D",  # Paraguay  — confirmed ESPN/Fox/CBS/Sky
    "3rd-CDFGH": "F",  # Sweden
    "3rd-CEFHI": "E",  # Ecuador
    "3rd-EHIJK": "K",  # DR Congo
    "3rd-BEFIJ": "B",  # Bosnia and Herzegovina
    "3rd-AEHIJ": "I",  # Senegal
    "3rd-EFGIJ": "J",  # Algeria
    "3rd-DEIJL": "L",  # Ghana
}

THIRD_PLACE_SLOTS = {
    "3rd-ABCDF": ["A","B","C","D","F"],
    "3rd-CDFGH": ["C","D","F","G","H"],
    "3rd-CEFHI": ["C","E","F","H","I"],
    "3rd-EHIJK": ["E","H","I","J","K"],
    "3rd-BEFIJ": ["B","E","F","I","J"],
    "3rd-AEHIJ": ["A","E","H","I","J"],
    "3rd-EFGIJ": ["E","F","G","I","J"],
    "3rd-DEIJL": ["D","E","I","J","L"],
}


def compute_best_thirds(groups_out):
    """
    Rank all 12 third-place teams.
    Key rules:
    - Teams that have played are ranked by pts → GD → GF
    - Teams that haven't played yet are shown as PENDING (can't be ranked)
    - Best 8 of played-and-finished teams qualify
    """
    thirds_played   = []  # teams who have played at least 1 game
    thirds_pending  = []  # teams whose group hasn't started

    for g in groups_out:
        teams = g["teams"]
        t3 = next((t for t in teams if t["rank"] == 3), teams[2] if len(teams) >= 3 else None)
        if not t3:
            continue
        entry = {**t3, "group": g["letter"],
                 "gd": t3.get("gd", t3["gf"] - t3["ga"])}
        if t3["played"] > 0:
            thirds_played.append(entry)
        else:
            thirds_pending.append(entry)

    # Sort played teams: pts desc, gd desc, gf desc
    thirds_played.sort(key=lambda x: (-x["points"], -x["gd"], -x["gf"]))

    # Best 8 from played groups only (unplayed groups can still change everything)
    # Mark in_best8 only when group stage is complete (played == 3)
    # During group stage, show provisional top 8 from played games
    best_8 = {t["group"] for t in thirds_played[:8]}

    # Combine: played first (sorted), then pending
    all_thirds = thirds_played + thirds_pending
    return all_thirds, best_8


def build_bracket(groups_out, ko_results=None):
    if ko_results is None: ko_results = {}
    gmap = {g["letter"]: g["teams"] for g in groups_out}
    thirds, best_8 = compute_best_thirds(groups_out)

    # All 12 groups done? Only then can we make confirmed slot assignments.
    all_groups_done = all(
        all(t["played"] == 3 for t in g["teams"])
        for g in groups_out
    )

    if all_groups_done:
        # ── FINAL ASSIGNMENT: use greedy best-fit, no duplicates ──────────
        # Use official FIFA slot assignment (not greedy dedup) so
        # e.g. Paraguay→M74, Sweden→M77 match the actual draw.
        slot_assignments = {}
        for slot_code in THIRD_PLACE_SLOTS:
            grp_letter = OFFICIAL_SLOT_ASSIGNMENT.get(slot_code)
            t = next((x for x in thirds if x["group"] == grp_letter), None) if grp_letter else None
            if t and t["group"] in best_8:
                slot_assignments[slot_code] = {
                    "name":   t["name"],
                    "label":  f"3rd Grp{grp_letter}",
                    "status": "confirmed",
                    "prob":   t.get("qualify_prob", 99),
                }
            else:
                slot_assignments[slot_code] = {
                    "name": None, "label": "3rd TBD", "status": "tbd", "prob": None
                }
    else:
        # ── LIVE PREVIEW: greedy dedup assignment (no team appears twice) ──
        # Even during the group stage we deduplicate — each 3rd-place team
        # can only fill one slot. We use the same greedy algorithm as the
        # final assignment but without requiring groups to be complete.
        slot_assignments = {}
        used_groups_live = set()
        for slot_code, eligible_groups in THIRD_PLACE_SLOTS.items():
            # Best available 3rd-place team from eligible groups not yet assigned
            candidates = [t for t in thirds
                          if t["group"] in eligible_groups
                          and t["group"] not in used_groups_live]
            played_candidates = [t for t in candidates if t["played"] > 0]

            if played_candidates:
                best = played_candidates[0]  # already sorted best-to-worst
                used_groups_live.add(best["group"])
                slot_assignments[slot_code] = {
                    "name":   best["name"],
                    "label":  f"3rd Grp{best['group']} ({best['points']}pts)",
                    "status": "likely",
                    "prob":   best.get("qualify_prob", 30),
                }
            else:
                slot_assignments[slot_code] = {
                    "name":   None,
                    "label":  "3rd " + "/".join(eligible_groups),
                    "status": "tbd",
                    "prob":   None,
                }

    def resolve_third(slot_code):
        return slot_assignments.get(slot_code, {
            "name": None, "label": "3rd TBD", "status": "tbd", "prob": None
        })

    def resolve(slot):
        if slot.startswith("3rd"):
            return resolve_third(slot)
        gl, idx = SLOT_MAP.get(slot, (None, None))
        if gl is None: return {"name": None, "label": slot, "status": "tbd", "prob": None}
        teams = gmap.get(gl, [])
        if idx >= len(teams): return {"name": None, "label": slot, "status": "tbd", "prob": None}
        t = teams[idx]
        status = "confirmed" if t["played"] > 0 else "likely"
        # Use the gap-aware qualify_prob already computed on the team dict,
        # NOT the old flat-value fallback function (which gives 50% for everyone)
        return {"name": t["name"], "label": slot, "status": status,
                "prob": t.get("qualify_prob", 50)}

    # Build bracket with head-to-head R32 win probabilities
    all_teams_map = {t["name"]: t for g in groups_out for t in g["teams"]}
    bracket_result = []
    for m in R32_MATCHES:
        t1 = resolve(m["s1"])
        t2 = resolve(m["s2"])
        # Compute head-to-head win probability when both teams are known
        if t1.get("name") and t2.get("name"):
            d1 = all_teams_map.get(t1["name"], {"points": 0, "played": 0, "rank": 2})
            d2 = all_teams_map.get(t2["name"], {"points": 0, "played": 0, "rank": 2})
            d1["name"] = t1["name"]
            d2["name"] = t2["name"]
            s1 = team_raw_strength(d1)
            s2 = team_raw_strength(d2)
            total = s1 + s2 or 1
            t1["prob"] = max(3, min(97, round(s1 / total * 100)))
            t2["prob"] = 100 - t1["prob"]
        for td in [t1, t2]:
            tname = td.get("name")
            if tname:
                form = []
                for g in groups_out:
                    for res in g.get("results", []):
                        if res["home"] == tname:
                            h,a = map(int, res["score"].split("-"))
                            form.append("W" if h>a else ("D" if h==a else "L"))
                        elif res["away"] == tname:
                            h,a = map(int, res["score"].split("-"))
                            form.append("W" if a>h else ("D" if h==a else "L"))
                td["form"] = form[-3:]
        # Look up knockout result by team pair
        score   = None; winner = None; loser = None; res = None
        n1 = t1.get("name",""); n2 = t2.get("name","")
        if n1 and n2:
            res = ko_results.get((n1,n2)) or ko_results.get((n2,n1))
            # Merge fallback if API result missing winner/loser
            fb = FALLBACK_KNOCKOUT.get(m["id"])
            if fb:
                # Fallback always overrides score and fills missing winner/loser
                base = res or {}
                overrides = {k: v for k, v in fb.items() if v is not None}
                res = {**base, **overrides}   # fallback wins for all keys present
            if res:
                score  = res.get("score")
                winner = res.get("winner")
                loser  = res.get("loser")
                # Mark winner/loser status on the slots
                if winner: 
                    if n1==winner: t1["status"]="winner"; t2["status"]="loser"
                    else:          t2["status"]="winner"; t1["status"]="loser"
        bracket_result.append({**m, "t1": t1, "t2": t2,
                                "kickoff": m.get("kickoff",""),
                                "score": score, "winner": winner})
    return bracket_result

# ── KNOCKOUT RESULTS FALLBACK ──────────────────────────────────────
# Updated manually after each match as backup when API fails.
# Format: match_id → {score, winner, loser}
FALLBACK_KNOCKOUT = {
    "M73": {"score":"0-1",    "winner":"Canada",     "loser":"South Africa"},
    "M74": {"score":"1-1 (p)","winner":"Paraguay",   "loser":"Germany"},       # AET + pens
    "M75": {"score":"1-1 (p)","winner":"Morocco",    "loser":"Netherlands"},   # AET + pens
    "M76": {"score":"2-1",    "winner":"Brazil",     "loser":"Japan"},
    # M74 slot: Paraguay (3rd Group D) — official FIFA assignment confirmed
    # M77 slot: Sweden (3rd Group F) — France vs Sweden Jun 30
}

def fetch_knockout_results(api_key):
    """Fetch R32/R16/QF/SF/Final results from API."""
    results = {}
    try:
        url = "https://api.football-data.org/v4/competitions/WC/matches"
        req = urllib.request.Request(url, headers={"X-Auth-Token": api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        for m in data.get("matches", []):
            if m.get("stage","").startswith("GROUP"): continue
            if m["status"] != "FINISHED": continue
            ht = NAME_MAP.get(m["homeTeam"]["name"], m["homeTeam"]["name"])
            at = NAME_MAP.get(m["awayTeam"]["name"], m["awayTeam"]["name"])
            ft = m.get("score",{}).get("fullTime",{})
            hg, ag = ft.get("home"), ft.get("away")
            if hg is None or ag is None: continue
            # Compute winner from goals — more reliable than API winner field
            if hg > ag:   winner, loser = ht, at
            elif ag > hg: winner, loser = at, ht
            else:         winner, loser = None, None
            # Store by team pair key so we can look up by bracket slot
            results[(ht, at)] = {
                "score": f"{hg}-{ag}", "winner": winner, "loser": loser
            }
        print(f"Knockout API: {len(results)} finished matches")
    except Exception as e:
        print(f"Knockout API failed: {e} — using fallback")
    return results

# ── FALLBACK DATA (updated with real scores) ──────────────────────────
FALLBACK_GROUPS = [
    {"letter":"A","teams":[
        {"name":"Mexico","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":0,"gd":2,"points":3,"rank":1,"qualify_prob":72,"eliminated":None},
        {"name":"South Korea","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":1,"gd":1,"points":3,"rank":2,"qualify_prob":58,"eliminated":None},
        {"name":"Czechia","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":2,"gd":-1,"points":0,"rank":3,"qualify_prob":35,"eliminated":None},
        {"name":"South Africa","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":2,"gd":-2,"points":0,"rank":4,"qualify_prob":22,"eliminated":None},
    ],"results":[{"home":"Mexico","away":"South Africa","score":"2-0","date":"2026-06-11"},
                 {"home":"South Korea","away":"Czechia","score":"2-1","date":"2026-06-11"}],
    "upcoming":[{"home":"Czechia","away":"South Africa","date":"2026-06-18"},{"home":"Mexico","away":"South Korea","date":"2026-06-18"}],"live":[]},

    {"letter":"B","teams":[
        {"name":"Switzerland","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":1,"qualify_prob":52,"eliminated":None},
        {"name":"Canada","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":48,"eliminated":None},
        {"name":"Qatar","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":3,"qualify_prob":30,"eliminated":None},
        {"name":"Bosnia and Herzegovina","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":4,"qualify_prob":28,"eliminated":None},
    ],"results":[{"home":"Canada","away":"Bosnia and Herzegovina","score":"1-1","date":"2026-06-12"},
                 {"home":"Qatar","away":"Switzerland","score":"1-1","date":"2026-06-14"}],
    "upcoming":[{"home":"Switzerland","away":"Bosnia and Herzegovina","date":"2026-06-18"},{"home":"Canada","away":"Qatar","date":"2026-06-19"}],"live":[]},

    {"letter":"C","teams":[
        {"name":"Scotland","played":1,"win":1,"draw":0,"lose":0,"gf":1,"ga":0,"gd":1,"points":3,"rank":1,"qualify_prob":44,"eliminated":None},
        {"name":"Brazil","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":70,"eliminated":None},
        {"name":"Morocco","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":3,"qualify_prob":55,"eliminated":None},
        {"name":"Haiti","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":1,"gd":-1,"points":0,"rank":4,"qualify_prob":12,"eliminated":None},
    ],"results":[{"home":"Scotland","away":"Haiti","score":"1-0","date":"2026-06-14"},
                 {"home":"Brazil","away":"Morocco","score":"1-1","date":"2026-06-14"}],
    "upcoming":[{"home":"Morocco","away":"Scotland","date":"2026-06-20"},{"home":"Brazil","away":"Haiti","date":"2026-06-20"}],"live":[]},

    {"letter":"D","teams":[
        {"name":"United States","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":0,"gd":2,"points":3,"rank":1,"qualify_prob":78,"eliminated":None},
        {"name":"Australia","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":52,"eliminated":None},
        {"name":"Paraguay","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":38,"eliminated":None},
        {"name":"Türkiye","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":2,"gd":-2,"points":0,"rank":4,"qualify_prob":34,"eliminated":None},
    ],"results":[{"home":"United States","away":"Türkiye","score":"2-0","date":"2026-06-12"}],
    "upcoming":[{"home":"Australia","away":"Paraguay","date":"2026-06-19"},{"home":"United States","away":"Australia","date":"2026-06-19"}],"live":[]},

    {"letter":"E","teams":[
        {"name":"Ecuador","played":1,"win":1,"draw":0,"lose":0,"gf":4,"ga":1,"gd":3,"points":3,"rank":1,"qualify_prob":62,"eliminated":None},
        {"name":"Germany","played":1,"win":1,"draw":0,"lose":0,"gf":3,"ga":0,"gd":3,"points":3,"rank":2,"qualify_prob":60,"eliminated":None},
        {"name":"Ivory Coast","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":4,"gd":-3,"points":0,"rank":3,"qualify_prob":28,"eliminated":None},
        {"name":"Curaçao","played":1,"win":0,"draw":0,"lose":1,"gf":0,"ga":3,"gd":-3,"points":0,"rank":4,"qualify_prob":8,"eliminated":None},
    ],"results":[{"home":"Germany","away":"Curaçao","score":"3-0","date":"2026-06-13"},
                 {"home":"Ecuador","away":"Ivory Coast","score":"4-1","date":"2026-06-13"}],
    "upcoming":[{"home":"Germany","away":"Ivory Coast","date":"2026-06-20"},{"home":"Ecuador","away":"Curaçao","date":"2026-06-20"}],"live":[]},

    {"letter":"F","teams":[
        {"name":"Sweden","played":1,"win":1,"draw":0,"lose":0,"gf":5,"ga":1,"gd":4,"points":3,"rank":1,"qualify_prob":65,"eliminated":None},
        {"name":"Netherlands","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":2,"qualify_prob":72,"eliminated":None},
        {"name":"Japan","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":3,"qualify_prob":42,"eliminated":None},
        {"name":"Tunisia","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":5,"gd":-4,"points":0,"rank":4,"qualify_prob":14,"eliminated":None},
    ],"results":[{"home":"Sweden","away":"Tunisia","score":"5-1","date":"2026-06-14"},
                 {"home":"Netherlands","away":"Japan","score":"2-2","date":"2026-06-14"}],
    "upcoming":[{"home":"Netherlands","away":"Sweden","date":"2026-06-20"},{"home":"Tunisia","away":"Japan","date":"2026-06-20"}],"live":[]},

    {"letter":"G","teams":[
        {"name":"Belgium","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":1,"qualify_prob":48,"eliminated":None},
        {"name":"Egypt","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":40,"eliminated":None},
        {"name":"Iran","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":3,"qualify_prob":32,"eliminated":None},
        {"name":"New Zealand","played":1,"win":0,"draw":1,"lose":0,"gf":2,"ga":2,"gd":0,"points":1,"rank":4,"qualify_prob":24,"eliminated":None},
    ],"results":[{"home":"Belgium","away":"Egypt","score":"1-1","date":"2026-06-15"},
                 {"home":"Iran","away":"New Zealand","score":"2-2","date":"2026-06-15"}],
    "upcoming":[{"home":"Belgium","away":"Iran","date":"2026-06-21"},{"home":"New Zealand","away":"Egypt","date":"2026-06-21"}],"live":[]},

    {"letter":"H","teams":[
        {"name":"Spain","played":1,"win":0,"draw":1,"lose":0,"gf":0,"ga":0,"gd":0,"points":1,"rank":1,"qualify_prob":55,"eliminated":None},
        {"name":"Saudi Arabia","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":2,"qualify_prob":36,"eliminated":None},
        {"name":"Uruguay","played":1,"win":0,"draw":1,"lose":0,"gf":1,"ga":1,"gd":0,"points":1,"rank":3,"qualify_prob":44,"eliminated":None},
        {"name":"Cape Verde","played":1,"win":0,"draw":1,"lose":0,"gf":0,"ga":0,"gd":0,"points":1,"rank":4,"qualify_prob":22,"eliminated":None},
    ],"results":[{"home":"Spain","away":"Cape Verde","score":"0-0","date":"2026-06-15"},
                 {"home":"Saudi Arabia","away":"Uruguay","score":"1-1","date":"2026-06-15"}],
    "upcoming":[{"home":"Spain","away":"Saudi Arabia","date":"2026-06-21"},{"home":"Uruguay","away":"Cape Verde","date":"2026-06-21"}],"live":[]},

    {"letter":"I","teams":[
        {"name":"France","played":1,"win":1,"draw":0,"lose":0,"gf":3,"ga":1,"gd":2,"points":3,"rank":1,"qualify_prob":88,"eliminated":None},
        {"name":"Norway","played":1,"win":1,"draw":0,"lose":0,"gf":2,"ga":1,"gd":1,"points":3,"rank":2,"qualify_prob":68,"eliminated":None},
        {"name":"Senegal","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":3,"gd":-2,"points":0,"rank":3,"qualify_prob":42,"eliminated":None},
        {"name":"Iraq","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":2,"gd":-1,"points":0,"rank":4,"qualify_prob":18,"eliminated":None},
    ],"results":[{"home":"France","away":"Senegal","score":"3-1","date":"2026-06-16"},
                 {"home":"Norway","away":"Iraq","score":"2-1","date":"2026-06-16"}],
    "upcoming":[{"home":"France","away":"Iraq","date":"2026-06-22"},{"home":"Norway","away":"Senegal","date":"2026-06-22"}],"live":[]},

    {"letter":"J","teams":[
        {"name":"Argentina","played":1,"win":1,"draw":0,"lose":0,"gf":3,"ga":1,"gd":2,"points":3,"rank":1,"qualify_prob":90,"eliminated":None},
        {"name":"Algeria","played":1,"win":0,"draw":0,"lose":1,"gf":1,"ga":3,"gd":-2,"points":0,"rank":2,"qualify_prob":42,"eliminated":None},
        {"name":"Austria","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":38,"eliminated":None},
        {"name":"Jordan","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":15,"eliminated":None},
    ],"results":[{"home":"Argentina","away":"Algeria","score":"3-1","date":"2026-06-16"}],
    "upcoming":[{"home":"Austria","away":"Jordan","date":"2026-06-17"},{"home":"Argentina","away":"Austria","date":"2026-06-22"}],"live":[]},

    {"letter":"K","teams":[
        {"name":"Portugal","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":1,"qualify_prob":84,"eliminated":None},
        {"name":"Colombia","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":60,"eliminated":None},
        {"name":"DR Congo","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":28,"eliminated":None},
        {"name":"Uzbekistan","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":18,"eliminated":None},
    ],"results":[],"upcoming":[{"home":"Portugal","away":"DR Congo","date":"2026-06-17"},{"home":"Uzbekistan","away":"Colombia","date":"2026-06-17"}],"live":[]},

    {"letter":"L","teams":[
        {"name":"England","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":1,"qualify_prob":76,"eliminated":None},
        {"name":"Croatia","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":2,"qualify_prob":55,"eliminated":None},
        {"name":"Ghana","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":3,"qualify_prob":32,"eliminated":None},
        {"name":"Panama","played":0,"win":0,"draw":0,"lose":0,"gf":0,"ga":0,"gd":0,"points":0,"rank":4,"qualify_prob":20,"eliminated":None},
    ],"results":[],"upcoming":[{"home":"England","away":"Croatia","date":"2026-06-17"},{"home":"Ghana","away":"Panama","date":"2026-06-18"}],"live":[]},
]

def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"WC 2026 update at {now}")




    groups_out = None
    source = "fallback"
    if API_KEY:
        print("Fetching from football-data.org...")
        standings = fetch_standings()
        matches   = fetch_matches()
        # Safety check: only trust the API response if we got BOTH standings
        # AND a reasonable number of matches (avoid partial/corrupt API responses
        # silently wiping out results and upcoming fixtures)
        if standings and matches and len(matches) >= 50:
            candidate = build_groups(standings, matches)
            total_results = sum(len(g["results"]) for g in candidate)
            # Sanity check: we should have at least as many results as last known good state.
            # If somehow we get 0 results across all groups while matches exist, something
            # is wrong with parsing — don't let it wipe out a previously working page.
            if total_results > 0 or all(t["played"] == 0 for g in candidate for t in g["teams"]):
                groups_out = candidate
                live_c = sum(len(g["live"]) for g in groups_out)
                done_c = sum(len(g["results"]) for g in groups_out)
                print(f"Live API OK: {done_c} results, {live_c} live")
                source = "live"
            else:
                print("API data looked inconsistent (0 results despite matches) - using fallback", file=sys.stderr)
        else:
            print(f"API returned insufficient data (standings={bool(standings)}, matches={len(matches) if matches else 0}) - using fallback", file=sys.stderr)
    else:
        print("No API key - using fallback", file=sys.stderr)
    if not groups_out:
        groups_out = FALLBACK_GROUPS
    ko_results = fetch_knockout_results(API_KEY) if API_KEY else {}
    bracket = build_bracket(groups_out, ko_results)

    # ── GUARANTEED FALLBACK APPLY ────────────────────────────────────────
    # If build_bracket didn't set score/winner (API silent or mismatched),
    # force-apply FALLBACK_KNOCKOUT entries now so nothing is ever missed.
    for _bm in bracket:
        if _bm.get("score") is not None:
            continue   # already resolved
        _fb = FALLBACK_KNOCKOUT.get(_bm["id"])
        if not _fb:
            continue
        _bm["score"]  = _fb.get("score")
        _bm["winner"] = _fb.get("winner")
        _win = _fb.get("winner")
        _los = _fb.get("loser")
        for _slot in ["t1", "t2"]:
            _t = _bm[_slot]
            if _t.get("name") == _win:
                _t["status"] = "winner"
            elif _t.get("name") == _los:
                _t["status"] = "loser"
        print(f"Fallback applied: {_bm['id']} → {_win} wins")
    total_live = sum(len(g["live"]) for g in groups_out)

    # ── R16 WIN PROBABILITIES FOR R32 WINNERS ───────────────────────────
    # For teams that have already passed Round of 32, replace their
    # bracket prob with the probability of advancing FROM Round of 16.
    R16_PAIRS_BY_R32 = {
        "M74":"M77","M77":"M74",  # M89
        "M73":"M75","M75":"M73",  # M90
        "M83":"M84","M84":"M83",  # M93
        "M81":"M82","M82":"M81",  # M94
        "M76":"M78","M78":"M76",  # M91
        "M79":"M80","M80":"M79",  # M92
        "M86":"M88","M88":"M86",  # M95
        "M85":"M87","M87":"M85",  # M96
    }
    bmap = {m["id"]: m for m in bracket_result}
    for bm in bracket_result:
        if not bm.get("winner"):
            continue  # R32 not yet played
        for slot in ["t1", "t2"]:
            t = bm[slot]
            if t.get("status") != "winner" or not t.get("name"):
                continue
            opp_mid = R16_PAIRS_BY_R32.get(bm["id"])
            opp_m   = bmap.get(opp_mid)
            if not opp_m:
                continue
            td_this = {**all_teams_map.get(t["name"], {}), "name": t["name"]}
            s_this  = team_raw_strength(td_this)
            if opp_m.get("winner"):
                # Opponent known — exact H2H R16 win probability
                opp_nm = opp_m["winner"]
                td_opp = {**all_teams_map.get(opp_nm, {}), "name": opp_nm}
                s_opp  = team_raw_strength(td_opp)
                total  = s_this + s_opp or 1
                t["prob"] = max(3, min(97, round(s_this / total * 100)))
                t["r16_opp"] = opp_nm
            else:
                # Opponent not yet known — weighted expectation over two candidates
                ot1 = opp_m["t1"]; ot2 = opp_m["t2"]
                p1  = (ot1.get("prob") or 50) / 100.0
                p2  = 1.0 - p1
                ev  = 0.0
                for opp_nm, opp_p in [(ot1.get("name"), p1), (ot2.get("name"), p2)]:
                    if not opp_nm: continue
                    td_o = {**all_teams_map.get(opp_nm, {}), "name": opp_nm}
                    s_o  = team_raw_strength(td_o)
                    ev  += opp_p * (s_this / (s_this + s_o)) if (s_this + s_o) > 0 else 0
                t["prob"] = max(3, min(97, round(ev * 100)))
                t["r16_opp"] = f"W({opp_mid})"

    # ── ZERO OUT KNOCKOUT STAGE LOSERS ──────────────────────────────────
    # Any team marked as loser in a bracket match is out of the tournament.
    # Their qualify_prob and win_cup_% must be 0 regardless of group finish.
    ko_losers = set()
    for _bm in bracket:
        if _bm.get("winner"):   # match has a result
            for _slot in [_bm["t1"], _bm["t2"]]:
                if _slot.get("status") == "loser" and _slot.get("name"):
                    ko_losers.add(_slot["name"])
    for _g in groups_out:
        for _t in _g["teams"]:
            if _t["name"] in ko_losers:
                _t["qualify_prob"] = 0
                _t["eliminated"]   = True

    # ── LOCK PROBABILITIES FOR FULLY FINISHED GROUPS ─────────────────
    for _g in groups_out:
        _res_done = len([_r for _r in _g.get("results", [])
                         if _r.get("score") and "None" not in str(_r.get("score", ""))]) >= 6
        if _res_done:
            for _t in _g["teams"]:
                if _t["rank"] <= 2 and not _t.get("eliminated"):
                    _t["qualify_prob"] = 99   # confirmed through
                elif _t["rank"] == 4 and not _t.get("eliminated"):
                    _t["qualify_prob"] = 1    # cannot qualify

    # Compute best 3rd places for display
    thirds_ranked, best_8_grps = compute_best_thirds(groups_out)
    # Compute accurate qualify_prob for each 3rd-place team based on their
    # actual ranking position (top 8 of 12 qualify).
    # Position 1-5 → safely in → 80%, 6-8 → on the bubble → 45%,
    # 9-10 → likely out → 15%, 11-12 → out → 5%
    # Once all groups finish the best_8_grps is exact → 99% or 0%.
    _all_grps_done = all(
        len([m for m in g.get("results",[]) if m.get("score") and "None" not in str(m.get("score",""))]) >= 6
        for g in groups_out
    )
    thirds_prob = {}
    for _i, _t in enumerate(thirds_ranked):
        _pos = _i + 1
        if _all_grps_done:
            thirds_prob[_t["name"]] = 99 if _t["group"] in best_8_grps else 0
        elif _t["played"] == 0:
            thirds_prob[_t["name"]] = qualify_prob(_t["name"], 3, 0, 0)
        elif _pos <= 5:
            thirds_prob[_t["name"]] = 80
        elif _pos <= 8:
            thirds_prob[_t["name"]] = 45
        elif _pos <= 10:
            thirds_prob[_t["name"]] = 15
        else:
            thirds_prob[_t["name"]] = 5

    thirds_display = [
        {
            "name":    t["name"],
            "group":   t["group"],
            "played":  t["played"],
            "points":  t["points"],
            "gd":      t.get("gd", t["gf"]-t["ga"]),
            "gf":      t["gf"],
            "in_best8": t["group"] in best_8_grps,
            "qualify_prob": thirds_prob.get(t["name"],
                            qualify_prob(t["name"], 3, t["played"], t["points"])),
        }
        for t in thirds_ranked
    ]

    # ── MATHEMATICAL ELIMINATION for 3rd-place teams ────────────────────
    # If a 3rd-place team from a DONE group already has 8+ teams guaranteed
    # to finish above them, they are mathematically eliminated from the top-8.
    for _t3 in thirds_ranked:
        if _t3["played"] < 3:
            continue  # group not done yet — can't eliminate mathematically
        _certain_better = 0
        for _other in thirds_ranked:
            if _other["name"] == _t3["name"]:
                continue
            _o_pts = _other["points"]; _o_gd = _other["gf"] - _other["ga"]; _o_gf = _other["gf"]
            _t_pts = _t3["points"];  _t_gd = _t3["gf"] - _t3["ga"];  _t_gf = _t3["gf"]
            if _other["played"] == 3:
                # Both done — direct final comparison
                if (_o_pts > _t_pts or
                    (_o_pts == _t_pts and _o_gd > _t_gd) or
                    (_o_pts == _t_pts and _o_gd == _t_gd and _o_gf > _t_gf)):
                    _certain_better += 1
            else:
                # Other group not done but already has MORE current points
                # — they can only stay same or go higher
                if _other["points"] > _t3["points"]:
                    _certain_better += 1
        if _certain_better >= 8:
            thirds_prob[_t3["name"]] = 0   # locked out of top-8

    # Sync the accurate 3rd-place qualify_prob back into groups_out
    for _g in groups_out:
        for _t in _g["teams"]:
            if _t["rank"] == 3 and _t["name"] in thirds_prob:
                _t["qualify_prob"] = thirds_prob[_t["name"]]
            # If a 3rd-place team has qualify_prob=0, mark them eliminated too
            if _t["rank"] == 3 and _t.get("qualify_prob") == 0 and not _t.get("eliminated"):
                _t["eliminated"] = True

    # Top scorers from API
    scorers_out = []
    if API_KEY:
        try:
            req_sc = urllib.request.Request(
                "https://api.football-data.org/v4/competitions/WC/scorers?limit=20",
                headers={"X-Auth-Token": API_KEY})
            with urllib.request.urlopen(req_sc, timeout=8) as resp_sc:
                sc_data = json.loads(resp_sc.read())
                for sc in sc_data.get("scorers", []):
                    scorers_out.append({
                        "name":  sc["player"]["name"],
                        "team":  sc["team"]["name"],
                        "goals": sc.get("numberOfGoals", sc.get("goals", 0)),
                    })
            print(f"Scorers: {len(scorers_out)} fetched")
        except Exception as e:
            print(f"Scorers fetch failed: {e}")

    output = {
        "updated_at":  now,
        "source":      source,
        "live_count":  total_live,
        "groups":      groups_out,
        "bracket":     bracket,
        "best_thirds": thirds_display,
        "scorers":     scorers_out,
        "win_probs":   WIN_PROBS,
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Written data.json ({source}) - {total_live} live")

    # ── APPEND HISTORY SNAPSHOT ───────────────────────────────────────
    append_history_snapshot(now, groups_out)


def append_history_snapshot(timestamp, groups_out):
    """
    Maintain a rolling history of each team's qualify_prob and win_prob
    over time, so the frontend can chart how probabilities evolved.
    Stored in history.json as: { "TeamName": [ {"t": iso_timestamp, "q": int, "w": float}, ... ] }
    Snapshots are de-duplicated: only appended if probabilities actually
    changed since the last snapshot, and trimmed to the most recent 500
    points per team to keep the file size reasonable over a long tournament.
    """
    hist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")
    try:
        if os.path.exists(hist_path):
            with open(hist_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = {}
    except Exception:
        history = {}

    # Compute win_prob the same way the frontend power rankings does:
    # normalise each team's raw strength-adjusted score across the full 48-team field.
    # Eliminated teams get raw=0 (no chance of winning the cup).
    all_teams = []
    for g in groups_out:
        for t in g["teams"]:
            if t.get("eliminated") or t.get("qualify_prob", 1) == 0:
                # Eliminated — cannot win the cup
                all_teams.append((t["name"], 0.0, 0))
                continue
            base = WIN_PROBS.get(t["name"], 0.3)
            mult = 1.0
            if t["played"] > 0:
                ppg = t["points"] / t["played"]
                rank = t["rank"]
                if rank == 1:   mult = 1.0 + ppg * 0.18
                elif rank == 2: mult = 1.0 + ppg * 0.08
                elif rank == 3: mult = 1.0 - 0.15
                else:           mult = 1.0 - 0.35
            raw = max(0.05, base * mult)
            all_teams.append((t["name"], raw, t["qualify_prob"]))

    # Only normalise over non-eliminated teams
    total_raw = sum(r for _, r, _ in all_teams if r > 0) or 1.0

    for name, raw, qp in all_teams:
        # Eliminated teams have 0 chance of winning the cup
        if qp == 0:
            win_pct = 0.0
        else:
            win_pct = round((raw / total_raw) * 100, 3)
        entry = {"t": timestamp, "q": qp, "w": win_pct}

        team_hist = history.setdefault(name, [])
        values_changed = bool(team_hist) and (team_hist[-1]["q"] != qp or team_hist[-1]["w"] != win_pct)

        # Always record the FIRST point for a team. After that, record either:
        #  (a) whenever the probability actually changes, for precise trend tracking, or
        #  (b) at least once every ~2 hours even if unchanged, so the line chart has a
        #      real timeline to draw instead of a single dot during quiet stretches
        #      between matches (the most common state for most of a 5-week tournament).
        should_record = (not team_hist) or values_changed
        if not should_record and team_hist:
            last_t = datetime.datetime.fromisoformat(team_hist[-1]["t"])
            now_t  = datetime.datetime.fromisoformat(timestamp)
            hours_since_last = (now_t - last_t).total_seconds() / 3600
            should_record = hours_since_last >= 2

        if should_record:
            team_hist.append(entry)
            if len(team_hist) > 500:
                history[name] = team_hist[-500:]

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False)

    print(f"History snapshot appended for {len(all_teams)} teams")


if __name__ == "__main__":
    main()
