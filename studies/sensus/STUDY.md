# `sensus` — de Lubac's four senses, counted

Started 2026-11-09. The design is `../../PLAN.md` section 5 (rulings S1–S4, stages A–G); this file
is the Study's working record. Amend rulings by number there, not here.

## 1. The question

Henri de Lubac argued from thousands of hand-picked passages that the fathers and the medievals
read Scripture in four senses that are really one movement. What does every exposition in the
Latin and Greek fathers show when it is read against that claim?

## 2. Layers

- **Used:** the PL TEI (`~/patrologia/sources/pl/tei/`, 5,276 files) and its works index
  (`~/patrologia/data/cc-pl-index.json`); the PG tome-author table
  (`~/patrologia/data/pg-tome-authors.json`, tome level only).
- **Produced so far:** a PL locator, volume and column to work (`data/pl-locator.tsv`,
  `data/pl-columns.json`; 5,204 works across all 217 volumes). Any project that has to turn a
  "PL 76, 843" into a text can use it. And the de Lubac ledger, below.

## 3. Stage A: de Lubac's footnotes as a ledger

### 3.1 The edition in hand (answers PLAN section 8, item 1)

*Exégèse médiévale: les quatre sens de l'Écriture*, Aubier (the "Théologie" series), French, all
four volumes, as Internet Archive scans of the Claremont School of Theology copies, each with an
OCR text layer. Wilson supplied them 2026-11-09; the originals are still in `~/Downloads`.

| file | volume | cited here as | printed pages | PDF pages |
|---|---|---|---|---|
| `em1.pdf` | Première partie, tome I (1959) | I/1 | to 366 | 378 |
| `em2.pdf` | Première partie, tome II (1959) | I/2 | 373–710 (continuous with I/1) | 352 |
| `em3.pdf` | Seconde partie, tome I (1961) | II/1 | to 562 | 574 |
| `em4.pdf` | Seconde partie, tome II (1964) | II/2 | to 552 | 570 |

His list of abbreviations is at I/2 pp. 683–5 (journals and collections, not patristic works), with
a supplement at the end of II/1. The index of proper names for Part I is at I/2 pp. 687–710, and
for Part II at II/2 pp. 517–552.

⛔ **The book is in copyright** (de Lubac died in 1991). The PDFs and the extracted text live in
`sources/`, and the Latin he quotes in `working/`; both are listed in `.gitignore` and neither is
ever published or pushed. The ledger is pointer-only: where he cites a passage is a fact, and his
words are not stored. `cited_as` (his abbreviated author and work) and `raw` (the reference as
printed) are working columns; review them before any export.

### 3.2 Method (all computation, no model tokens)

Run in this order from `studies/sensus/`. Use `python3 -I`, because the text comes from downloaded
files.

1. `scripts/pl_locator.py` builds the locator from the TEI `<pb n="0473A"/>` marks.
2. `scripts/harvest_refs.py` reads the four text files page by page. It maps each PDF page to its
   printed page from the running head, finds the footnote zone, splits it into notes, and takes
   every reference in three forms:
   - **explicit**: `(PL, CVII, 406 BC)`;
   - **bare**: `(CXCVIII, 1046 B)`. De Lubac drops the siglum freely, above all in Part II;
   - **column only**: `(312-4)`, a number with no volume.
   Roman numerals are repaired where the OCR damaged them (`CXCVIIL`, `XXKVI`), and each repair is
   flagged. A bare reference takes its series from the last siglum before it in the same note, so
   a bare number after `CCL` is not counted as Migne. A column-only reference takes its volume
   from an earlier reference in the same note, and only if the column lies inside that same work.
3. `scripts/verify_quotes.py` runs the one check that tests everything at once. Where de Lubac
   prints the Latin before the reference (about a quarter of the references), that Latin should
   stand in the TEI at that column. A match confirms volume, column and work together.
4. `scripts/summarize.py` writes `ledger/SUMMARY.md`.

### 3.3 What the harvest found (2026-11-09)

Full tables in `ledger/SUMMARY.md`. In short:

Numbers as of the harvest fix after the pilot (3.6), 2026-11-09:

- **9,011 references in the ledger:** 4,347 PL with the siglum, 3,627 PL with it dropped, 641
  column-only with the volume carried, 322 PG, 74 bare references that belong to another series.
  (The first harvest found 7,690. The pilot showed it dropped every column after the first in a
  list such as "(PL, LIV, 290 A, 311 B)", plus some damaged numerals; 3.6.)
- **8,304 of the 8,615 PL references resolve to a work** in the TEI: 347 author headings, 1,225
  works, 197 of the 217 volumes.
