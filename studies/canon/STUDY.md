# canon — the working canon

PLAN 5.3 stage C and QUESTIONS.md item 2. Stage 1 is **the citation spine**: every scripture
citation in the PL, `refKey` × author × work × column, in both Vulgate and KJV numbering.

## Spine v0 (2026-11-10, `scripts/spine.py`, no tokens)

| stream | rows | what |
|---|---:|---|
| `migne-notes` | 10,941 (1,558 single-verse; 9,235 chapter-level) | migne.app's own index (172 PL works), converted with `tools/refkey.py` |
| `ngram` | 639,794 | rare 5-grams (≤3 Vulgate verses) shared with the Clementine, runs ≥6 words; whole PL in 9 s |
| `fuzzy` | 894,964 (pairs 3: 256,119; 4: 85,062; 5+: 553,783) | ordered stem pairs, for Old Latin wording; whole PL in 15 s |
| `inline` | 399,679 (212,494 verse; 187,185 chapter) | Migne's own parenthetical citations in the text, 2,757 works; whole PL in 5 s |

Recall check: the n-gram stream finds **600 of Migne's 1,558 single-verse notes (38.5%)** in the
same work within one column (645 anywhere in the work). Misses read at the page:
- quotations shorter than the 6-word floor ("Sumite psalmum, et date tympanum")
- the Father's wording departs from the Clementine (*Sapientiam loquimur* without *autem*;
  *Abundante peccato refrigescit charitas*): the Old Latin trap PLAN named
- errors in Migne's index itself ("Psal. CXVIII, 72" keyed Ps.72.28)

## Stream `inline` (2026-11-10, `spine.py inline` then `spine.py calibrate`, no tokens)

Migne prints citations in parentheses, mostly inside `<note>` in the TEI: "(Psal. LXXX, 3)",
"(Matth. XXII; Marc. XII)". Each parenthetical whose text begins with a book name and a numeral goes
through `refkey.parse_many` (scheme `vulg`). The row keeps the 12 words before it as evidence, plus
three checks:
- `exists`: does the Clementine have the verse or chapter? 1.4% of verse rows and 1.3% of chapter
  rows fail. These are false hits ("Can. 16", a conciliar canon read as Song 16) and Migne's own
  errors.
- `confirmed`: do the 25 words before the parenthesis share a rare 5-gram with the cited
  reference? Verse rows: 42.6% y, 4.4% `near` (within 2 verses). Chapter rows: 44.3% y.
- `ngram_saw`: the verses those 5-grams did match, so a disagreement can be read off the row.

Rules added on the way:
- `Jud.` is Judges whenever the chapter is above 1 (Jude has one chapter). At chapter 1 it is
  whichever book the 5-grams confirm.
- `refkey` now drops "sec. LXX" / "juxta Hebr." suffixes and splits "Habac. II, 4, et Rom. I, 17".
  Tests: 68/68 parse, 8/8 crosswalk.
- 4,182 book-led parentheticals stay unparsed (`spine/inline-unparsed.tsv`). Most are not scripture
  ("Ex Isidoro", "Joan. Chrys.").

**What the unconfirmed verse rows are** (122K): allusions and paraphrases Migne identified, where no
5-gram matches (85K); verse lists and neighbouring verses (13K); wording that matches a parallel in
another book, which Migne cites by the other one (16K). Only the inline stream catches allusions.

**Calibration**, in the 1,480 works where Migne cites densely (at least 1 inline row per 3 n-gram
rows):
- **n-gram recall against inline: 42.0%** (83,801 / 199,397 verse citations, ±1 column, ±2 verses).
  This agrees with the 38.5% against migne-notes, so 6-word Clementine matching finds about two in
  five of the citations Migne identified.
- **n-gram "precision floor": about 50% at every run length** (6 words 45%, 15+ words 50%). This is
  a floor, not precision. A sample of 15+ word rows Migne leaves uncited reads as **lemmata**:
  commentaries quote the text under comment (Rabanus on Leviticus, Rupert on Zechariah, Bruno on 1
  Cor.), and Migne doesn't cite it. A random 6-word sample is mostly genuine quotation too. The
  noise sits in repeated formulas: "patris et filii et spiritus sancti" ×476, "patrem uestrum qui
  in celis est" ×435, the doxology "honor et gloria in secula seculorum" ×265, "a solis ortu usque
  ad occasum" ×198. That is the exclusion list in step 3.

