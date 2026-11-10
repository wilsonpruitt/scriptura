#!/usr/bin/env python3
"""Build the Vulgate -> KJV verse crosswalk from texts already on disk (no tokens).

  python3 -I tools/build_crosswalk.py

Vulgate side: the Douay-Rheims (Challoner), whose numbering is the Clementine Vulgate's verse for
verse (checked: chapter and verse counts identical in all 78 books), ~/douay-glossa/raw/DRC.json.
English side: the KJV, ~/kjv-wesley/web/data/kjv/, except Matthew and Mark, where that dataset is
damaged (three verses dropped and renumbered in each), so the WEB from ~/fons/web/ stands in (same
numbering as the KJV).

Method: per book, a banded monotone alignment of the two English texts on content-word overlap,
with moves 1:1, 1:2 (one Vulgate verse = two English), 2:1, and skips (a verse with no partner:
the Greek additions to Daniel and Esther, psalm titles counted as verses). The alignment, not a
hand table, finds every shift; the known seams are then asserted (CHECKS) so a bad alignment
fails loudly.

Writes ~/scriptura/data/crosswalk-vulg-kjv.tsv:
  vulg   OSIS key in Vulgate numbering (book codes are OSIS: 1Sam = I Regum, Ezra = I Esdrae)
  kjv    OSIS key in KJV numbering, or a two-verse range for a 1:2, or '' for none
  rel    same | moved | split | merge | title (a psalm title the Vulgate counts as a verse) |
         vulg-only | kjv-only
  score  alignment similarity (0-1); low scores are where to look first
"""
import collections, json, math, os, re, sys

H = os.path.expanduser('~')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'crosswalk-vulg-kjv.tsv')

# Douay book name -> (OSIS code, kjv-wesley slug or None for Vulgate-only)
BOOKS = [('Genesis','Gen','genesis'),('Exodus','Exod','exodus'),('Leviticus','Lev','leviticus'),('Numbers','Num','numbers'),
 ('Deuteronomy','Deut','deuteronomy'),('Joshua','Josh','joshua'),('Judges','Judg','judges'),('Ruth','Ruth','ruth'),
 ('I Samuel','1Sam','1samuel'),('II Samuel','2Sam','2samuel'),('I Kings','1Kgs','1kings'),('II Kings','2Kgs','2kings'),
 ('I Chronicles','1Chr','1chronicles'),('II Chronicles','2Chr','2chronicles'),('Ezra','Ezra','ezra'),('Nehemiah','Neh','nehemiah'),
 ('Tobit','Tob',None),('Judith','Jdt',None),('Esther','Esth','esther'),('Job','Job','job'),('Psalms','Ps','psalms'),
 ('Proverbs','Prov','proverbs'),('Ecclesiastes','Eccl','ecclesiastes'),('Song of Solomon','Song','songofsolomon'),
 ('Wisdom','Wis',None),('Sirach','Sir',None),('Isaiah','Isa','isaiah'),('Jeremiah','Jer','jeremiah'),
 ('Lamentations','Lam','lamentations'),('Baruch','Bar',None),('Ezekiel','Ezek','ezekiel'),('Daniel','Dan','daniel'),
 ('Hosea','Hos','hosea'),('Joel','Joel','joel'),('Amos','Amos','amos'),('Obadiah','Obad','obadiah'),('Jonah','Jonah','jonah'),
 ('Micah','Mic','micah'),('Nahum','Nah','nahum'),('Habakkuk','Hab','habakkuk'),('Zephaniah','Zeph','zephaniah'),
 ('Haggai','Hag','haggai'),('Zechariah','Zech','zechariah'),('Malachi','Mal','malachi'),('I Maccabees','1Macc',None),
 ('II Maccabees','2Macc',None),('Matthew','Matt','matthew'),('Mark','Mark','mark'),('Luke','Luke','luke'),('John','John','john'),
 ('Acts','Acts','acts'),('Romans','Rom','romans'),('I Corinthians','1Cor','1corinthians'),('II Corinthians','2Cor','2corinthians'),
 ('Galatians','Gal','galatians'),('Ephesians','Eph','ephesians'),('Philippians','Phil','philippians'),('Colossians','Col','colossians'),
 ('I Thessalonians','1Thess','1thessalonians'),('II Thessalonians','2Thess','2thessalonians'),('I Timothy','1Tim','1timothy'),
 ('II Timothy','2Tim','2timothy'),('Titus','Titus','titus'),('Philemon','Phlm','philemon'),('Hebrews','Heb','hebrews'),
 ('James','Jas','james'),('I Peter','1Pet','1peter'),('II Peter','2Pet','2peter'),('I John','1John','1john'),
 ('II John','2John','2john'),('III John','3John','3john'),('Jude','Jude','jude'),('Revelation of John','Rev','revelation'),
 ('Prayer of Manasses','PrMan',None),('I Esdras','1Esd',None),('II Esdras','2Esd',None),('Additional Psalm','AddPs',None),
 ('Laodiceans','EpLao',None)]
