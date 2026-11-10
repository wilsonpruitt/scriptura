#!/usr/bin/env python3
"""Stage A reading pass, pilot: one model call per note-bearing page of Exégèse médiévale.

The reader sees the page (prose + footnotes, OCR), the tail of the page before it, and the
harvested ledger rows for the page. It returns, per row: whether the harvested reference is right
(with a correction if not), the role of the citation, the senses in play (S1), the source's own
label (S2), the verse under exposition, and one line in our words on what it is cited for.
Column-only rows get the same, plus what kind of number it is and which work it points to.

Two codings of the same pages are run as independent calls (coder A and coder B): neither sees the
other. `pilot_agree.py` compares them. PLAN section 4: a briefed second coder is not independent.

The key comes from the macOS Keychain (service "anthropic-api"), never ANTHROPIC_API_KEY.

  uv run --with anthropic python -I scripts/pilot_read.py <em> <first_pdf> <last_pdf> <coder> [model]
  e.g. uv run --with anthropic python -I scripts/pilot_read.py 2 9 60 A

Writes working/pilot/<coder>/em<em>-p<pdf>.json (raw model output plus usage) and appends to
working/pilot/usage.tsv. working/ is gitignored: the page text sent is in copyright, and the
outputs echo his reference strings.
"""
import csv, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT = os.path.join(HERE, 'sources', 'exegese-medievale', 'text')
LEDGER = os.path.join(HERE, 'ledger')
OUT = os.path.join(HERE, 'working', 'pilot')
MODEL = 'claude-opus-5-5'
EFFORT = 'high'
CODEBOOK = 'R1-R7 2026-11-09'   # STUDY.md section 4; bump when the rulings change

SYSTEM = """You are coding the footnotes of Henri de Lubac, Exégèse médiévale (Aubier, 1959-64), for a research ledger. The ledger records WHERE he cites patristic and medieval sources and WHAT FOR. It must never store his prose: the book is in copyright.

You get one printed page (OCR text: running head, body, then footnotes; OCR errors are common, especially in roman numerals and note numbers), the end of the previous page as context, and the references a script harvested from this page's footnotes, each with an id.

Reference forms: "PL" = Migne, Patrologia Latina; "PG" = Patrologia Graeca. De Lubac often drops the siglum: "(CXCVIII, 1046 B)" is volume 198, column 1046, band B. A bare column "(312-4)" takes its volume from an earlier reference to the same work, or is a page of a critical edition (GCS, CSEL, CCL, SC, MGH ...), a folio, or a year. The script's resolution (author, work from the Corpus Corporum index) and its quote check are given where it has them; they can be wrong.

For EVERY harvested row, return one entry, with its id:
- verdict: "ok" if series/volume/column as harvested are right; "corrected" if you can see from the page that they are wrong (OCR or misparse), giving the right values; "not_a_reference" if it is not a citation of a patristic/medieval text (a modern book's volume and page, a date, a chapter number ...).
- role: what the citation does in his argument.
    example   = a passage where the source READS a scripture text in one or more senses (an exegetical move);
    theory    = the source states or defines the doctrine of the senses (lists, names, orders them);
    vocabulary= cited to attest a word or usage, not a reading;
    history   = establishes a date, attribution, transmission, a biographical or textual fact;
    other     = anything else (say what in cited_for).
- senses: the senses in play in the cited passage, named with DE LUBAC'S term for them (R5), IN THE ORDER the source moves through them (S1: we record movement, not bins). Values:
    letter    = what happened or was said; includes a figure of speech when the source or de Lubac counts it with the letter;
    allegory  = what the things and events signify of Christ and the Church (what to believe);
    tropology = what they signify for the soul's conduct (what to do);
    anagogy   = what they signify of the last things (where we are headed);
    spiritual = an undivided spiritual sense, when none of the three is named or meant;
    other     = a sense outside the scheme (say which in cited_for).
  Empty list only if no sense at all is in play (a date, an attribution, a bare word with no reading).
  Code pagan allegory (Homer, Stoics, myths) like any other reading (R3). A compound naming one sense ("spiritalis allegoria", "mystica allegoria") is ONE sense (R6). A figurative reading with no sense named on the page is coded by the definitions above, confidence at most medium (R7).
- allegory_kind: for any row whose senses include allegory (else "none"):
    in_factis      = the thing or event told signifies another (Augustine's "in facto, non in verbo"; Ambrose; Bede). Code senses [letter, allegory]: the letter is the first step of the movement. The default for a narrative read figuratively;
    in_verbis      = a figure of speech, words saying one thing and meaning another (the grammarians' trope). Code [allegory]; but [letter] alone if the source or de Lubac counts the figure with the letter;
    mythic         = pagan allegory of myths. Code [allegory];
    letter_denying = allegory that abolishes or bypasses the letter. Code [allegory];
    unspecified    = the word is used without showing which.
- stance: the cited source's stance toward the reading it names: endorsed | rejected | reported. A source censuring letter-denying allegory is senses [allegory], allegory_kind letter_denying, stance rejected; never an empty sense list.
- author_label: ALL the source's own terms for the sense(s), verbatim in Latin or Greek as printed, separated by "; " (R4), if the page quotes them (e.g. "mystice; spiritualiter"); else "". Never his French.
- term_differs: true when the source's own word names a different sense from the one recorded in senses, or one outside the scheme (mystice, spiritualiter or anagoge where de Lubac says allegory); else false (R5).
- scripture: the verse or passage being expounded, as an OSIS-style key ("Gen.22.1-14", "Song.1.2", "Gal.4.24"), only if the page makes it clear; else "".
- cited_for: ONE line, at most 20 words, in plain English, in YOUR words: what the cited passage is used to show. Do not translate, quote or closely paraphrase de Lubac's sentences.
- confidence: high | medium | low.

For each COLUMN-ONLY row, the same fields, plus:
- kind: migne_column | edition_page | folio | year | section_number | other
- series, volume, author, work: what it points to, if the note shows it (e.g. series "GCS", work "Origen, Homilies on Genesis"); else "".

Then, in "missed", list any patristic or medieval reference in this page's footnotes that the harvest did not catch (give the note number, the reference as printed, and the same coding fields). Do not list modern scholarship.

Return JSON only, matching the schema. Where a field has no value, give an empty string "" (never the word null); give volume and column numbers as arabic digits in a string."""

