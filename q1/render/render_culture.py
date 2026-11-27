import sys, math, random
sys.path.insert(0, '/mnt/project-files/cleffy-instagram/q1/render')
from PIL import Image, ImageDraw, ImageFilter
import io,contextlib
with contextlib.redirect_stdout(io.StringIO()):
    import render as R
from render import P, S, W, H, INK, PAPER, PAGE, ACC, MUTED, BOD, BODI, BOD4, SANS, SANSM, SANSB, HAND, text, tw

C = '/tmp/q1out'
R.OUT = C + '/out'
CREAM = (243, 234, 214)
CREAM_MUTED = (176, 166, 150)

def wrap(d, s, font, maxw):
    words = s.split(); lines = []; cur = ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if tw(d, t, font) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def para(d, x, y, s, font, fill, maxw, lh):
    for ln in wrap(d, s, font, maxw):
        text(d, (x, y), ln, font, fill); y += lh
    return y

def card(im, src, box, mat=0, shadow=True, crop=None, fit='contain'):
    x0, y0, x1, y1 = box
    img = Image.open(src).convert('RGB')
    if crop: img = img.crop(crop)
    if src.endswith('bonn-draft.png'):
        from PIL import ImageOps, ImageEnhance
        img = ImageEnhance.Contrast(img).enhance(1.35)
    bw, bh = x1 - x0, y1 - y0
    r = min(bw / img.width, bh / img.height) if fit == 'contain' else max(bw / img.width, bh / img.height)
    w, h = img.width * r, img.height * r
    cx, cy = x0 + (bw - w) / 2, y0 + (bh - h) / 2
    if fit == 'cover':
        img = img.resize((P(w), P(h)), Image.LANCZOS)
        l, t = P((w - bw) / 2), P((h - bh) / 2)
        img = img.crop((l, t, l + P(bw), t + P(bh))); cx, cy, w, h = x0, y0, bw, bh
    else:
        img = img.resize((P(w), P(h)), Image.LANCZOS)
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        sd.rectangle([P(cx - mat), P(cy - mat + 16), P(cx + w + mat), P(cy + h + mat + 16)], fill=(28, 25, 23, 80))
        sh = sh.filter(ImageFilter.GaussianBlur(P(24))); im.paste(sh, (0, 0), sh)
    d = ImageDraw.Draw(im)
    if mat: d.rectangle([P(cx - mat), P(cy - mat), P(cx + w + mat), P(cy + h + mat)], fill=PAGE)
    im.paste(img, (P(cx), P(cy)))
    return cx, cy, w, h

def header(d, n, dark=False):
    col = (165, 160, 230) if dark else ACC
    lab = 'FROM THE ARCHIVE'
    x = 72
    for ch in lab:
        text(d, (x, 64), ch, SANSB(17), col); x += tw(d, ch, SANSB(17)) + 2.6
    text(d, (1008, 64), 'No. %02d' % n, SANSM(17), CREAM_MUTED if dark else MUTED, anchor='ra')

def footer(d, credit, dark=False):
    y = 1278
    d.line([(P(72), P(y - 22)), (P(1008), P(y - 22))], fill=(70, 64, 60) if dark else (222, 218, 208), width=P(1))
    sz = 16  # long credits shrink, then drop middle parts, so they never run into the wordmark
    while R.tw(d, credit, SANS(sz)) > 820 and sz > 12: sz -= 1
    while R.tw(d, credit, SANS(sz)) > 820 and credit.count(' · ') >= 2:
        parts = credit.split(' · '); first = parts[0].split(', ')
        if len(first) > 2: parts[0] = ', '.join(first[:-2] + first[-1:]) if len(first) > 3 else ', '.join(first[:1] + first[-1:])
        else: parts.pop(1)
        credit = ' · '.join(parts)
    text(d, (72, y), credit, SANS(sz), CREAM_MUTED if dark else MUTED)
    text(d, (1008, y + 9), 'Cleffy', BOD(26), CREAM if dark else INK, anchor='rm')

def archive_post(n, src, name, head, sub, credit, crop=None, dark=False, img_box=None, mat=14, maxw=None):
    bg = INK if dark else PAPER
    im, d = R.base(bg)
    header(d, n, dark)
    hl = wrap(d, head, BOD(54), 936); sl = wrap(d, sub, SANS(26), 920)
    th = len(hl) * 66 + 18 + len(sl) * 38
    ty = 1210 - th
    top, bot = 118, ty - 56
    l, r = 72 + mat, 1008 - mat
    if maxw: l, r = 540 - maxw / 2, 540 + maxw / 2
    card(im, src, (l, top + mat, r, bot - mat), mat=mat, crop=crop)
    d = ImageDraw.Draw(im)
    fg = CREAM if dark else INK
    y = ty
    for ln in hl: text(d, (72, y), ln, BOD(54), fg); y += 66
    y += 18
    for ln in sl: text(d, (72, y), ln, SANS(26), CREAM_MUTED if dark else MUTED); y += 38
    footer(d, credit, dark)
    R.save(im, name)

