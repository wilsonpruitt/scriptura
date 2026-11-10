# Scriptura — the Bible as a dataset

Written 2026-11-09 (Fable session) at Wilson's request. **This file is the score.** Execution runs
in cheaper sessions against the stages below. The register of questions is `QUESTIONS.md`.

Wilson's framing, verbatim:

> "A lot of these have to do with seeing the Bible as a data set to be explored in that kind of way
> the history of concordance is vast, but the tools of data analysis of an LLM opens different doors."

> "This makes me think about de lubac and taking his fourfold description to a maximal level with
> the pg and pl"

> "we can use kraken to get a solid Greek transcription to do a lot of the pg work"

---

## 1. What Scriptura is, and is not

Scriptura is an **organizing layer and a register of Studies** over the scripture and paleography
projects Wroot Press already has. It names the shared dataset those projects have each been
building a piece of, and it makes the *question* the unit of new work.

It is **not** a monorepo, a hosting move, or (yet) a website. No existing project moves, renames, or
changes its home. The shelves stay the findability layer; the lenses stay lenses.

Standing rules that bind everything here (read them, do not restate them):

- One translation, one home: memory `reference_one-translation-one-home`.
- The reference key and store format: memory `reference_data-repository-standard` (OSIS `refKey`
  plus human `refDisplay`; SQLite as source of truth, per-book JSON as export; `text` / `index` /
  `pointer` modes).
- Tag layers: memory `reference_tagging-philosophy` (open-tag, consolidate, freeze, tag against).
- Rights, robots, exports, Hugging Face: `~/open-corpus/PLAN.md`.
- The WIP rule: one queue, in order; nothing here starts because it is written down.

## 2. The dataset: three layers

| Layer | Holds | Already built |
|---|---|---|
| **Text** (what it says) | words, versions, alignment, per-verse annotation | `~/wpb` (WLC / Swete / SBLGNT, MT–LXX alignment), `~/fons`, the Hebrew morphology in `~/verbum`, and every lens: Topographia (where), Loci (what), `~/catena` (connections), `~/annales-sacra` (when), `~/voces` (who speaks), `~/verbum` (sound) |
| **Witness** (how it reached us) | hands, pages, prints, divisions, variants | `~/paleography` (paleography.app), the Kraken pipeline (`~/patrologia/htr`, FitzRalph, Vincent), the Glossa and Lyra plates |
| **Reception** (what readers did with it) | who cited which verse, and how | `~/bereshit`, `~/surplus` (Talmai), `~/douay-glossa`, `~/bible-in-bom` (Brass), KJV + Wesley's Notes, `~/liber-generationis`, `~/nt-prosopography`, Abstracting the Bible, `~/reception-corpus`, and the Latin on disk (PL 87M words, Acta 95M, Bonaventure 2.6M; measured in `~/latin-lm/PLAN.md` §0) |

