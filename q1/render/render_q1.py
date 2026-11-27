"""Covers (curated 4:5 card on a 9:16 canvas) and 9:16 Reel frames for the 3-month queue.
python3 render_q1.py <queue.json> <src dir> <out dir> [n ...]
Same layout as feed-v5/render916.py (v7 + Max's option B shade on light posts)."""
import sys, os, json, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
with contextlib.redirect_stdout(io.StringIO()):
    import render as R
    import render_culture as RC
from PIL import Image, ImageDraw

CREAM, CM = RC.CREAM, RC.CREAM_MUTED
GAP, GAP_MIN = 28, 22   # space between headline and body (was 12; Max, Nov 27: too tight)

import re as _re
_ABBR = {'op', 'no', 'nos', 'c', 'ca', 'st', 'ste', 'mr', 'mrs', 'dr', 'jr', 'sr', 'mt', 'vol', 'fol', 'bk', 'k', 'bwv', 'hob', 'rv', 'woo', 'p', 'pp', 'ff', 'd', 'vs', 'etc', 'lt', 'col', 'gen', 'capt', 'sgt', 'rev', 'prof', 'fr', 'ft', 'mme', 'mlle', 'mm', 'messrs', 'ms', 'abb'}
def first_sentence(s):
    """First sentence of s, never split after an abbreviation (Op., No., c., St.) or an initial (J. S.)."""
    for m in _re.finditer(r'\. (?=[A-Z0-9"\'(])', s):
        w = _re.search(r'([A-Za-z]+)$', s[:m.start()])
        if w and (len(w.group(1)) == 1 or w.group(1).lower() in _ABBR): continue
        return s[:m.start()] + '.'
    return s
S = R.S; W, HH = 1080 * S, 1920 * S


def shade(im):
    # soft ink shade so Instagram's white buttons and caption read on cream (Max picked B, Nov 26)
    import numpy as np
    a = np.asarray(im.convert('RGB')).astype(float); H, W_ = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W_].astype(float)
    def ease(t): t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
    al = np.maximum(ease((yy - 1700) / 220) * 0.78, ease((xx - 935) / 145) * ease((yy - 1170) / 120) * 0.62)[..., None]
    ink = np.array([28, 24, 22], float)
    return Image.fromarray((a * (1 - al) + ink * al).astype('uint8'))


def cover(it, n, dark, src, out):
    R.OUT = '/tmp/q1cards'; os.makedirs(R.OUT, exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        RC.archive_post(n, src, 'card.jpg', it['head'], it['sub'], it['credit'], crop=it.get('crop'), dark=dark, mat=0 if dark else 14)
    card = Image.open(R.OUT + '/card.jpg').convert('RGB')
    canvas = Image.new('RGB', (1080, 1920), R.INK if dark else R.PAPER)
    canvas.paste(card, (0, (1920 - card.height) // 2))
    canvas.save(out, quality=93)


def frame(it, n, dark, src_path, out):
    bg = R.INK if dark else R.PAPER
    im = Image.new('RGB', (W, HH), bg); d = ImageDraw.Draw(im)
    L, TR = 112, 900
    ART_T, ART_B, TXT_T, TXT_B = 236, 1160, 1204, 1660
    hs, ss = 74, 34
    sub = it['sub']
    gap = GAP
    while True:
        hf, sf = R.BOD(hs), R.SANS(ss)
        hl = RC.wrap(d, it['head'], hf, TR - L); sl = RC.wrap(d, sub, sf, TR - L)
        th = 36 + 26 + len(hl) * int(hs * 1.18) + gap + len(sl) * int(ss * 1.45)
        if TXT_T + th <= TXT_B: break
        if gap > GAP_MIN: gap = GAP_MIN; continue
        if first_sentence(sub) != sub: sub = first_sentence(sub); continue
        if hs > 56: hs -= 2; continue
        if ss > 28: ss -= 1; continue
        break
    src = Image.open(src_path).convert('RGB')
    if it.get('crop'): src = src.crop(it['crop'])
    bw, bh = 1080, ART_B - ART_T
    contain = min(bw / src.width, bh / src.height); cov = max(bw / src.width, bh / src.height)
    r = min(cov, contain * 1.25)
    w, h = src.width * r, src.height * r
    img = src.resize((R.P(w), R.P(h)), Image.LANCZOS)
    cw, ch = min(w, bw), min(h, bh)
    l, t = (w - cw) / 2, (h - ch) / 2
    img = img.crop((R.P(l), R.P(t), R.P(l + cw), R.P(t + ch)))
    x0, y0 = (1080 - cw) / 2, ART_B - ch
    ImageDraw.Draw(im).rectangle((0, 0, W, R.P(ART_B)), fill=(0, 0, 0))   # any gap around the art is black
    im.paste(img, (R.P(x0), R.P(y0)))
    d = ImageDraw.Draw(im)
    col = (165, 160, 230) if dark else R.ACC; fg = CREAM if dark else R.INK; mu = CM if dark else R.MUTED
    y = TXT_T
    R.text(d, (L, y - 4), 'Cleffy', R.BOD(36), fg)
    x = L + R.tw(d, 'Cleffy', R.BOD(36)) + 22
    for c in 'FROM THE ARCHIVE  ·  No. %02d' % n:
        R.text(d, (x, y + 6), c, R.SANSB(21), col); x += R.tw(d, c, R.SANSB(21)) + 3.2
    y += 36 + 26
    for ln in hl: R.text(d, (L, y), ln, hf, fg); y += int(hs * 1.18)
    y += gap
    for ln in sl: R.text(d, (L, y), ln, sf, mu); y += int(ss * 1.45)
    im = im.resize((1080, 1920), Image.LANCZOS)
    if not dark: im = shade(im)
    im.save(out, quality=93)
    return sub != it['sub']


if __name__ == '__main__':
    q = json.load(open(sys.argv[1])); srcd, outd = sys.argv[2], sys.argv[3]
    want = set(sys.argv[4:])
    os.makedirs(outd + '/frames', exist_ok=True); os.makedirs(outd + '/covers', exist_ok=True)
    for e in q:
        if want and str(e['n']) not in want and e['key'] not in want: continue
        src = f"{srcd}/{e['key']}.jpg"
        cover(e, e['no'], e['dark'], src, f"{outd}/covers/{e['key_file']}.jpg")
        cut = frame(e, e['no'], e['dark'], src, f"{outd}/frames/{e['key_file']}.jpg")
        print(e['n'], e['key_file'], 'DARK' if e['dark'] else 'LIGHT', 'sub cut' if cut else '')
