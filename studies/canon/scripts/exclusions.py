#!/usr/bin/env python3
"""Propose the formula exclusion list (canon STUDY, Next 3). No tokens; a reader rules.

  python3 -I studies/canon/scripts/exclusions.py

A candidate is an n-gram evidence string (its first 6 words) repeated in many works, which Migne
seldom cites inline where it occurs (verse/mixed-practice volumes only). Writes
studies/canon/exclusions-proposed.tsv with an empty `ruling` column: keep | exclude | context.
"""
import collections, csv, importlib.util, os, re
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('sp', os.path.join(HERE, 'scripts', 'spine.py'))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
OUT = sp.OUT
colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9
prac = {r['vol']: r['practice'] for r in csv.DictReader(open(os.path.join(OUT, 'volume-practice.tsv'), encoding='utf-8'), delimiter='\t')}
inl = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
    if r['exists'] == 'y':
        inl[(r['idno'], colnum(r['col']))].append(r['vulg'])
occ = collections.Counter(); works = collections.defaultdict(set); verses = collections.defaultdict(collections.Counter)
cited = collections.Counter(); seen = collections.Counter()
for r in csv.DictReader(open(os.path.join(OUT, 'spine-ngram.tsv'), encoding='utf-8'), delimiter='\t'):
    key = ' '.join(r['evidence'].split()[:6])
    occ[key] += 1; works[key].add(r['idno']); verses[key][r['vulg']] += 1
    if prac.get(r['vol']) in ('verse', 'mixed'):
        c = colnum(r['col']); seen[key] += 1
        cited[key] += any(sp._within(r['vulg'], ref) or sp._near(r['vulg'], ref) for k in (c - 1, c, c + 1) for ref in inl.get((r['idno'], k), ()))
rows = []
for key, n in occ.items():
    if len(works[key]) < 25:
        continue
    rate = cited[key] / seen[key] if seen[key] else 0
    if rate < 0.25:
        rows.append((n, len(works[key]), rate, key, ' '.join(f'{v}:{c}' for v, c in verses[key].most_common(3))))
rows.sort(reverse=True)
p = os.path.join(HERE, 'exclusions-proposed.tsv')
with open(p, 'w', encoding='utf-8') as o:
    o.write('rows\tworks\tmigne_cites_inline\trun\tverses\truling\n')
    for n, w, rate, key, vs in rows:
        o.write(f'{n}\t{w}\t{rate:.2f}\t{key}\t{vs}\t\n')
print(len(rows), 'candidates (in 25+ works, Migne cites <25% of occurrences) ->', p)
print('rows they cover:', sum(r[0] for r in rows), 'of', sum(occ.values()))
for r in rows[:30]:
    print(f'{r[0]:>5} {r[1]:>4} {r[2]:.2f}  {r[3]:<45} {r[4]}')
