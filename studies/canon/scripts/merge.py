#!/usr/bin/env python3
"""Spine v1: the three streams merged into one row per citation, with broad tags. No tokens.

  python3 -I studies/canon/scripts/merge.py          # -> spine/spine.tsv, spine/tags-summary.tsv
  python3 -I studies/canon/scripts/merge.py sample   # a few rows per tag, for reading

Ruling (Wilson, 2026-11-10): NOTHING IS EXCLUDED. Liturgical use of Scripture is use of Scripture;
the modern line between quoting a verse and praying its words does not hold for these authors.
Instead every row is tagged as broadly as the evidence allows, so that any later study (the
liturgy of the PL and PG among them) filters on tags instead of going back to the text. Tags are
computed, never ruled; a reader rules on tags, not on rows.

A citation:
  - ngram rows that share (work, column, first 6 words of the run) are ONE citation; if they name
    several verses it is a PARALLEL (Ps 109:4 = Heb 5:6 = Heb 7:17);
  - a fuzzy row (pairs >= 4) or an inline row with no ngram citation on that verse within +/-1
    column is a citation of its own.
Parallels are resolved, in order: by Migne's inline citation within +/-1 column (`inline`); by the
fuzzy stream naming exactly one of the candidates with the most pairs there (`context`); else the
verse stays an open set (`open`).

Tags (a row may carry several, ';'-separated):
  liturgical:doxology   a doxology (cui est honor/gloria, gloria et imperium, per omnia secula seculorum)
  liturgical:trinitarian  Father, Son and Holy Spirit named together (patris et filii et spiritus sancti)
  liturgical:invocation the solemn invocation (in nomine sancte et indiuidue trinitatis; in nomine patris et filii)
  liturgical:prayer     the Pater noster, Gloria in excelsis, Sanctus/Benedictus, Agnus Dei
  liturgical:office     the office versicles (Deus in adiutorium meum intende, Domine labia mea aperies ...)
  phrase:in-nomine-domini  'in nomine domini/dei/iesu' outside the solemn invocation (descriptive only)
  genre:liturgical      the work's title is a sacramentary, ordo, office, missal, hymnal, antiphoner...
  genre:sacraments      the work is ON the sacraments (theology of baptism, eucharist ...), not a liturgical book
  genre:diplomatic      charters, diplomas, privileges, donations
  genre:conciliar       councils, canons, decretals
  parallel:<method>     several verses fit the words; method = inline | context | open
  lemma                 the work is a commentary on the book the verse is in (likely the text
                        under comment, not a quotation)
  refrain               the same run 5+ times in the same work
  widespread-uncited    the run is in 25+ works, Migne cites it under 25% of the time, and no
                        liturgical tag applies: famous verses, stock phrases, idioms alike
                        ('a solis ortu usque ad occasum', 'uerbum domini manet in eternum');
                        descriptive, a reader sub-tags it if a study needs to
  chapter-only          an inline citation to a chapter, not a verse
  low-confidence        a fuzzy-only citation at exactly 4 pairs
"""
import collections, csv, importlib.util, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('sp', os.path.join(HERE, 'scripts', 'spine.py'))
sp = importlib.util.module_from_spec(spec); spec.loader.exec_module(sp)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), '..', 'tools'))
from refkey import book  # noqa: E402
OUT = sp.OUT
colnum = lambda c: int(re.match(r'\d+', c).group()) if re.match(r'\d+', c or '') else -9

