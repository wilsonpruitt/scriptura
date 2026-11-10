#!/usr/bin/env python3
"""One normalizer for every verse-key form in the Scriptura layer registry (LAYERS.md section 4).

  from refkey import parse, to_kjv
  parse('III Reg. 4, 21', scheme='vulg')  -> Ref(osis='1Kgs.4.21', scheme='vulg')
  parse('Esther 1:1')                     -> Ref(osis='Esth.1.1', scheme='kjv')
  to_kjv('Ps.22.1')                       -> ['Ps.23.1']

  python3 -I tools/refkey.py              # self-test on samples from every layer

Output is the Wroot data-repository standard (Catena lib/osis.ts; reception-corpus src/osis.py):
  Ps.110.1 · Ps.110 · Ps.45.6-Ps.45.7 · Exod.2.8-Exod.3.3 · Exod.12-Exod.14

Accepted inputs: OSIS any case (bereshit's gen.1.1), OSIS short ranges (Rev.4.6-8), English names
and singular Psalm (Talmai, Brass, Loci, Annales, Voces), SBL abbreviations (Liber generationis),
eBible codes incl. PHI and JAM (Named in Acts), USFM, slugs (kjv-wesley 1samuel, fons 1-samuel,
topographia), Douay-Glossa's Latin slugs (liber-iii-regum), Latin citation abbreviations as Migne
and de Lubac print them (III Reg., Psal., Matth., Eccli.), and the common French ones.

Versification is not guessed. `scheme` is what the caller says the source uses ('kjv' default,
'vulg' for Migne, Douay, de Lubac, the Vulgate). A Latin "Reg." book name implies the Vulgate's
four Kingdoms books and is mapped (I-II Reg. = 1-2Sam, III-IV Reg. = 1-2Kgs) whatever the scheme.
to_kjv() converts a Vulgate-numbered key through data/crosswalk-vulg-kjv.tsv.
"""
import csv, os, re, unicodedata
from functools import lru_cache
from typing import NamedTuple, Optional

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# OSIS code: aliases (matched after lowercasing, stripping accents, dots and spaces)
_B = {
 'Gen': 'gen genesis gn ge genese',
 'Exod': 'exod exodus ex exo exode exodi',
 'Lev': 'lev leviticus lv le levitique',
 'Num': 'num numbers numeri nb nm nu nombres nombr',
 'Deut': 'deut deuteronomy deuteronomium dt deu deuteronome',
 'Josh': 'josh joshua jos josue ios',
 'Judg': 'judg judges judic iudic jdg jg jug juges jdc',
 'Ruth': 'ruth rt rth',
 '1Sam': '1sam 1samuel 1sa 1s isam isamuel 1sm',
 '2Sam': '2sam 2samuel 2sa 2s iisam iisamuel 2sm',
 '1Kgs': '1kgs 1kings 1ki 1k ikings ikgs 1kin 1rois',
 '2Kgs': '2kgs 2kings 2ki 2k iikings iikgs 2kin 2rois',
 '1Chr': '1chr 1chronicles 1ch ichr ichronicles 1par iparalipomenon 1paral iparal 1chron 1chroniques',
 '2Chr': '2chr 2chronicles 2ch iichr iichronicles 2par iiparalipomenon 2paral iiparal 2chron 2chroniques',
 'Ezra': 'ezra ezr esdras 1esdr iesdr iesdrae',
 'Neh': 'neh nehemiah ne 2esdr iiesdr iiesdrae nehemie',
 'Esth': 'esth esther est es',
 'Job': 'job jb iob',
 'Ps': 'ps psalm psalms psalmi psal psalmus pss psa psaumes psaume',
 'Prov': 'prov proverbs pr prv proverbia pro proverbes',
 'Eccl': 'eccl ecclesiastes ecc qoh eccle ecclesiastae qo ecclesiaste',
 'Song': 'song songofsolomon songofsongs canticles cant canticum canticumcanticorum sg sng sos ct cantique',
 'Isa': 'isa isaiah is isaias esaias isai isaie',
 'Jer': 'jer jeremiah jr jere jeremias ieremias jeremie hier hieremias hierem',
 'Lam': 'lam lamentations lm thren threni lamentationes la',
 'Ezek': 'ezek ezekiel ez ezk ezech ezechiel ezekias ezechias',
 'Dan': 'dan daniel dn da',
 'Hos': 'hos hosea ho osee os',
 'Joel': 'joel jl joe',
 'Amos': 'amos am',
 'Obad': 'obad obadiah ob oba abd abdias abdi',
 'Jonah': 'jonah jon jonas ion jnh',
 'Mic': 'mic micah mi mich michaeas micheas mich',
 'Nah': 'nah nahum na',
 'Hab': 'hab habakkuk hb habacuc abacuc',
 'Zeph': 'zeph zephaniah zep soph sophonias so',
 'Hag': 'hag haggai hg agg aggaeus aggee',
 'Zech': 'zech zechariah zec zach zacharias za',
 'Mal': 'mal malachi ml malachias',
 'Tob': 'tob tobit tb tobias',
 'Jdt': 'jdt judith jdth iudith',
 'Wis': 'wis wisdom sap sapientia wisdomofsolomon sg sag sagesse',
 'Sir': 'sir sirach ecclus ecclesiasticus eccli si siracide',
 'Bar': 'bar baruch ba',
 '1Macc': '1macc 1maccabees 1mac imach imacc 1mach 1m 1machab imachab 1machabaeorum',
 '2Macc': '2macc 2maccabees 2mac iimach iimacc 2mach 2m 2machab iimachab 2machabaeorum',
 'Matt': 'matt matthew mt mat matth matthaeus mth mathieu',
 'Mark': 'mark mk mrk marc marcus mc mr',
 'Luke': 'luke lk luk luc lucas lc',
 'John': 'john jn jhn ioh joan ioan joannes iohannes jo jean',
 'Acts': 'acts act ac actus actes',
 'Rom': 'rom romans ro rm romains',
 '1Cor': '1cor 1corinthians 1co icor',
 '2Cor': '2cor 2corinthians 2co iicor',
 'Gal': 'gal galatians ga galates',
 'Eph': 'eph ephesians ephes ep',
 'Phil': 'phil philippians php phi philipp philip',
 'Col': 'col colossians co',
 '1Thess': '1thess 1thessalonians 1th ithess 1thes',
 '2Thess': '2thess 2thessalonians 2th iithess 2thes',
 '1Tim': '1tim 1timothy 1ti itim',
 '2Tim': '2tim 2timothy 2ti iitim',
 'Titus': 'titus tit ti',
 'Phlm': 'phlm philemon phm philem phile',
 'Heb': 'heb hebrews hebr he hebreux',
 'Jas': 'jas james jam jac jacobi jacques jm',
 '1Pet': '1pet 1peter 1pe 1pt ipetr 1petr ipet',
 '2Pet': '2pet 2peter 2pe 2pt iipetr 2petr iipet',
 '1John': '1john 1jn 1jo ijoan 1joan ijohn 1jean',
 '2John': '2john 2jn 2jo iijoan 2joan iijohn 2jean',
 '3John': '3john 3jn 3jo iiijoan 3joan iiijohn 3jean',
 'Jude': 'jude jud jd juda',
 'Rev': 'rev revelation revelationofjohn apoc apocalypsis apocalypse re rv ap apocalypsisbjoannis',
 'PrMan': 'prman prayerofmanasses manasses',
 '1Esd': '1esd iesdras 3esdr iiiesdr',
 '2Esd': '2esd iiesdras 4esdr ivesdr 4ezra',
}
# Latin "Regum": the Vulgate's four books of Kingdoms
# VulSearch / Clementine-text book codes (~/patrologia/sources/vulgate/clementine-flat.txt)
_VULSEARCH = {'1mcc': '1Macc', '2mcc': '2Macc', '1rg': '1Sam', '2rg': '2Sam', '3rg': '1Kgs', '4rg': '2Kgs', 'apc': 'Rev',
              'hbr': 'Heb', 'esr': 'Ezra', 'ecl': 'Eccl', '1ptr': '1Pet', '2ptr': '2Pet', 'mch': 'Mic', 'phlp': 'Phil'}