WEB_FOR = {'matthew': 'matthew', 'mark': 'mark'}   # kjv-wesley slug -> fons slug

STOP = set('the and of to in that he his him for unto is was be not they them with shall all thou thy thee ye you i me my '
           'it as which a an are but this by from have their will were who upon when then so said there or what at out '
           'up into had hath also come came let no do did one even before against these those may our us we on over her '
           'she said saith god lord'.split())
def toks(s):
    w = re.findall(r"[a-z]+", s.lower())
    return {x[:6] for x in w if len(x) > 2 and x not in STOP}
def sim(a, b):
    return len(a & b) / math.sqrt(len(a) * len(b)) if a and b else 0.0

def load_drc():
    d = json.load(open(os.path.join(H, 'douay-glossa/raw/DRC.json'), encoding='utf-8'))
    return {b['name']: [(c['chapter'], v['verse'], v['text']) for c in b['chapters'] for v in c['verses']] for b in d['books']}
def load_eng(slug):
    if slug in WEB_FOR:
        f = os.path.join(H, 'fons/web', WEB_FOR[slug]); out = []
        for n in sorted(int(x[:-5]) for x in os.listdir(f) if x[:-5].isdigit()):
            out += [(n, v['v'], v['t']) for v in json.load(open(os.path.join(f, f'{n}.json'), encoding='utf-8'))['verses']]
        return out
    d = json.load(open(os.path.join(H, 'kjv-wesley/web/data/kjv', slug + '.json'), encoding='utf-8'))
    return [(c['chapter'], v['verse'], v['text']) for c in d['chapters'] for v in c['verses']]

def align(A, B, band=80):
    """A, B: lists of token sets. Returns list of (ai list, bj list, score)."""
    n, m = len(A), len(B)
    NEG = -1e9
    best = {(0, 0): (0.0, None)}
    GAP, PAIR, SPLIT = -0.12, 0.22, 0.30
    def get(i, j):
        return best.get((i, j), (NEG, None))[0]
    for i in range(n + 1):
        c = int(i * m / n) if n else 0
        for j in range(max(0, c - band), min(m, c + band) + 1):
            if i == 0 and j == 0:
                continue
            cands = []
            if i and j:
                s = sim(A[i-1], B[j-1]); cands.append((get(i-1, j-1) + s - PAIR, (1, 1, s)))
            if i and j >= 2:
                s = sim(A[i-1], B[j-2] | B[j-1]); cands.append((get(i-1, j-2) + s - SPLIT, (1, 2, s)))
            if i >= 2 and j:
                s = sim(A[i-2] | A[i-1], B[j-1]); cands.append((get(i-2, j-1) + s - SPLIT, (2, 1, s)))
            if i:
                cands.append((get(i-1, j) + GAP, (1, 0, 0.0)))
            if j:
                cands.append((get(i, j-1) + GAP, (0, 1, 0.0)))
            sc, mv = max(cands, key=lambda x: x[0])
            if sc > NEG / 2:
                best[(i, j)] = (sc, mv)
    out, i, j = [], n, m
    while i or j:
        di, dj, s = best[(i, j)][1]
        out.append((list(range(i - di, i)), list(range(j - dj, j)), s)); i -= di; j -= dj
    return out[::-1]

