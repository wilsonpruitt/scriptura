#!/usr/bin/env python3
"""Stage A, step 1: harvest every Migne reference from the OCR text of de Lubac,
Exégèse médiévale (Aubier 1959-64, 4 vols), and resolve PL refs to a work.

Pointer mode (PLAN 5.3 A): the ledger holds locations and bibliographic strings.
It holds none of de Lubac's prose. `cited_as` is his abbreviated author/work
citation and is a WORKING column: review before any export. The Latin he quotes
goes to working/quotes.tsv (the Father's words, in de Lubac's transcription, OCR'd)
and is used only to verify the column; it is never the ledger's anchor.

Reads   sources/exegese-medievale/text/em{1..4}.txt   (pdftotext -layout, \\f = page)
        data/pl-columns.json, data/pl-locator.tsv      (scripts/pl_locator.py)
Writes  ledger/refs.tsv         one row per reference with a volume (explicit or bare)
        ledger/colonly.tsv      parenthesised column/page with no volume: residue
        ledger/notes.tsv        one row per footnote: what kinds of reference it carries
        ledger/pages.tsv        pdf page -> printed page, note count, ref count
        working/quotes.tsv      ref id -> the Latin quoted just before it
No model tokens.
"""
import csv, json, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TXT = ROOT / "sources/exegese-medievale/text"
LED = ROOT / "ledger"
WRK = ROOT / "working"
VOLS = {1: "I/1", 2: "I/2", 3: "II/1", 4: "II/2"}      # em file -> part/tome
SERIES_MAX = {"PL": 221, "PG": 161}

# ---------- roman numerals, tolerant of OCR ----------
RV = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

