"""Place curated items into rows of art/score/art, 3 a day from Dec 6, 2026.
python3 schedule_q1.py <items.json>... --fails f1.json f2.json --out schedule.json"""
import json, sys, random, datetime as dt, re
args = sys.argv[1:]; out = args[args.index('--out') + 1]
fails = set()
if '--fails' in args:
    i = args.index('--fails') + 1
    while i < len(args) and not args[i].startswith('--'): fails |= set(json.load(open(args[i]))); i += 1
paths = [a for a in args[:args.index('--fails') if '--fails' in args else args.index('--out')]]
items = [x for p in paths for x in json.load(open(p)) if x['key'] not in fails]
art = [x for x in items if x['kind'] == 'art']; score = [x for x in items if x['kind'] == 'score']
R = min(len(score), len(art) // 2)
D0 = dt.date(2026, 12, 6)
days = [{'art': [], 'score': []} for _ in range(R)]
cap = {'art': 2, 'score': 1}
def who(x):  # rough subject id for spacing
    return re.split(r'-', x['key'])[0]
placed = set()
dated = sorted([x for x in items if x.get('date_hint')], key=lambda x: x['date_hint'])
for x in dated:
    d = (dt.date.fromisoformat(x['date_hint']) - D0).days
    for off in (0, -1, 1, -2, 2, -3, 3):
        k = d + off
        if 0 <= k < R and len(days[k][x['kind']]) < cap[x['kind']]:
            days[k][x['kind']].append(x); placed.add(x['key']); x['_off'] = off; break
rnd = random.Random(7)
for kind in ('art', 'score'):
    pool = [x for x in (art if kind == 'art' else score) if x['key'] not in placed]
    groups = {}
    for x in pool: groups.setdefault(x['group'], []).append(x)
    for g in groups.values(): rnd.shuffle(g)
    last = []
    for k in range(R):
        while len(days[k][kind]) < cap[kind]:
            near = {who(y) for j in range(max(0, k - 4), min(R, k + 5)) for kk in ('art', 'score') for y in days[j][kk]}
            gs = sorted([g for g in groups if groups[g]], key=lambda g: (g in last[-1:], -len(groups[g])))
            if not gs: break
            pick = None
            for g in gs:
                for x in groups[g]:
                    if who(x) not in near: pick = (g, x); break
                if pick: break
            if not pick: pick = (gs[0], groups[gs[0]][0])
            groups[pick[0]].remove(pick[1]); days[k][kind].append(pick[1]); last.append(pick[0])
    left = [x['key'] for g in groups.values() for x in g]
    print(kind, 'unused:', left)
sched = []; no = 31
for k, d in enumerate(days):
    date = D0 + dt.timedelta(k)
    for slot, (kind, idx) in enumerate([('art', 0), ('score', 0), ('art', 1)]):
        x = d[kind][idx]
        sched.append({'n': no, 'no': no, 'dark': no % 2 == 0, 'date': date.isoformat(),
                      'time': ['08:00', '12:30', '19:00'][slot], 'key': x['key'], 'kind': kind, 'group': x['group'],
                      'date_hint': x.get('date_hint'), 'off': x.get('_off')})
        no += 1
json.dump(sched, open(out, 'w'), indent=1, ensure_ascii=False)
print(R, 'rows', sched[0]['date'], '->', sched[-1]['date'], 'Nos', sched[0]['no'], '-', sched[-1]['no'])
for s in sched:
    if s['date_hint'] and s['off'] is None: print('  dated but unplaced near date:', s['key'], s['date_hint'], '->', s['date'])