_REG = {'ireg': '1Sam', '1reg': '1Sam', 'iireg': '2Sam', '2reg': '2Sam', 'iiireg': '1Kgs', '3reg': '1Kgs',
        'ivreg': '2Kgs', '4reg': '2Kgs', 'iregum': '1Sam', 'iiregum': '2Sam', 'iiiregum': '1Kgs', 'ivregum': '2Kgs'}
# eBible verse-per-line codes and USFM where they differ from OSIS
_CODES = {'GEN': 'Gen', 'EXO': 'Exod', 'LEV': 'Lev', 'NUM': 'Num', 'DEU': 'Deut', 'JOS': 'Josh', 'JDG': 'Judg',
 'RUT': 'Ruth', '1SA': '1Sam', '2SA': '2Sam', '1KI': '1Kgs', '2KI': '2Kgs', '1CH': '1Chr', '2CH': '2Chr', 'EZR': 'Ezra',
 'NEH': 'Neh', 'EST': 'Esth', 'JOB': 'Job', 'PSA': 'Ps', 'PRO': 'Prov', 'ECC': 'Eccl', 'SNG': 'Song', 'SOL': 'Song',
 'ISA': 'Isa', 'JER': 'Jer', 'LAM': 'Lam', 'EZK': 'Ezek', 'EZE': 'Ezek', 'DAN': 'Dan', 'HOS': 'Hos', 'JOL': 'Joel',
 'AMO': 'Amos', 'OBA': 'Obad', 'JON': 'Jonah', 'MIC': 'Mic', 'NAM': 'Nah', 'NAH': 'Nah', 'HAB': 'Hab', 'ZEP': 'Zeph',
 'HAG': 'Hag', 'ZEC': 'Zech', 'MAL': 'Mal', 'MAT': 'Matt', 'MRK': 'Mark', 'MAR': 'Mark', 'LUK': 'Luke', 'JHN': 'John',
 'JOH': 'John', 'ACT': 'Acts', 'ROM': 'Rom', '1CO': '1Cor', '2CO': '2Cor', 'GAL': 'Gal', 'EPH': 'Eph', 'PHP': 'Phil',
 'PHI': 'Phil', 'COL': 'Col', '1TH': '1Thess', '2TH': '2Thess', '1TI': '1Tim', '2TI': '2Tim', 'TIT': 'Titus',
 'PHM': 'Phlm', 'HEB': 'Heb', 'JAS': 'Jas', 'JAM': 'Jas', '1PE': '1Pet', '2PE': '2Pet', '1JN': '1John', '1JO': '1John',
 '2JN': '2John', '2JO': '2John', '3JN': '3John', '3JO': '3John', 'JUD': 'Jude', 'REV': 'Rev', 'TOB': 'Tob', 'JDT': 'Jdt',
 'WIS': 'Wis', 'SIR': 'Sir', 'BAR': 'Bar', '1MA': '1Macc', '2MA': '2Macc'}