def to_roman(n):
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
                 (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out += s; n -= v
    return out

def roman_strict(s):
    if not s or any(c not in RV for c in s):
        return None
    t = 0
    for i, c in enumerate(s):
        v = RV[c]
        t += -v if i + 1 < len(s) and RV[s[i + 1]] > v else v
    return t if to_roman(t) == s else None

def roman_candidates(raw):
    """(value, fixed?) readings of an OCR'd roman numeral, most literal first."""
    up = raw.upper().replace(" ", "")
    seen = []
    def add(t):
        v = roman_strict(t)
        if v and all(v != x for x, _ in seen):
            seen.append((v, t != up))
    add(up)
    s = up.replace("1", "I").replace("T", "I").replace("J", "I").replace("!", "I").replace("K", "X")
    s = re.sub(r"I{4,}", "III", s)                 # LXXXIITI -> LXXXIIII -> LXXXIII
    add(s)
    for k in (1, 2):                               # a final L is the commonest misreading of I
        if len(s) > k and s.endswith("L" * k):
            add(s[:-k] + "I" * k)
            add(s[:-k])                            # ...or a stray stroke: CVIIIL -> CVIII
    add(re.sub(r"(?<=[IV])L", "I", s))             # an L after I/V cannot stand: CLXXVILI
    if "W" in s:                                   # XXXWVIII, XXXWI: W is a damaged V (or IV / VI)
        for w in ("V", "IV", "VI", ""):
            add(re.sub(r"I{4,}", "III", s.replace("W", w)))
    return seen

# ---------- reference patterns ----------
def cols(p):
    return (r"(?P<%sc1>\d{1,4})(?:\s?(?P<%sb1>[A-DÀ]{1,4})(?![A-Za-zé]))?"
            r"(?:\s?-\s?(?P<%sc2>\d{1,4})(?:\s?(?P<%sb2>[A-DÀ]{1,4})(?![A-Za-zé]))?)?") % (p, p, p, p)
ROM1 = r"(?=[1!JTW]*[IVXLCDMK])[IVXLCDMKT1!JW]{1,10}"   # at least one true roman letter
ROM = ROM1 + r"(?: (?=[IVX]{2,5}\b)[IVXLCDM]{2,5})?"       # "XXX VIII": the OCR splits a numeral
# three forms, most explicit first:
#   e  explicit  (PL, CVII, 406 BC)   siglum present; PI / PZ / PE are OCR for PL
#   b  bare      (CXCVIII, 1046 B)    de Lubac drops the siglum freely, above all in part II
#   o  colonly   (312-4)              column or PAGE alone: often NOT Migne (GCS, CSEL, folios)
REF = re.compile(
    r"(?:\b(?:P\.?\s?(?P<s>[LG])\.{0,2}|P(?P<so>[IZE])z?)\s?[,.]?\s+(?P<evol>" + ROM + r"|[ivxlc]{2,8}|\d{1,3})(?:\s?[,.]\s*|\s)" + cols("e") + r")"
    r"|(?:(?<=\()(?!(?:CCL|CSEL|MGH|SC|PLS|GCS|CCCM|CCSL)\b)(?P<bvol>" + ROM + r"|\d{1,3}(?=, ?\d{1,4}\s?[A-DÀ](?![A-Za-zé])))"   # arabic only with a band: "(184, 706 C)"
    r", ?" + cols("b") + r"(?=\s?[),;]))"
    r"|(?:(?<=\()" + cols("o") + r"(?=\)))")
# after a reference, more columns of the same volume ("290 A, 311 B") or, after a semicolon, a
# new volume of the same series ("...; LXXVI, 1045 C"), up to the closing parenthesis
CONT = re.compile(r"(?:\s?[,;]\s?|\s(?=\d{2,4}\s?[A-DÀ]))" + cols("k") + r"(?=\s?[),;.]|\s?etc)")
CONTVOL = re.compile(r"\s?;\s?(?!(?:CCL|CSEL|MGH|SC|PLS|GCS|CCCM|CCSL)\b)(?P<kvol>" + ROM + r"),\s?" + cols("k") + r"(?=\s?[),;.]|\s?etc)")
MARK = r"(\d{1,2}|[:;?!Ilx+*°$£&%€@à.])"
NOTE_START = re.compile(r"^(\s{1,9})" + MARK + r"\s?[.,:;]?\s+\S")
OTHER = re.compile(r"\b(CCL|CSEL|SC|MGH|GCS|PLS|Pitra|PITRA|Mansi|MANSI|ASS)\b")
LOCUS = re.compile(r"\b(?:[lLchnsqv]|ep|Ep|str|tr|hom|Hom|serm|Serm)\. ?(?:[IVXLCivxlc]+|\d+)\b")
SIGLA = re.compile(r"\b(P\. ?L\.|P\. ?G\.|PL|PG|CCL|CSEL|SC|MGH|GCS|PLS)(?=[\s,.])")
# CCL volumes in print by 1964 that hold an author Migne prints under the same number's
# neighbourhood: a bare "(XXXVIII, 123)" may be CCL 38 (Enarr. in Ps.) and not PL 38 (Sermones).
# ⚠ The list is from memory of the CCL's publication dates: verify before leaning on it.
CCL_BY_1964 = {1, 2, 9, 14, 36, 38, 39, 40, 47, 48, 72, 73, 74, 75, 78, 97, 98, 103, 104,
               117, 119, 120, 122}
MODERN = re.compile(r"\((?:1[5-9]\d\d)\)|\b(?:1[89]\d\d)\b|\bp\. ?\d|\bt\. ?\d|\béd\.|\btr\.")

def expand_end(c1, c2):
    """406-7 -> 407, 285-98 -> 298; full numbers stay."""
    if c2 is None:
        return None
    a, b = str(c1), str(c2)
    if len(b) < len(a):
        b = a[: len(a) - len(b)] + b
    b = int(b)
    return b if b >= c1 else None

def printed_pages(pages):
    """Printed page per pdf page: read the running head, then fill gaps by offset."""
    got = {}
    for i, p in enumerate(pages):
        first = next((l for l in p.split("\n") if l.strip()), "")
        m = re.match(r"^\s*(\d{1,3})\s{2,}\S", first) or re.search(r"\S\s{2,}(\d{1,3})\s*$", first)
        if m:
            got[i] = int(m.group(1))
    offs = collections.Counter(i - n for i, n in got.items())
    good = {o for o, c in offs.items() if c >= 5}
    got = {i: n for i, n in got.items() if (i - n) in good}
    out, known = {}, sorted(got)
    for i in range(len(pages)):
        if i in got:
            out[i] = (got[i], "head")
            continue
        near = min(known, key=lambda k: abs(k - i)) if known else None
        out[i] = (i - (near - got[near]), "offset") if near is not None else (None, "none")
    return out

def split_columns(line):
    """A line can carry two short notes side by side: '3. Cité ...      4. Wright, 453.'"""
    parts, last = [], 0
    for m in re.finditer(r"\s{6,}(?=\d{1,2}[.,] \S)", line):
        if line[last:m.start()].strip():
            parts.append((line[last:m.start()], last == 0))
            last = m.start()
    parts.append((line[last:], last == 0))
    return parts

def note_zone(lines):
    """Index of the first footnote line, and how it was found.
    'one'   the last line that opens note 1;
    'gap'   no legible '1.': the first indented, marker-led line after a blank line
            in the lower part of the page (the OCR often loses the numeral)."""
    start = None
    for i, l in enumerate(lines):
        if i > 2 and re.match(r"^\s{1,9}[1Il]\s?[.,:] ?\S", l):
            start = i
    if start is not None:
        return start, "one"
    lo = len(lines) // 4
    for i in range(max(lo, 3), len(lines)):
        if not lines[i - 1].strip() and re.match(r"^\s{1,9}(\d{1,2}|[:;?!x+*°$£&%€@à.])\s?[.,:;]? ?[A-ZÉ«(]", lines[i]):
            return i, "gap"
    return None, "none"

def harvest(n):
    label = VOLS[n]
    pages = (TXT / f"em{n}.txt").read_text(encoding="utf-8").split("\f")
    pp = printed_pages(pages)
    refs, colonly, notes, pagerows, quotes = [], [], [], [], []
    for pi, page in enumerate(pages):
        lines = page.split("\n")
        z, zhow = note_zone(lines)
        segs = [[None, " ".join(l.strip() for l in lines[: z if z is not None else len(lines)])]]
        if z is not None:
            cur = 0
            for l in lines[z:]:
                for piece, at_margin in split_columns(l):
                    m = NOTE_START.match(piece) if at_margin else re.match(r"^(\s*)(\d{1,2})[.,] \S", piece)
                    if m and (not at_margin or 1 <= len(m.group(1)) <= 9):
                        tok = m.group(2)
                        num = int(tok) if tok.isdigit() else None
                        # trust a legible numeral near the running count (it resyncs after a
                        # lost or spurious marker); otherwise take the next number
                        if num is None or abs(num - (cur + 1)) > 2 or num < 1:
                            num = cur + 1
                        cur = num
                        segs.append([cur, piece.strip()])
                    else:
                        segs[-1][1] += " " + piece.strip()
        nref = k = 0                      # k runs through the page, so ids are unique
        for num, text in segs:
            text = re.sub(r"(\w)- (?=[a-zéèàç])", r"\1", text)      # rejoin hyphenated words
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"(?<=\d)o(?=\s?[A-DÀ]?\b)", "0", text)   # "8o A": OCR o for 0
            found = list(REF.finditer(text))
            sig = [(x.end(), x.group(1).replace(" ", "").replace(".", "")) for x in SIGLA.finditer(text)]
            kinds = collections.Counter()
            prev_end, last_series = 0, None
            for m in found:
                g = m.groupdict()
                form = "e" if g["evol"] else "b" if g["bvol"] else "o"
                c1 = int(g[form + "c1"])
                c2 = expand_end(c1, int(g[form + "c2"]) if g[form + "c2"] else None)
                band = (g[form + "b1"] or "").replace("À", "A")
                band_end = (g[form + "b2"] or "").replace("À", "A")
                lead = text[prev_end:m.start()]
                # the citation string: what stands before the quotation, after the last break
                cite = re.split(r"«", lead)[0]
                cite = re.split(r"(?:\. — |\) ?[;.] |» ?[;.,] )", cite)[-1]
                cite = re.sub(r"^\s*\S{0,2}\s?[.,:] ", "", cite).strip(" (:;,.—-")[-140:]
                q = re.search(r"«\s*([^«»]{12,})\s*»[\s.,;]*\(?$", lead)
                prev_end = m.end()
                k += 1
                rid = f"em{n}-p{pi + 1:03d}-n{num if num is not None else 0:02d}-{k}"
                base = dict(id=rid, em=n, tome=label, page=pp[pi][0], page_src=pp[pi][1], pdf_page=pi + 1,
                            note=num if num is not None else "")
                if form == "o":
                    kinds["colonly"] += 1
                    year = int(not band and not c2 and 1500 <= c1 <= 1965)   # "(1938)": a date, not a column
                    colonly.append(dict(base, col=c1, band=band, col_end=c2 or "", band_end=band_end,
                                        has_quote=int(bool(q)), year=year, cited_as=cite, raw=m.group(0).strip()))
                    if q and not year:
                        quotes.append(dict(id=rid, quote=q.group(1).strip()))
                    continue
                if form == "e":
                    series = "PG" if g["s"] == "G" else "PL"
                    last_series, series_src, rawvol = series, "siglum", g["evol"]
                else:
                    # a bare ref takes the series of the last siglum before it in the same note
                    # (which may be CCL, SC...: then it is not Migne); with none, PL by default
                    before = [x for e, x in sig if e <= m.start()]
                    series, series_src, rawvol = (before[-1], "carried") if before else ("PL", "default"), None, g["bvol"]
                    series, series_src = series
                cands = [(int(rawvol), False)] if rawvol.isdigit() else roman_candidates(rawvol)
                cands = [(v, f) for v, f in cands if 1 <= v <= SERIES_MAX.get(series, 999)]
                kinds[series] += 1
                refs.append(dict(base, form="explicit" if form == "e" else "bare", series=series, series_src=series_src,
                                 vol_raw=rawvol, vol=cands[0][0] if cands else "",
                                 vol_alt=" ".join(str(v) for v, _ in cands[1:]),
                                 vol_fixed=int(bool(cands and cands[0][1])),
                                 siglum_ocr=int(bool(g["so"])),
                                 ccl_collision=int(series_src == "default" and bool(cands) and cands[0][0] in CCL_BY_1964),
                                 col=c1, band=band, col_end=c2 or "", band_end=band_end,
                                 has_quote=int(bool(q)), cited_as=cite, raw=m.group(0).strip()))
                refs[-1]["list_item"] = 0
                if q:
                    quotes.append(dict(id=rid, quote=q.group(1).strip()))
                nref += 1
                # the rest of a list: "(PL, LIV, 290 A, 311 B)", "(PL, LXXV, 9 A, 123 B; LXXVI, 1045 C)".
                # The quote, if any, belongs to the first item only. Pilot 2026-11-09 found these
                # dropped: about 90 PL references on 50 pages of I/2.
                pos, head = m.end(), refs[-1]
                while True:
                    mm = CONT.match(text, pos) or CONTVOL.match(text, pos)
                    if not mm:
                        break
                    kg = mm.groupdict()
                    row = dict(head)
                    if kg.get("kvol"):
                        cv = roman_candidates(kg["kvol"])
                        cv = [(v, f) for v, f in cv if 1 <= v <= SERIES_MAX.get(series, 999)]
                        row.update(vol_raw=kg["kvol"], vol=cv[0][0] if cv else "",
                                   vol_alt=" ".join(str(v) for v, _ in cv[1:]), vol_fixed=int(bool(cv and cv[0][1])),
                                   ccl_collision=int(series_src == "default" and bool(cv) and cv[0][0] in CCL_BY_1964))
                        head = row
                    k1 = int(kg["kc1"])
                    k += 1
                    row.update(id=f"em{n}-p{pi + 1:03d}-n{num if num is not None else 0:02d}-{k}",
                               col=k1, band=(kg["kb1"] or "").replace("À", "A"),
                               col_end=expand_end(k1, int(kg["kc2"]) if kg["kc2"] else None) or "",
                               band_end=(kg["kb2"] or "").replace("À", "A"),
                               has_quote=0, raw=mm.group(0).strip(" ,;"), list_item=1)
                    refs.append(row)
                    kinds[series] += 1
                    nref += 1
                    pos = mm.end()
                prev_end = pos
            if num is not None:
                notes.append(dict(em=n, tome=label, page=pp[pi][0], pdf_page=pi + 1, note=num,
                                  n_pl=kinds["PL"], n_pg=kinds["PG"], n_colonly=kinds["colonly"],
                                  other=" ".join(sorted({x.upper() for x in OTHER.findall(text)})),
                                  locus=int(bool(LOCUS.search(text))), modern=int(bool(MODERN.search(text))),
                                  chars=len(text)))
        pagerows.append(dict(em=n, tome=label, pdf_page=pi + 1, page=pp[pi][0], page_src=pp[pi][1],
                             notes=max((s[0] or 0) for s in segs), refs=nref, zone=zhow))
    return refs, colonly, notes, pagerows, quotes

