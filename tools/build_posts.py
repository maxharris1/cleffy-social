"""Build posts.json from feed-v4/calendar.csv and captions.md.
Run locally: python3 tools/build_posts.py <feed-v4 dir> <repo dir>
"""
import csv, json, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

feed, repo = sys.argv[1], sys.argv[2]
ET = ZoneInfo("America/New_York")
YEAR = 2026

sections = {}
cur = None
for line in open(f"{feed}/captions.md", encoding="utf-8").read().split("\n"):
    m = re.match(r"^## (\d+)\. ", line)
    if m:
        cur = int(m.group(1)); sections[cur] = []; continue
    if cur is not None:
        sections[cur].append(line)

def caption(n):
    lines = sections[n]
    body = [l for l in lines if not l.startswith(("Files:", "Audio:"))]
    text = "\n".join(body).strip()
    parts = [p.strip() for p in re.split(r"\n(?=Image:)|\n(?=#)", text) if p.strip()]
    return "\n\n".join(parts)

posts = []
for row in csv.DictReader(open(f"{feed}/calendar.csv", encoding="utf-8")):
    n = int(row["#"])
    when = datetime.strptime(f"{row['date']} {YEAR} {row['time (ET)']}", "%a %b %d %Y %I:%M %p").replace(tzinfo=ET)
    posts.append({
        "n": n,
        "title": row["title"],
        "when_et": when.isoformat(),
        "video": f"reels/{row['reel']}",
        "audio_search": row["audio (search in Instagram)"],
        "caption": caption(n),
    })
json.dump(posts, open(f"{repo}/posts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"{len(posts)} posts")