Each lens hand-built one verse-keyed layer. They are joinable in principle through `refKey` and
joined nowhere. Scriptura's first organizational act is a **layer registry** (`LAYERS.md`, ✅ written
2026-11-10): one row per layer giving its repo, its `refKey` coverage, its versification, its licence,
and its manifest URL where one exists (Verbum's `/index.json` is the model).

## 3. The workshop: paleography and Kraken

Paleography is not a fourth layer. It plays two roles:

1. **It is the Witness layer for scripture**: the hands and pages the text travelled in.
2. **It is the workshop that makes text for the Studies.** The Patrologia Graeca exists here only
   as scans; Kraken turns it into Greek the Studies can read. OCR is local and free. The PG
   fine-tune measured 0.50–1.08% character error on gap pages (`~/patrologia/htr/QUEUE.md`,
   benchmark 2026-10-17).

**Two grades of text.** An edition needs checked text (the kt method in `~/patrologia`). A census
may not. Whether raw Kraken Greek is good enough to classify from is a measured gate, not an
assumption: see Sensus stage G1.

**The PG queue stays in `~/patrologia/htr/QUEUE.md`.** Scriptura states what it wants read and why;
it does not keep a second queue.

## 4. The unit of work: a Study

A Study is one bounded question taken to a finding. Talmai already calls its work "Study 1" inside
its own repo, so Scriptura names Studies by **slug, not number**.

Each Study lives at `studies/<slug>/STUDY.md` and carries:

1. **The question**, in one sentence a non-specialist can read.
2. **Layers used** and layers produced (a Study should leave a reusable layer behind).
3. **Method**, computation first. Whatever counting, matching, or lexicon lookup can settle is
   settled before any model reads anything.
4. **Codebook and rulings**, numbered, for anything a reader has to judge.
5. **Ledger**: every claim traceable to a located source. Nothing is attributed from recall.
6. **The finding**, stated so it could have come out otherwise.
7. **Two outputs, both owed**: the scholarly one (data export, method page, write-up) and the
   pastoral turn (what lands in Lectern or Difficult Passages, and what a preacher does with it).

Rules for every Study:

- **The full pass is what gets planned and priced.** A pilot calibrates the codebook; it is never
  offered as a cheaper substitute for the pass.
- **Blind control before volume.** Two independent codings of the same set, agreement measured,
  disagreements ruled. A briefed second coder is not independent.
- **In-copyright sources are pointers only.** Where a modern book treats a passage is a fact; its
  words are not stored.
- **Studies choose where editions dig.** A computed map across the whole canon is how the next
  crux pages get picked.

**Hard stops** (Wilson's per-action answer required): any volume model run (state the count, the
estimated burn, and ask "which model, and go?"); any Hugging Face push or published export; any
deploy; any push to a site repo.

---

## 5. Lead Study: `sensus` — de Lubac's four senses, counted

**Question.** Henri de Lubac argued from thousands of hand-picked passages that the fathers and the
medievals read Scripture in four senses that are really one movement. What does every exposition
in the PL, and then the PG, show when it is read against that claim?

De Lubac never counted. This Study is the census he could not take.

### 5.1 What it tests

1. **Order.** In the fourfold formula tropology follows allegory, so the moral sense flows from the
   mystery of Christ. The older threefold order (history, tropology, allegory) puts it before. In
   practice, which order do expositions follow, and does a moral reading lean on a preceding
   allegorical one?
2. **The decline.** De Lubac saw the senses come apart in the twelfth and thirteenth centuries;
   Beryl Smalley told the same years as the rise of the literal. The share of each sense by century
   and by genre tests both accounts. The PL ends at 1216, at the hinge; Bonaventure, Lyra (who
   wrote a literal *and* a moral postill), FitzRalph and the Kraken prints carry the series on.
3. **Stated versus performed.** How often is the formula stated, and how often is one verse
   actually given all four senses, as Cassian does with Jerusalem? Hypothesis, to be tested: the
   complete fourfold reading is far rarer than the formula.
4. **The life of an allegory.** One reading followed from its first attestation through the Glossa
   to Lyra: Bereshit's transmission map, done per interpretation.
5. **Does the grid fit the Greeks?** The fourfold is a Latin formula. Whether it describes Greek
   practice (*historia*, *theoria*, *typos*, *anagoge*) is a finding, not a premise.

### 5.2 Design rulings (S1–S4, adopted 2026-11-09 in conversation; amend by number)

- **S1. Record movement, not bins.** De Lubac's thesis is unity. Each record holds the *ordered
  sequence* of senses in the passage and which sense depends on which. Four independent boxes would
  measure the thing he argued against.
- **S2. Two labels, never merged.** `authorLabel` is the author's own term, verbatim (*mystice*,
  *moraliter*, *iuxta historiam*), or null. `coderLabel` is the codebook's. The gap is a finding.
- **S3. The unit is the exegetical move:** one verse (or lemma) plus one interpretive statement
  about it. A passage that gives three readings of one verse is three moves in one sequence.
- **S4. Not every citation is exegesis.** A verse quoted as a proof, a prayer, or an ornament is
  recorded with its `use` and gets no sense label.

Record sketch (extends the standard record model, does not replace it):

```
{ refKey, refDisplay, source, author, work, century, genre,
  locus,                 // PL/PG volume:column
  anchor,                // exact substring of the source, never paraphrase
  use,                   // exposition | proof | prayer | ornament | other
  authorLabel,           // verbatim or null            (S2)
  sequence: [ { sense, anchor, dependsOn? } ],          // (S1, S3)
  coder, confidence, rulings: [] }
```