def resolve(refs):
    cols_ = json.load(open(ROOT / "data/pl-columns.json"))
    meta = {r["idno"]: r for r in csv.DictReader(open(ROOT / "data/pl-locator.tsv", encoding="utf-8"), delimiter="\t")}
    for r in refs:
        r.update(status="", idno="", author="", author_year="", title="")
        if r["vol"] == "":
            r["status"] = "bad-volume"; continue
        if r["series"] != "PL":
            r["status"] = "pg" if r["series"] == "PG" else "other-series"; continue
        tries = [r["vol"]] + [int(x) for x in r["vol_alt"].split()]
        hit = None
        for v in tries:
            ids = cols_.get(str(v), {}).get(str(r["col"]))
            if ids:
                hit = (v, ids); break
        if hit is None:
            # volumes 218-221 are Migne's indices; a column absent from the TEI is a residue
            r["status"] = "index-volume" if tries[0] >= 218 else "column-not-in-tei"
            continue
        v, ids = hit
        if v != r["vol"]:
            r["vol_alt"], r["vol"], r["vol_fixed"] = str(r["vol"]), v, 1
        ids = sorted(ids, key=lambda i: int(meta[i]["n_cols"]) if i in meta else 10**6)
        w = meta.get(ids[0], {})
        r.update(status="resolved" if len(ids) == 1 else "resolved-shared", idno=" ".join(ids),
                 author=w.get("author", ""), author_year=w.get("author_year", ""), title=w.get("title", ""))
        # a bare low volume could be a modern work's "(II, 164)": keep it apart for a reader
        if r["form"] == "bare" and r["vol"] <= 10 and not r["band"] and r["series_src"] == "default":
            r["status"] += "?low"

