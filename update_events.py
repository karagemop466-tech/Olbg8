import json
import os
import glob

sports_map = {
    "Golf": "golf", 
    "Volleyball": "volleyball", 
    "Rugby Union": "rugby-union", 
    "Cricket": "cricket", 
    "Snooker": "snooker", 
    "Darts": "darts", 
    "Baseball": "baseball", 
    "Gaelic Sports": "gaelic-sports", 
    "Greyhounds": "greyhounds", 
    "Tennis": "tennis", 
    "Motor Racing": "motor-racing", 
    "Handball": "handball", 
    "Ice Hockey": "ice-hockey", 
    "Basketball": "basketball", 
    "Rugby League": "rugby-league"
}

events = []

for s, slug in sports_map.items():
    safe_name = s.lower().replace(" ", "_")
    with open(f"data/{safe_name}.json", "r") as f:
        data = json.load(f)
        for m in data["matches"]:
            # mapping our data into their structure
            events.append({
                "sport": slug,
                "event": m["match"],
                "start": "2026-10-26 (OLBG display)",
                "market": "Money Line",
                "olbgPick": m["pick"],
                "support": m["odds"] + " (" + m["confidence"] + ")",
                "url": m["source_link"] or "https://www.olbg.com/",
                "ourLine": m["odds"],
                "ourPick": m["pick"],
                "confidence": m["confidence"],
                "prediction": m["prediction"],
                "verified": m["verified"]
            })

with open("data/events.json", "w") as f:
    json.dump(events, f, indent=4)

print("Updated data/events.json")
