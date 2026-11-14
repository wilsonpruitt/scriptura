#!/usr/bin/env python3
"""Stage A for the PG: place de Lubac's PG references and check them against the page. No tokens.

    python3 -I studies/sensus/scripts/pg_refs_check.py

The resolver (pl_locator.py) knew only PL columns, so the 322 PG references in ledger/refs.tsv stopped at
"PG tome, column". Now that whole PG volumes are read (Kraken Greek, ~/patrologia/raw/kraken/) and their
running heads mapped to columns (~/patrologia/data/pg-heads/NNN.tsv), each reference in a mapped volume is:

  placed    the PDF page whose head carries the column (colL or colL+1), with the work title from the
            head (or the nearest head of the same side that read);
  quoted    where de Lubac prints the passage (working/quotes.tsv; always Latin for the PG, often
            Rufinus or Jerome), the Latin 3-grams of the quote are looked for on that page and its two
            neighbours (Tesseract lat; PG 12-14 already OCRed in sources/editions/ocr/, other pages
            OCRed here on demand);
  termed    the sense terms the claim names (claims-all.tsv `senses`) looked for on the same pages,
            Greek (Kraken) and Latin (Tesseract).

Writes ledger/pg-refs-check.tsv (local ledger, never pushed). Columns are OCR evidence: "col. ≈N".
"""
import csv, glob, importlib.util, os, re, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAT = Path.home() / 'patrologia'
HEADS = PAT / 'data/pg-heads'
KRAKEN = PAT / 'raw/kraken'
OCR = ROOT / 'sources/editions/ocr'
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_quotes import norm as lnorm, grams          # Latin normalisation shared with the PL check
import census_gr                                        # Greek normalisation
import pg_latin_ocr

_sp = importlib.util.spec_from_file_location('pgh', PAT / 'htr/pg-heads.py')
pgh = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(pgh)