DOX = re.compile(r'(?:cui|ipsi|ei|illi|quoniam ipsius) (?:est|sit) (?:honor|gloria|imperium|uirtus)|gloria et imperium|honor et gloria|per omnia secula seculorum|in secula seculorum amen|gloria in secula')
TRIN = re.compile(r'patris et filii et spiritus sancti|patri et filio et spiritui sancto|pater et filius et spiritus sanctus')
INVOC = re.compile(r'in nomine (?:sancte|indiuidue|summe)|sancte et indiuidue trinitatis|in nomine patris et filii')
INNOM = re.compile(r'in nomine domini|in nomine dei|in nomine iesu')
PRAYER = re.compile(r'pater noster qui es|sanctificetur nomen tuum|panem nostrum quotidianum|dimitte nobis debita|sanctus sanctus sanctus|gloria in excelsis|benedictus qui uenit|agnus dei qui tollis')
OFFICE = re.compile(r'deus in adiutorium meum intende|domine ad adiuuandum me festina|domine labia mea aperies|adiutorium nostrum in nomine domini|sit nomen domini benedictum|dominus uobiscum|sursum corda|uenite exultemus|benedicamus domino|deo gratias')
G_LIT = re.compile(r'sacramentari|ordo\b|ordines|officium|ecclesiasticis officiis|divinis officiis|officia\b|missal|missae\b|ordo missae|antiphon|breviari(?!um fidei)|hymn|(?<!in )(?<!super )psalteri|liber officialis|lectionar|pontifical|rituale|benedictional|caeremon|liturg', re.I)
G_SAC = re.compile(r'sacrament', re.I)   # works ON the sacraments (theology), tagged apart from liturgical books
G_DIP = re.compile(r'diplom|charta|chartae|privileg|donatio|praecept(um|a) |testament(um|a) |instrument', re.I)
G_CON = re.compile(r'concili|synod|canones|canon(es|um)\b|decret', re.I)
FILL = {'evangelium', 'evangelii', 'euangelium', 'epistolam', 'epistolas', 'epistola', 'epistolae', 'librum', 'libros',
        'libri', 'prophetam', 'prophetas', 'sanctum', 'b', 'beati', 'beatum', 'pauli', 'apostoli', 'ad', 'secundum', 'sancti',
        'divi', 'omnes', 'quosdam', 'aliquot', 'locos', 'loca', 'capita', 'priores', 'duodecim', 'minores', 'quatuor', 'et'}
NOTBOOK = {'regulam', 'regula', 'regulas', 'regum', 'iob'}   # Rule of Benedict is not Kings; 'iob' handled by book()
def commented_book(title):
    """Book a commentary is ON: the first book name after in/super, skipping fillers, tolerating Latin
    case endings (Lucam, Matthaei, Psalmos, Exodum, Genesim, Romanos, Ezechielem, Cantica)."""
    t = re.sub(r'\(.*?\)', ' ', title or '').lower()
    if not re.search(r'commentar|exposit|enarrat|explanat|tractat|homili|postill|gloss|annotat|quaestion|in\s|super\s', t):
        return None
    ws = re.findall(r'[a-z]+', t)
    for i, w in enumerate(ws):
        if w not in ('in', 'super'):
            continue
        num = ''
        for x in ws[i + 1:i + 6]:
            if x in ('i', 'ii', 'iii', 'iv', 'primam', 'secundam', 'priorem', 'posteriorem', 'primum', 'secundum', 'tertium', 'quartum'):
                num = {'i': '1', 'primam': '1', 'priorem': '1', 'primum': '1', 'ii': '2', 'secundam': '2', 'posteriorem': '2',
                       'secundum': '2', 'iii': '3', 'tertium': '3', 'iv': '4', 'quartum': '4'}[x]; continue
            if x in FILL:
                continue
            if x in NOTBOOK:
                return None
            if x.startswith('cantic'):
                return 'Song'
            for cand in (x, x[:-1], x[:-2], x[:-3]):
                if len(cand) >= 3:
                    b = book((num + ' ' if num else '') + cand)
                    if b:
                        return b
            break
    return None