- **The quote check confirms 1,604 of 1,860 at the column (86%).** By form: explicit 88%, bare 85
  to 87%, carried 78%. Another 31 stand in the same work at a different column, which is either an
  OCR digit error or a slip of de Lubac's; the rest were not found. List items carry no quotation;
  95% of them resolve to a work, and 83% to the same work as the item before.
- **A first reading map already exists.** Gregory the Great and Rupert of Deutz lead (546 and
  507), then Augustine, Jerome, Rabanus, Bede, Hugh of St Victor. By the author's death, 36% of
  the resolved references are twelfth-century and 16% ninth-century.

### 3.4 What the ledger does not yet hold (read before quoting any number above)

1. **The map undercounts everyone he cites from a critical edition.** Origen is the clearest case:
   he is central to the book and nearly absent from the table, because de Lubac cites him by page
   of the Berlin edition, and those references fall in the column-only residue. Augustine and
   Jerome are undercounted for the same reason (Corpus Christianorum). The author table is a map of
   his *Migne* references only until item 2 is done.
2. **Column-only residue: 2,252 references with no volume** (679 with a band letter, so surely
   Migne; 1,573 bare numbers that may be a Migne column, an edition's page, or a folio). They are
   in `ledger/colonly.tsv`. Assigning each to a work takes a reader with the note in view; the
   pilot did it reliably (3.6).
3. **About 600 ledger references need a look at the printed page:** 53 unreadable
   volume numerals, 222 columns absent from the TEI (some are Migne's prefatory matter, which
   Corpus Corporum does not carry; some are OCR), 31 low volume numbers that may be a modern
   work's "(II, 164)", and the 256 that failed the quote check.
4. **5,300 resolved references have no quotation to check.** Their error rate is unmeasured. The
   quote check bounds it loosely: at most 14% of checked references failed, and some of those are
   mismatched quotations, not wrong references.
5. **Note numbers are approximate.** The OCR loses some note numerals; 514 references have no note
   number and others may be off by one. Page numbers are sound (1,623 of 1,878 read from the
   running head, the rest from the offset).
6. **A known trap, flagged and not yet settled:** a bare "(XXXVIII, 123)" may be Corpus
   Christianorum 38 and not PL 38. The `ccl_collision` column marks the candidates. The list of
   CCL volumes behind it was written from memory and needs checking against a catalogue.
7. **Rules that were tried and thrown out.** Carrying a volume across notes on the same page:
   the quote check confirmed 29% (60 of 207), so the rule was removed.
8. **Upstream data, flagged and left:** the works index dates "Guillelmus abbas" to 1268, which
   looks wrong for William of Saint-Thierry; 405 references sit under undated headings
   ("Auctor incertus"). Pseudonymous works sit under the heading Migne gave them.
9. **PG references are resolved to the tome only.**

### 3.5 What stage A still owes, and what it costs

The plan asks for the *claim each passage is cited for*. That, and items 1 to 3 above, need a
reader, so they are one model pass over the book and a **hard stop**:

- **The pass:** each of the 1,622 pages that carry notes, read once, with that page's ledger rows
  beside it. For each note the reader returns (a) corrections to the harvested references, (b) the
  work and volume for each column-only reference, checked against the locator afterwards, and (c)
  what the passage is cited for, in the record form below.
- **Estimated burn, corrected by the pilot:** the pilot measured about 6,000 input and 3,200 output
  tokens per page at Opus 5.5, effort high (output includes thinking). Over 1,622 pages that is
  about 9.7M in and 5.2M out for one coder, about **$145 at Opus 5.5 ($4/$20), about $73 with the
  Batch API**. Sonnet 5.5 would be half that. The first estimate (3M / 0.8M) left out thinking and
  the ledger rows sent with each page. Chapter VI is dense in notes, so the average page may be
  cheaper. One-shot per-page work, so it goes through the direct API, not agents.
- **Before the pass, a pilot on one chapter** to settle the record form. Proposed form, for Wilson
  to rule on:

  ```
  { ref_id,                  // the ledger row
    role,                    // example | theory | vocabulary | history | other
    senses: [],              // the senses de Lubac says are in play, in his order (S1)
    authorLabel,             // the source's own term if he quotes it, verbatim (S2)
    scripture,               // refKey of the verse under exposition, or null
    cited_for }              // one line, our words, none of his
  ```

  `role` matters because many of his references are not examples of a reading at all: they attest
  a word, state the theory, or establish a date. Only `example` rows can serve as the gold set for
  stage D.
- **Blind control:** two independent codings of the pilot chapter before the volume run, per the
  rule in PLAN section 4.

### 3.6 The pilot (2026-11-09)

I/2, chapter VI, "Les noms des sens bibliques" (PDF pp. 9–60; 50 pages carry references).
Two independent codings, coder A and coder B, both Claude Opus 5.5 at effort high, neither shown
the other's output. Script `scripts/pilot_read.py`; agreement `scripts/pilot_agree.py`; outputs,
agreement table and disagreements in `working/pilot/` (gitignored: they echo his reference
strings). The ledger as the coders saw it is kept in `working/pilot/ledger-at-pilot/`, because the
row ids changed when the harvest was fixed. Cost: 600,710 input and 325,380 output tokens,
**$8.91** for both codings.

- **Agreement is high where the field is factual.** Role: kappa 0.91 over 447 rows. Verdict on the
  harvested reference: 99%. Kind of a column-only number: kappa 0.98. Volume and work assigned to
  column-only rows: 86%. Scripture verse: 95–96%.
- **Agreement is lower where the codebook is silent:** senses 86–87%, the source's own label
  81–85%. The disagreements are about convention, not reading; 4 below.
- **The coders corrected 25–28 harvested references** (OCR volumes, misparses) and threw out 1–3.
- **The harvest was undercounting.** Each coder listed about 230 references the harvest missed,
  about 100 of them PL with volume and column. Located causes: the columns after the first in a
  list; a list after a bare reference; OCR "W" and split numerals ("XXXWVIII", "XXX VIII"); "8o"
  for 80; arabic volumes ("(184, 706 C)"); a lost comma. All fixed in `harvest_refs.py`, with the
  quote-check rates unchanged. The fixed harvest catches about 80 of the 100. One bad rule was
  caught on the way: allowing a list after a bare reference first read "(CCL, 40, ...)" as PL 201.
  Series sigla are now barred from being read as numerals.
- **The role mix of this chapter:** vocabulary 46%, theory 23%, other 16%, example 14%, history
  1%. Expected for a chapter on the names of the senses; it says nothing yet about the book.

**Rulings the pilot needs (Wilson), before the full pass:**

1. **A definition of allegory** ("one thing said, another meant"), or a reading that sets the
   letter aside to reach the figure: senses `[letter, allegory]` (the movement, per S1) or
   `[allegory]` alone? The coders split on this more than on anything else.
2. **Pagan allegory** (Homer, the Stoics, myth), cited for contrast: code its senses, or leave
   senses empty because no scripture is being read?
3. **The source's label:** every term it uses ("secundum litteram; allegorica; spiritus"), or only
   the term for the sense in question? Verbatim form, or lemma?
4. **"Spiritual" versus a named sense:** when the source says *spiritualiter* and de Lubac glosses it
   as allegory, which is recorded: the source's word (`spiritual`) or his gloss?

### 3.7 The pilot rerun with R1–R7, and the Part I pass (2026-11-09)

Same chapter, two blind Opus 5.5 codings, effort high, through the Batch API: **$5.75**. Output
in `working/pilot2/`. Against the first pilot: senses 86% → 91% (harvested rows) and 87% → 93%
(column-only); label 81–85% → 86–89%; role kappa unchanged at 0.91. New fields: stance 98–100%,
allegory kind 92–96%, `term_differs` 94–95%. The gate Wilson set (kappa ≥ 0.85, senses ≥ 90%) passed.
Measured cost with the R1–R7 codebook: about $0.0575 a page on Batch.

**Part I pass, one coder, submitted 2026-11-09:** I/1 whole and I/2 chapters VII–IX, 528 pages,
about $30 (batch `msgbatch_01GmCd7s2sMhRBgEkskmzrwb`, output `working/partI/A/`). I/2
chapter X (PDF pp. 257–352, 59 pages) was held for credit margin, then run 2026-11-10: ✅ 59/59
pages, **$2.91** (432K in, 204K out; batch `msgbatch_01GPybvXqjvctnJTqC92j9vw`). Part I is now
complete: 7,875 claims rows; cross-check agree 525, differ 61. Part II: see below.

**Part II pass, 2026-11-10** (Wilson refilled credit): II/1 and II/2, all 984 pages with citations,
one batch (`msgbatch_016p8KXM3aw5Z7XYfteaA2XM`), Opus 5.5 high, codebook R1–R7. ✅ 984/984 pages,
**$39.16** (6.94M in, 2.53M out; under the $57 estimate). `ledger/claims-partII.tsv`, 9,166 rows,
51 dropped by the reader; `ledger/READING-MAP-partII.md`. Part II reaches past the PL into the
13th–16th centuries (Erasmus, Roger Bacon, Lefèvre, Gerson, Ficino), so 179 aliases went into
`data/author-aliases.tsv` (mostly `hand`; 17 modern scholars). Cross-check now agree 1,009, differ
62 (Part I: 528 / 58). Still unmatched: 503 rows under 511 names, mostly single mentions.
Part II examples lead with Rupert (144), Augustine (125), Joachim (100); 12th century 35%.

**Part I pass, returned 2026-11-09:** all 528 pages with valid JSON, **$27.73** (3.97M in, 1.98M
out). `scripts/merge_pass.py partI A` writes **`ledger/claims-partI.tsv`: 7,195 coded rows**
(harvested 4,062, column-only 1,260, references the reader found that the harvest missed 1,873).
41 harvested rows came back uncoded (`working/partI/dropped-A.txt`). The reader corrected 413
harvested references (10%) and threw out 17.
- Roles: vocabulary 1,801, other 1,690, example 1,570, theory 1,476, history 675.
- **1,563 examples** (readings of a text), 918 with a verse key. Movements: letter > allegory 356,
  spiritual 288, allegory 263, letter > spiritual 160, tropology 153, allegory > tropology 89; the
  full four-step letter > allegory > tropology > anagogy only 20.
- **The critical-edition hole is visible:** among examples the reader coded from column-only and
  missed references, Origen leads (about 147), then Jerome and Augustine. Among examples resolved
  through the PL: Rupert 68, Gregory 66, Rabanus 57, Bernard 47, Augustine 44, Bede 40.
- One coder only: no agreement figure for Part I beyond the pilot's.

**Clean-ups, no tokens (2026-11-09):** `scripts/enrich_claims.py partI` (run after
`merge_pass.py`) rewrites the claims file with:
- **Locations resolved:** every PL location the reader supplied goes through the locator: 333
  missed references, 202 column-only rows, 325 corrected harvest rows; 21 columns not in the TEI.
- **Authors normalized:** the reader's 716 free-text names map to the Corpus Corporum headings
  (`scripts/authors.py` + `data/author-aliases.tsv`, about 240 aliases). Authors outside the PL
  index get a Latin heading and a death year marked `hand` (general knowledge, unchecked). Left:
  278 rows of a long tail of names used once or twice, 469 with no author, 24 modern scholars
  (excluded from the map).
- **Cross-check:** where both exist, the locator's author agrees with the reader's in 483 of 528
  (91%). The 45 that differ are mostly real attribution questions (Pseudo-Richard vs Hugh,
  *Glossa* vs Anselm of Laon) and some wrong reader volumes; they are flagged `loc_vs_reader =
  differ`, and the locator's author is kept.
- **`ledger/READING-MAP-partI.md`:** in Part I, **Origen leads the examples** (161), then
  Augustine 86, Rupert 79, Gregory 75, Jerome 68, Bernard 66, Rabanus 65, Bede 57. By century,
  examples are 36% twelfth-century, 13% fifth, 12% third (almost all Origen), 11% ninth. The
  Migne-only table (3.3) had Origen nearly absent: the reader pass is what puts him back.

### 3.8 Cheaper models tested on the pilot chapter (2026-11-09)

Sonnet 5.5 (coder S) and Haiku 5.5 (coder H), effort high, the same codebook, one Batch coding
each of I/2 ch. VI: **$1.12 and $0.22**. Each was scored against both Opus codings; the Opus-vs-Opus
agreement (A vs B) is the ceiling. `working/pilot2/agreement-{AB,SA,SB,HA,HB}.md`.

| field | Opus vs Opus | Sonnet vs Opus | Haiku vs Opus |
|---|---:|---:|---:|
| role (kappa) | 0.91 | 0.79–0.81 | 0.66–0.68 |
| senses | 91% | 79–80% | 70–71% |
| allegory kind | 92% | 87–88% | 74–76% |
| stance | 98% | 78–79% | 88% |
| source's label | 86% | 69–70% | 59–64% |
| work for column-only rows | 89% | 72–74% | 72% |

Sonnet's stance gap is systematic (it calls 153 rows `reported` where Opus calls about 65), so a
prompt note might close that one; the senses gap, the field the Study exists for, is the larger
and is not one pattern. Haiku is cheap but well below. **Result: Opus stays the coder.** Mixing
models across the book would put a 10-point consistency step at the boundary.

## 4. Codebook and rulings

S1–S4 in PLAN 5.2. Study rulings R1–R7 below, all approved by Wilson 2026-11-09: R3–R6 are his
rulings on the pilot (3.6); R1, R2 and R7 are the allegory definition he asked to have fleshed out.
The coder's prompt carries them as codebook "R1-R7 2026-11-09".

**The senses** (the medieval distich de Lubac starts from: *littera gesta docet, quid credas
allegoria, moralis quid agas, quo tendas anagogia*):

| code | what the passage reads in the text |
|---|---|
| `letter` | what happened or was said; includes a figure of speech when the source or de Lubac counts it with the letter |
| `allegory` | what the things and events signify of Christ and the Church: what to believe |
| `tropology` | what they signify for the soul's conduct: what to do |
| `anagogy` | what they signify of the last things: where we are headed |
| `spiritual` | an undivided spiritual sense, when none of the three is named or meant |
| `other` | a sense outside the scheme (say which in `cited_for`) |

**R1. Allegory has a kind.** Every row whose senses include `allegory` takes `allegory_kind`:
- `in_factis`: the thing or event told signifies another (Augustine's *in facto, non in verbo*;
  Ambrose; Bede). Senses `[letter, allegory]`: the letter is the first step of the movement (S1).
  This is the Christian allegory of de Lubac's thesis, and the default for a narrative.
- `in_verbis`: a figure of speech, words saying one thing and meaning another (the grammarians'
  trope). Senses `[allegory]`, no history to pass through; but `[letter]` alone if the source or
  de Lubac counts the figure with the letter.
- `mythic`: pagan allegory of myths (Homer, the Stoics; physical or moral). Senses `[allegory]`.
- `letter_denying`: allegory that abolishes or bypasses the letter. Senses `[allegory]`.
- `unspecified`: the word is used without showing which.
**R2. Stance.** Every row takes `stance`: `endorsed`, `rejected` or `reported`, the cited
source's stance toward the reading it names. Origen censuring letter-denying allegory is
`[allegory]`, `letter_denying`, `rejected`; it is not an empty sense list.
**R3. Pagans are coded** like anyone else: senses as read, `scripture` empty.
**R4. The source's label records all its terms** for the sense, verbatim as printed, separated
by "; ".
**R5. Senses use de Lubac's term.** `term_differs` is true when the source's own word names a
different sense, or one outside the scheme (*mystice*, *spiritualiter*, *anagoge* where he says
allegory). The word itself is in the label (R4).
**R6. A compound naming one sense is one sense:** *spiritalis allegoria*, *mystica allegoria* →
`[allegory]`, both words in the label.
**R7. A figurative reading with no sense named** (the breasts of the Song as preachers) is coded
by the table above, confidence at most medium.

## 5. Ledger

`ledger/refs.tsv` (one row per reference: de Lubac's tome, page, note; series, volume, column,
band; work, author and year from the locator; status), `ledger/quote-check.tsv`,
`ledger/colonly.tsv`, `ledger/notes.tsv`, `ledger/pages.tsv`, `ledger/SUMMARY.md`.

## 6. The finding

None yet. Stage A's own finding will be the reading map: which authors and centuries carry his
argument, and which he passed over. It could come out otherwise than the Migne-only table
suggests, because the critical-edition citations are not yet in it.

## 7. Outputs owed

Scholarly and pastoral, as in PLAN 5.4. Nothing is published from this Study yet.

**Attribution layer (2026-11-10).** Every claims row now carries `author_printed` (the heading the
PL prints), `author_alt` (the other candidate) and `attrib_status`: `ruled` where
`data/author-rulings.tsv` chose de Lubac's attribution, `open` where Wilson has not ruled. Open
cases live in `data/attributions-open.tsv` and count under a joint heading until a confirmation
pass settles them. First open case: **Haymo of Halberstadt / Haimo of Auxerre**, 121 rows (38
examples), counted as "Haymo (Halberstatensis / Antissiodorensis)". Wilson: keep both, confirm
later. Both died in the 9th century, so the century tables do not depend on it. The confirmation
pass is `attrib_status != ''` in any claims file.

## 8. Stage B: the vocabulary census (2026-11-10)

`scripts/census.py` (no tokens, 21 s) over all 5,276 PL TEI files, 87.1M words. Output in
`census/`: `CENSUS.md` (totals, variants, core terms per million words by century, formulas),
`terms-by-work.tsv`, `terms-by-century.tsv`, `formulas.tsv` (each place with volume, column and a
Latin snippet; the PL is public domain).

- **Terms.** The plan's starter list, opened to 36 terms in five families (L, A, T, N, S). Each is
  graded `core` (technical: *allegorice, tropologia, anagoge, ad litteram, spiritualiter*…) or
  `broad` (common words that often name a sense: *historia, littera, figura, mysterium,
  sacramentum, typus, mysticus, moralis, spiritualis*; read as upper bounds). **Frozen by Wilson 2026-11-10 at 41 terms**: added
  *iuxta/secundum historiam* (838), *mystica intelligentia / mysticus sensus* (410), *sensus moralis /
  moralis intelligentia* (195), *parabolice* (98), *allegorizare* (48), *theoria* (303) and
  *theorice* (8), the last two filed under S as the bridge to the Greek census. *littera,
  sacramentum, mysterium* stay counted but never enter rates or the formula test.
- **Stated formulas:** three or more of L, A, T, N within 60 words, from core terms plus
  *historia*. 269 places on the frozen list (251 before); 85 name all four. Hugh of St-Victor leads (26), then Rabanus (18),
  Honorius (12). Spot-checked hits: Cassian, *Conl.* XIV.8 (PL 49, 962 C); Eucherius, *Formulae*
  (PL 50, 728 B); Bede, *De schematibus* (PL 90, 185 B); Guibert, *Quo ordine sermo* (PL 156, 25 D).
- **Shape, first read.** The technical vocabulary jumps in the 8th–9th centuries (Bede, the
  Carolingians: *mystice* 128 per million words in the 8th century against 15 in the 7th) and is
  densest in the 12th by volume (111 of the 269 formulas). Centuries after the 13th hold under 0.5M
  words in the PL and their rates mean nothing.
- **Variants.** *spiritalis* against *spiritualis*: 36% *spirit-* overall. *intellegentia*
  barely occurs (14 files): Corpus Corporum's text is normalized ("Classical Latin orthography" in
  every header), so that variant cannot be studied from this text.
