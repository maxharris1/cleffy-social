"""Host a Reel cover image where Instagram can fetch it: an unpublished photo on the Cleffy
Facebook Page (never shown on the Page or in any feed). Returns a public CDN URL for cover_url.
Test: python tools/cover_host.py covers/a01-liszt-danhauser.jpg
"""
import os, sys, requests
API = "https://graph.facebook.com/v26.0"
PAGE = os.environ.get("FB_PAGE_ID", "1509215732274136")


def page_token(user_token):
    r = requests.get(f"{API}/{PAGE}", params={"fields": "access_token", "access_token": user_token}, timeout=60).json()
    return r.get("access_token") or user_token


def host(path, user_token):
    tok = page_token(user_token)
    with open(path, "rb") as f:
        r = requests.post(f"{API}/{PAGE}/photos", data={"published": "false", "temporary": "false", "access_token": tok},
                          files={"source": (os.path.basename(path), f, "image/jpeg")}, timeout=120).json()
    if "id" not in r:
        raise RuntimeError(f"cover upload failed: {r.get('error', {}).get('message', r)}")
    imgs = requests.get(f"{API}/{r['id']}", params={"fields": "images", "access_token": tok}, timeout=60).json().get("images", [])
    if not imgs:
        raise RuntimeError("cover uploaded but no image URL returned")
    best = max(imgs, key=lambda i: i["height"])
    return best["source"], best["width"], best["height"]


if __name__ == "__main__":
    url, w, h = host(sys.argv[1], os.environ["IG_PAGE_TOKEN"])
    print(f"Hosted {sys.argv[1]} at {w}x{h}: {url.split('?')[0][:60]}...")
    print("Fetchable:", requests.get(url, timeout=60).status_code)