rd = lambda f: list(csv.DictReader(open(f, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))

TERMS = {   # claim sense -> (Latin stems, Greek stems)
    'allegory': (('allegor',), ('αλληγορ',)),
    'anagogy': (('anagog',), ('αναγωγ',)),
    'tropology': (('tropolog', 'moral'), ('τροπολογ', 'ηθικ')),
    'spiritual': (('spiritual', 'spiritalis', 'spiritaliter', 'mystic', 'myster'), ('πνευματικ', 'μυστικ', 'νοητ', 'θεωρ')),
    'letter': (('litter', 'histor', 'carnal', 'corporal'), ('ιστορ', 'ρητ', 'γραμμ', 'λεξ', 'σωματικ')),
}


def parts(vol):
    """Head tables for a PG tome number: '7' -> ['007-1'], '16' -> ['016-1', '016-2', '016-3']."""
    v = f'{int(vol):03d}'
    return sorted(os.path.basename(f)[:-4] for f in glob.glob(str(HEADS / f'{v}*.tsv')))


_T = {}
def table(part):
    if part not in _T:
        rows = [l.split('\t') for l in open(HEADS / f'{part}.tsv', encoding='utf-8').read().splitlines()[1:]]
        _T[part] = {int(r[0]): r for r in rows}
    return _T[part]


def place(vol, col):
    """(part, page, status) for a column, or None. A page holds colL and colL+1."""
    for part in parts(vol):
        hits = [(r[3] != 'read', p) for p, r in table(part).items() if r[1] and int(r[1]) in (col, col - 1)]
        if hits:
            st, p = min(hits)
            return part, p, table(part)[p][3]
    return None


def kraken_dir(part):
    for w in (f'pg-{part}', f'origen-pg{part}'):
        if (KRAKEN / w / 'text').is_dir():
            return w
    return None


def latin(part, p):
    f = OCR / f'pg{part}' / f'p-{p:04d}.txt'
    return f.read_text(encoding='utf-8', errors='replace') if f.exists() else ''


def greek(part, p):
    w = kraken_dir(part)
    f = KRAKEN / w / 'text' / f'p-{p:04d}.txt' if w else None
    return census_gr.norm(f.read_text(encoding='utf-8', errors='replace')) if f and f.exists() else ''


def main():
    refs = [r for r in rd(ROOT / 'ledger/refs.tsv') if r['series'] == 'PG' and r['vol'].isdigit() and r['col'].isdigit()]
    quotes = {q['id']: q['quote'] for q in rd(ROOT / 'working/quotes.tsv')}
    senses = {c['id']: c['senses'] for c in rd(ROOT / 'ledger/claims-all.tsv') if c['series'] == 'PG'}
    placed = {}
    for r in refs:
        loc = place(r['vol'], int(r['col']))
        if loc and kraken_dir(loc[0]):
            placed[r['id']] = loc
    # Latin OCR for the pages (and neighbours) not yet read
    jobs = set()
    for part, p, _ in placed.values():
        pdf = pgh.pdf_for(part)
        for q in (p - 1, p, p + 1):
            if q > 0 and not (OCR / f'pg{part}' / f'p-{q:04d}.txt').exists():
                jobs.add((part, q, pdf, str(OCR / f'pg{part}'), 'lat', '300'))
    for j in jobs:
        os.makedirs(j[3], exist_ok=True)
    if jobs:
        print(f'OCR {len(jobs)} pages ...', flush=True)
        with ProcessPoolExecutor(6) as ex:
            list(ex.map(pg_latin_ocr.page, sorted(jobs)))
    out = []
    for r in refs:
        loc = placed.get(r['id'])
        row = {'id': r['id'], 'vol': r['vol'], 'col': r['col'], 'part': '', 'page': '', 'page_status': '',
               'head': '', 'quote': '', 'quote_score': '', 'senses': senses.get(r['id'], ''), 'terms_found': '',
               'check': 'unmapped'}
        if loc:
            part, p, st = loc
            col, head = census_gr.locate(f'pg-{part}', f'p-{p:04d}')
            lat = ' '.join(latin(part, q) for q in (p - 1, p, p + 1))
            grk = ' '.join(greek(part, q) for q in (p - 1, p, p + 1))
            lw = lnorm(lat)
            row.update(part=part, page=p, page_status=st, head=head[:90], check='placed')
            q = quotes.get(r['id'])
            if q and re.search(r"\b(les|des|nous|il|une|ces|mots|faut|choses)\b|c’est|l’", q):
                row.update(quote=q[:80], check='quote-french')   # his French rendering: no Latin n-grams to match
            elif q:
                qg = grams(lnorm(re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', q)))
                sc = len(qg & grams(lw)) / len(qg) if qg else 0
                row.update(quote=q[:80], quote_score=f'{sc:.2f}', check='quote-here' if sc >= .5 else 'quote-weak' if sc >= .2 else 'quote-absent')
            found = []
            lj = ' '.join(lw)
            for s in re.split(r'[^a-z]+', row['senses']):
                if s in TERMS:
                    la, gr = TERMS[s]
                    hit = [t for t in la if t in lj] + [t for t in gr if t in grk]
                    found.append(f'{s}:{"+".join(hit) if hit else "-"}')
            row['terms_found'] = ' '.join(found)
        out.append(row)
    f = ROOT / 'ledger/pg-refs-check.tsv'
    with open(f, 'w', encoding='utf-8', newline='') as o:
        w = csv.DictWriter(o, fieldnames=list(out[0]), delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\')
        w.writeheader(); w.writerows(out)
    import collections
    print(f'{len(out)} PG refs -> {f.relative_to(ROOT)}')
    print(' ', dict(collections.Counter(x['check'] for x in out)))
    tf = [x for x in out if x['terms_found']]
    print(f'  claims naming a sense, placed: {len(tf)}; with every named sense found on the page: '
          f'{sum("-" not in x["terms_found"].split(":")[-1] and ":-" not in x["terms_found"] for x in tf)}')


if __name__ == '__main__':
    main()