# Douay-Glossa's Latin file slugs (the Vulgate titles)
_LATIN_TITLES = {'genesis': 'Gen', 'exodus': 'Exod', 'leviticus': 'Lev', 'numeri': 'Num', 'deuteronomium': 'Deut',
 'josue': 'Josh', 'judicum': 'Judg', 'ruth': 'Ruth', 'i-regum': '1Sam', 'ii-regum': '2Sam', 'iii-regum': '1Kgs',
 'iv-regum': '2Kgs', 'i-paralipomenon': '1Chr', 'ii-paralipomenon': '2Chr', 'esdrae': 'Ezra', 'i-esdrae': 'Ezra',
 'nehemiae': 'Neh', 'ii-esdrae': 'Neh', 'tobiae': 'Tob', 'judith': 'Jdt', 'esther': 'Esth', 'job': 'Job',
 'psalmorum': 'Ps', 'proverbiorum': 'Prov', 'ecclesiastes': 'Eccl', 'canticum-canticorum': 'Song',
 'sapientiae': 'Wis', 'ecclesiasticus': 'Sir', 'isaiae': 'Isa', 'jeremiae': 'Jer', 'lamentationes': 'Lam',
 'baruch': 'Bar', 'ezechielis': 'Ezek', 'danielis': 'Dan', 'osee': 'Hos', 'joel': 'Joel', 'amos': 'Amos',
 'abdiae': 'Obad', 'jonae': 'Jonah', 'michaeae': 'Mic', 'nahum': 'Nah', 'habacuc': 'Hab', 'sophoniae': 'Zeph',
 'aggaei': 'Hag', 'zachariae': 'Zech', 'malachiae': 'Mal', 'i-machabaeorum': '1Macc', 'ii-machabaeorum': '2Macc',
 'matthaeum': 'Matt', 'marcum': 'Mark', 'lucam': 'Luke', 'joannem': 'John', 'actus-apostolorum': 'Acts',
 'romanos': 'Rom', 'i-ad-corinthios': '1Cor', 'ii-ad-corinthios': '2Cor', 'galatas': 'Gal', 'ephesios': 'Eph',
 'philippenses': 'Phil', 'colossenses': 'Col', 'i-ad-thessalonicenses': '1Thess', 'ii-ad-thessalonicenses': '2Thess',
 'i-ad-timotheum': '1Tim', 'ii-ad-timotheum': '2Tim', 'titum': 'Titus', 'philemonem': 'Phlm', 'hebraeos': 'Heb',
 'b-jacobi': 'Jas', 'i-b-petri': '1Pet', 'ii-b-petri': '2Pet', 'i-b-joannis': '1John', 'ii-b-joannis': '2John',
 'iii-b-joannis': '3John', 'b-judae': 'Jude', 'apocalypsis-b-joannis': 'Rev'}

