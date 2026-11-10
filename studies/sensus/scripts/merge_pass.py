#!/usr/bin/env python3
"""Merge a reading pass (working/<run>/<coder>/*.json) into the ledger.

  python3 -I scripts/merge_pass.py partI A

Writes ledger/claims-<run>.tsv: one row per coded reference (harvested, column-only, and the
ones the reader found that the harvest missed), with the harvest's location fields beside the
reader's coding. Pointer-only: our words (cited_for), the source's Latin terms (author_label),
locations. The reader's `printed` string for a missed reference is de Lubac's citation as
printed; it is kept for checking, like `raw` in refs.tsv, and is reviewed before any export.
"""
import csv, glob, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
run, coder = sys.argv[1], sys.argv[2]
rd = lambda f: list(csv.DictReader(open(os.path.join(HERE, 'ledger', f), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
refs = {r['id']: r for r in rd('refs.tsv')}
col = {r['id']: r for r in rd('colonly.tsv')}

OUT = ['id', 'source', 'em', 'tome', 'page', 'pdf_page', 'note', 'series', 'vol', 'col', 'band', 'author', 'author_year',
       'title', 'status', 'verdict', 'reader_series', 'reader_volume', 'reader_column', 'kind', 'reader_author', 'reader_work',
       'role', 'senses', 'allegory_kind', 'stance', 'author_label', 'term_differs', 'scripture', 'cited_for', 'confidence',
       'printed', 'model', 'codebook']
rows, dropped = [], []
for f in sorted(glob.glob(os.path.join(HERE, 'working', run, coder, '*.json'))):
    d = json.load(open(f, encoding='utf-8'))
    if not d['data']:
        continue
    meta = {'model': d['model'], 'codebook': d.get('codebook', '')}
    def code(x):
        return dict(role=x['role'], senses=' > '.join(x['senses']), allegory_kind=x['allegory_kind'], stance=x['stance'],
                    author_label=x['author_label'], term_differs=int(x['term_differs']), scripture=x['scripture'],
                    cited_for=x['cited_for'], confidence=x['confidence'], **meta)
    got = {x['id']: x for x in d['data']['refs']}
    for i in d['expected_refs']:
        if i not in got:
            dropped.append(i); continue
        r, x = refs.get(i, {}), got[i]
        rows.append(dict(id=i, source='harvest', **{k: r.get(k, '') for k in ('em', 'tome', 'page', 'pdf_page', 'note', 'series',
                    'vol', 'col', 'band', 'author', 'author_year', 'title', 'status')},
                    verdict=x['verdict'], reader_series=x['series'], reader_volume=x['volume'], reader_column=x['column'],
                    **code(x)))
    got = {x['id']: x for x in d['data']['colonly']}
    for i in d['expected_colonly']:
        if i not in got:
            dropped.append(i); continue
        r, x = col.get(i, {}), got[i]
        rows.append(dict(id=i, source='colonly', **{k: r.get(k, '') for k in ('em', 'page', 'pdf_page', 'note', 'col', 'band')},
                    kind=x['kind'], reader_series=x['series'], reader_volume=x['volume'], reader_author=x['author'],
                    reader_work=x['work'], **code(x)))
    for k, x in enumerate(d['data']['missed'], 1):
        rows.append(dict(id=f"em{d['em']}-p{d['pdf']:03d}-m{k}", source='reader', em=d['em'], pdf_page=d['pdf'], note=x['note'],
                    reader_series=x['series'], reader_volume=x['volume'], reader_column=x['column'], reader_author=x['author'],
                    reader_work=x['work'], printed=x['printed'], **code(x)))
clean = lambda v: str(v).replace('\t', ' ').replace('\n', ' ')
path = os.path.join(HERE, 'ledger', f'claims-{run}.tsv')
with open(path, 'w', encoding='utf-8') as f:
    f.write('\t'.join(OUT) + '\n')
    for r in rows:
        f.write('\t'.join(clean(r.get(k, '')) for k in OUT) + '\n')
print(len(rows), 'rows ->', path, '| dropped by the reader:', len(dropped))
open(os.path.join(HERE, 'working', run, f'dropped-{coder}.txt'), 'w').write('\n'.join(dropped) + '\n')
