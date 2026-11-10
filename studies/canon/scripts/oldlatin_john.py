#!/usr/bin/env python3
"""Experiment: does an Old Latin index close the early-Father gap? John, or with `nt` the whole NT
(Sabatier vol. III, + Iohannes for John) (Vetus Latina
Iohannes, 37 MSS, CC BY 4.0, IGNTP). No tokens.

  python3 -I studies/canon/scripts/oldlatin_john.py        # John: Clementine vs + Iohannes
  python3 -I studies/canon/scripts/oldlatin_john.py nt     # NT: Clementine vs + Sabatier vs + Sabatier + Iohannes

Index A = the fuzzy stream's Clementine stem pairs. Index B = A plus the stem pairs of every Old
Latin manuscript's reading of each verse of John, rarity counted over distinct verse keys. Both are
scanned over the works of authors d. <= 600 in verse/mixed-practice volumes; the measure is recall on
Migne's inline verse citations of John (+/-1 col, +/-2 verses) and rows per index.
"""
import collections, csv, glob, html, importlib.util, os, re
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('sp', os.path.join(HERE, 'scripts', 'spine.py'))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
VL = os.path.join(HERE, 'sources', 'oldlatin', 'iohannes')

def vl_verses():
    out = collections.defaultdict(list)   # John.c.v -> [word lists]
    for f in glob.glob(os.path.join(VL, '*.xml')):
        x = open(f, encoding='utf-8').read()
        for m in re.finditer(r'<ab n="B04K(\d+)V(\d+)">(.*?)</ab>', x, re.S):
            c, v = int(m.group(1)), int(m.group(2))
            if c == 0 or v == 0:
                continue
            ws = [html.unescape(re.sub(r'<[^>]+>', '', w)) for w in re.findall(r'<w[^>]*>(.*?)</w>', m.group(3), re.S)]
            out[f'John.{c}.{v}'].append(sp.norm_words(' '.join(ws)))
    return out

import sys
NTMODE = sys.argv[1:] == ['nt']
PREFIX = None
def sabatier_verses(name='sabatier-v3.tsv'):
    out = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(HERE, 'sources', 'oldlatin', name), encoding='utf-8'), delimiter='\t'):
        out[r['key']].append(r['text'].split())
    return out

IDX = None
def build(with_vl):
    global IDX
    vs = sp.vulgate()
    freq = collections.Counter(w[:sp.STEM] for _, ws in vs for w in ws)
    stop = {w for w, _ in freq.most_common(sp.STOP)}
    pairs = collections.defaultdict(set)
    def add(key, ws):
        st = [w[:sp.STEM] for w in ws if len(w) > 2 and w[:sp.STEM] not in stop]
        for i in range(len(st)):
            for j in range(i + 1, min(i + 1 + sp.GAP, len(st))):
                if st[i] != st[j]:
                    pairs[(st[i], st[j])].add(key)
    for k, ws in vs:
        add(k, ws)
    extra = []
    if with_vl in (True, 'sab+vl'):
        extra.append(vl_verses())
    if with_vl in ('sab', 'sab+vl', 'all'):
        extra.append(sabatier_verses()); extra.append(sabatier_verses('sabatier-v3-djvu.tsv'))
    if with_vl == 'all':
        extra.append(vl_verses())
        extra.append(sabatier_verses('sabatier-notes-v3.tsv')); extra.append(sabatier_verses('sabatier-notes-v3-djvu.tsv'))
    for d in extra:
        for k, readings in d.items():
            for ws in readings:
                add(k, ws)
    IDX = ({p: tuple(s) for p, s in pairs.items() if len(s) <= sp.FRARE}, stop)

