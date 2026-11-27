import json, re, unicodedata, collections, sys
R = '/home/claude/cleffy-social/'
pool = json.load(open(R + 'q1/pool.json'))
clean = sorted(t for t, v in pool.items() if v.get('clean'))
extra = {156: ('praetorius', 'H', 'voice', 'Praetorius, Es ist ein Ros entsprungen', '~'), 244: ('holst', 'L', 'band', 'Holst, The Planets: Mercury', 'the U.S. Air Force Band'), 297: ('polska', 'F', 'strings', 'Polska, a Swedish folk dance', '~')}
T = []
for ln in open('/home/claude/q1work/tracks.txt', encoding='utf-8'):
    i, comp, era, inst, title, perf = ln.rstrip('\n').split('|')
    T.append(dict(i=int(i), comp=comp, era=era, inst=inst, title=title, perf=perf))
for i, (comp, era, inst, title, perf) in extra.items(): T.append(dict(i=i, comp=comp, era=era, inst=inst, title=title, perf=perf))
T = [t for t in T if t['i'] != 98]
STOP = {'the','and','for','von','des','les','del','sur','from','piano','solo','major','minor','orchestra','voice','with','une','dans'}
def strip(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
for t in T:
    t['file'] = clean[t['i']]; v = pool[t['file']]
    t['license'] = v['license']; t['start'] = (v['m'] or {}).get('start', 0)
    art = re.sub(r'\s+', ' ', v.get('artist') or '').strip()
    if t['perf'] == '~':
        t['performer'] = t['title'] + (f', recording by {art}' if art and len(art) < 60 and not art.lower().startswith(('unknown', 'see ', 'http')) else ', recording via Wikimedia Commons')
    else:
        p = t['perf']
        t['performer'] = f"{t['title']}, " + (p if 'conducting' in p else ('performed by ' + p) if p.startswith('the ') or 'Band' in p else ('played by ' + p))
    t['comp'] = strip(t['comp'])
    if t['comp'] == 'auld': t['era'] = 'NY'
    t['tok'] = set(re.findall(r'[a-z]{3,}|\d+', strip(t['title']))) - STOP
ERA = {}
for era, names in {
 'M': 'anonymous browne josquin barbireau milano machaut ockeghem ghizeghem sermisy cabezon spinacino fayrfax obrecht arbeau landini perotin tromboncino frauenlob alfonso byrd merulo dowland valerius gregorian chant',
 'B': 'pepusch sweelinck gaultier chedeville simpson couperin visee kapsberger froberger handel vinci geminiani guerre caccini purcell strozzi corelli vivaldi frescobaldi corbetta eyck rameau scarlatti bach',
 'C': 'clementi haydn mozart boccherini hummel beethoven saint-georges gluck arne cpebach jcbach bologne',
 'R': 'chopin schubert grieg viardot berlioz gottschalk dvorak paganini brahms albeniz mendelssohn liszt schumann wieniawski sor tarrega field rubinstein gade demersseman wagner verdi offenbach leoncavallo mussorgsky rimsky-korsakov tchaikovsky strauss faure chabrier foster bruant carreno holmes saint-saens',
 'L': 'ravel satie debussy holst boulanger paderewski chaminade coleridge-taylor beach',
 'A': 'sousa joplin handy harris europe wiggins',
}.items():
    for n in names.split(): ERA[n] = era
def comp_of(it):
    a = strip(it['audio']); c = a.split(',')[0]
    if 'c. p. e.' in c or 'philipp emanuel' in c: return 'cpebach'
    if 'johann christian' in c: return 'jcbach'
    if 'saint-georges' in a or 'bologne' in c: return 'saint-georges'
    if 'jacquet' in c: return 'guerre'
    if 'de visee' in c: return 'visee'
    if 'van eyck' in c: return 'eyck'
    if 'da milano' in c: return 'milano'
    if 'gregorian' in c or 'chant' in c: return 'chant'
    if 'van ghizeghem' in c: return 'ghizeghem'
    if 'des prez' in c: return 'josquin'
    if 'mesomedes' in c: return 'mesomedes'
    if 'strauss' in c: return 'strauss'
    if 'joplin' in c: return 'joplin'
    if 'dabney' in c or 'reese europe' in c: return 'europe'
    if 'alfonso' in c: return 'alfonso'
    if 'polska' in a: return 'polska'
    w = re.sub(r'\(.*?\)', '', c).split()
    return w[-1] if w else ''
def bucket(it, comp):
    a = strip(it['audio'])
    if any(k in a for k in ('koto', 'pipa', 'guqin', 'biwa', 'shamisen', 'korean', 'mongolian', 'kengyo')): return 'EA'
    if any(k in a for k in ('raga', 'sitar', 'veena', 'bansuri', 'tanpura', 'carnatic')): return 'W-IN'
    if any(k in a for k in ('persian', 'makam', 'hurrian', 'mesomedes', 'cantemir', 'tanbur')): return 'W-ME'
    if 'spiritual' in a or 'negro melodies' in a: return 'SPIR'
    if any(k in a for k in ('silent night', 'holly and the ivy', 'jingle bells', 'es ist ein ros', 'puer natus')): return 'H'
    if 'polska' in a: return 'R'
    return ERA.get(comp, 'R')
FALL = {
 'EA': [317, 318, 319, 117, 119, 229, 230],
 'W-IN': [21, 316], 'W-ME': [310], 'SPIR': [159, 138],
}
byi = {t['i']: t for t in T}
def cands(it):
    comp = comp_of(it); b = bucket(it, comp)
    tok = set(re.findall(r'[a-z]{3,}|\d+', strip(it['audio'].split(',', 1)[-1]))) - STOP
    a = strip(it['audio'])
    vocal = any(k in a for k in ('voice', 'choir', 'chant', 'chorus', 'soprano'))
    out = []
    for t in T:
        s = 0
        if t['comp'] == comp or (comp == 'cpebach' and False): s += 10
        if b == 'H':
            if t['era'] == 'H': s += 6
            if t['comp'] == comp: s += 6
        elif b in FALL:
            if t['i'] in FALL[b]: s += 6
        elif t['era'] == b and t['era'] != 'H': s += 4
        elif b == 'M' and t['i'] in (302, 305, 132, 133, 154, 155, 190): s += 3
        if s == 0: continue
        if s < 10:
            if t['inst'] in ('piano', 'harpsichord', 'strings', 'ens', 'guitar'): s += 1
            if b == 'M': s += 2 if (t['inst'] == 'choir') == vocal else 0
        if t['inst'] == 'guitar' and any(k in a for k in ('guitar',)): s += 5
        s += 2 * len(tok & t['tok'])
        out.append((s, t))
    return comp, b, out
it = {i['key']: i for i in json.load(open(R + 'q1/items.json'))}
sched = json.load(open(R + 'q1/schedule.json'))
used = collections.Counter(); last = {}
res = []
for k, e in enumerate(sched):
    i = it[e['key']]; comp, b, cs = cands(i)
    best = None
    for s, t in cs:
        sc = s - 3 * used[t['i']] - (100 if k - last.get(t['i'], -99) < 12 else 0)
        if best is None or sc > best[0]: best = (sc, s, t)
    if best is None: print('NO CANDIDATE', e['no'], e['key'], i['audio']); continue
    _, s, t = best; used[t['i']] += 1; last[t['i']] = k
    res.append((e, i, comp, b, s, t))
for e, i, comp, b, s, t in res:
    flag = '' if s >= 10 else ('~' if s >= 6 else '?')
    print(f"{e['no']} {flag:1} {i['audio'][:55]:55} -> {t['title'][:60]}")
print(len(res), 'max reuse', used.most_common(5), 'distinct', len(used))
json.dump({e['no']: dict(file=t['file'], start=t['start'], title=t['title'], performer=t['performer'], license=t['license']) for e, i, comp, b, s, t in res}, open('/home/claude/q1work/music_q1.json', 'w'), indent=1, ensure_ascii=False)