- **Limits.** Migne's editorial matter is counted with the work it sits in. Authors and years come
  from the PL locator, so the century table carries the PL's attributions (11.4M words undated).
  A formula is a co-occurrence, not yet a read statement of theory: stage D reads them.

## 9. Stage D, first pass: what the stated formulas say (2026-11-10)

The 269 census formulas (section 8), each with ~1,900 characters of Latin, read twice blind by
Opus 5.5 (codebook F1 in `scripts/formulas_read.py`; batches `msgbatch_01FBLL9ztfRs7ygfXss3VrYG`,
`msgbatch_01McYKndsv3pMMcx24SFzJjF`; **$6.32** for both, estimate was $10–16). Merged by
`scripts/formulas_merge.py` → `ledger/formulas-coded.tsv`, `ledger/FORMULAS.md`.

- **Agreement:** kind 257/269 (kappa 0.93); scheme (senses in order of first mention)
  250/269; stated number 265/269 once 'quatuor' = 4; authority 258/269.
  - The 12 kind splits were ruled by one recorded rule (R-kind): a passage that states the
    number of senses or defines one is theory.
- **What the 269 are:** 132 theory, 68 list, 62 application, 5 quotation, 2 false hits. So
  the census's co-occurrence test finds a statement of theory about half the time.
