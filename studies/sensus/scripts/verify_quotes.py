#!/usr/bin/env python3
"""Stage A, step 2: check each harvested reference against the Latin de Lubac quotes.

Where he prints the passage before the reference, the passage should stand in the
PL TEI at that column. A match confirms volume + column + work in one stroke, and it
is the only computed check that catches a bare "(XXXVIII, 123)" that is really CCL 38.

Reads   ledger/refs.tsv, working/quotes.tsv, ~/patrologia/sources/pl/tei/<idno>.xml
Writes  ledger/quote-check.tsv   id, check, score, where
          check = at-column   the quote stands within one column of the reference
                  in-work     found in the same work but at another column (col given)
                  absent      not found in the work the reference resolves to
        (refs without a quote, or unresolved, are not listed)
No model tokens.
"""
import csv, re, html, functools, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEI = Path.home() / "patrologia/sources/pl/tei"
rd = lambda f: list(csv.DictReader(open(f, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE))

def norm(t):
    t = html.unescape(t).lower()
    t = t.replace("æ", "ae").replace("œ", "oe").replace("j", "i").replace("v", "u")
    t = re.sub(r"[àâä]", "a", t); t = re.sub(r"[éèêë]", "e", t); t = re.sub(r"[îï]", "i", t)
    t = re.sub(r"[ôö]", "o", t); t = re.sub(r"[ùûü]", "u", t)
    t = re.sub(r"ae|oe", "e", t)
    t = re.sub(r"[^a-z]+", " ", t)
    # spellings Migne and de Lubac's editions split on
    t = re.sub(r"\bintellig", "intelleg", t); t = t.replace("mpt", "mt").replace("spirital", "spiritual")
    return t.split()

PB = re.compile(r'<pb\b[^>]*\bn="(\d{1,5})[A-D]?[^"]*"[^>]*/?>')

@functools.lru_cache(maxsize=64)
def columns(idno):
    """{column: [normalized words]} for one TEI file."""
    s = (TEI / f"{idno}.xml").read_text(encoding="utf-8", errors="replace")
    s = s[s.find("<body"):] if "<body" in s else s
    out, cur, pos = collections.defaultdict(list), None, 0
    for m in PB.finditer(s):
        if cur is not None:
            out[cur] += norm(re.sub(r"<[^>]+>", " ", s[pos:m.start()]))
        cur, pos = int(m.group(1)), m.end()
    if cur is not None:
        out[cur] += norm(re.sub(r"<[^>]+>", " ", s[pos:]))
    return out

def grams(w, n=3):
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}

def main():
    refs = {r["id"]: r for r in rd(ROOT / "ledger/refs.tsv")}
    rows = []
    for q in rd(ROOT / "working/quotes.tsv"):
        r = refs.get(q["id"])
        if not r or not r["status"].startswith("resolved"):
            continue
        text = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", q["quote"])        # his glosses inside the quote
        qg = set()
        for frag in re.split(r"\.{2,}|…", text):
            qg |= grams(norm(frag))
        if len(qg) < 3:
            continue
        c1 = int(r["col"]); c2 = int(r["col_end"] or c1)
        best = ("absent", 0.0, "")
        for idno in r["idno"].split():
            cols = columns(idno)
            win = []
            for c in range(c1 - 1, c2 + 2):
                win += cols.get(c, [])
            sc = len(qg & grams(win)) / len(qg)
            if sc >= 0.5:
                best = ("at-column", sc, idno); break
            # elsewhere in the same work: slide a two-column window
            for c in sorted(cols):
                w2 = cols[c] + cols.get(c + 1, [])
                s2 = len(qg & grams(w2)) / len(qg)
                if s2 >= 0.6 and s2 > best[1]:
                    best = ("in-work", s2, f"{idno}:{c}")
            if best[0] == "absent" and sc > best[1]:
                best = ("absent", sc, idno)
        rows.append(dict(id=q["id"], check=best[0], score=f"{best[1]:.2f}", where=best[2], n_grams=len(qg)))
    with open(ROOT / "ledger/quote-check.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader(); w.writerows(rows)
    c = collections.Counter((refs[x["id"]]["form"], refs[x["id"]]["series_src"], x["check"]) for x in rows)
    for k in sorted(c):
        print(*k, c[k], sep="\t")
    print("checked:", len(rows))

if __name__ == "__main__":
    main()
