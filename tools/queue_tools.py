"""Tools for the 3-month Reel queue (q1/). Runs in GitHub Actions (needs the open internet and ffmpeg).

pool                      -> list clean public-domain / CC0 recordings on Wikimedia Commons, measured, into q1/pool.json
images                    -> download each q1/items.json commons_file (max 2400 px) into release q1-src as src-<n>.zip
build <shard> <nshards>   -> render q1/queue.json Reels (frames from release q1-frames), check the sound,
                             upload the mp4s to release q1-reels and write q1/manifest-<shard>.json
"""
import json, os, re, subprocess, sys, html, time, zipfile, glob
import requests

API = "https://commons.wikimedia.org/w/api.php"
S = requests.Session()
S.headers["User-Agent"] = "cleffy-social-bot/1.0 (Cleffy Instagram; public-domain archive Reels)"
OK_LIC = re.compile(r"public domain|^pd|cc0", re.I)          # pool: only PD / CC0 (no attribution chains)
OK_LIC_BUILD = re.compile(r"public domain|^pd|cc0|cc by(-sa)? ?[1-4]", re.I)
DUR = 15


def get(params):
    for i in range(8):
        try:
            r = S.get(API, params={"format": "json", **params}, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(10 * (i + 1)); continue
            return r.json()
        except (ValueError, requests.RequestException):
            time.sleep(5 * (i + 1))
    return {}


def clean(s):
    return re.sub(r"\s+", " ", re.sub("<[^>]+>", "", html.unescape(s or ""))).strip()


def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)


# ---------------------------------------------------------------- audio measurement
def measure(path_or_url, start=0.0, secs=DUR):
    """Loudness, hiss and silence of a DUR-second window (after leading silence) of a recording."""
    tmp = "/tmp/m.wav"
    r = sh("ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(secs + 20), "-i", path_or_url,
           "-af", f"silenceremove=start_periods=1:start_threshold=-50dB,atrim=duration={secs}", "-ac", "2", "-ar", "44100", tmp,
           timeout=240)
    if r.returncode or not os.path.exists(tmp):
        return None
    vd = sh("ffmpeg", "-i", tmp, "-af", "volumedetect", "-f", "null", "-").stderr
    mv = re.search(r"mean_volume: (-?[\d.]+)", vd)
    hf = re.search(r"mean_volume: (-?[\d.]+)", sh("ffmpeg", "-i", tmp, "-af", "highpass=f=6000,volumedetect", "-f", "null", "-").stderr)
    fl = [float(x) for x in re.findall(r"flatness=([\d.]+)", sh("ffmpeg", "-i", tmp, "-af",
          "aspectralstats=measure=flatness,ametadata=print:key=lavfi.aspectralstats.1.flatness", "-f", "null", "-").stderr)]
    sil = re.search(r"silence_start: ([\d.]+)", sh("ffmpeg", "-i", tmp, "-af", "silencedetect=n=-50dB:d=1.5", "-f", "null", "-").stderr)
    du = sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", tmp).stdout.strip()
    os.remove(tmp)
    return {"mean_db": float(mv.group(1)) if mv else -99, "hf_db": float(hf.group(1)) if hf else 0,
            "flatness": round(sum(fl) / len(fl), 4) if fl else 1, "silence_at": float(sil.group(1)) if sil else None,
            "secs": float(du or 0)}


def is_clean(m, max_hf=-45):
    return (m and m["mean_db"] > -40 and m["flatness"] <= 0.06 and m["hf_db"] <= max_hf
            and m["secs"] >= DUR - 0.5 and (m["silence_at"] is None or m["silence_at"] >= DUR - 2.5))


# ---------------------------------------------------------------- pool
POOL_CATS = ["Category:Musopen", "Category:Open Goldberg Variations", "Category:Open Well-Tempered Clavier",
             "Category:Audio files of piano music", "Category:Audio files by Musopen"]


