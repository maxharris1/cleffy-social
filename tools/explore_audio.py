"""List what Instagram's music library returns for many searches (ids, titles, artists)."""
import json, os, requests
API = "https://graph.facebook.com/v22.0"
TOKEN = os.environ["IG_PAGE_TOKEN"]; IG = "17841437414226316"
qs = ["Hugh Sung", "Mike Block", "Bach", "Beethoven", "Chopin", "Debussy", "Scarlatti", "Dowland", "Faure", "Grieg",
      "Handel", "Liszt", "Joplin", "Mendelssohn", "Mozart", "Offenbach", "Saint-Saens", "Satie", "Schubert", "Vivaldi",
      "Wagner", "Clair de Lune", "Gymnopedie", "Nocturne", "Moonlight Sonata", "Fur Elise", "Canon in D", "harpsichord",
      "lute", "string quartet", "classical", "piano solo", "solo piano", "cello", "Gregorian", "choir", "Hallelujah",
      "Maple Leaf Rag", "Liebestraum", "Air on the G String", "Four Seasons", "Pachelbel", "Brahms", "Tchaikovsky", "Schumann"]
seen = {}
for q in qs:
    r = requests.get(f"{API}/ig_audio", params={"audio_type": "music", "user_id": IG, "search_query": q, "access_token": TOKEN}, timeout=60).json()
    for a in r.get("audio", []):
        seen.setdefault(a["audio_id"], (a.get("title"), a.get("display_artist"), a.get("duration_in_ms"), q))
for k, (t, ar, d, q) in sorted(seen.items(), key=lambda x: (x[1][1] or "", x[1][0] or "")):
    print(f"AUD|{k}|{t}|{ar}|{(d or 0)//1000}s|{q}")
