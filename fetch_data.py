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

R32_MATCHES = [
    {"id":"M73","venue":"Los Angeles - Jun 28","side":"left", "s1":"2A","s2":"2B"},
    {"id":"M74","venue":"Boston - Jun 29",     "side":"left", "s1":"1E","s2":"3rd-ABCDF"},
    {"id":"M75","venue":"Monterrey - Jun 29",  "side":"left", "s1":"1F","s2":"2C"},
    {"id":"M76","venue":"Houston - Jun 29",    "side":"left", "s1":"1C","s2":"2F"},
    {"id":"M77","venue":"New York - Jun 30",   "side":"left", "s1":"1I","s2":"3rd-CDFGH"},
    {"id":"M78","venue":"Dallas - Jun 30",     "side":"left", "s1":"2E","s2":"2I"},
    {"id":"M79","venue":"Mexico City - Jun 30","side":"left", "s1":"1A","s2":"3rd-CEFHI"},
    {"id":"M80","venue":"Atlanta - Jul 1",     "side":"left", "s1":"1L","s2":"3rd-EHIJK"},
    {"id":"M81","venue":"San Francisco - Jul 1","side":"right","s1":"1D","s2":"3rd-BEFIJ"},
    {"id":"M82","venue":"Seattle - Jul 1",     "side":"right","s1":"1G","s2":"3rd-AEHIJ"},
    {"id":"M83","venue":"Toronto - Jul 2",     "side":"right","s1":"2K","s2":"2L"},
    {"id":"M84","venue":"Los Angeles - Jul 2", "side":"right","s1":"1H","s2":"2J"},
    {"id":"M85","venue":"Vancouver - Jul 2",   "side":"right","s1":"1B","s2":"3rd-EFGIJ"},
    {"id":"M86","venue":"Miami - Jul 3",       "side":"right","s1":"1J","s2":"2H"},
    {"id":"M87","venue":"Kansas City - Jul 3", "side":"right","s1":"1K","s2":"3rd-DEIJL"},
    {"id":"M88","venue":"Dallas - Jul 3",      "side":"right","s1":"2D","s2":"2G"},
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
    Estimate % probability of qualifying from group stage (top 2 auto + best 8 third places).
    Based purely on current standing + remaining matches + team strength modifier.
    """
    remaining = 3 - played
    max_pts = points + remaining * 3

    # Base qualification probability from current standing
    if played == 0:
        # Pre-tournament: use FIFA ranking tier as guide
        strength = WIN_PROBS.get(name, 0.5)
        total = 100.0  # will normalise across group later
        # Rough tiers: top 5 teams 70-85%, mid 45-65%, minnows 15-35%
        if strength >= 8.0:   return 80
        elif strength >= 5.0: return 70
        elif strength >= 3.0: return 60
        elif strength >= 1.5: return 50
        elif strength >= 0.8: return 35
        elif strength >= 0.4: return 22
        else:                 return 12

    # After games played — model based on points trajectory
    # Max possible points and current points determine fate

    if played == 3:
        # Group stage complete — definitive
        if rank == 1:   return 99  # top 2 auto qualify
        elif rank == 2: return 97
        elif rank == 3: return 25  # best 8 third-places out of 12 groups
        else:           return 1   # eliminated

    # Mid-group: simulate remaining outcomes
    # Use points as primary indicator, strength as tiebreaker
    strength = WIN_PROBS.get(name, 0.5)
    str_bonus = min(8, round(strength * 0.8))  # max +8 bonus from strength

    if rank == 1:
        if points == 3:
            if remaining == 2: return min(95, 82 + str_bonus)
            else:              return min(97, 88 + str_bonus)
        elif points == 6:      return 99
        elif points == 1:
            if remaining == 1: return min(75, 58 + str_bonus)
            else:              return min(80, 62 + str_bonus)
        else: # 0 pts, somehow rank 1 (all drew)
            return min(70, 50 + str_bonus)

    elif rank == 2:
        if points == 3:
            if remaining == 2: return min(88, 72 + str_bonus)
            else:              return min(92, 80 + str_bonus)
        elif points == 6:      return 98
        elif points == 1:
            if remaining == 1: return min(55, 40 + str_bonus)
            else:              return min(65, 48 + str_bonus)
        else: # 0 pts rank 2
            return min(60, 42 + str_bonus)

    elif rank == 3:
        if points == 3:        return min(60, 42 + str_bonus)
        elif points == 1:
            if remaining == 2: return min(42, 28 + str_bonus)
            else:              return min(30, 18 + str_bonus)
        elif points == 0:
            if max_pts >= 9:   return min(38, 22 + str_bonus)
            elif max_pts >= 6: return min(28, 15 + str_bonus)
            else:              return min(15, 8 + str_bonus)
        else: return min(50, 35 + str_bonus)

    else:  # rank 4
        if points == 3:        return min(45, 30 + str_bonus)  # weird but possible
        elif points == 1:
            if max_pts >= 7:   return min(22, 12 + str_bonus)
            else:              return min(12, 5 + str_bonus)
        elif points == 0:
            if max_pts >= 9:   return min(18, 8 + str_bonus)
            elif max_pts >= 6: return min(10, 4 + str_bonus)
            else:              return 2  # basically eliminated
        else: return min(18, 8 + str_bonus)

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
        out.append({
            "date":m.get("utcDate","")[:10],"group":letter,
            "stage":m.get("stage",""),"status":status,
            "home":normalize(m.get("homeTeam",{}).get("name","")),
            "away":normalize(m.get("awayTeam",{}).get("name","")),
            "home_goals":ft.get("home"),"away_goals":ft.get("away"),
            "finished":status=="FINISHED",
            "live":status in ("IN_PLAY","PAUSED","HALFTIME"),
        })
    return out

def build_groups(standings, matches):
    groups_out = []
    for letter in GROUPS_ORDER:
        static = STATIC_TEAMS[letter]
        lmap = {t["name"]:t for t in (standings or {}).get(letter,[])}
        teams_out = []
        for i,name in enumerate(static):
            lt = lmap.get(name,{})
            played=lt.get("played",0); points=lt.get("points",0); rank=lt.get("rank",i+1)
            teams_out.append({
                "name":name,"played":played,"win":lt.get("win",0),
                "draw":lt.get("draw",0),"lose":lt.get("lose",0),
                "gf":lt.get("gf",0),"ga":lt.get("ga",0),"gd":lt.get("gd",0),
                "points":points,"rank":rank,
                "qualify_prob":qualify_prob(name,rank,played,points),
                "eliminated":None,
            })
        # Sort by points desc, then GD desc, then GF desc (ignore API rank for ordering)
        teams_out.sort(key=lambda x:(-x["points"],-x["gd"],-x["gf"]))
        # Re-assign ranks based on our sort
        for _i,_t in enumerate(teams_out):
            _t["rank"] = _i + 1
        teams_out = check_eliminated(teams_out)
        gm = [m for m in matches if m["group"]==letter]
        results  = [m for m in gm if m["finished"]]
        live_now = [m for m in gm if m["live"]]
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

def build_bracket(groups_out):
    gmap = {g["letter"]:g["teams"] for g in groups_out}
    def resolve(slot):
        if slot.startswith("3rd"):
            return {"name":None,"label":"3rd "+slot[4:].replace("-","/"),"status":"tbd","prob":None}
        gl,idx = SLOT_MAP.get(slot,(None,None))
        if gl is None: return {"name":None,"label":slot,"status":"tbd","prob":None}
        teams = gmap.get(gl,[])
        if idx>=len(teams): return {"name":None,"label":slot,"status":"tbd","prob":None}
        t = teams[idx]
        prob = qualify_prob(t["name"], idx+1, t["played"], t["points"])
        status = "confirmed" if t["played"]>0 else "likely"
        return {"name":t["name"],"label":slot,"status":status,"prob":prob}
    return [{**m,"t1":resolve(m["s1"]),"t2":resolve(m["s2"])} for m in R32_MATCHES]

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
        if standings and matches is not None:
            groups_out = build_groups(standings, matches)
            live_c = sum(len(g["live"]) for g in groups_out)
            done_c = sum(len(g["results"]) for g in groups_out)
            print(f"Live API OK: {done_c} results, {live_c} live")
            source = "live"
        else:
            print("API returned nothing - using fallback", file=sys.stderr)
    else:
        print("No API key - using fallback", file=sys.stderr)
    if not groups_out:
        groups_out = FALLBACK_GROUPS
    bracket = build_bracket(groups_out)
    total_live = sum(len(g["live"]) for g in groups_out)
    output = {
        "updated_at": now,
        "source": source,
        "live_count": total_live,
        "groups": groups_out,
        "bracket": bracket,
    }
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Written data.json ({source}) - {total_live} live")

if __name__ == "__main__":
    main()