- **The schemes:** L-A-T-N is the most common of 137 (36); L-A-T has 23.
  - Gregory's L-T-A order appears 4 times, and L-T-A-N 4 times.
  - 45 passages state "four" and 33 "three".
- **Earliest four-fold statements in the PL:** Cassian (*Conl.* XIV.8, PL 49, 962 C; order
  history, then tropology, allegory, anagoge), then Eucherius (*Formulae*, PL 50, 728 B), then
  Bede. The canonical L-A-T-N order is first stated by Bede (*De tabernaculo*, PL 91, 410 B),
  then Amalarius and Rabanus.
- **Authorities invoked:** Gregory (7) and Augustine (5) lead. **Figures:** Jerusalem 28
  passages; the four feet of the tabernacle table 5.
- **Caveats:** this is the PL only, and only what the census window catches. A scheme laid out
  over a longer passage, or stated with terms outside the frozen list, is missed. Authors carry
  the PL's attributions (Haymo is open; see the attribution layer).

## 10. Stage D, second step: the formulas against de Lubac (2026-11-10, no tokens)

`scripts/formulas_vs_lubac.py` matches the 269 formulas against de Lubac's PL citations by
volume and column (±1 column). Ledgers: `ledger/formulas-vs-lubac.tsv` (one row per formula),
`ledger/lubac-theory-vs-census.tsv` (one row per de Lubac theory citation) and
`ledger/lubac-theory-misses.tsv` (one row per miss, with its cause).