def main():
    drc = load_drc()
    rows, stats = [], collections.Counter()
    for name, code, slug in BOOKS:
        V = drc[name]
        if slug is None:
            for c, v, _ in V:
                rows.append((f'{code}.{c}.{v}', '', 'vulg-only', '')); stats['vulg-only'] += 1
            continue
        E = load_eng(slug)
        TV, TE = [toks(t) for *_, t in V], [toks(t) for *_, t in E]
        steps = align(TV, TE)
        # second pass: the Vulgate sometimes swaps two verses (Matt 5:4-5, 23:13-14, Phil 1:16-17).
        # A monotone alignment leaves one side unmatched on each side of the crossing; pair an
        # unmatched Vulgate verse with an unmatched English verse within 3 steps if their texts agree.
        lone_v = [k for k, (ai, bj, _) in enumerate(steps) if ai and not bj]
        lone_e = [k for k, (ai, bj, _) in enumerate(steps) if bj and not ai]
        used = set()
        for kv in lone_v:
            for ke in lone_e:
                if ke in used or abs(ke - kv) > 3:
                    continue
                sc = sim(TV[steps[kv][0][0]], TE[steps[ke][1][0]])
                if sc >= (0.2 if abs(ke - kv) <= 2 else 0.3):
                    steps[kv] = (steps[kv][0], steps[ke][1], sc); steps[ke] = ([], [], 0.0); used.add(ke); break
        for ai, bj, s in steps:
            if not ai and not bj:
                continue
            vk = [f'{code}.{V[a][0]}.{V[a][1]}' for a in ai]
            ek = [f'{code}.{E[b][0]}.{E[b][1]}' for b in bj]
            if not ek:
                rel = 'vulg-only'; rows += [(k, '', rel, '') for k in vk]
            elif not vk:
                rel = 'kjv-only'; rows += [('', k, rel, '') for k in ek]
            elif len(vk) == 1 and len(ek) == 1:
                rel = 'same' if vk[0] == ek[0] else 'moved'; rows.append((vk[0], ek[0], rel, f'{s:.2f}'))
            elif len(vk) == 1:
                rel = 'split'; rows.append((vk[0], f'{ek[0]}-{ek[1]}', rel, f'{s:.2f}'))
            else:
                rel = 'merge'; rows += [(k, ek[0], rel, f'{s:.2f}') for k in vk]
            stats[rel] += max(len(vk), 1) if rel != 'kjv-only' else len(ek)
    # Psalm titles: the KJV dataset folds a psalm's title into verse 1, so the Vulgate's title
    # verses align as a merge (or a skip) onto KJV v.1. In KJV numbering a title is not a verse:
    # every Vulgate verse before the last one that lands on KJV Ps.N.1 is a title.
    by = collections.defaultdict(list)
    for k, r in enumerate(rows):
        if r[0].startswith('Ps.') and r[0].split('.')[2] in ('1', '2', '3'):
            by[r[0].split('.')[1]].append(k)
    for ch, ks in by.items():
        hits = [k for k in ks if rows[k][1].endswith('.1') and rows[k][1].count('.') == 2]
        lead = [k for k in ks if k < max(hits)] if hits else []
        for k in lead:
            if rows[k][2] in ('merge', 'vulg-only'):
                rows[k] = (rows[k][0], '', 'title', '')
        for k in hits[-1:]:
            if rows[k][2] == 'merge':
                rows[k] = (rows[k][0], rows[k][1], 'same' if rows[k][0] == rows[k][1] else 'moved', rows[k][3])
    stats = collections.Counter(r[2] for r in rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vulg\tkjv\trel\tscore\n')
        for r in rows:
            f.write('\t'.join(r) + '\n')
    print(dict(stats), '->', OUT)
    # known seams: a wrong alignment fails here
    m = {r[0]: r[1] for r in rows if r[0]}
    CHECKS = {'Ps.22.1': 'Ps.23.1', 'Ps.50.3': 'Ps.51.1', 'Ps.9.22': 'Ps.10.1', 'Ps.118.1': 'Ps.119.1',
              'Ps.147.1': 'Ps.147.12', 'Dan.3.91': 'Dan.3.24', 'Ps.3.1': '', 'Ps.3.2': 'Ps.3.1', 'Ps.50.2': '', 'Ps.17.2': 'Ps.18.1', 'Dan.3.24': '', 
              'Job.40.20': 'Job.41.1', 'Gen.1.1': 'Gen.1.1', 'John.3.16': 'John.3.16', 'Matt.5.3': 'Matt.5.3',
              'Mal.4.1': 'Mal.4.1', 'Esth.11.2': '', 'Matt.5.4': 'Matt.5.5', 'Matt.5.5': 'Matt.5.4',
              'John.6.52': 'John.6.51', 'Mark.8.39': 'Mark.9.1', '3John.1.15': ''}
    bad = {k: (m.get(k), v) for k, v in CHECKS.items() if (m.get(k) or '').split('-')[0] != v}
    print('checks:', 'all pass' if not bad else bad)
    return 1 if bad else 0

if __name__ == '__main__':
    sys.exit(main())
