#!/usr/bin/env python3
"""Preliminary canon findings from spine v0 (no tokens). Counts DISTINCT WORKS citing a verse, from
inline (verse-level, exists), ngram, and fuzzy (pairs >= 4) together. Exclusions are not ruled yet
and parallels count once per verse each, so read these as provisional.

  python3 -I studies/canon/scripts/headline.py
"""
import collections, csv, importlib.util, os, re
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('sp', os.path.join(HERE, 'scripts', 'spine.py'))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
OUT = sp.OUT
def era(y):
    try: y = int(y)
    except ValueError: return None
    if y <= 0: return None
    return 'to 600' if y <= 600 else '601-1000' if y <= 1000 else '1001-1216'
cites = collections.defaultdict(set)          # verse -> works
work_era = {}
def add(idno, v, y):
    v = v.split('-')[0]
    if v.count('.') == 2:
        cites[v].add(idno); work_era[idno] = era(y)
for r in csv.DictReader(open(os.path.join(OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
    if r['level'] == 'verse' and r['exists'] == 'y':
        add(r['idno'], r['vulg'], r['author_year'])
for r in csv.DictReader(open(os.path.join(OUT, 'spine-ngram.tsv'), encoding='utf-8'), delimiter='\t'):
    add(r['idno'], r['vulg'], r['author_year'])
for r in csv.DictReader(open(os.path.join(OUT, 'spine-fuzzy.tsv'), encoding='utf-8'), delimiter='\t'):
    if int(r['pairs']) >= 4:
        add(r['idno'], r['vulg'], r['author_year'])
allv = [k for k, _ in sp.vulgate()]
vt = dict(sp.vulgate())
works = {w for s in cites.values() for w in s}
print(f'works citing anything: {len(works)}; verses cited by at least one work: {sum(1 for v in allv if cites.get(v))} of {len(allv)}')
never = [v for v in allv if not cites.get(v)]
print(f'never cited (no stream, no work): {len(never)} ({100*len(never)/len(allv):.1f}%)')
bk = collections.Counter(v.split('.')[0] for v in allv); nb = collections.Counter(v.split('.')[0] for v in never)
print('books with the highest never-cited share (>=50 verses):')
for b in sorted((b for b in bk if bk[b] >= 50), key=lambda b: -nb[b] / bk[b])[:12]:
    print(f'  {b}: {nb[b]}/{bk[b]} ({100*nb[b]/bk[b]:.0f}%)')
print('books with the lowest never-cited share:')
for b in sorted((b for b in bk if bk[b] >= 50), key=lambda b: nb[b] / bk[b])[:8]:
    print(f'  {b}: {nb[b]}/{bk[b]} ({100*nb[b]/bk[b]:.0f}%)')
for e in ('to 600', '601-1000', '1001-1216'):
    ew = {w for w, x in work_era.items() if x == e}
    top = sorted(allv, key=lambda v: -len(cites.get(v, set()) & ew))[:12]
    print(f'\n== {e}: {len(ew)} works. Most-cited verses (works citing):')
    for v in top:
        print(f'  {v:<12} {len(cites[v] & ew):>4}  {" ".join(vt[v])[:70]}')
# book share by era (distinct work-verse pairs)
print('\nshare of work-verse citations by group:')
G = {'Psalms': {'Ps'}, 'Gospels': {'Matt', 'Mark', 'Luke', 'John'}, 'Paul': {'Rom', '1Cor', '2Cor', 'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess', '1Tim', '2Tim', 'Titus', 'Phlm', 'Heb'},
     'Prophets': {'Isa', 'Jer', 'Ezek', 'Dan', 'Hos', 'Joel', 'Amos', 'Obad', 'Jonah', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal', 'Lam', 'Bar'},
     'Pentateuch': {'Gen', 'Exod', 'Lev', 'Num', 'Deut'}, 'Wisdom': {'Prov', 'Eccl', 'Song', 'Job', 'Wis', 'Sir'}}
tot = collections.Counter(); grp = collections.Counter()
for v, ws in cites.items():
    b = v.split('.')[0]
    for w in ws:
        e = work_era.get(w)
        if not e: continue
        tot[e] += 1
        for g, bs in G.items():
            if b in bs: grp[(e, g)] += 1
print('  group       ' + ''.join(f'{e:>12}' for e in ('to 600', '601-1000', '1001-1216')))
for g in G:
    print(f'  {g:<12}' + ''.join(f'{100*grp[(e,g)]/tot[e]:>11.1f}%' for e in ('to 600', '601-1000', '1001-1216')))