**Census → de Lubac.** Of the 132 theory formulas:
- de Lubac cites 96 for theory and 12 for another role;
- 5 more are cited for theory by the same author within 10 columns (Lyra's prologue: he cites
  113, 28; the formula is 113, 33 C);
- 8 belong to authors he cites for theory without a PL column (Eucherius among them);
- **11 he does not cite at all:**
  - F002 Bruno Carth., 152, 957 C
  - F006 Radulfus Ardens, 155, 1899 A
  - F022 Hildebert, 171, 681 A (the four-legged table)
  - F039 anon. (Hugh?), 175, 664 B
  - F080 anon., 177, 1196 D
  - F094, F095, F097 Wolbero, 195, 1035–1150
  - F195 anon. (Cassiodorus?), 70, 1077 B
  - F217 Sedulius, 103, 155 D
  - F269 Atto, 134, 433 C

  These are candidates, not findings yet. The anonymous ones may sit in his apparatus under an
  attributed name, and he may cite another edition. A reader confirms them before any of them is
  called something de Lubac missed. The table figure (F022, F039, F080) he does know: he cites it
  in Rabanus on Chronicles, 109, 449.

**De Lubac → census.** He has 1,843 PL theory citations (1,360 distinct loci). The census's
three-sense window can only be asked about the ones where he says three or more senses are named.
Of those, **222 of 440 (50%) land on a census formula**. For two-sense and one-sense citations the
figures are 9% and 13%, as expected, since the census never looked for them.