def scan(args):
    f, with_vl = args
    if IDX is None:
        pass
    pairs, stop = IDX[with_vl]
    body = sp.body_text(f)
    words, cols, cur = [], [], ''
    for k, seg in enumerate(re.split(r'\x01([^\x01]*)\x01', body)):
        if k % 2:
            cur = seg; continue
        w = [x[:sp.STEM] for x in sp.norm_words(seg) if len(x) > 2 and x[:sp.STEM] not in stop]
        words += w; cols += [cur] * len(w)
    hits = collections.defaultdict(list)
    for i in range(len(words)):
        for j in range(i + 1, min(i + 1 + sp.GAP, len(words))):
            for key in pairs.get((words[i], words[j]), ()):
                if key.split('.')[0] in WANT:
                    hits[key].append((i, (words[i], words[j])))
    rows = []
    for key, hs in hits.items():
        hs.sort(); k = 0
        while k < len(hs):
            m = k
            while m + 1 < len(hs) and hs[m + 1][0] - hs[k][0] <= sp.SPAN:
                m += 1
            d = {p for _, p in hs[k:m + 1]}
            if len(d) >= sp.MINPAIRS:
                rows.append((cols[hs[k][0]], key, len(d))); k = m + 1
            else:
                k += 1
    return os.path.basename(f)[:-4], rows

NTB = {'Matt', 'Mark', 'Luke', 'John', 'Acts', 'Rom', '1Cor', '2Cor', 'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess',
       '1Tim', '2Tim', 'Titus', 'Phlm', 'Heb', 'Jas', '1Pet', '2Pet', '1John', '2John', '3John', 'Jude', 'Rev'}
WANT = NTB if NTMODE else {'John'}
FLAGS = (False, 'sab+vl', 'all') if NTMODE else (False, True)
NAMES = {False: 'Clementine', True: 'Clementine + Old Latin', 'sab': '+ Sabatier', 'sab+vl': '+ Sabatier + Iohannes', 'all': '+ Sab + Ioh + notes'}
def init():
    global IDX
    d = {}
    for fl in FLAGS:
        build(fl); d[fl] = IDX
    IDX = d

if __name__ == '__main__':
    colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9
    meta = sp.meta()
    prac = {r['vol']: r['practice'] for r in csv.DictReader(open(os.path.join(sp.OUT, 'volume-practice.tsv'), encoding='utf-8'), delimiter='\t')}
    def early(idno):
        w = meta.get(idno, {})
        try:
            y = int(w.get('author_year', ''))
        except ValueError:
            return None
        return ('<=400' if y <= 400 else '401-600') if 0 < y <= 600 and prac.get(w.get('volume')) in ('verse', 'mixed') else None
    files = [f for f in sorted(glob.glob(os.path.join(sp.TEI, '*.xml'))) if early(os.path.basename(f)[:-4])]
    inl = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(sp.OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['vulg'].split('.')[0] in WANT and r['level'] == 'verse' and r['exists'] == 'y' and early(r['idno']):
            inl[r['idno']].append((colnum(r['col']), r['vulg']))
    print(len(files), 'early works;', sum(map(len, inl.values())), 'inline verse citations of', 'the NT' if NTMODE else 'John')
    res = {}
    with ProcessPoolExecutor(6, initializer=init) as ex:
        for flag in FLAGS:
            res[flag] = dict(ex.map(scan, [(f, flag) for f in files], chunksize=4))
    for flag, name in ((f, NAMES[f]) for f in FLAGS):
        for minp in (3, 4):
            tot = collections.Counter(); hit = collections.Counter(); nrows = 0; onl = 0
            for idno, rows in res[flag].items():
                rows = [r for r in rows if r[2] >= minp]; nrows += len(rows)
                by = collections.defaultdict(list)
                for c, k, _ in rows:
                    by[colnum(c)].append(k)
                b = early(idno)
                for c, ref in inl.get(idno, ()):
                    tot[b] += 1
                    hit[b] += any(sp._within(k, ref) or sp._near(k, ref) for x in (c - 1, c, c + 1) for k in by.get(x, ()))
                for c, k, _ in rows:
                    onl += any(sp._within(k, ref) or sp._near(k, ref) for cc, ref in inl.get(idno, ()) if abs(cc - colnum(c)) <= 1)
            print(f'{name:<24} pairs>={minp}: recall <=400 {hit["<=400"]}/{tot["<=400"]} ({100*hit["<=400"]/max(tot["<=400"],1):.1f}%), '
                  f'401-600 {hit["401-600"]}/{tot["401-600"]} ({100*hit["401-600"]/max(tot["401-600"],1):.1f}%); rows {nrows}, on an inline cite {100*onl/max(nrows,1):.0f}%')
