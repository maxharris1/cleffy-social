"""Download recent published Reels and measure their sound. Usage: python tools/check_audio.py [count]"""
import os, re, subprocess, sys, requests
API = "https://graph.facebook.com/v26.0"
TOKEN = os.environ["IG_PAGE_TOKEN"]
IG_USER = os.environ.get("IG_USER_ID", "17841437414226316")
n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
r = requests.get(f"{API}/{IG_USER}/media", params={"fields": "id,permalink,media_product_type,media_url,timestamp",
                                                    "limit": 25, "access_token": TOKEN}, timeout=60).json()
reels = [m for m in r.get("data", []) if m.get("media_product_type") == "REELS"][:n]
bad = 0
for m in reels:
    with open("/tmp/r.mp4", "wb") as f:
        f.write(requests.get(m["media_url"], timeout=120).content)
    out = subprocess.run(["ffmpeg", "-i", "/tmp/r.mp4", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    mv = re.search(r"mean_volume: (-?[\d.]+)", out)
    db = float(mv.group(1)) if mv else None
    ok = db is not None and db > -45
    bad += not ok
    print(f"{'SOUND ' if ok else 'SILENT'} {m['timestamp']} {m['permalink']} mean {db} dB")
sys.exit(1 if bad else 0)
