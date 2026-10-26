import json
import os
import glob

html_head = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OLBG Predictions Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }
        header { background-color: #1c3d5a; color: white; padding: 20px; text-align: center; }
        nav { background-color: #2b5c85; overflow: hidden; display: flex; flex-wrap: wrap; justify-content: center; }
        nav a { color: white; padding: 14px 20px; text-decoration: none; font-weight: bold; }
        nav a:hover { background-color: #ddd; color: black; }
        .container { padding: 20px; max-width: 1200px; margin: auto; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        th, td { padding: 15px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #2b5c85; color: white; }
        tr:hover { background-color: #f1f1f1; }
        .badge { padding: 5px 10px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px;}
        .high { background-color: #28a745; }
        .medium { background-color: #ffc107; color: black; }
        .low { background-color: #dc3545; }
        .card { background: white; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-radius: 5px; }
        .unverified { color: #dc3545; font-weight: bold; }
    </style>
</head>
<body>
<header>
    <h1>OLBG Daily Sports Predictions</h1>
    <p>Data updated for October 26, 2026</p>
</header>
<nav>
    <a href="index.html">Executive Summary</a>
"""

sports = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", 
    "Darts", "Baseball", "Gaelic Sports", "Greyhounds", "Tennis", 
    "Motor Racing", "Handball", "Ice Hockey", "Basketball", "Rugby League"
]

for s in sports:
    safe = s.lower().replace(" ", "_")
    html_head += f'    <a href="{safe}.html">{s}</a>\n'

html_head += '    <a href="flagged.html">Flagged for Review</a>\n</nav>\n<div class="container">\n'

html_foot = """
</div>
</body>
</html>
"""

# Load all data
all_data = {}
for s in sports:
    safe = s.lower().replace(" ", "_")
    with open(f"data/{safe}.json", "r") as f:
        all_data[s] = json.load(f)

# --- Generate Executive Summary (index.html) ---
index_html = html_head + "<h2>Executive Summary: Today's Highest Confidence Picks</h2>\n"
index_html += "<p>Below is a curated list of our highest confidence predictions across all covered sports with odds sitting between -250 and +10000.</p>\n"
index_html += "<table><tr><th>Sport</th><th>Match / Event</th><th>Pick</th><th>Odds</th><th>Prediction</th><th>Source</th></tr>\n"

unverified_items = []

for s in sports:
    matches = all_data[s]["matches"]
    high_picks = [m for m in matches if m["confidence"] == "High"]
    for m in high_picks:
        if m["verified"] == "False":
            unverified_items.append({"sport": s, "match": m["match"], "link": m["source_link"]})
            v_badge = ' <span class="unverified" title="Unverified">[Unverified]</span>'
        else:
            v_badge = ''
            
        index_html += f'<tr><td>{s}</td><td>{m["match"]}{v_badge}</td><td><strong>{m["pick"]}</strong></td><td>{m["odds"]}</td><td>{m["prediction"]}</td><td><a href="{m["source_link"]}" target="_blank">Link</a></td></tr>\n'
        
index_html += "</table>\n" + html_foot
with open("index.html", "w") as f:
    f.write(index_html)

# --- Generate individual sport pages ---
for s in sports:
    safe = s.lower().replace(" ", "_")
    d = all_data[s]
    page_html = html_head + f'<h2>{s} Predictions</h2>\n'
    page_html += f'<div class="card"><strong>Event/League:</strong> {d["event"]}</div>\n'
    page_html += "<table><tr><th>Match / Race</th><th>Confidence</th><th>Pick</th><th>Odds</th><th>Prediction Analysis</th><th>Source</th></tr>\n"
    for m in d["matches"]:
        c_class = m["confidence"].lower()
        if m["verified"] == "False":
            v_badge = ' <span class="unverified" title="Unverified">[Unverified]</span>'
            if m not in [u for u_dict in unverified_items for u in (u_dict,)]:
                # Avoid duplicates but collect for medium/low picks too
                if not any(u["match"] == m["match"] for u in unverified_items):
                    unverified_items.append({"sport": s, "match": m["match"], "link": m["source_link"]})
        else:
            v_badge = ''
        page_html += f'<tr><td>{m["match"]}{v_badge}</td><td><span class="badge {c_class}">{m["confidence"]}</span></td><td><strong>{m["pick"]}</strong></td><td>{m["odds"]}</td><td>{m["prediction"]}</td><td><a href="{m["source_link"]}" target="_blank">Official Source</a></td></tr>\n'
    page_html += "</table>\n" + html_foot
    with open(f"{safe}.html", "w") as f:
        f.write(page_html)

# --- Generate Flagged for Review page ---
flagged_html = html_head + "<h2>Flagged for Review</h2>\n"
flagged_html += "<p>The following matches and events could not be 100% verified from an official source for the exact date of October 26, 2026. They have been flagged for manual review as per the requirements.</p>\n"
if unverified_items:
    flagged_html += "<table><tr><th>Sport</th><th>Match / Event</th><th>Source Checked</th></tr>\n"
    for u in unverified_items:
        flagged_html += f'<tr><td>{u["sport"]}</td><td>{u["match"]}</td><td><a href="{u["link"]}" target="_blank">{u["link"]}</a></td></tr>\n'
    flagged_html += "</table>\n"
else:
    flagged_html += "<p>All items successfully verified.</p>\n"

flagged_html += html_foot
with open("flagged.html", "w") as f:
    f.write(flagged_html)

print("Website generation complete.")