def _k(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

@lru_cache(None)
def _alias():
    a = {}
    for code, names in _B.items():
        a[_k(code)] = code
        for n in names.split():
            a.setdefault(n, code)
    a.update(_REG)
    a.update(_VULSEARCH)
    return a

OSIS = set(_B)

class Ref(NamedTuple):
    osis: str          # the refKey
    scheme: str        # the versification the numbers are in: kjv | vulg | mt | lxx
    book: str
    c1: int
    v1: Optional[int]
    c2: int
    v2: Optional[int]

def book(name):
    """Any book name, abbreviation, code or slug -> OSIS code, or None."""
    raw = name.strip().strip('.')
    if raw.upper() in _CODES and not raw.islower():
        return _CODES[raw.upper()]
    if raw in OSIS:
        return raw
    s = raw.lower()
    sl = re.sub(r'^(liber|prophetia|evangelium-secundum|epistola-canonica|epistola-beati-pauli-apostoli|epistola)-(ad-)?', '', s)
    for cand in (s, sl, sl.replace('ad-', '')):
        if cand in _LATIN_TITLES:
            return _LATIN_TITLES[cand]
    k = _k(re.sub(r'\b(the|of|book|first|second|third|saint|st)\b',
                  lambda m: {'first': '1', 'second': '2', 'third': '3'}.get(m.group(1), ''), s))
    a = _alias()
    for cand in (k, _k(raw), k.rstrip('s')):
        if cand in a:
            return a[cand]
    # a leading roman numeral only if the name as written is not a book ("Is." is Isaiah)
    r = re.sub(r'^(iii|ii|i)(?=[a-z])', lambda m: str(len(m.group(1))), k)
    if a.get(r) or a.get(r.rstrip('s')):
        return a.get(r) or a.get(r.rstrip('s'))
    # truncated Latin abbreviations ('Habac.', 'Jerem.', 'Levit.', 'Michae.'): a unique prefix of a long name
    for cand in (k, r):
        if len(re.sub(r'^\d', '', cand)) >= 3:
            hits = {c for n, c in a.items() if len(n) >= 4 and n.startswith(cand)}
            if len(hits) == 1:
                return hits.pop()

_REF = re.compile(r"""^\s*(?P<b>(?:[1-4]|I{1,3}V?|IV)?[\s.\-]{0,2}[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.\-' ]*?)\.?\s*
    (?P<c1>\d+)(?:(?:\s*[:.,]\s*|\s+)(?P<v1>\d+)[a-z]?)?
    (?:\s*[-–—]\s*(?:(?P<b2>[A-Za-z0-9]+)\.)?(?P<x>\d+)(?:\s*[:.]\s*(?P<y>\d+)[a-z]?)?)?\s*$""", re.X)

_XBOOK = re.compile(r'^(?P<a>.+?\d+[:.]\d+)\s*[–—-]\s*(?P<b>(?:[1-4]\s?)?[A-Za-z][A-Za-z. ]+\d+[:.]\d+)$')
_ROM = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
def _r2i(t):
    n = 0
    for a, b in zip(t, t[1:] + ' '):
        v = _ROM[a]; n += -v if b != ' ' and _ROM.get(b, 0) > v else v
    return n
def _unroman(s):
    """Migne and de Lubac print chapters in roman numerals: 'Psal. XXXIX', 'Joan. VIII, 12', 'I Cor. X, 11'.
    Convert roman numerals that FOLLOW the book name; a leading I/II/III/IV is the book number."""
    m = re.match(r'^((?:I{1,3}V?|IV|[1-4])?[\s.]{0,2}[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ.\'\- ]*?\.?\s+)(.*)$', s)
    if not m:
        return s
    tail = re.sub(r',\s*(?=[IVXLCDM]+\b)', ' ; ', m.group(2))   # 'XXI, XXII' is two chapters, not ch. 21 v. 22
    tail = re.sub(r'^([IVXLCDM]+\b[^;]*?)\s*;\s*(?=[IVXLCDM]+\b)', lambda t: t.group(1) + ' ; ' + m.group(1).strip() + ' ', tail)
    return m.group(1) + re.sub(r'\b[IVXLCDM]+\b', lambda t: str(_r2i(t.group())), tail)

def parse_many(s, scheme='kjv', default_book=None):
    """Several references in one string ('2 Kings 16 · Isaiah 7', 'Gen 1:1; 2:4'): list of Ref.
    A part with no book of its own takes the previous part's book."""
    out, last = [], default_book
    s = s or ''
    if re.search(r'\b[IVXLC]+\b', s) and ',' in s and not re.search(r'\d', s):
        s = _unroman(s)                  # 'Gen. XXI, XXII' -> two chapters
    s = re.sub(r',?\s+et\s+(?=(?:I{1,3}\s|[1-3]\s?)?[A-Z]?[IVXLCa-z\d])', ' ; ', s)   # 'Ezech. XL et XLI', 'Habac. II, 4, et Rom. I, 17'
    s = re.sub(r',\s*(?=(?:I{1,3}\s|[1-3]\s?)?[A-Z][a-z]+\.?\s+[IVXLC\d])', ' ; ', s)   # 'Matth. V, Luc. VI'
    for part in re.split(r'\s*[·;]\s*', s):
        r = parse(part, scheme, last)
        if r:
            out.append(r); last = r.book
            extra = re.match(r'^.*?\d+\s*,\s*\d+((?:\s*,\s*\d+)+)\s*$', _unroman(part).rstrip('. '))
            if extra and r.v1 is not None:             # the rest of a verse list
                for v in re.findall(r'\d+', extra.group(1)):
                    out.append(Ref(f'{r.book}.{r.c1}.{v}', r.scheme, r.book, r.c1, int(v), r.c1, int(v)))
    return out

def parse(s, scheme='kjv', default_book=None):
    """A reference string in any registry form -> Ref, or None. default_book: for bare "1:1–2"."""
    s = (s or '').strip().replace('\u00a0', ' ').rstrip('.;, ')
    s = re.sub(r',?\s*\b(?:sec|secund|secundum|juxta|iuxta|apud|ex)\.?\s+(?:LXX|Hebr|Hebraeum|Hebraicum|Vulg|Vulgatam|Graec|Graecum)\.?$', '', s, flags=re.I)   # 'Isai. VII, 9, sec. LXX'
    s = re.sub(r'^((?:I{1,3}V?|IV|[1-4])?\s?[A-Za-zÀ-ÿ]+\.?)\s*,\s*', r'\1 ', s)      # 'I Cor., VI'
    if not s:
        return None
    if re.search(r'\s+et\s+(?=(?:I{1,3}\s|[1-3]\s?)?[A-Z]?[IVXLCa-z\d])|,\s*(?:I{1,3}\s|[1-3]\s?)?[A-Z][a-z]+\.?\s+[IVXLC\d]', s):
        many = parse_many(s, scheme, default_book)
        return many[0] if many else None
    u = s if ';' in s or '·' in s else _unroman(s)
    if ';' in u or '·' in u:
        many = parse_many(u, scheme, default_book)
        return many[0] if many else None
    if default_book and re.match(r'^\d+(?:\s*[:.,]\s*\d+)?(?:\s*[-–—]\s*\d+(?:[:.]\d+)?)?\s*$', s):
        s = f'{default_book} {s}'
    s = re.sub(r'\s*\b(?:seqq|seq|sqq|ss|sq|etc|et seq)\.?$', '', s)
    vl = re.match(r'^(.*?\d+\s*,\s*\d+)((?:\s*,\s*\d+)+)$', _unroman(s))   # 'XIII, 6, 21': verses 6 and 21
    if vl:
        s = vl.group(1)
    m = None
    for cand in (s, _unroman(s)):
        mm = _REF.match(cand)
        if mm and book(mm['b']):
            m = mm; break
    if not m:
        x = _XBOOK.match(s)              # cross-book range: 1 Kings 22:51–2 Kings 1:18
        if x:
            a, b = parse(x['a'], scheme), parse(x['b'], scheme)
            if a and b and a.v1 is not None and b.v1 is not None:
                return Ref(f'{a.osis.split("-")[0]}-{b.osis.split("-")[-1]}', a.scheme, a.book, a.c1, a.v1, b.c2, b.v2)
        return None
    bk = book(m['b'])
    if not bk:
        return None
    if re.match(r'^\s*(?:I{1,3}|IV|[1-4])\s?\.?\s?Reg', m['b'], re.I):
        scheme = 'vulg' if scheme == 'kjv' else scheme
    c1 = int(m['c1']); v1 = int(m['v1']) if m['v1'] else None
    c2, v2 = c1, v1
    if m['x']:
        if m['y']:                       # 3:16-4:2  /  Exod.2.8-Exod.3.3
            c2, v2 = int(m['x']), int(m['y'])
        elif v1 is not None:             # 3:16-18  /  Rev.4.6-8
            v2 = int(m['x'])
        else:                            # 12-14 (chapters)
            c2 = int(m['x'])
    if (c2, v2 or 0) == (c1, v1 or 0):
        key = f'{bk}.{c1}' + (f'.{v1}' if v1 is not None else '')
    elif v1 is None:
        key = f'{bk}.{c1}-{bk}.{c2}'
    else:
        key = f'{bk}.{c1}.{v1}-{bk}.{c2}.{v2}'
    return Ref(key, scheme, bk, c1, v1, c2, v2)

@lru_cache(None)
def _cross():
    m = {}
    p = os.path.join(HERE, 'data', 'crosswalk-vulg-kjv.tsv')
    for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
        if r['vulg']:
            m[r['vulg']] = (r['kjv'], r['rel'])
    return m

def to_kjv(key):
    """A Vulgate-numbered single-verse OSIS key -> list of KJV keys ([] = no KJV counterpart).
    Chapter keys and ranges: convert the endpoints yourself; chapter shifts (Psalms) follow the
    first verse of the chapter."""
    k = key.split('-')[0]
    if k.count('.') == 1:                 # whole chapter: follow its first real verse
        for v in (1, 2, 3):
            got = _cross().get(f'{k}.{v}')
            if got and got[0]:
                return [got[0].rsplit('.', 1)[0]]
        return []
    got = _cross().get(k)
    if not got or not got[0]:
        return []
    return [got[0]]

if __name__ == '__main__':
    T = [  # (input, kwargs, expected refKey) from every layer in LAYERS.md
        ('Gen.1.1', {}, 'Gen.1.1'), ('gen.1.2', {}, 'Gen.1.2'), ('Rev.4.6-8', {}, 'Rev.4.6-Rev.4.8'),
        ('Matt.1.1-Matt.1.17', {}, 'Matt.1.1-Matt.1.17'), ('Exod.12-Exod.14', {}, 'Exod.12-Exod.14'),
        ('Esther 1:1', {}, 'Esth.1.1'), ('1 Kings 12:20–14:20', {}, '1Kgs.12.20-1Kgs.14.20'), ('Psalm 23', {}, 'Ps.23'),
        ('Psalms 2:7–9', {}, 'Ps.2.7-Ps.2.9'), ('Song 1:16–2:1', {}, 'Song.1.16-Song.2.1'), ('Exodus 2:2', {}, 'Exod.2.2'),
        ('Philemon 1:19', {}, 'Phlm.1.19'), ('1 Nephi 1:1', {}, None), ('1Chr 3:1-19', {}, '1Chr.3.1-1Chr.3.19'),
        ('Gen 6:1-9:29', {}, 'Gen.6.1-Gen.9.29'), ('ACT 1:13', {}, 'Acts.1.13'), ('PHI 1:1', {}, 'Phil.1.1'),
        ('JAM 1:1', {}, 'Jas.1.1'), ('6:14–23', {'default_book': 'Lev'}, 'Lev.6.14-Lev.6.23'),
        ('1samuel 3:4', {}, '1Sam.3.4'), ('1-samuel 3:4', {}, '1Sam.3.4'), ('liber-iii-regum 4:21', {'scheme': 'vulg'}, '1Kgs.4.21'),
        ('canticum-canticorum 2:1', {'scheme': 'vulg'}, 'Song.2.1'), ('III Reg. 4, 21', {}, '1Kgs.4.21'),
        ('Psal. 118, 66', {'scheme': 'vulg'}, 'Ps.118.66'), ('Matth. 13, 44', {}, 'Matt.13.44'),
        ('Eccli. 24, 5', {}, 'Sir.24.5'), ('Apoc. 5, 1', {}, 'Rev.5.1'), ('I Cor. 10, 11', {}, '1Cor.10.11'),
        ('Joan. 1, 14', {}, 'John.1.14'), ('Is. 7, 14', {}, 'Isa.7.14'), ('Jér. 1, 11', {}, 'Jer.1.11'),
        ('II Esdr. 8, 8', {}, 'Neh.8.8'), ('Cant. 1, 1', {}, 'Song.1.1'), ('Thren. 1, 1', {}, 'Lam.1.1'),
        ('Revelation of John 1:1', {}, 'Rev.1.1'), ('Song of Solomon 2:1', {}, 'Song.2.1'), ('I Samuel 1:1', {}, '1Sam.1.1'),
        ('Mt 5:3', {}, 'Matt.5.3'), ('Psal. XXXIX', {'scheme': 'vulg'}, 'Ps.39'), ('Joan. VIII, 12', {}, 'John.8.12'),
        ('I Cor. X, 11', {}, '1Cor.10.11'), ('1 Chronicles 1:1–27', {'default_book': 'Chronicles'}, '1Chr.1.1-1Chr.1.27'),
        ('1 Kings 22:51–2 Kings 1:18', {}, '1Kgs.22.51-2Kgs.1.18'), ('Isa. XLIX', {}, 'Isa.49'),
        ('Job. XIV.', {}, 'Job.14'), ('I Cor., VI', {}, '1Cor.6'), ('Gen. XXI, XXII', {}, 'Gen.21'),
        ('Matth. XXV, 34', {}, 'Matt.25.34'), ('Sap. II; Isa. XXII', {}, 'Wis.2'), ('Cant. VI.', {}, 'Song.6'), ('Habac. II', {}, 'Hab.2'), ('Ose. I', {}, 'Hos.1'),
        ('Jerem. I', {}, 'Jer.1'), ('Levit. XVI', {}, 'Lev.16'), ('Jacob. II.', {}, 'Jas.2'), ('Rom. VII 24.', {}, 'Rom.7.24'),
        ('Ezech. XL et XLI', {}, 'Ezek.40'), ('Matth. V, Luc. VI', {}, 'Matt.5'), ('Michae. II', {}, 'Mic.2'), ('Matth. XIII, 6, 21', {}, 'Matt.13.6'), ('Abac. I', {}, 'Hab.1'),
        ('Prov. I, 1 seq.', {}, 'Prov.1.1'), ('Isai. VII, 9, sec. LXX', {}, 'Isa.7.9'), ('Job XIV, 4, juxta LXX', {}, 'Job.14.4'),
        ('Prov. VIII, sec. LXX', {}, 'Prov.8'), ('Jn 1:1', {}, 'John.1.1'), ('Ps.110', {}, 'Ps.110'),
    ]
    bad = 0
    for s, kw, want in T:
        r = parse(s, **kw)
        got = r.osis if r else None
        if got != want:
            bad += 1; print('FAIL', repr(s), '->', got, 'want', want)
    print(f'{len(T) - bad}/{len(T)} parse tests pass')
    many = [r.osis for r in parse_many('Joan. XII; Matth. XXI; Marc. XI')] + [r.osis for r in parse_many('Gen. XXI, XXII')]
    many += [r.osis for r in parse_many('Matth. V, 3, 4, 7')] + [r.osis for r in parse_many('Habac. II, 4, et Rom. I, 17')]
    if many != ['John.12', 'Matt.21', 'Mark.11', 'Gen.21', 'Gen.22', 'Matt.5.3', 'Matt.5.4', 'Matt.5.7', 'Hab.2.4', 'Rom.1.17']:
        bad += 1; print('FAIL parse_many', many)
    X = [('Ps.22.1', ['Ps.23.1']), ('Ps.118.66', ['Ps.119.66']), ('Ps.50.3', ['Ps.51.1']), ('Ps.50.1', []),
         ('Ps.22', ['Ps.23']), ('Dan.3.24', []), ('Dan.3.91', ['Dan.3.24']), ('John.6.52', ['John.6.51'])]
    xb = [(k, to_kjv(k), w) for k, w in X if to_kjv(k) != w]
    print(f'{len(X) - len(xb)}/{len(X)} crosswalk tests pass', xb or '')
