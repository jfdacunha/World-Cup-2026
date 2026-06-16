import urllib.request, urllib.error, json, os

KEY = os.environ.get("FOOTBALL_API_KEY", "")
results = {"key_present": bool(KEY), "key_length": len(KEY), "tests": []}

def call(url, label):
    try:
        req = urllib.request.Request(url, headers={"X-Auth-Token": KEY, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return {"label": label, "status": 200, "data": data}
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        return {"label": label, "status": e.code, "error": body}
    except Exception as e:
        return {"label": label, "status": 0, "error": str(e)}

# Test 1: List all competitions (checks if key works at all)
r1 = call("https://api.football-data.org/v4/competitions/", "list_competitions")
results["tests"].append(r1)
if r1["status"] == 200:
    comps = r1["data"].get("competitions", [])
    results["available_competitions"] = [
        {"code": c.get("code"), "name": c.get("name"), "area": c.get("area",{}).get("name")}
        for c in comps
    ]

# Test 2: Try WC directly
r2 = call("https://api.football-data.org/v4/competitions/WC", "get_WC")
results["tests"].append(r2)

# Test 3: Try WC standings
r3 = call("https://api.football-data.org/v4/competitions/WC/standings", "WC_standings")
results["tests"].append(r3)

# Test 4: Try WC matches
r4 = call("https://api.football-data.org/v4/competitions/WC/matches?status=FINISHED", "WC_matches_finished")
results["tests"].append(r4)

with open("api_test_result.json", "w") as f:
    json.dump(results, f, indent=2)
print(json.dumps(results, indent=2)[:2000])