def cat_files(cat, depth=2, seen=None):
    seen = seen if seen is not None else set()
    if cat in seen or depth < 0: return []
    seen.add(cat)
    out, cont = [], {}
    while True:
        r = get({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": 500, "cmtype": "file|subcat", **cont})
        for m in r.get("query", {}).get("categorymembers", []):
            if m["ns"] == 6: out.append(m["title"])
            elif m["ns"] == 14: out += cat_files(m["title"], depth - 1, seen)
        if "continue" not in r: break
        cont = r["continue"]
    return out


def vinfo(titles):
    r = get({"action": "query", "titles": "|".join(titles), "prop": "videoinfo",
             "viprop": "url|mime|size|extmetadata|derivatives"})
    res = {}
    norm = {n["to"]: n["from"] for n in r.get("query", {}).get("normalized", [])}
    for p in r.get("query", {}).get("pages", {}).values():
        vi = (p.get("videoinfo") or [{}])[0]
        if not vi: continue
        em = vi.get("extmetadata", {})
        mp3 = next((d["src"] for d in vi.get("derivatives", []) if d.get("type", "").startswith("audio/mpeg")), None)
        ogg = next((d["src"] for d in vi.get("derivatives", []) if "ogg" in d.get("type", "")), None)
        res[p["title"]] = {"url": vi.get("url"), "mime": vi.get("mime"), "size": vi.get("size", 0),
                           "listen": mp3 or ogg or vi.get("url"),
                           "license": clean(em.get("LicenseShortName", {}).get("value")),
                           "artist": clean(em.get("Artist", {}).get("value"))[:120],
                           "desc": clean(em.get("ImageDescription", {}).get("value"))[:300]}
    return res


def pool():
    os.makedirs("q1", exist_ok=True)
    P = "q1/pool.json"
    out = json.load(open(P)) if os.path.exists(P) else {}
    titles = []
    for c in POOL_CATS:
        fs = cat_files(c)
        print(f"{c}: {len(fs)} files"); titles += fs
    titles = [t for t in dict.fromkeys(titles) if re.search(r"\.(flac|ogg|oga|opus|wav|mp3)$", t, re.I) and t not in out]
    print(f"{len(titles)} new audio files to check")
    t0 = time.time()
    for i in range(0, len(titles), 40):
        if time.time() - t0 > 4.6 * 3600: print("time budget reached"); break
        info = vinfo(titles[i:i + 40])
        for t, v in info.items():
            if not OK_LIC.search(v["license"]):
                continue
            m = measure(v["listen"])
            ok = is_clean(m)
            out[t] = {**v, "m": m, "clean": bool(ok)}
            print(f"{'OK ' if ok else '-- '}{t} | {v['license']} | {m}")
            time.sleep(1.5)
        json.dump(out, open(P, "w"), indent=0, ensure_ascii=False)
    print(f"pool: {sum(1 for v in out.values() if v['clean'])} clean of {len(out)}")


# ---------------------------------------------------------------- images
def images():
    items = json.load(open("q1/items.json"))
    os.makedirs("/tmp/src", exist_ok=True)
    fails = []
    for it in items:
        key, f = it["key"], it["commons_file"]
        dst = f"/tmp/src/{key}.jpg"
        r = get({"action": "query", "titles": f, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 2400})
        p = next(iter(r.get("query", {}).get("pages", {}).values()), {})
        ii = (p.get("imageinfo") or [None])[0]
        if not ii:
            print(f"MISSING {key}: {f}"); fails.append(key); continue
        lic = clean(ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value"))
        url = ii.get("thumburl") if ii.get("width", 0) > 2400 else ii["url"]
        if url.lower().endswith((".tif", ".tiff", ".pdf", ".djvu")):
            url = ii.get("thumburl") or url
        for a in range(6):
            time.sleep(2 + 10 * a)
            rr = S.get(url, timeout=120)
            if rr.status_code == 200: break
        if rr.status_code != 200:
            print(f"FAIL {key}: {rr.status_code}"); fails.append(key); continue
        raw = f"/tmp/src/{key}.raw"
        open(raw, "wb").write(rr.content)
        c = sh("convert", raw + "[0]", "-auto-orient", "-colorspace", "sRGB", "-quality", "93", dst)
        os.remove(raw)
        if c.returncode:
            print(f"CONVERT FAIL {key}: {c.stderr[:200]}"); fails.append(key); continue
        print(f"ok {key} {ii.get('width')}x{ii.get('height')} | {lic}")
    files = sorted(glob.glob("/tmp/src/*.jpg"))
    for n in range(0, len(files), 60):
        with zipfile.ZipFile(f"/tmp/src-{n // 60}.zip", "w") as z:
            for fn in files[n:n + 60]: z.write(fn, os.path.basename(fn))
    json.dump(fails, open("q1/image_fails.json", "w"))
    print(f"{len(files)} images, failed: {fails}")


# ---------------------------------------------------------------- build
def build(shard, nshards):
    q = json.load(open("q1/queue.json"))
    mine = [e for i, e in enumerate(q) if i % nshards == shard]
    MAN = f"q1/manifest-{shard}.json"
    man = json.load(open(MAN)) if os.path.exists(MAN) else {}
    have = set(sh("gh", "release", "view", "q1-reels", "--json", "assets", "--jq", ".assets[].name").stdout.split())
    os.makedirs("/tmp/b", exist_ok=True)
    failed = []
    for e in mine:
        name = os.path.basename(e["video"])
        if name in have and str(e["n"]) in man and man[str(e["n"])]["file"] == e["music"]["file"] and not e.get("rebuild"):
            continue
        try:
            m = build_one(e)
            sh("gh", "release", "upload", "q1-reels", f"/tmp/b/{name}", "--clobber", check=True)
            man[str(e["n"])] = m
            json.dump(man, open(MAN, "w"), indent=1, ensure_ascii=False)
        except Exception as ex:
            print(f"FAIL #{e['n']} {e['key']}: {ex}"); failed.append(e["n"])
    print(f"shard {shard}: failed {failed}")


def build_one(e):
    mu = e["music"]
    v = vinfo([mu["file"]]).get(mu["file"])
    if not v: raise RuntimeError(f"recording not found: {mu['file']}")
    if not OK_LIC_BUILD.search(v["license"]): raise RuntimeError(f"licence {v['license']}")
    src = f"/tmp/b/audio{os.path.splitext(v['listen'])[1] or '.mp3'}"
    for a in range(6):
        time.sleep(3 + a * 20)
        with S.get(v["listen"], stream=True, timeout=300) as r:
            if (r.status_code == 429 or r.status_code >= 500) and a < 5: continue
            r.raise_for_status()
            with open(src, "wb") as f:
                for c in r.iter_content(1 << 16): f.write(c)
            break
    base = e["key_file"]
    frame, cover = f"/tmp/frames/frames/{base}.jpg", f"/tmp/frames/covers/{base}.jpg"
    out = f"/tmp/b/{os.path.basename(e['video'])}"
    start = float(mu.get("start", 0))
    af = (f"atrim=start={start},asetpts=PTS-STARTPTS,silenceremove=start_periods=1:start_threshold=-50dB,"
          f"atrim=duration={DUR},afade=t=in:d=0.4,afade=t=out:st={DUR-2}:d=2,loudnorm=I=-16:TP=-1.5")
    vf = (f"scale=2160:3840,zoompan=z='1+0.03*on/{DUR*30}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d=1:s=1080x1920:fps=30,format=yuv420p")
    fc = (f"[0:v]{vf},trim=duration={DUR},setpts=PTS-STARTPTS[a];"
          f"[2:v]scale=1080:1920,fps=30,format=yuv420p,trim=duration={DUR},setpts=PTS-STARTPTS[c];"
          f"[a][c]xfade=transition=fade:duration=0.4:offset={DUR-1.2}[v];[1:a]{af}[au]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", frame, "-i", src, "-loop", "1", "-i", cover,
                    "-filter_complex", fc, "-map", "[v]", "-map", "[au]", "-frames:v", str(DUR * 30), "-t", str(DUR),
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
                    "-movflags", "+faststart", out], check=True)
    os.remove(src)
    m = measure(out)
    print(f"#{e['n']} {e['key']}: {mu['file']} | {v['license']} | {m}")
    if not is_clean(m, mu.get("max_hf", -45)):
        os.remove(out); raise RuntimeError(f"sound check failed {m}")
    return {"file": mu["file"], "license": v["license"], "artist": v["artist"], "mean_db": m["mean_db"],
            "title": mu.get("title", ""), "performer": mu.get("performer", ""), "flatness": m["flatness"], "hf_db": m["hf_db"]}


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "pool": pool()
    elif cmd == "images": images()
    elif cmd == "build": build(int(sys.argv[2]), int(sys.argv[3]))