def carry(colonly, refs):
    """A bare column takes its volume from the nearest earlier reference in the same note,
    IF the column lies inside that same work in the TEI.
    Returns (rows to add to the ledger, what is left)."""
    cols_ = json.load(open(ROOT / "data/pl-columns.json"))
    okey = lambda x: (x["em"], x["pdf_page"], int(x["note"] or 0), int(x["id"].rsplit("-", 1)[1]))
    good = [r for r in refs if r["status"] in ("resolved", "resolved-shared")]
    by_note, by_page = collections.defaultdict(list), collections.defaultdict(list)
    for r in good:
        by_note[(r["em"], r["pdf_page"], r["note"])].append(r)
        by_page[(r["em"], r["pdf_page"])].append(r)
    add, left = [], []
    for c in colonly:
        hit = None
        if not c["year"]:
            k = okey(c)
            # same note only. Carrying across notes on the same page was tried and measured
            # 2026-11-09: the quote check confirmed 60 of 207 (29%), against 142 of 179 (79%)
            # within a note. A wrong volume is worse than none, so the page rule is out.
            pools = (("note", by_note.get((c["em"], c["pdf_page"], c["note"]), [])),)
            for scope, pool in pools:
                for r in reversed([r for r in pool if okey(r) < k]):
                    ids = [i for i in r["idno"].split() if i in cols_.get(str(r["vol"]), {}).get(str(c["col"]), [])]
                    if ids:
                        hit = (scope, r, ids); break
                if hit:
                    break
        if not hit:
            left.append(c); continue
        scope, r, ids = hit
        add.append(dict({k: c[k] for k in ("id", "em", "tome", "page", "page_src", "pdf_page", "note")},
                        form="colonly", series="PL", series_src="carried-" + scope,
                        vol_raw="", vol=r["vol"], vol_alt="", vol_fixed=0, siglum_ocr=0, ccl_collision=0,
                        col=c["col"], band=c["band"], col_end=c["col_end"], band_end=c["band_end"],
                        has_quote=c["has_quote"], cited_as=c["cited_as"], raw=c["raw"],
                        status="resolved-carried", idno=" ".join(ids), author=r["author"],
                        author_year=r["author_year"], title=r["title"]))
    return add, left

