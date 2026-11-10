#!/usr/bin/env python3
"""Normalize a free-text author name (as the reader wrote it) to one heading.

Headings are the Corpus Corporum author headings the PL locator uses ("Augustinus Hipponensis"),
so harvested and reader-coded rows count together. Authors outside the PL index get a Latin
heading from data/author-aliases.tsv, with a death year marked `hand` (from general knowledge,
to be checked, like the CCL list in harvest_refs.py).

  normalize(name) -> (heading, year, src)   src: cc | alias | hand | pseudo | unknown | unmatched
"""
import csv, json, os, re, unicodedata
from functools import lru_cache

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.expanduser('~/patrologia/data/cc-pl-index.json')
ALIASES = os.path.join(HERE, 'data', 'author-aliases.tsv')
STOP = {'s', 'st', 'saint', 'sancti', 'sanctus', 'of', 'de', 'the', 'von', 'van', 'di', 'da', 'du', 'le', 'la', 'a', 'ab',
        'venerable', 'venerabilis', 'abbot', 'bishop', 'pope', 'monk', 'master', 'magister', 'abbas', 'episcopus'}

def key(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'[^a-z ]', ' ', s.replace('-', ' '))
    return ' '.join(t for t in s.split() if t not in STOP)

@lru_cache(None)
def tables():
    works = json.load(open(INDEX, encoding='utf-8'))['works']
    heads = {}
    for w in works:
        a = w['author']
        if a and not a.startswith('Auctor incertus'):
            heads[a] = w.get('authorYear') or ''
    bykey = {}
    for a in heads:
        bykey.setdefault(key(a), set()).add(a)
    alias = {}
    if os.path.exists(ALIASES):
        for r in csv.DictReader(open(ALIASES, encoding='utf-8'), delimiter='\t'):
            alias[key(r['alias'])] = (r['heading'], r['year'], r['src'])
    return heads, bykey, alias

def normalize(name):
    heads, bykey, alias = tables()
    raw = (name or '').strip()
    if not raw or key(raw) in ('', 'anonymous', 'anon', 'unknown', 'auctor incertus', 'anonymus'):
        return ('', '', 'unknown')
    pseudo = bool(re.match(r'^\s*(ps\.?|pseudo)[\s-]', raw, re.I)) or 'attrib' in raw.lower() or raw.rstrip().endswith('?')
    base = re.sub(r'^\s*(ps\.?|pseudo)[\s-]+', '', raw, flags=re.I)
    base = re.sub(r'\((attrib|attr|ps)[^)]*\)', '', base, flags=re.I).strip(' ?')
    k = key(base)
    hit = None
    if base in heads:
        hit = (base, str(heads[base]), 'cc')
    elif k in alias:
        hit = alias[k]
    elif k in bykey and len(bykey[k]) == 1:
        h = next(iter(bykey[k])); hit = (h, str(heads[h]), 'cc')
    else:
        # every word of the reader's name inside exactly one heading ("Rabanus" -> "Rabanus Maurus")
        toks = set(k.split())
        cands = [h for kk, hs in bykey.items() for h in hs if toks and toks <= set(kk.split())]
        if len(cands) == 1:
            hit = (cands[0], str(heads[cands[0]]), 'cc')
    if not hit:
        return (raw, '', 'unmatched')
    if pseudo:
        return ('Pseudo-' + hit[0], '', 'pseudo')
    return hit

if __name__ == '__main__':
    import sys, collections
    rows = list(csv.DictReader(open(os.path.join(HERE, 'ledger', sys.argv[1]), encoding='utf-8'), delimiter='\t',
                               quoting=csv.QUOTE_NONE))
    c, src = collections.Counter(), collections.Counter()
    for r in rows:
        if r['source'] == 'harvest':
            continue
        h, y, s = normalize(r['reader_author'])
        src[s] += 1
        if s == 'unmatched':
            c[r['reader_author'].strip()] += 1
    print(dict(src)); print(len(c), 'unmatched names')
    for k, v in c.most_common(int(sys.argv[2]) if len(sys.argv) > 2 else 60):
        print(v, k, sep='\t')
