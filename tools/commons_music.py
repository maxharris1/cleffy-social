"""Find and fetch public-domain / open-licensed recordings on Wikimedia Commons.

search: python tools/commons_music.py search            -> prints candidates per post
build:  python tools/commons_music.py build [n ...]     -> downloads music.json picks, renders reels/ with sound
"""
import json, os, re, subprocess, sys, html
import requests

API = "https://commons.wikimedia.org/w/api.php"
S = requests.Session()
S.headers["User-Agent"] = "cleffy-social-bot/1.0 (Reels music fetcher)"
OK_LIC = re.compile(r"public domain|^pd|cc0|cc by(-sa)? ?[1-4]", re.I)
DUR = 15  # seconds per Reel


def get(params):
    import time
    for i in range(6):
        r = S.get(API, params=params, timeout=60)
        try:
            return r.json()
        except ValueError:
            time.sleep(5 * (i + 1))
    r.raise_for_status(); return {}


def search(q, limit=15):
    r = get({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                           "gsrsearch": f"{q} filemime:audio", "gsrlimit": limit,
                           "prop": "imageinfo", "iiprop": "url|mime|extmetadata|size"})
    out = []
    for p in (r.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
        lic = em.get("LicenseShortName", {}).get("value", "")
        art = re.sub("<[^>]+>", "", html.unescape(em.get("Artist", {}).get("value", "")))[:60]
        if "midi" in (ii.get("mime") or ""): continue
        out.append((p["title"], ii.get("mime"), lic, art.strip(), ii.get("size", 0)))
    return out


def info(title):
    r = get({"action": "query", "format": "json", "titles": title, "prop": "imageinfo",
             "iiprop": "url|extmetadata"})
    p = next(iter(r["query"]["pages"].values()))
    ii = p["imageinfo"][0]; em = ii.get("extmetadata", {})
    clean = lambda k: re.sub("<[^>]+>", "", html.unescape(em.get(k, {}).get("value", ""))).strip()
    return ii["url"], clean("LicenseShortName"), clean("Artist")


def do_search(only=()):
    import time
    posts = [p for p in json.load(open("posts.json")) if not only or p["n"] in only]
    extra = json.load(open("tools/music_queries.json")) if os.path.exists("tools/music_queries.json") else {}
    for p in posts:
        qs = extra.get(str(p["n"])) or [p["audio_search"]]
        print(f"=== #{p['n']} {p['title'][:50]} | want: {p['audio_search']}")
        seen = set()
        for q in qs:
            time.sleep(1)
            for t, mime, lic, art, size in search(q):
                if t in seen: continue
                seen.add(t)
                flag = "OK " if OK_LIC.search(lic) else "?? "
                print(f"  {flag}{t} | {lic} | {art} | {mime} | {size//1024}KB")


def build(only):
    picks = json.load(open("music.json"))
    MAN = "reels/music_manifest.json"
    man = json.load(open(MAN)) if os.path.exists(MAN) else {}
    posts = {p["n"]: p for p in json.load(open("posts.json"))}
    os.makedirs("reels", exist_ok=True); os.makedirs("/tmp/music", exist_ok=True)
    failed = []
    for n_s, m in picks.items():
        n = int(n_s)
        if only and n not in only: continue
        try:
            build_one(n, m, posts[n], man, MAN)
        except (SystemExit, Exception) as e:
            print(f"FAIL #{n}: {e}"); failed.append(n)
    if failed:
        sys.exit(f"failed: {' '.join(map(str, failed))}")


def build_one(n, m, p, man, MAN):
    if True:
        url, lic, art = info(m["file"])
        if not OK_LIC.search(lic):
            sys.exit(f"#{n}: licence '{lic}' not allowed")
        ext = os.path.splitext(url)[1]
        src = f"/tmp/music/{n}{ext}"
        import time
        for attempt in range(6):   # upload.wikimedia.org rate-limits bursts: back off on 429
            time.sleep(15 + attempt * 30)
            with S.get(url, stream=True, timeout=300) as r:
                if (r.status_code == 429 or r.status_code >= 500) and attempt < 5: continue
                r.raise_for_status()
                with open(src, "wb") as f:
                    for c in r.iter_content(1 << 16): f.write(c)
                break
        frame = f"frames/{os.path.basename(p['video'])[:-4]}.jpg"
        out = p["video"]
        start = float(m.get("start", 0))
        af = (f"atrim=start={start},asetpts=PTS-STARTPTS,"
              f"silenceremove=start_periods=1:start_threshold=-50dB,"
              f"atrim=duration={DUR},afade=t=in:d=0.4,afade=t=out:st={DUR-2}:d=2,loudnorm=I=-16:TP=-1.5")
        vf = (f"scale=2160:3840,zoompan=z='1+0.03*on/{DUR*30}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d=1:s=1080x1920:fps=30,format=yuv420p")
        cover = f"covers/{os.path.basename(p['video'])[:-4]}.jpg"
        if os.path.exists(cover):
            # end card: the curated card fades in for the last 1.2 s; post_reel.py points the grid cover at it
            fc = (f"[0:v]{vf},trim=duration={DUR},setpts=PTS-STARTPTS[a];"
                  f"[2:v]scale=1080:1920,fps=30,format=yuv420p,trim=duration={DUR},setpts=PTS-STARTPTS[c];"
                  f"[a][c]xfade=transition=fade:duration=0.4:offset={DUR-1.2}[v];[1:a]{af}[au]")
            inputs = ["-loop", "1", "-i", frame, "-i", src, "-loop", "1", "-i", cover]
        else:
            fc = f"[0:v]{vf}[v];[1:a]{af}[au]"
            inputs = ["-loop", "1", "-i", frame, "-i", src]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs,
                        "-filter_complex", fc, "-map", "[v]", "-map", "[au]",
                        "-frames:v", str(DUR * 30), "-t", str(DUR), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", out], check=True)
        mean = subprocess.run(["ffmpeg", "-i", out, "-af", "volumedetect", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
        mv = re.search(r"mean_volume: (-?[\d.]+)", mean)
        print(f"#{n}: {m['file']} | {lic} | {art} | mean {mv.group(1) if mv else '?'} dB -> {out}")
        if not mv or float(mv.group(1)) < -45:
            sys.exit(f"#{n}: audio is near silent")
        # Cleanliness: old 78s and noisy transfers have broadband hiss (high spectral flatness,
        # lots of energy above 6 kHz). A clean piano recording sits near 0.01-0.03 flatness.
        flat_out = subprocess.run(["ffmpeg", "-i", out, "-af", "aspectralstats=measure=flatness,"
                                   "ametadata=print:key=lavfi.aspectralstats.1.flatness", "-f", "null", "-"],
                                  capture_output=True, text=True).stderr
        vals = [float(x) for x in re.findall(r"flatness=([\d.]+)", flat_out)]
        flat = sum(vals) / len(vals) if vals else 1.0
        hf_out = subprocess.run(["ffmpeg", "-i", out, "-af", "highpass=f=6000,volumedetect", "-f", "null", "-"],
                                capture_output=True, text=True).stderr
        hf = float(re.search(r"mean_volume: (-?[\d.]+)", hf_out).group(1))
        print(f"#{n}: spectral flatness {flat:.3f}, energy above 6 kHz {hf} dB")
        dur_out = subprocess.run(["ffmpeg", "-i", out, "-map", "0:a", "-af", "silencedetect=n=-50dB:d=1.5", "-f", "null", "-"],
                                 capture_output=True, text=True).stderr
        adur = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "format=duration:stream=duration",
                               "-of", "csv=p=0", out], capture_output=True, text=True).stdout.split()
        if adur and min(float(x) for x in adur if x.replace('.', '', 1).isdigit()) < DUR - 0.5:
            os.remove(out)
            sys.exit(f"#{n}: recording is shorter than the Reel ({adur}); pick a longer one")
        if re.search(r"silence_start: ([\d.]+)", dur_out) and float(re.search(r"silence_start: ([\d.]+)", dur_out).group(1)) < DUR - 2.5:
            os.remove(out)
            sys.exit(f"#{n}: recording runs out (or goes silent) before the end of the Reel; pick a longer one or another start")
        if flat > 0.06 or hf > m.get("max_hf", -45):  # bright modern string/band recordings may allow a little more top end
            os.remove(out)
            sys.exit(f"#{n}: recording is noisy (hiss or surface noise); pick a cleaner one")
        man[str(n)] = {"file": m["file"], "license": lic, "artist": art, "mean_db": float(mv.group(1)),
                       "title": m.get("title", ""), "performer": m.get("performer", ""),
                       "flatness": round(flat, 3), "hf_db": hf}
        json.dump(man, open(MAN, "w"), indent=1, ensure_ascii=False)


def reframe(only):
    """New frames, same recordings: rebuild each Reel's picture and keep the audio already in it."""
    posts = {p["n"]: p for p in json.load(open("posts.json"))}
    man = json.load(open("reels/music_manifest.json"))
    vf = (f"scale=2160:3840,zoompan=z='1+0.03*on/{DUR*30}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d=1:s=1080x1920:fps=30,format=yuv420p")
    for n in sorted(only or map(int, man)):
        p = posts[n]; out = p["video"]; base = os.path.basename(out)[:-4]
        frame, cover = f"frames/{base}.jpg", f"covers/{base}.jpg"
        tmp = f"/tmp/{base}.mp4"
        fc = (f"[0:v]{vf},trim=duration={DUR},setpts=PTS-STARTPTS[a];"
              f"[2:v]scale=1080:1920,fps=30,format=yuv420p,trim=duration={DUR},setpts=PTS-STARTPTS[c];"
              f"[a][c]xfade=transition=fade:duration=0.4:offset={DUR-1.2}[v]")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", frame, "-i", out, "-loop", "1", "-i", cover,
                        "-filter_complex", fc, "-map", "[v]", "-map", "1:a", "-frames:v", str(DUR * 30), "-t", str(DUR),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "copy", "-movflags", "+faststart", tmp], check=True)
        os.replace(tmp, out)
        print(f"#{n}: reframed {out}")


if __name__ == "__main__":
    if sys.argv[1] == "search": do_search([int(x) for x in sys.argv[2:]])
    elif sys.argv[1] == "reframe": reframe([int(x) for x in sys.argv[2:]])
    else: build([int(x) for x in sys.argv[2:]])