def write(d, name, rows):
    d.mkdir(exist_ok=True)
    with open(d / name, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t", quoting=csv.QUOTE_NONE,
                           escapechar="\\", quotechar=None)
        w.writeheader()
        for r in rows:
            w.writerow({k: (re.sub(r"[\t\\]", " ", str(v)) if v is not None else "") for k, v in r.items()})

if __name__ == "__main__":
    R, C, N, P, Q = [], [], [], [], []
    for n in VOLS:
        r, c, nt, pg, q = harvest(n)
        R += r; C += c; N += nt; P += pg; Q += q
    resolve(R)
    added, C = carry(C, R)
    R += added
    R.sort(key=lambda x: (x["em"], x["pdf_page"], int(x["note"] or 0), int(x["id"].rsplit("-", 1)[1])))
    write(LED, "refs.tsv", R); write(LED, "colonly.tsv", C); write(LED, "notes.tsv", N); write(LED, "pages.tsv", P)
    write(WRK, "quotes.tsv", Q)
    c = collections.Counter((r["tome"], r["form"], r["series"], r["status"]) for r in R)
    for k in sorted(c):
        print(*k, c[k], sep="\t")
    print("refs:", len(R), "| in a numbered note:", sum(1 for r in R if r["note"] != ""),
          "| col-only:", len(C), "| notes:", len(N), "| quotes:", len(Q))
    print("zones:", dict(collections.Counter(p["zone"] for p in P)))