**The inline stream is not one practice** (Wilson, 2026-11-10). Each volume carries the citation
habits of whatever edition Migne reprinted and whoever edited it. Measured per volume (216 vols):
- 8 have no inline citations at all, and 19 have fewer than 1 per 10 n-gram rows.
- It is bimodal. The share of rows that are verse-level runs from 0% (PL 111, 169, 175, 203, 213,
  217: chapter only) to 99% (PL 16, 33, 70, 136, 156, 183). Deciles: 0 · .01 · .11 · .32 · .63 ·
  .78 · .92 · .96 · .98.
- The rate of citations to a verse the Clementine doesn't have reaches 14% in PL 66 and 88 (median
  about 1%). Those editors used different numbering. Flagged here; not chased.

So:
- the pooled figures above (42% recall, the 50% floor) are averages over different practices. Any
  calibration that matters is per volume, or better per source edition.
- verse-level calibration is only meaningful in verse-citing volumes.
- inline is a record of Migne's editors, not a gold standard. Its agreement with the n-gram stream
  is a property of each edition.
- volumes reprinted from the same edition behave alike, so the natural stratum is the source
  edition. `pl-locator.tsv` doesn't record it. A per-volume practice profile (verse share, density,
  invalid rate) is the proxy until it does.

### Per-volume practice (`spine.py profile` → `spine/volume-practice.tsv`)

Each volume is classed by its inline stream. Thresholds are first guesses, in `practice()`:
- `sparse`: under 1 inline citation per 10 n-gram rows;
- otherwise `chapter` (verse share under 0.2), `verse` (over 0.8) or `mixed`.

| practice | volumes | inline verse citations | n-gram recall |
|---|---:|---:|---:|
| verse | 75 | 155,010 | 41.8% |
| mixed | 55 | 50,633 | 42.9% |
| chapter | 65 | 3,398 | 50.4% |
| sparse | 21 | 581 | 21.5% |

The pooled 42% holds in the verse-citing volumes, but per volume it runs 23–61%. The spread follows
the **author's date**, not the editor (verse and mixed volumes):

| author died | inline verse citations | n-gram recall |
|---|---:|---:|
| ≤400 | 22,732 | 29.2% |
| 401–600 | 67,018 | 39.6% |
| 601–800 | 15,476 | 53.3% |
| 801–1000 | 25,592 | 46.5% |
| 1001–1100 | 2,726 | 50.4% |
| 1101–1200 | 48,943 | 46.1% |
| 1201+ | 3,606 | 37.2% |

Clementine matching loses most on the pre-Vulgate Fathers: the Old Latin, measured. The fuzzy
stream (step 2) should be judged on the ≤600 rows first. The 1201+ dip is small-n and unread.
Editorial practice decides what inline can calibrate (verse volumes only). The author's Bible
decides what the n-gram stream can find.

## Stream `fuzzy` (2026-11-10, `spine.py fuzzy` then `spine.py bydate`, no tokens)

For wording that departs from the Clementine (Old Latin, paraphrase, free order):
- every word is cut to its first 5 letters;
- the 150 commonest Vulgate stems are dropped;
- an index holds the ordered stem pairs (a then b within 3 words) that occur in at most 3 Vulgate
  verses: 509,005 pairs;
- a candidate is at least 3 distinct pairs on one verse within 20 words. `pairs` is the row's
  confidence.

Against Migne's inline verse citations, in verse- and mixed-practice volumes (`bydate`):

| author died | inline verse cites | ngram | fuzzy | either | ngram floor | fuzzy floor |
|---|---:|---:|---:|---:|---:|---:|
| ≤400 | 22,732 | 29.2% | 43.6% | **47.9%** | 42% | 40% |
| 401–600 | 67,018 | 39.6% | 51.7% | **57.9%** | 36% | 35% |
| 601–800 | 15,476 | 53.3% | 64.6% | **70.0%** | 48% | 43% |
| 801–1000 | 25,592 | 46.5% | 59.3% | **65.0%** | 32% | 28% |
| 1001–1100 | 2,726 | 50.4% | 64.3% | **69.1%** | 20% | 17% |
| 1101–1200 | 48,943 | 46.1% | 59.7% | **65.8%** | 30% | 25% |
| 1201+ | 3,606 | 37.2% | 57.7% | **61.5%** | 34% | 30% |
| undated | 19,550 | 40.2% | 54.8% | **60.1%** | 27% | 25% |

