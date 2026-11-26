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


def find_audio(query):
    """Return (audio_id, label). Try the planned track, then trending music."""
    for q in [query.split(",")[0] + " " + query.split(",")[1] if "," in query else query, query, None]:
        params = {"audio_type": "music", "user_id": IG_USER}
        if q:
            params["search_query"] = q.strip()
        res = call("GET", "ig_audio", params=params).get("audio", [])
        if res:
            a = res[0]
            return a["audio_id"], f"{a.get('title')} by {a.get('display_artist')} (search: {q or 'trending'})"
    return None, None


def main():
    me = call("GET", "me", params={"fields": "id,name"})
    print(f"Token works for: {me.get('name')} ({me.get('id')})")
    acct = call("GET", IG_USER, params={"fields": "username"})
    print(f"Instagram account: @{acct.get('username')}")

    posts = json.load(open("posts.json", encoding="utf-8"))
    done = json.load(open(STATE)) if os.path.exists(STATE) else []
    p = pick(posts, done)
    if not p:
        print("Nothing due.")
        return
    print(f"Due: #{p['n']} {p['title']} ({p['when_et']})")

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

    pub = call("POST", f"{IG_USER}/media_publish", data={"creation_id": cid})
    media = call("GET", pub["id"], params={"fields": "permalink"})
    print(f"Published #{p['n']}: {media.get('permalink')}")
    done.append(p["n"])
    os.makedirs("state", exist_ok=True)
    json.dump(sorted(done), open(STATE, "w"))


if __name__ == "__main__":
    main()