def main():
    meta = sp.meta()
    title = {k: v.get('title', '') for k, v in meta.items()}
    cbook = {k: commented_book(t) for k, t in title.items()}
    # inline
    inl = collections.defaultdict(list)            # (idno, col) -> refs
    inline_rows = []
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-inline.tsv'), encoding='utf-8'), delimiter='\t'):
        if r['exists'] != 'y':
            continue
        c = colnum(r['col'])
        inl[(r['idno'], c)].append(r['vulg'])
        inline_rows.append(r)
    def inline_near(idno, c):
        return [x for k in (c - 1, c, c + 1) for x in inl.get((idno, k), ())]
    # fuzzy, by (idno, col)
    fz = collections.defaultdict(list)
    fuzzy_rows = []
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-fuzzy.tsv'), encoding='utf-8'), delimiter='\t'):
        if int(r['pairs']) >= 4:
            fz[(r['idno'], colnum(r['col']))].append((r['vulg'], int(r['pairs'])))
            fuzzy_rows.append(r)
    # ngram citations
    groups = collections.OrderedDict()
    runcount = collections.Counter(); runworks = collections.defaultdict(set); perwork = collections.Counter()
    for r in csv.DictReader(open(os.path.join(OUT, 'spine-ngram.tsv'), encoding='utf-8'), delimiter='\t'):
        run = ' '.join(r['evidence'].split()[:6])
        key = (r['idno'], r['col'], run)
        g = groups.setdefault(key, {'r': r, 'verses': [], 'words': 0})
        g['verses'].append(r['vulg']); g['words'] = max(g['words'], int(r['run_words']))
    for (idno, col, run), g in groups.items():
        runcount[run] += 1; runworks[run].add(idno); perwork[(idno, run)] += 1
    # Migne's inline rate per run (for idiom-candidate): share of the run's citations with an inline cite
    run_cited = collections.Counter()
    for (idno, col, run), g in groups.items():
        c = colnum(col)
        if any(sp._within(v, x) or sp._near(v, x) for v in g['verses'] for x in inline_near(idno, c)):
            run_cited[run] += 1
    rows, tagc = [], collections.Counter()
    covered = set()                                    # (idno, col, verse) already in a citation

    def tag_common(idno, verses, text, run=None):
        t = []
        if DOX.search(text): t.append('liturgical:doxology')
        if TRIN.search(text): t.append('liturgical:trinitarian')
        if INVOC.search(text): t.append('liturgical:invocation')
        if PRAYER.search(text): t.append('liturgical:prayer')
        if OFFICE.search(text): t.append('liturgical:office')
        if INNOM.search(text) and 'liturgical:invocation' not in t: t.append('phrase:in-nomine-domini')
        ti = title.get(idno, '')
        if G_LIT.search(ti): t.append('genre:liturgical')
        if G_SAC.search(ti) and 'genre:liturgical' not in t: t.append('genre:sacraments')
        if G_DIP.search(ti): t.append('genre:diplomatic')
        if G_CON.search(ti): t.append('genre:conciliar')
        cb = cbook.get(idno)
        if cb and any(v.split('.')[0] == cb for v in verses): t.append('lemma')
        if run:
            if perwork[(idno, run)] >= 5: t.append('refrain')
            if (len(runworks[run]) >= 25 and run_cited[run] / max(runcount[run], 1) < 0.25
                    and not any(x.startswith('liturgical:') for x in t)):
                t.append('widespread-uncited')
        return t

    for (idno, col, run), g in groups.items():
        r = g['r']; c = colnum(col)
        vs = sorted(set(g['verses']))
        streams = ['ngram']; resolved = vs; method = ''
        near_inl = inline_near(idno, c)
        hit_inl = [v for v in vs if any(sp._within(v, x) or sp._near(v, x) for x in near_inl)]
        if hit_inl:
            streams.append('inline')
        tags = []
        if len(vs) > 1:
            if len(hit_inl) == 1:
                resolved, method = hit_inl, 'inline'
            else:
                fzp = {v: p for v, p in fz.get((idno, c), ()) if v in vs}
                if fzp:
                    top = max(fzp.values()); best = [v for v, p in fzp.items() if p == top]
                    if len(best) == 1:
                        resolved, method = best, 'context'
                if not method:
                    method = 'open'
            tags.append(f'parallel:{method}')
        if any(v in vs for v, _ in fz.get((idno, c), ())):
            streams.append('fuzzy')
        tags += tag_common(idno, vs, r['evidence'], run)
        for v in vs:
            for k in (c - 1, c, c + 1):
                covered.add((idno, k, v))
        rows.append([idno, r['vol'], col, r['author'], r['author_year'], '|'.join(resolved), '|'.join(vs) if len(vs) > 1 else '',
                     sp.kjv_of(resolved[0]) if len(resolved) == 1 else '', '+'.join(streams), str(g['words']), ';'.join(tags), r['evidence']])
    for r in fuzzy_rows:
        c = colnum(r['col'])
        if (r['idno'], c, r['vulg']) in covered:
            continue
        covered.add((r['idno'], c, r['vulg']))
        near = inline_near(r['idno'], c)
        streams = ['fuzzy'] + (['inline'] if any(sp._within(r['vulg'], x) or sp._near(r['vulg'], x) for x in near) else [])
        tags = tag_common(r['idno'], [r['vulg']], r['evidence'])
        if int(r['pairs']) == 4 and len(streams) == 1: tags.append('low-confidence')
        rows.append([r['idno'], r['vol'], r['col'], r['author'], r['author_year'], r['vulg'], '', r['kjv'], '+'.join(streams),
                     '', ';'.join(tags), r['evidence']])
    for r in inline_rows:
        c = colnum(r['col']); first = r['vulg'].split('-')[0]
        if r['level'] == 'verse' and (r['idno'], c, first) in covered:
            continue
        covered.add((r['idno'], c, first))
        tags = tag_common(r['idno'], [first], (r['evidence'] or '').lower())
        if r['level'] == 'chapter': tags.append('chapter-only')
        rows.append([r['idno'], r['vol'], r['col'], r['author'], r['author_year'], r['vulg'], '', r['kjv'], 'inline', '',
                     ';'.join(tags), r['evidence']])
    with open(os.path.join(OUT, 'spine.tsv'), 'w', encoding='utf-8') as o:
        o.write('idno\tvol\tcol\tauthor\tauthor_year\tvulg\tparallel_set\tkjv\tstreams\trun_words\ttags\tevidence\n')
        for x in rows:
            o.write('\t'.join(s.replace('\t', ' ') for s in x) + '\n')
            for t in (x[10].split(';') if x[10] else ['(none)']):
                tagc[t] += 1
    sc = collections.Counter(x[8] for x in rows)
    with open(os.path.join(OUT, 'tags-summary.tsv'), 'w', encoding='utf-8') as o:
        o.write('tag\trows\n')
        for t, n in tagc.most_common():
            o.write(f'{t}\t{n}\n')
    print(f'spine v1: {len(rows)} citations -> {os.path.join(OUT, "spine.tsv")}')
    print('by streams:', ', '.join(f'{k} {v}' for k, v in sc.most_common()))
    print('tags:'); [print(f'  {t:<26}{n:>8}') for t, n in tagc.most_common()]

def sample():
    import random
    random.seed(5)
    by = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(OUT, 'spine.tsv'), encoding='utf-8'), delimiter='\t'):
        for t in (r['tags'].split(';') if r['tags'] else []):
            by[t].append(r)
    for t in sorted(by):
        print(f'\n== {t} ({len(by[t])})')
        for r in random.sample(by[t], min(4, len(by[t]))):
            print(f"   {r['author'][:22]:<22} {r['vulg']:<16} {r['parallel_set'][:30]:<30} | {r['evidence'][:70]}")

if __name__ == '__main__':
    sample() if sys.argv[1:] == ['sample'] else main()
