"""Post the next due Cleffy Reel to Instagram with music.

Reads IG_PAGE_TOKEN from the environment (GitHub Actions secret). Never prints it.
Env:
  IG_PAGE_TOKEN  Page access token for the Cleffy Facebook Page (required)
  IG_USER_ID     Instagram user id (default @cleffy.io)
  DRY_RUN        "1" = check token, find the due post and audio, upload nothing
  FORCE_N        post this calendar number now, ignoring its time (manual test)
"""
import json, os, sys, time
from datetime import datetime, timezone
import requests

API = "https://graph.facebook.com/v22.0"
TOKEN = os.environ["IG_PAGE_TOKEN"]
IG_USER = os.environ.get("IG_USER_ID", "17841437414226316")
DRY = os.environ.get("DRY_RUN") == "1"
FORCE_N = os.environ.get("FORCE_N", "").strip()
NO_PUBLISH = os.environ.get("NO_PUBLISH") == "1"  # upload and process, but never publish
STATE = "state/posted.json"
LATE_LIMIT_H = 6  # skip a slot rather than post it more than 6 hours late


def die(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


def call(method, path, **kw):
    params = kw.pop("params", {}) or {}
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", params=params, timeout=120, **kw)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:300]}
    if r.status_code >= 400 or "error" in body:
        err = body.get("error", body)
        die(f"{method} {path} -> {r.status_code}: {json.dumps(err)[:500]}")
    return body


def pick(posts, done):
    if FORCE_N:
        p = next((p for p in posts if str(p["n"]) == FORCE_N), None)
        if not p:
            die(f"no post #{FORCE_N}")
        return p
    now = datetime.now(timezone.utc)
    for p in posts:
        if p["n"] in done:
            continue
        when = datetime.fromisoformat(p["when_et"]).astimezone(timezone.utc)
        late_h = (now - when).total_seconds() / 3600
        if late_h < 0:
            return None  # next one isn't due yet
        if late_h > LATE_LIMIT_H:
            print(f"Skipping #{p['n']} ({p['title']}): {late_h:.1f}h late")
            continue
        return p
    return None


import unicodedata


def plain(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def search(q):
    return call("GET", "ig_audio", params={"audio_type": "music", "user_id": IG_USER, "search_query": q}).get("audio", [])


def label(a):
    return f"{a.get('title')} by {a.get('display_artist')}"


def find_audio(planned):
    """Return (audio_id, label). Only a track that names the composer counts as a match;
    otherwise fall back to classical piano. Never random trending audio."""
    composer = planned.split(",")[0].strip()
    piece = planned.split(",")[1].split("(")[0].split(" or ")[0].strip() if "," in planned else ""
    words = [w for w in plain(piece).replace(".", " ").split() if len(w) > 3 and w not in ("major", "minor", "sonata", "prelude")]
    pool = []
    for q in [f"{composer} {piece}", f"{composer} {plain(piece)}", composer]:
        res = search(q.strip())
        if DRY:
            print(f"  search '{q}': " + ("; ".join(label(a) for a in res[:5]) or "nothing"))
        pool += [a for a in res if plain(composer) in plain(label(a))]
    if pool:
        best = max(pool, key=lambda a: sum(w in plain(label(a)) for w in words))
        return best["audio_id"], f"{label(best)} (matched {composer})"
    for q in ["classical piano", "piano"]:
        res = search(q)
        if DRY:
            print(f"  search '{q}': " + ("; ".join(label(a) for a in res[:5]) or "nothing"))
        if res:
            return res[0]["audio_id"], f"{label(res[0])} (fallback: {q})"
    return None, None


def main():
    me = call("GET", "me", params={"fields": "id,name"})
    print(f"Token works for: {me.get('name')} ({me.get('id')})")
    dbg = call("GET", "debug_token", params={"input_token": TOKEN}).get("data", {})
    exp = dbg.get("expires_at", 0)
    left = (exp - time.time()) / 86400 if exp else None
    print(f"Token type: {dbg.get('type')}, expires: {'never' if not exp else f'in {left:.1f} days'}")
    if left is not None and left < 7:
        print("WARNING: token expires within a week; renew IG_PAGE_TOKEN")
    acct = call("GET", IG_USER, params={"fields": "username"})
    print(f"Instagram account: @{acct.get('username')}")

    posts = json.load(open("posts.json", encoding="utf-8"))
    done = json.load(open(STATE)) if os.path.exists(STATE) else []
    p = pick(posts, done)
    if not p:
        print("Nothing due.")
        return
    print(f"Due: #{p['n']} {p['title']} ({p['when_et']})")

    audio_id, label = None, None
    if p.get("audio_id"):
        try:
            a = call("GET", p["audio_id"], params={"user_id": IG_USER})
            audio_id, label = p["audio_id"], f"{p['audio_label']} (picked)"
        except SystemExit:
            print(f"Picked track {p['audio_label']} unavailable; searching instead")
    if not audio_id:
        audio_id, label = find_audio(p["audio_search"])
    if not audio_id:
        die("no audio found; not posting a silent Reel")
    print(f"Audio: {label}")

    if DRY:
        print("Dry run: stopping before upload.")
        return

    container = call("POST", f"{IG_USER}/media", data={
        "media_type": "REELS",
        "upload_type": "resumable",
        "caption": p["caption"],
        "share_to_feed": "true",
        "audio_configuration": json.dumps({"audio_id": audio_id, "audio_volume": 100, "video_volume": 0}),
    })
    cid = container["id"]
    print(f"Container: {cid}")

    path = p["video"]
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        r = requests.post(
            f"https://rupload.facebook.com/ig-api-upload/v22.0/{cid}",
            headers={"Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(size)},
            data=f, timeout=300)
    if r.status_code >= 400:
        die(f"upload -> {r.status_code}: {r.text[:500]}")
    print(f"Uploaded {path} ({size} bytes)")

    for _ in range(20):
        time.sleep(30)
        st = call("GET", cid, params={"fields": "status_code,status"})
        print(f"Status: {st.get('status_code')}")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            die(f"container failed: {st.get('status')}")
    else:
        die("container not ready after 10 minutes")

    if NO_PUBLISH:
        print("Upload test passed: container is ready. Not publishing; it expires unpublished in 24 hours.")
        return
    pub = call("POST", f"{IG_USER}/media_publish", data={"creation_id": cid})
    media = call("GET", pub["id"], params={"fields": "permalink"})
    print(f"Published #{p['n']}: {media.get('permalink')}")
    done.append(p["n"])
    os.makedirs("state", exist_ok=True)
    json.dump(sorted(done), open(STATE, "w"))


if __name__ == "__main__":
    main()