Starting codebook (to be opened, consolidated, then frozen): *historia / littera*; *allegoria*
(Christ and the Church); *tropologia* (the soul and conduct); *anagogia* (the last things). The
medieval distich is the plain-language key: the letter teaches what happened, allegory what to
believe, the moral sense what to do, anagogy where you are going.

### 5.3 Stages

Stages A and B cost no model tokens. Nothing after D runs without Wilson's go.

**A. De Lubac's footnotes as a ledger.** Every PL and PG reference in the four volumes of
*Exégèse médiévale*, resolved to volume and column, with the claim it is cited for. Pointer mode:
locations and our own one-line description, none of his prose. Yields (i) a gold set to test the
coder against and (ii) a map of what he read: which authors and centuries carry his argument, and
which he passed over. That map is publishable on its own.
✅ Edition (2026-11-09): French, Aubier 1959–64, all four volumes, as Internet Archive scans with
an OCR layer. Copies in `studies/sensus/sources/` (in copyright, never pushed).
✅ Harvest done (2026-11-09), no tokens, fixed after the pilot: 9,011 references, 8,304 of 8,615 PL
references resolved to a work, 86% of the checkable ones confirmed at the column. Read `studies/sensus/STUDY.md` 3.3–3.4
before quoting a number.
⚠ Amendment: locations cost no tokens, but *the claim each is cited for* needs a reader. That is
one model pass over the book (about 3M tokens in, 0.8M out) and a hard stop. STUDY.md 3.5.
✅ Pilot (2026-11-09): one chapter, two blind Opus codings, $8.91; role kappa 0.91. STUDY.md 3.6.
⬜ Wilson: four codebook rulings (STUDY.md 3.6); then the full pass, about $145 Opus / $73 Batch.