N = lambda t: {'type': 'string'}  # unions are capped by the API: "" means none, numbers as digits
SENSES = {'type': 'array', 'items': {'type': 'string', 'enum': ['letter', 'allegory', 'tropology', 'anagogy', 'spiritual', 'other']}}
CODE = {
    'role': {'type': 'string', 'enum': ['example', 'theory', 'vocabulary', 'history', 'other']},
    'senses': SENSES,
    'author_label': N('string'),
    'scripture': N('string'),
    'cited_for': {'type': 'string'},
    'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']},
    'allegory_kind': {'type': 'string', 'enum': ['none', 'in_factis', 'in_verbis', 'mythic', 'letter_denying', 'unspecified']},
    'stance': {'type': 'string', 'enum': ['endorsed', 'rejected', 'reported']},
    'term_differs': {'type': 'boolean'},
}
def obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}
SCHEMA = obj({
    'refs': {'type': 'array', 'items': obj({
        'id': {'type': 'string'},
        'verdict': {'type': 'string', 'enum': ['ok', 'corrected', 'not_a_reference']},
        'series': N('string'), 'volume': N('integer'), 'column': N('integer'), 'band': N('string'),
        **CODE})},
    'colonly': {'type': 'array', 'items': obj({
        'id': {'type': 'string'},
        'kind': {'type': 'string', 'enum': ['migne_column', 'edition_page', 'folio', 'year', 'section_number', 'other']},
        'series': N('string'), 'volume': N('integer'), 'author': N('string'), 'work': N('string'),
        **CODE})},
    'missed': {'type': 'array', 'items': obj({
        'note': N('integer'), 'printed': {'type': 'string'},
        'series': N('string'), 'volume': N('integer'), 'column': N('integer'),
        'author': N('string'), 'work': N('string'),
        **CODE})},
})

def load(name):
    with open(os.path.join(LEDGER, name), encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))

