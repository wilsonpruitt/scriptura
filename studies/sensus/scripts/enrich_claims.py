#!/usr/bin/env python3
"""Enrich ledger/claims-<run>.tsv after merge_pass.py (no tokens).

  python3 -I scripts/enrich_claims.py partI

1. Resolve every PL location the reader supplied through the PL locator: references the reader
   found that the harvest missed, column-only rows the reader gave a volume, and harvested rows
   the reader corrected.
2. Normalize the reader's free-text author names (scripts/authors.py, data/author-aliases.tsv).
3. One final author per row: the locator's, where the location resolves; else the reader's,
   normalized. Death year and century with it, and where they came from.
4. Cross-check: where both exist, does the locator's author agree with the reader's?
Rewrites the claims file in place (merge_pass.py regenerates the base columns), and writes
ledger/READING-MAP-<run>.md.
"""
import collections, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from authors import normalize, key

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
run = sys.argv[1]
path = os.path.join(HERE, 'ledger', f'claims-{run}.tsv')
rows = list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
base_cols = [c for c in rows[0].keys() if c not in ('loc_status', 'loc_vol', 'loc_col', 'loc_idno', 'loc_author', 'loc_title',
             'author_reader_norm', 'author_reader_src', 'author_final', 'year_final', 'century', 'author_src', 'loc_vs_reader',
             'author_printed', 'author_alt', 'attrib_status', 'attrib_note')]
cols_ = json.load(open(os.path.join(HERE, 'data', 'pl-columns.json')))
meta = {r['idno']: r for r in csv.DictReader(open(os.path.join(HERE, 'data', 'pl-locator.tsv'), encoding='utf-8'), delimiter='\t')}
rulings = {(r['loc_author'], r['reader_norm']): r for r in csv.DictReader(
    open(os.path.join(HERE, 'data', 'author-rulings.tsv'), encoding='utf-8'), delimiter='\t')}
opened = {}   # either heading -> the open-attribution row (data/attributions-open.tsv)
for o in csv.DictReader(open(os.path.join(HERE, 'data', 'attributions-open.tsv'), encoding='utf-8'), delimiter='\t'):
    opened[o['printed']] = opened[o['alternative']] = o
digits = lambda s: (re.match(r'\d+', str(s or '').strip()) or [None])[0]

def locate(vol, col):
    ids = cols_.get(str(vol), {}).get(str(col))
    if not ids:
        return None
    ids = sorted(ids, key=lambda i: int(meta[i]['n_cols']) if i in meta else 10**6)
    return ids, meta.get(ids[0], {})

def same_author(a, b):
    ka, kb = set(key(a).split()), set(key(b).split())
    return bool(ka and kb and (ka <= kb or kb <= ka))