**B. The vocabulary census.** ✅ 2026-11-10, `studies/sensus/census/` (STUDY.md section 8; term list awaits Wilson's freeze). Every occurrence of the sense terms across the PL TEI
(`~/patrologia/sources/pl/tei/`, 5,276 files), by author and century, plus every *stated formula*
(three or more sense terms inside one window). Starter list, to be opened and frozen: *historia,
historice, historialiter, littera, ad litteram, iuxta/secundum litteram; allegoria, allegorice,
mystice, mysterium, typus, typice, figura, figuraliter, sacramentum; tropologia, tropologice,
moraliter, moralitas; anagoge, anagogice; spiritualiter, spiritalis intellegentia*. Handle
*spiritalis/spiritualis* and *intellegentia/intelligentia*. Output: the history of the vocabulary,
and the list of places where theory is stated.

**C. The citation spine.** A table of every scripture citation in the PL: `refKey` × author × work
× column. **This is stage 1 of the `canon` Study and is built once, there.** Known facts that shape
it: the PL TEI carries no scripture markup (sampled 2026-11-09: body is `<p>/<hi>/<pb>` only);
migne.app's index rests on Migne's own notes and is uneven (one Psalms commentary indexes zero
scripture). So the spine needs a detector run against the Clementine Vulgate at
`~/patrologia/sources/vulgate/`, on the Brass model (n-gram, fuzzy, semantic streams, then
adjudication; `~/bible-in-bom`). Two traps: the Fathers often quote the Old Latin, so exact
matching undercounts; and Vulgate Psalm numbers differ from the `refKey` default, so store both.

**D. Calibrate the codebook.** Two calibration sets: Gregory's *Moralia in Iob*, where he labels
his own senses (author-labelled ground truth), and Bereshit's 292 witnesses, already curated
(`~/bereshit/data`). Run the blind control; rule the disagreements; freeze the codebook; then score
the coder against the de Lubac ledger from stage A.

**E. Count and price. HARD STOP.** The spine gives the number of citations; stage D gives tokens
per move. Report the count and the full-pass burn, and ask which model and whether to go. One-shot
per-item work at volume goes through the direct API (memory `reference_api-vs-agent-cost`).

**F. The full PL pass,** then the series past 1216 (Bonaventure, the Glossa, Lyra, the Kraken
prints) as their text exists.

**G. The PG track** (runs beside A–F as workshop time allows; OCR is local):

- **G1. The census-grade gate.** Take a work with checked Greek already in hand (Dorotheus,
  Moschus). Code the same passages twice, once from raw Kraken text and once from the checked
  text. If the labels agree, raw Kraken Greek is census-grade and the PG can be read without the
  per-work check. If not, the check stays in the path and the cost changes.
- **G2. What to read first.** ~~Exegetes first (Origen, Chrysostom)~~. **Ruled by Wilson
  2026-11-10: the whole PG, in volume order (1 → 161).** Kraken makes the OCR local and cheap,
  so the unit is the corpus, not a hand-picked set of volumes; there is no reading-order triage.
  The census and the Greek pass take volumes as Kraken delivers them. The G1 gate still decides
  whether raw Kraken Greek is census-grade.
  Origen (PG 11–17) arrives in order with the rest. His Latin-only survivals (Rufinus and Jerome)
  are chiefly in PG 12–14. Corpus Corporum carries no PG Latin (memory `patrologia`), and only PG 12's existing OCR
  reads the Latin, so those volumes need a Latin model, not the Greek one (`studies/sensus/STUDY.md`,
  Next 5).
- **G3. The Greek vocabulary census** (*historia, theoria, allegoria, tropologia, anagoge, typos*),
  the counterpart of stage B, as soon as text exists.
- **G4. The Greek pass,** under the same codebook, with the fit of the grid reported as a result.

### 5.4 Outputs

- **Scholarly:** the verse × sense × author × century table as an open data layer; the de Lubac
  reading map; a method page that says what the coder gets wrong.
- **Pastoral:** for any Sunday's text, Lectern shows the readings the tradition actually gave under
  the four heads. Building anything in Lectern is confirmed with Wilson first.

---

## 6. The other Studies

Chosen by Wilson 2026-11-09 and specified in `QUESTIONS.md`: `canon` (the working canon),
`nameless` (who named the nameless), `questions` (the questions of the Bible), `divisions` (who cut
the text where). The questions not chosen are kept there in one line each so they are not
re-invented.

## 7. What the next session does

Done as of 2026-11-10:
- spine `inline` stream and stage D against de Lubac (section 7 items 1–2 below)
- stage A, the whole book (`studies/sensus/STUDY.md` 3.7)
- stage B (STUDY 8)
- stage D first pass (STUDY 9)
- `LAYERS.md`, `tools/refkey.py` and the Vulgate→KJV crosswalk
- spine v0 (`studies/canon/STUDY.md`)

1. ~~Spine: the `inline` stream~~: done 2026-11-10. 399,679 rows; n-gram recall against it is
   42%; precision reads as lemmata plus formulas (`studies/canon/STUDY.md`). Steps 1–4 are listed
   there.
2. ~~Stage D against de Lubac~~: done 2026-11-10 (`studies/sensus/STUDY.md` 10). He cites 96 of
   the 132 theory formulas for theory; 11 he doesn't cite at all (a reader confirms). The census
   finds 50% of his three-sense theory citations; most misses are window or vocabulary rules,
   and 64 loci are figured schemes no vocabulary finds.
3. ~~Wilson's rulings~~: done 2026-11-10. Register order as proposed (QUESTIONS.md); PG in volume order, whole corpus (G2).
4. ~~Canon fuzzy stream~~: done 2026-11-10. Recall with both streams is 48% (d. ≤400) to 70%
   (601–800); the Old Latin gap narrows but holds.
5. Next, canon: the formula exclusion list and the lemma flag (proposed by machine, ruled by a
   reader), then the merge to one spine row per work, column and verse. No tokens until the ruling.

Routine work throughout: Sonnet for the scripts and the census, Haiku for harvests. Fable or Opus
only for codebook rulings and reading passes.

## 8. Decisions Wilson owes

1. ~~De Lubac, stage A~~: rulings made, full reading pass done 2026-11-10 (STUDY.md 3.7).
2. ~~The order of the register~~: ruled 2026-11-10, as proposed.
3. ~~PG reading order (G2)~~: ruled 2026-11-10, the whole PG in volume order.
4. ~~Git~~: a local-only repository since 2026-11-10. No remote; a pre-push hook refuses every push
   (the ledger holds in-copyright citation strings).
