#!/usr/bin/env python3
"""Tesseract OCR of Migne's PG 12-14 (Latin Origen) for the sensus census. No tokens.

  python3 -I studies/sensus/scripts/pg_latin_ocr.py [012 013 014]
  python3 -I studies/sensus/scripts/pg_latin_ocr.py --pdf FILE.pdf --out DIR [--lang lat] [--dpi 400]

Per page: pdftoppm 300 dpi grey -> tesseract lat+grc --psm 3 -> sources/editions/ocr/pgNNN/p-NNNN.txt.
Resumable (a page with a .txt is skipped); the PNG is deleted after each page. Post-processing (Latin
line filter, dehyphenation, ae-rules, lexicon, PatroLLM triage) is a separate step.
"""
import os, subprocess, sys, tempfile
from concurrent.futures import ProcessPoolExecutor

ED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sources', 'editions')

def page(args):
    vol, n = args[:2]
    pdf, outdir, lang, dpi = args[2:] if len(args) > 2 else (os.path.join(ED, f'pg{vol}.pdf'), os.path.join(ED, 'ocr', f'pg{vol}'), 'lat+grc', '300')
    out = os.path.join(outdir, f'p-{n:04d}')
    if os.path.exists(out + '.txt'):
        return 0
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, 'p')
        subprocess.run(['pdftoppm', '-f', str(n), '-l', str(n), '-r', dpi, '-gray', '-png', '-singlefile',
                        pdf, png], check=True, capture_output=True)
        subprocess.run(['tesseract', png + '.png', out + '.part', '-l', lang, '--psm', '3'],
                       check=True, capture_output=True, env=dict(os.environ, OMP_THREAD_LIMIT='1'))
    os.replace(out + '.part.txt', out + '.txt')
    return 1

def pages(vol, pdf=None):
    r = subprocess.run(['pdfinfo', pdf or os.path.join(ED, f'pg{vol}.pdf')], capture_output=True, text=True)
    return int(next(l.split()[-1] for l in r.stdout.splitlines() if l.startswith('Pages')))

if __name__ == '__main__':
    a = sys.argv[1:]
    jobs = []
    if '--pdf' in a:
        g = lambda k, d=None: a[a.index(k) + 1] if k in a else d
        pdf, outdir = os.path.abspath(g('--pdf')), os.path.abspath(g('--out'))
        os.makedirs(outdir, exist_ok=True)
        jobs = [('x', n, pdf, outdir, g('--lang', 'lat'), g('--dpi', '400')) for n in range(1, pages(None, pdf) + 1)]
    else:
        for v in a or ['012', '013', '014']:
            os.makedirs(os.path.join(ED, 'ocr', f'pg{v}'), exist_ok=True)
            jobs += [(v, n) for n in range(1, pages(v) + 1)]
    done = 0
    with ProcessPoolExecutor(6) as ex:
        for k, r in enumerate(ex.map(page, jobs, chunksize=4), 1):
            done += r
            if k % 100 == 0:
                print(f'{k}/{len(jobs)} pages ({done} new)', flush=True)
    print(f'done: {len(jobs)} pages, {done} new')
