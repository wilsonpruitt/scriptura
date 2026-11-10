#!/usr/bin/env python3
"""Compare two independent codings of the pilot pages (coder A vs coder B).

  python3 -I scripts/pilot_agree.py [run] [A] [B]      (run defaults to "pilot")

Writes working/pilot/agreement.md (the numbers) and working/pilot/disagreements.tsv (one row
per field the coders differ on, for Wilson to rule). Both stay in working/: rows carry
de Lubac's reference strings.
"""
import collections, glob, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = sys.argv[1] if len(sys.argv) > 1 else 'pilot'
P = os.path.join(HERE, 'working', RUN)
A, B = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else ('A', 'B')
NEW = ['allegory_kind', 'stance', 'term_differs']

def load(coder):
    out = {}
    for f in sorted(glob.glob(os.path.join(P, coder, '*.json'))):
        out[os.path.basename(f)] = json.load(open(f, encoding='utf-8'))
    return out

def norm(s):
    return re.sub(r'\s+', ' ', str(s or '').strip().lower())

def kappa(pairs):
    n = len(pairs)
    if not n: return float('nan')
    po = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / n / n
    return (po - pe) / (1 - pe) if pe < 1 else 1.0

a, b = load(A), load(B)
pages = sorted(set(a) & set(b))
stats = collections.defaultdict(lambda: [0, 0])  # field -> [agree, total]
role_pairs, kind_pairs = [], []
dis = []
cover = collections.Counter()
missed = {A: 0, B: 0, 'both_same_note': 0}
usage = {A: [0, 0], B: [0, 0]}

for pg in pages:
    ra, rb = a[pg], b[pg]
    for c, r in ((A, ra), (B, rb)):
        usage[c][0] += r['input']; usage[c][1] += r['output']
    if not ra['data'] or not rb['data']:
        cover['page_without_json'] += 1; continue
    for kind, fields in (('refs', ['verdict', 'series', 'volume', 'column', 'role', 'senses', 'author_label', 'scripture']),
                         ('colonly', ['kind', 'series', 'volume', 'work', 'role', 'senses', 'author_label', 'scripture'])):
        exp = ra['expected_refs' if kind == 'refs' else 'expected_colonly']
        fields = fields + [f for f in NEW if ra['data'][kind] and f in ra['data'][kind][0]]
        ia = {x['id']: x for x in ra['data'][kind]}
        ib = {x['id']: x for x in rb['data'][kind]}
        for i in exp:
            if i not in ia or i not in ib:
                cover[f'{kind}_row_dropped'] += 1; continue
            cover[f'{kind}_rows'] += 1
            xa, xb = ia[i], ib[i]
            for f in fields:
                if kind == 'refs' and f in ('series', 'volume', 'column') and xa['verdict'] == xb['verdict'] == 'ok':
                    continue  # only compared where someone corrected
                va, vb = xa.get(f), xb.get(f)
                same = (va == vb) if f == 'senses' else (norm(va) == norm(vb))
                if f == 'work':  # free text: count as agreeing if both empty or both name the same first word
                    same = norm(va).split(' ')[:1] == norm(vb).split(' ')[:1]
                key = f'{kind}.{f}'
                stats[key][1] += 1; stats[key][0] += same
                if not same:
                    dis.append([pg, kind, i, f, json.dumps(va, ensure_ascii=False), json.dumps(vb, ensure_ascii=False),
                                xa['cited_for'], xb['cited_for']])
            # senses as a set, to separate order disagreements from content disagreements
            stats[f'{kind}.senses_as_set'][1] += 1
            stats[f'{kind}.senses_as_set'][0] += set(xa['senses']) == set(xb['senses'])
            if kind == 'refs':
                role_pairs.append((xa['role'], xb['role']))
            else:
                kind_pairs.append((xa['kind'], xb['kind']))
                role_pairs.append((xa['role'], xb['role']))
    ma = {(m['note'], norm(m['volume']), norm(m['column'])) for m in ra['data']['missed']}
    mb = {(m['note'], norm(m['volume']), norm(m['column'])) for m in rb['data']['missed']}
    missed[A] += len(ma); missed[B] += len(mb); missed['both_same_note'] += len({x[0] for x in ma} & {x[0] for x in mb})

roles = collections.Counter(r for p in role_pairs for r in p)
lines = [f'# Pilot agreement, coder {A} vs coder {B}', '',
         f'Pages compared: {len(pages)}. Coverage: ' + ', '.join(f'{k} {v}' for k, v in sorted(cover.items())), '',
         '| field | agree | of | % |', '|---|---|---|---|']
for k in sorted(stats):
    ag, n = stats[k]
    lines.append(f'| {k} | {ag} | {n} | {100 * ag / n:.0f}% |' if n else f'| {k} | 0 | 0 | |')
lines += ['', f'Role, Cohen\'s kappa: {kappa(role_pairs):.2f} over {len(role_pairs)} rows. Role mix (both coders): ' +
          ', '.join(f'{k} {v}' for k, v in roles.most_common()),
          f'Column-only kind, kappa: {kappa(kind_pairs):.2f} over {len(kind_pairs)} rows.',
          f'Missed references proposed: {A} {missed[A]}, {B} {missed[B]}; notes both flagged: {missed["both_same_note"]}.',
          '', 'Role confusion (A row, B column):', '']
rk = ['example', 'theory', 'vocabulary', 'history', 'other']
lines.append('| A \\ B | ' + ' | '.join(rk) + ' |'); lines.append('|---' * (len(rk) + 1) + '|')
cm = collections.Counter(role_pairs)
for x in rk:
    lines.append(f'| {x} | ' + ' | '.join(str(cm[(x, y)]) for y in rk) + ' |')
for c in (A, B):
    lines.append(f'\nTokens, coder {c}: {usage[c][0]:,} in, {usage[c][1]:,} out')
open(os.path.join(P, f'agreement-{A}{B}.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
with open(os.path.join(P, f'disagreements-{A}{B}.tsv'), 'w', encoding='utf-8') as f:
    f.write('\t'.join(['page', 'kind', 'id', 'field', A, B, f'cited_for_{A}', f'cited_for_{B}']) + '\n')
    for d in dis:
        f.write('\t'.join(str(x).replace('\t', ' ').replace('\n', ' ') for x in d) + '\n')
print('\n'.join(lines)); print(f'\n{len(dis)} disagreements -> working/{RUN}/disagreements-{A}{B}.tsv')