def build(em, pdf, pages, refs, colonly, checks):
    prev = pages[pdf - 2] if pdf >= 2 else ''
    tail = '\n'.join(prev.rstrip().split('\n')[-25:])
    R = [r for r in refs if r['em'] == str(em) and r['pdf_page'] == str(pdf)]
    C = [r for r in colonly if r['em'] == str(em) and r['pdf_page'] == str(pdf)]
    if not R and not C:
        return None, [], []
    lines = ['HARVESTED REFERENCES (id | note | form | series | vol | col band-col_end | status | author | work | quote check)']
    for r in R:
        ch = checks.get(r['id'])
        q = f"{ch['check']} {ch['score']}" if ch else 'no quote'
        span = f"{r['col']}{r['band']}" + (f"-{r['col_end']}{r['band_end']}" if r['col_end'] else '')
        lines.append(' | '.join([r['id'], r['note'] or '?', r['form'], r['series'], r['vol'] or '?', span,
                                 r['status'], r['author'], r['title'][:80], q, 'printed: ' + r['raw']]))
    lines.append('\nCOLUMN-ONLY REFERENCES, no volume (id | note | number | printed)')
    for r in C:
        lines.append(' | '.join([r['id'], r['note'] or '?', f"{r['col']}{r['band']}" + (f"-{r['col_end']}" if r['col_end'] else ''),
                                 ('year? ' if r['year'] == '1' else '') + 'printed: ' + r['raw']]))
    user = (f"PREVIOUS PAGE, last lines (context only):\n{tail}\n\n=== THIS PAGE (tome {R[0]['tome'] if R else C[0]['tome']}, "
            f"PDF page {pdf}) ===\n{pages[pdf - 1]}\n=== END OF PAGE ===\n\n" + '\n'.join(lines))
    return user, [r['id'] for r in R], [r['id'] for r in C]

def client():
    key = subprocess.run(['security', 'find-generic-password', '-s', 'anthropic-api', '-w'],
                         capture_output=True, text=True, check=True).stdout.strip()
    return anthropic.Anthropic(api_key=key, max_retries=4)

def run_page(c, model, coder, em, pdf, user, rid, cid):
    path = os.path.join(OUT, coder, f'em{em}-p{pdf:03d}.json')
    if os.path.exists(path):
        return None
    t = time.time()
    with c.messages.stream(model=model, max_tokens=64000, system=SYSTEM,
                           output_config={'effort': EFFORT, 'format': {'type': 'json_schema', 'schema': SCHEMA}},
                           messages=[{'role': 'user', 'content': user}]) as s:
        msg = s.get_final_message()
    text = ''.join(b.text for b in msg.content if b.type == 'text')
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    u = msg.usage
    rec = {'em': em, 'pdf': pdf, 'coder': coder, 'model': model, 'effort': EFFORT, 'stop': msg.stop_reason,
           'input': u.input_tokens, 'output': u.output_tokens, 'secs': round(time.time() - t),
           'expected_refs': rid, 'expected_colonly': cid, 'data': data, 'raw_text': None if data else text}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return rec

def main():
    em, first, last, coder = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    model = sys.argv[5] if len(sys.argv) > 5 else MODEL
    with open(os.path.join(TEXT, f'em{em}.txt'), encoding='utf-8') as f:
        pages = f.read().split('\f')
    refs, colonly = load('refs.tsv'), load('colonly.tsv')
    checks = {r['id']: r for r in load('quote-check.tsv')}
    os.makedirs(os.path.join(OUT, coder), exist_ok=True)
    jobs = []
    for pdf in range(first, last + 1):
        user, rid, cid = build(em, pdf, pages, refs, colonly, checks)
        if user:
            jobs.append((pdf, user, rid, cid))
    c = client()
    tin = tout = 0
    with ThreadPoolExecutor(6) as ex, open(os.path.join(OUT, 'usage.tsv'), 'a') as log:
        futs = {ex.submit(run_page, c, model, coder, em, p, u, r, k): p for p, u, r, k in jobs}
        for fu in as_completed(futs):
            try:
                rec = fu.result()
            except anthropic.APIStatusError as e:
                print('page', futs[fu], 'API error', e.status_code, str(e)[:200]); continue
            except anthropic.APIConnectionError as e:
                print('page', futs[fu], 'connection error', e); continue
            if not rec:
                continue
            tin += rec['input']; tout += rec['output']
            log.write('\t'.join(map(str, [coder, model, EFFORT, em, rec['pdf'], rec['stop'], rec['input'], rec['output'], rec['secs']])) + '\n')
            flag = '' if rec['data'] else '  !! no JSON'
            print(f"p{rec['pdf']:03d} {rec['stop']} in {rec['input']} out {rec['output']} {rec['secs']}s{flag}", flush=True)
    price = {'claude-opus-5-5': (4, 20), 'claude-sonnet-5-5': (2, 10), 'claude-haiku-5-5': (0.1, 0.5)}.get(model, (0, 0))
    print(json.dumps({'pages': len(jobs), 'input': tin, 'output': tout,
                      'usd': round((tin * price[0] + tout * price[1]) / 1e6, 2)}))

# ---------- Batch API (-50%) ----------
#   submit <run> <coder> <em>:<first>-<last> [...]   e.g. submit pilot2 A 2:9-60
#   fetch  <run> [batch_id ...]                        (no id: every batch logged for <run>)
# Outputs go to working/<run>/<coder>/, in the same record form as the direct runs.