stats = collections.Counter()
for r in rows:
    r.update(loc_status='', loc_vol='', loc_col='', loc_idno='', loc_author='', loc_title='')
    rs = (r['reader_series'] or '').strip().upper().replace('.', '').replace(' ', '')
    vol = digits(r['reader_volume'])
    if r['source'] == 'reader':
        col = digits(r['reader_column'])
        want = rs == 'PL' and vol and col
    elif r['source'] == 'colonly':
        col = digits(r['col'])
        want = vol and col and (rs == 'PL' or (rs == '' and r['kind'] == 'migne_column'))
    else:  # harvest: only where the reader corrected a PL location
        col = digits(r['reader_column']) or digits(r['col'])
        vol = vol or digits(r['vol'])
        want = r['verdict'] == 'corrected' and (rs or r['series']) == 'PL' and vol and col
    if want:
        hit = locate(vol, col)
        if hit:
            ids, w = hit
            r.update(loc_status='resolved' if len(ids) == 1 else 'resolved-shared', loc_vol=vol, loc_col=col,
                     loc_idno=' '.join(ids), loc_author=w.get('author', ''), loc_title=w.get('title', ''))
            r['_loc_year'] = w.get('author_year', '')
        else:
            r.update(loc_status='column-not-in-tei', loc_vol=vol, loc_col=col)
        stats[f"{r['source']}:{r['loc_status']}"] += 1
    # the reader's own author, normalized
    h, y, s = normalize(r['reader_author']) if r['source'] != 'harvest' else ('', '', '')
    r['author_reader_norm'], r['author_reader_src'] = h, s
    # final author
    if r['loc_author']:
        r.update(author_final=r['loc_author'], year_final=r.pop('_loc_year', ''), author_src='locator')
        if h:
            r['loc_vs_reader'] = 'agree' if same_author(r['loc_author'], h) or r['loc_author'].startswith('Auctor incertus') else 'differ'
            ru = rulings.get((r['loc_author'], h)) if r['loc_vs_reader'] == 'differ' else None
            if ru:  # data/author-rulings.tsv: same | reader | locator | check
                r['loc_vs_reader'] = {'same': 'agree', 'reader': 'ruled-reader', 'locator': 'ruled-locator', 'check': 'check'}[ru['ruling']]
                if ru['ruling'] == 'reader':
                    r.update(author_final=ru['final_heading'] or h, year_final=ru['final_year'] or y, author_src='ruling-reader')
                elif ru['ruling'] == 'locator' and ru['final_heading']:
                    r.update(author_final=ru['final_heading'], year_final=ru['final_year'])
            stats['xcheck:' + r['loc_vs_reader']] += 1
    elif r['source'] == 'harvest' and r['author']:
        r.update(author_final=r['author'], year_final=r['author_year'], author_src='harvest')
    elif h:
        r.update(author_final=h, year_final=y, author_src='reader-' + s)
    else:
        r.update(author_final='', year_final='', author_src='modern' if s == 'modern' else 'none')
    r.pop('_loc_year', None)
    # attribution layer: what the edition prints, the other candidate, and whether it is settled
    printed = r['loc_author'] or (r['author'] if r['source'] == 'harvest' else '')
    r.update(author_printed=printed, author_alt='', attrib_status='', attrib_note='')
    if r['author_src'] == 'ruling-reader':
        r.update(author_alt=r['author_final'], attrib_status='ruled', attrib_note='data/author-rulings.tsv')
    o = opened.get(r['author_final']) or opened.get(printed)
    if o:
        r.update(author_printed=printed or o['printed'], author_alt=o['alternative'] if (printed or o['printed']) == o['printed'] else o['printed'],
                 attrib_status='open', attrib_note=o['note'][:120], author_final=o['count_as'], year_final=o['year'])
        stats['attrib:open'] += 1
    y = digits(r['year_final'])
    r['century'] = str((int(y) - 1) // 100 + 1) if y and int(y) > 0 else ''
    r.setdefault('loc_vs_reader', '')

cols = base_cols + ['loc_status', 'loc_vol', 'loc_col', 'loc_idno', 'loc_author', 'loc_title', 'author_reader_norm',
                    'author_reader_src', 'author_final', 'year_final', 'century', 'author_src', 'loc_vs_reader',
                    'author_printed', 'author_alt', 'attrib_status', 'attrib_note']
with open(path, 'w', encoding='utf-8') as f:
    f.write('\t'.join(cols) + '\n')
    for r in rows:
        f.write('\t'.join(str(r.get(c, '')).replace('\t', ' ') for c in cols) + '\n')

# ---------- the reading map ----------
coded = [r for r in rows if r['author_src'] != 'modern']
ex = [r for r in coded if r['role'] == 'example']
def table(rs, n=30):
    c = collections.Counter(r['author_final'] or '(no author)' for r in rs)
    yr = {r['author_final']: r['year_final'] for r in rs}
    return ['| author | d. | rows |', '|---|---:|---:|'] + [f'| {a} | {yr.get(a, "")} | {v} |' for a, v in c.most_common(n)]
def cent(rs):
    c = collections.Counter(r['century'] or 'undated' for r in rs)
    tot = sum(v for k, v in c.items() if k != 'undated')
    order = sorted((k for k in c if k != 'undated'), key=int) + (['undated'] if 'undated' in c else [])
    return ['| century | rows | share of dated |', '|---|---:|---:|'] + \
           [f'| {k} | {c[k]} | {"" if k == "undated" else f"{100 * c[k] / tot:.1f}%"} |' for k in order]
src = collections.Counter(r['author_src'] for r in coded)
mov = collections.Counter(r['senses'] or '(none)' for r in ex)
md = [f'# Reading map, {run} (de Lubac, Exégèse médiévale)', '',
      'Generated by `scripts/enrich_claims.py` from `ledger/claims-' + run + '.tsv`. One coder (Opus 5.5, codebook R1–R7).',
      'Authors: locator heading where the reader\'s or harvest\'s PL location resolves, else the reader\'s name normalized.',
      'Years marked `hand` in `data/author-aliases.tsv` are from general knowledge and unchecked.', '',
      f'Rows: {len(rows)}; modern scholarship excluded: {len(rows) - len(coded)}. Author source: ' +
      ', '.join(f'{k} {v}' for k, v in src.most_common()), '',
      'Locator resolution of reader-supplied PL locations: ' + ', '.join(f'{k} {v}' for k, v in sorted(stats.items()) if not k.startswith('xcheck')),
      f"Cross-check, locator author vs the reader's: agree {stats['xcheck:agree']}; ruled for de Lubac's attribution {stats['xcheck:ruled-reader']}, "
      f"for the printed author {stats['xcheck:ruled-locator']}; to check at the page {stats['xcheck:check']}; unruled {stats['xcheck:differ']} "
      "(rulings: `data/author-rulings.tsv`; the printed author stays in `loc_author`).", '',
      '## 1. Examples (readings of a text), by author', ''] + table(ex) + \
     ['', '## 2. Examples by century of the author\'s death', ''] + cent(ex) + \
     ['', '## 3. All coded citations, by author', ''] + table(coded) + \
     ['', '## 4. All coded citations by century', ''] + cent(coded) + \
     ['', '## 5. The movements in the examples (senses in order)', '', '| movement | examples |', '|---|---:|'] + \
     [f'| {k} | {v} |' for k, v in mov.most_common(20)] + \
     ['', '## 6. Attributions not yet settled', '',
      'Counted under a joint heading until a confirmation pass rules them (`data/attributions-open.tsv`). '
      'Rows carry `author_printed`, `author_alt` and `attrib_status=open`; rows ruled for de Lubac\'s attribution carry `attrib_status=ruled`.', '',
      '| counted as | printed | alternative | rows | examples |', '|---|---|---|---:|---:|'] + \
     [f'| {k[0]} | {k[1]} | {k[2]} | {v} | {sum(1 for r in ex if r["attrib_status"] == "open" and r["author_final"] == k[0])} |'
      for k, v in collections.Counter((r['author_final'], r['author_printed'], r['author_alt']) for r in rows if r['attrib_status'] == 'open').most_common()]
open(os.path.join(HERE, 'ledger', f'READING-MAP-{run}.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')
print('\n'.join(md[:12]))