**Why the census misses the other 218** (172 loci, re-read at the TEI with the census's own term
list; the first test a locus passes is its cause):

| cause | loci | citations |
|---|---:|---:|
| window: formula-grade terms for 3 of L/A/T/N in the columns, never within 60 words | 20 | 27 |
| broad: reaches 3 within 60 words once moralis, mysticus, littera… count | 42 | 60 |
| S: reaches 3 once the spiritual family counts as a sense | 19 | 25 |
| wide: reaches 3 only within 200 words | 17 | 21 |
| no terms: under 3 families anywhere in the three columns | 64 | 71 |
| no text: the column is not in the TEI | 10 | 14 |

So about half the misses (98 loci) are a rule of the census: admitting broad terms, the S family,
or a wider window would find them. The cost is precision, which the 269 currently do not
pay. The 64 "no terms" loci are where de Lubac reads a scheme the vocabulary doesn't name:
- figures: the three modes of cooking the sacrifices, four casks in a cellar, shadow / image /
  truth, the threefold coming of Christ;
- or his column is off. A sample shows at least one locator error: "Cyprianus, 4, 464" is
  Irimbert's *In Ruth* in Pez, *Thesaurus* IV, read as PL 4. This is the stage A locator; flagged,
  not chased.

A vocabulary census over this corpus can find stated formulas. It cannot find figured ones. Those
are de Lubac's own contribution, and the ledger is the only place they are counted.