def pages_of(em):
    with open(os.path.join(TEXT, f'em{em}.txt'), encoding='utf-8') as f:
        return f.read().split('\f')

def submit(run, coder, spans, model=MODEL):
    refs, colonly = load('refs.tsv'), load('colonly.tsv')
    checks = {r['id']: r for r in load('quote-check.tsv')}
    base = os.path.join(HERE, 'working', run)
    os.makedirs(os.path.join(base, coder), exist_ok=True)
    reqs, manifest = [], {}
    for span in spans:
        em, rng = span.split(':'); em = int(em); first, last = map(int, rng.split('-'))
        pages = pages_of(em)
        for pdf in range(first, last + 1):
            if os.path.exists(os.path.join(base, coder, f'em{em}-p{pdf:03d}.json')):
                continue
            user, rid, cid = build(em, pdf, pages, refs, colonly, checks)
            if not user:
                continue
            cust = f'{coder}-em{em}-p{pdf:03d}'
            manifest[cust] = {'em': em, 'pdf': pdf, 'coder': coder, 'expected_refs': rid, 'expected_colonly': cid}
            reqs.append({'custom_id': cust, 'params': {
                'model': model, 'max_tokens': 64000, 'system': SYSTEM,
                'output_config': {'effort': EFFORT, 'format': {'type': 'json_schema', 'schema': SCHEMA}},
                'messages': [{'role': 'user', 'content': user}]}})
    if not reqs:
        print('nothing to submit'); return
    b = client().messages.batches.create(requests=reqs)
    with open(os.path.join(base, f'manifest-{b.id}.json'), 'w', encoding='utf-8') as f:
        json.dump({'batch': b.id, 'model': model, 'effort': EFFORT, 'codebook': CODEBOOK, 'pages': manifest}, f, indent=1)
    with open(os.path.join(base, 'batches.tsv'), 'a') as f:
        f.write('\t'.join([b.id, coder, model, EFFORT, CODEBOOK, ' '.join(spans), str(len(reqs))]) + '\n')
    print(b.id, b.processing_status, len(reqs), 'pages')

def fetch(run, ids):
    base = os.path.join(HERE, 'working', run)
    if not ids:
        ids = [l.split('\t')[0] for l in open(os.path.join(base, 'batches.tsv'))]
    c = client()
    for bid in ids:
        b = c.messages.batches.retrieve(bid)
        print(bid, b.processing_status, b.request_counts)
        if b.processing_status != 'ended':
            continue
        man = json.load(open(os.path.join(base, f'manifest-{bid}.json'), encoding='utf-8'))
        price = {'claude-opus-5-5': (4, 20), 'claude-sonnet-5-5': (2, 10), 'claude-haiku-5-5': (0.1, 0.5)}.get(man['model'], (0, 0))
        tin = tout = 0; bad = []
        for r in c.messages.batches.results(bid):
            m = man['pages'][r.custom_id]
            path = os.path.join(base, m['coder'], f"em{m['em']}-p{m['pdf']:03d}.json")
            if r.result.type != 'succeeded':
                bad.append((r.custom_id, r.result.type)); continue
            msg = r.result.message
            text = ''.join(x.text for x in msg.content if x.type == 'text')
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
            if msg.stop_reason != 'end_turn' or data is None:
                bad.append((r.custom_id, msg.stop_reason))
            tin += msg.usage.input_tokens; tout += msg.usage.output_tokens
            rec = {**m, 'model': man['model'], 'effort': man['effort'], 'codebook': man['codebook'], 'batch': bid,
                   'stop': msg.stop_reason, 'input': msg.usage.input_tokens, 'output': msg.usage.output_tokens,
                   'data': data, 'raw_text': None if data else text}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(rec, f, ensure_ascii=False, indent=1)
        print(json.dumps({'batch': bid, 'input': tin, 'output': tout,
                          'usd_batch': round((tin * price[0] + tout * price[1]) / 2e6, 2), 'problems': bad}))

if __name__ == '__main__':
    if sys.argv[1] == 'submit':
        m = [x[6:] for x in sys.argv[4:] if x.startswith('model=')]
        submit(sys.argv[2], sys.argv[3], [x for x in sys.argv[4:] if not x.startswith('model=')], *(m[:1] or [MODEL]))
    elif sys.argv[1] == 'fetch':
        fetch(sys.argv[2], sys.argv[3:])
    else:
        main()