- Fuzzy lifts recall about 13 points in every band, at about the same precision floor as ngram
  (the floor is a floor: lemmata, see above).
- The early Fathers gain most in relative terms (29% → 48% together), but the Old Latin gap does
  not close. Pre-400 authors remain about 20 points below the Carolingians. What is left is a
  different wording, which pair matching on a Clementine index cannot reach. Closing it needs an
  Old Latin index (Vetus Latina readings; none open on disk), or the de Lubac-style reader.
- A read of pre-400 rows: at **4 pairs** the sample is nearly all genuine (Rom 7:23, Song 1:1,
  John 18:23, Ezek 14:18). At **3 pairs** it is mixed: real (Luke 3:9 *arbor… fructum… excidetur…
  ignem*, Rev 2:5, Mark 13:17) beside noise built on short common stems ("esse simul unum", "tamen
  causa adipi"). Default to 4+; keep the 3s marked low.

## Next

0. ~~Per-volume practice profile~~: done (above).
1. ~~Fuzzy stream~~: done (above). The 4-gram floor is dropped; fuzzy covers what it would have.
2. **Old Latin index** (2026-11-10). Sources, in `sources/oldlatin/` (gitignored):
   - **Corpus Corporum (Zurich) has none.** Its *Biblia* holds the Hebrew, the Clementine, the LXX,
     Nestle, the Douay and Castellio (1551).
   - **Vetus Latina Iohannes** (IGNTP, Birmingham): 37 Old Latin manuscripts of John, TEI, **CC BY
     4.0**, attribution to the IGNTP and named participants. `iohannes/`.
   - **Sabatier, *Bibliorum Sacrorum Latinae Versiones Antiquae*** (Reims 1743–49, 3 vols, public
     domain): the Old Latin beside the Vulgate for the whole Bible. Under each verse the notes list
     which Father reads what, with columns in the Maurist editions. In effect it is a per-verse
     index of patristic readings. The Archive's djvu text of all three volumes is downloaded
     (`sabatier{1,2,3}_djvu.txt`; vol. III, NT, is a Google scan). It is old OCR: long s read as f,
     ligature noise, a column layout to unpick.

   **Experiment, John only** (`scripts/oldlatin_john.py`): the Clementine pair index against the
   Clementine plus every Iohannes manuscript's reading, scanned over the 759 works of authors d. ≤600
   in verse- and mixed-practice volumes (9,084 inline John citations):

   | index | min pairs | recall d. ≤400 | recall 401–600 | John rows | on an inline cite |
   |---|---:|---:|---:|---:|---:|
   | Clementine | 3 | 44.0% | 46.6% | 11,231 | 46% |
   | Clementine + Old Latin | 3 | **51.5%** | **53.1%** | 14,950 | 43% |
   | Clementine | 4 | 36.7% | 38.2% | 8,409 | 48% |
   | Clementine + Old Latin | 4 | **43.7%** | **44.1%** | 10,425 | 49% |

   The Old Latin adds about 7 points of recall at the same precision floor. It works for John.

   **Sabatier, vol. III (NT), parsed** (`scripts/sabatier.py 3`, `notes 3`):
   - The *Versio antiqua* blocks are cut at verse numbers (OCR'd numerals repaired: "1o", "r5") and
     long s is fixed against the PL lexicon ("ipfum" → "ipsum"). Chunks are keyed to the Clementine
     by content, or by sequence after an anchor. 6,200 chunks; **4,877 of 7,953 NT verses (61%)**.
     Gospels 63–70%, 2 Pet 9%. Some of the gap is Sabatier's own: where no manuscript survived he
     stitched the text from patristic quotations ("Apoc. apud August."), so verses are missing.
   - The NOTAE are cut at verse markers ("Y. 2.", "ý. 2.") and keyed to the chapter of the page's
     Old Latin: 2,942 note sections, 2,731 verses. They hold the manuscripts' and Fathers' readings
     (Sangermanensis on Matt 25:43 "hospes eram non colligistis me"; Irenaeus on Luke 6:46).
   - **What Sabatier is:** in the Gospels and Paul the running text comes mostly from manuscripts
     (Colbertinus, a mixed text half Vulgate already; Claromontanus); elsewhere it is patchwork from
     the Fathers. The notes are the patristic record.

   **Whole NT, authors d. ≤600** (`oldlatin_john.py nt`, 54,365 inline NT verse citations):

   | index | min pairs | recall d. ≤400 | recall 401–600 | on an inline cite |
   |---|---:|---:|---:|---:|
   | Clementine | 3 | 51.0% | 57.1% | 42% |
   | + Sabatier text + Iohannes | 3 | 53.0% | 58.7% | 42% |
   | + Sabatier notes | 3 | **54.7%** | **59.9%** | 40% |
   | Clementine | 4 | 41.8% | 47.0% | 45% |
   | + all three | 4 | **46.2%** | **50.7%** | 44% |

   - Sabatier's running text adds about 1 point. Being half Vulgate already, it adds little the
     Clementine lacks.
   - Iohannes, which is pure manuscripts, gives the most per verse.
   - The notes add about 2 points at slightly lower precision.
   - Altogether the Old Latin buys about 4 points on the NT. That is real, but it is diminishing
     returns, and the early-Father gap mostly stays.
   - Likely reason: many of Migne's inline citations mark allusions and paraphrases (the 85K
     "no 5-gram" rows above), which no wording index can match. Part of the gap is how the early
     Fathers cite, not only which Bible they read. That is a finding in itself, not a parser fault.
   - The ceilings are OCR (the Google layer; a Tesseract re-read of Sabatier is ~3,300 pages, ~3
     h) and notes coverage (2,942 sections caught; the volume has more).
   - Not yet done: Sabatier I–II (OT), with the Psalms in several versions.

   **Tesseract re-OCR of Sabatier** (2026-11-10, 400 dpi, `lat`, `pg_latin_ocr.py --pdf`; vol. III
   1,157 pp., vol. I 1,022, vol. II 1,126; about 110 pp. a minute on bilevel scans):
   - The words are cleaner, but Tesseract's page layout yields fewer clean *Versio antiqua* blocks
     (693 against 1,034 from the Archive text). Header variants ("VERS10", "ANTIQU A", "VERSIO
     ALTERA") were widened to match.
   - Keyed verses: Tesseract 3,720, djvu 5,029, **union 6,003 of 7,953 (75%)**. Notes: union 3,725
     verses. `sabatier.py` writes both (`--djvu` gives the `-djvu` files) and the index takes the
     union.
   - **Recall does not move:** everything combined gives 54.0% (d. ≤400) and 58.9% (401–600) at 3
     pairs, against 54.7% and 59.9% from the djvu text alone, with precision down to 38%.
   - So the OCR is not the bottleneck. **Stop investing in Sabatier for recall.** Its value from
     here is the notes as a per-verse record of who read what, a check on the spine, not as an
     index.
   - The default Old Latin index is Clementine + Iohannes + Sabatier text (union).
   - OT vols. I–II are OCR'd and unparsed. Parse them only if the OT recall question needs it.
3. Precision: the formula exclusion list. **Proposed 2026-11-10** (`scripts/exclusions.py` →
   `exclusions-proposed.tsv`): 354 runs found in 25+ works, which Migne cites inline at under 25%
   of their occurrences. They cover 34,436 of the 639,794 n-gram rows. A low Migne rate is not
   noise, though. The list holds three kinds, and the `ruling` column takes one of these:
   - `exclude`: liturgical and doxological formulas, not a citation event ("patris et filii et
     spiritus sancti" ×1,148; "honor et gloria in secula seculorum"; "dei et domini nostri iesu
     christi"; "gloria et imperium in secula seculorum").
   - `keep`: quotations too famous to cite ("panem nostrum quotidianum", "in manus tuas commendo
     spiritum meum", "oculum pro oculo").
   - `parallel`: real quotations whose verse the words cannot decide (synoptic triples; Ps 13:3 =
     Rom 3:12; Ps 109:4 = Heb 5:6 = Heb 7:17). Keep the citation and leave the verse open as a set.

   Wilson or a reader rules on the top of the list. The tail can follow by pattern. Then a lemma flag for commentaries, so that the text under comment is counted apart
   from quotation.
4. Merge: one spine row per (work, column, verse), carrying which streams found it.