## 11. The Latin Origen: PG 12–14 (2026-11-10, no tokens)

**Text.** Tesseract 5, `lat+grc` at 300 dpi, over 2,632 pages (`scripts/pg_latin_ocr.py`).
`scripts/pg_latin_clean.py` then:
- keeps the Latin lines;
- rejoins hyphenated line ends;
- repairs the systematic errors (ae read as z/x, c/e, n/u, rn/m) only where the repair is a PL word
  (lexicon: every form occurring twice in the PL TEI, `sources/pl-lexicon.txt`);
- assigns PG columns from the running heads (column = 2 × page index + the windowed mode of the
  offsets; spot-checked at 587, 991 and 1699);
- tags each page **Latin-only** (the ancient translations: Rufinus, Jerome, the old Latin Matthew
  series) or **bilingual** (Greek with Migne's facing Latin, i.e. early-modern humanist
  translations).

**94–95% of Latin words are PL words** (about 3% by rule). The residue is 5–6%, so counts are a
lower bound; the sense terms are long and survive OCR well. Front matter (the roman-paginated
prefaces) and index pages are excluded. They are the editors' own Latin: Delarue summarises Origen
as "Triplex est scripturae sensus, litteralis, moralis, et mysticus seu allegoricus". Migne's
footnotes cannot be separated cheaply and remain; the residual *litteralis* (1.3 per 100K, a word
Rufinus does not use) is the trace of them.

`scripts/pg_census.py la|bi` → `census/pg-terms-{la,bi}.tsv`, `census/pg-formulas-{la,bi}.tsv`.
Per 100K words:

| term | Latin-only (862K words) | humanist (606K) | PL, cent. 2–5 |
|---|---:|---:|---:|
| iuxta/secundum litteram | **13.6** | 3.0 | 1.8 |
| spiritualiter | **11.6** | 6.1 | 5.6 |
| allegoria | **7.0** | 3.0 | 1.4 |
| spiritualis intelligentia | **5.0** | 0.5 | 0.9 |
| allegoricus | 5.0 | 1.2 | 0.7 |
| moraliter | **2.6** | 3.1 | 0.2 |
| iuxta/secundum historiam | 2.2 | 2.5 | 1.0 |
| tropologia | 0.7 | 2.1 | 1.1 |
| anagoge | 0.3 | **3.1** | 0.6 |

**Findings (provisional):**
- **The ancient Latin Origen speaks in two levels, letter against spirit**, and far more densely
  than the Latin Fathers of his own centuries: *secundum litteram* 7.5×, *spiritualis
  intelligentia* 5.5×, *allegoria* 5×, *moraliter* about 13×. If Latin spiritual exegesis learned
  its vocabulary somewhere, these translations are a prime candidate. That is de Lubac's thesis,
  now with a rate.
- **The technical names are rare in the ancient translations** (*anagoge* 0.3, *tropologia*
  0.7, below the early PL) and common in the humanist Latin of the Greek works (*anagoge* 3.1,
  *tropologia* 2.1). The Greek Origen used ἀναγωγή and τροπολογία. Rufinus and Jerome mostly
  rendered them as *spiritualis intelligentia* and *moraliter*. This is a translator's effect, to be
  checked against the Greek (G3).
- **Only 4 stated formulas** (three or more of L/A/T/N within 60 words) in the ancient
  translations, 2 in the humanist ones. Origen's scheme is not stated in the medieval terms; it is
  carried by the letter/spirit pair and by figures, as in section 10.
- **The Greek side, first look** (2026-11-10). The Greek lines of the 1,083 bilingual pages of PG
  13–14 (Tesseract `grc`, not Kraken: 350K Greek words, normalized without accents; a lower bound)
  give these rates per 100K words: ἀναγωγ- **12.6**, τροπολογ- **10.3**, ἀλληγορ- 7.4, θεωρ- 61.4,
  ἱστορ- 32.6, πνευματικ- 10.3, σωματικ- 7.7. Against *anagoge* 0.3 and *tropologia* 0.7 in the
  ancient Latin translations, **the Greek Origen uses the technical names some 15–40 times as
  often.** The contexts are his own usage ("κατὰ δὲ τὴν ἀναγωγήν", "πρὸς ἀναγωγήν", "τροπολογεῖ",
  "ἀλληγορητέον"). The translator's effect holds at this grain. Caveat: the Greek and the Latin are
  mostly different works (the Greek Matthew and John commentaries and the Jeremiah homilies,
  against Rufinus's Genesis–Judges, Song and Romans). **The decisive test is a work extant in
  both:** the Jeremiah homilies (Greek, and Jerome's Latin of part of them), set side by side.
- PatroLLM triage, planned for the census windows, is not needed at this grain. Six formula
  windows can be read by eye, and the term counts are lexicon words, not the real-word residue
  where the scorer helps.

## Next

1. Part I is in `ledger/claims-partI.tsv`, enriched, with `ledger/READING-MAP-partI.md` (3.7).
   Part I complete with chapter X (2026-11-10). Open: check the `hand` death years; rule the 58
   locator-vs-reader author differences; 274 reader rows still unmatched.
2. Part II coded 2026-11-10 ($39.16), `ledger/claims-partII.tsv`. Stage A's reading pass is
   complete. Open: 62 author differences, 511 unmatched names (long tail), `hand` years.
3. Stage B done (section 8); stage D first pass done (section 9); D against de Lubac done
   (section 10). Open for D: a reader confirms the 11 uncited theory formulas. Optionally a
   relaxed census (broad + S, 60 words) priced by its precision on a sample. And Wilson's read
   of the earliest statements.
4. `LAYERS.md` (PLAN section 7, item 1) is still unwritten.
5. Editions beyond Migne (2026-11-09), in `sources/editions/` (public domain, gitignored):
   PG 12, 13, 14 (Latin Origen; only PG 12's OCR reads the Latin, 13 and 14 need a Latin OCR),
   *Maxima Bibliotheca Veterum Patrum* XIII (Lyon 1677; Ambrose Autpert, as "Ansbertus"),
   Aponius on the Song (Rome 1843). Not on the Internet Archive: Beatus (Sanders 1930),
   Apringius (Férotin 1900).
   **The Latin OCR for PG 12–14: Tesseract, not vision** (tested 2026-11-10, no tokens). The
   Archive's text of PG 13 reads the Latin as Greek ("εὐπίδηδα, οἱ 58Πη016"), so it is unusable.
   Tesseract 5 with `lat+grc` at 300 dpi takes about 2 s a page. Keep the lines that are over 80%
   Latin script, rejoin hyphenated line ends, and the Latin column of four sample pages (150, 300,
   520, 880) scores **89–95% in a PL lexicon after simple rules**. That is a lower bound, since the
   lexicon came from 600 sampled works and misses real words like *inscrutabilium* and
   *interficiemus*.
   - The errors are systematic: the æ ligature read as z or x (*czesus*, *przdixissent*,
     *Judzeos*), c/e and n/u (*qued*, *autein*, *operc*), and split words.
   - Pipeline: Tesseract reads; rules plus a whole-PL lexicon fix the non-words; PatroLLM
     (`~/latin-lm`, a scorer that cannot read an image) flags the real-word residue, where it beat
     frequency on FitzRalph (AUC 0.77 vs 0.73). Only the flagged lines that fall inside a census
     window get an image check.
   - That is census-grade, not translation-grade. The sense terms are long words, and Tesseract
     gets them right.
   - Cost: about 3,000 pages, about 20 min on 6 cores. Not run yet. This is the sensus Origen gap,
     not the PG track (which is Greek, Kraken, volume order).
