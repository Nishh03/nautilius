# Nautilus

Turn a folder of markdown notes into a system that can **show** what you know,
**answer** questions about it, and eventually **maintain itself**.

Local-first, no database, no build tools, and free to run.

## Documentation

Open `docs/guides/index.html` in a browser, or go straight to:

| Guide | For |
|---|---|
| `docs/guides/1-presenting-nautilus.html` | **Start here.** What Nautilus is, the tech stack and the reasoning behind it, flowcharts, a six-minute demo script, and the questions you will be asked |
| `docs/guides/2-future-scope.html` | Where the project goes next, who else it serves, and what would need fixing first |

Both are self-contained HTML - just double-click them.

## Running it on another machine

Nothing here needs a paid account. Two options for the AI layer, both free.

```bash
git clone <this-repo-url>
cd nautilius
pip install -r requirements.txt
```

Then create your `.env` — **it is not in the repo, because it holds an API key**:

```bash
copy .env.example .env      # Windows
cp .env.example .env        # Mac/Linux
```

Open `.env` and pick one:

**Option A - fully local, no key, no internet** (slower, needs ~3 GB free RAM)

```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
```
Install [Ollama](https://ollama.com), then `ollama pull llama3.2:3b`.

**Option B - free cloud key, much faster** (~1.5s per answer)

```
LLM_PROVIDER=groq
GROQ_API_KEY=<your own free key from console.groq.com/keys>
GROQ_MODEL=openai/gpt-oss-120b
```

Model availability varies by key. To list what yours can use:
`curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`

Then start it:

```bash
python -m uvicorn app:app --app-dir backend
```

Open <http://127.0.0.1:8000>. The dashboard, orbit, note list and link graph all
work with **no AI configured at all** — only the Ask panel needs a provider.

Check everything is wired up:

```bash
python backend/test_nautilus.py     # expect: 59 passed, 0 failed
```

### Showing it to someone else

`share.bat` serves on your local network instead of just your machine, and
`share.bat tunnel` also creates a temporary public link. A plain
`http://127.0.0.1:8000` address only ever works on the machine running it.

## Run it

```bash
pip install -r requirements.txt
python -m uvicorn app:app --app-dir backend --reload
```

Then open <http://127.0.0.1:8000>. (Or double-click `run.bat`.)

Uses the bundled `vault/` by default. Point `VAULT_PATH` in `.env` at your own
Obsidian vault to use real notes.

### How notes get grouped into domains

1. **Folders first.** A note in `ai/` belongs to the `ai` domain. No setup.
2. **Then tags.** A vault kept flat - which Obsidian encourages - would put
   every note in `unfiled` and leave the orbit a single circle. For a root
   note with YAML frontmatter, its first *distinguishing* tag becomes its
   domain instead.
3. **Universal tags are ignored.** A tag every note carries separates no notes,
   and is usually just the vault's own name.

Obsidian frontmatter is parsed, not treated as text: it never reaches the
search index or the AI, but `tags` and keys like `status` stay available.

## Tests

```bash
python backend/test_nautilus.py
```

59 checks over reading notes, Obsidian frontmatter and tag-derived domains,
domain counts, the link graph, keyword retrieval, the automation safety rules,
and the edge cases that break a demo (empty vault, empty note, unicode titles,
an unreachable AI provider). No network, no pytest, runs in under a second.

## The AI provider

Set `LLM_PROVIDER` in `.env`. All three options are free:

| Provider | Key needed | Notes |
|---|---|---|
| `ollama` | none | Local. Notes never leave the machine. Default. |
| `groq` | free key | Fast cloud inference, generous free tier. |
| `gemini` | free key | Google free tier. |

Only `backend/llm.py` knows a provider exists, so adding a fourth is one function.

## Layout

```
vault/           your markdown notes; top-level folders are the domains
backend/
  config.py      all settings, read from .env
  vault.py       FR1-FR4  read notes, count domains, build the link graph
  retrieve.py    FR5      keyword scoring, no embeddings needed
  llm.py         the only file that knows about an AI provider
  app.py         FR5-FR6  HTTP routes, nothing else
frontend/
  index.html     FR7-FR8  the whole UI in one file, no build step
automation/
  common.py      shared safety rules: dry-run, no-clobber, audit log
  organize.py    FR9   file rough captures into the right domain
  digest.py      FR10  write a weekly digest note
  conflicts.py   FR11  flag notes that contradict each other
  schedule.bat   register all three with Windows Task Scheduler
docs/            literature review + requirement analysis
```

## Requirement coverage

| ID | Requirement | Where |
|---|---|---|
| FR1 | Read markdown from a vault, folders as domains | `vault.py: load_notes` |
| FR2 | List notes with title, domain, modified | `app.py: /api/notes` |
| FR3 | Count notes per domain and total | `vault.py: domain_counts` |
| FR4 | Wikilink graph including broken links | `vault.py: build_graph` |
| FR5 | Answer a question from the user's notes | `retrieve.py` + `llm.py: ask` |
| FR6 | Name the source notes in every answer | `llm.py: ask` -> `sources` |
| FR7 | Domains as an orbit sized by note count | `index.html: renderOrbit` |
| FR8 | Clicking a domain filters and pre-fills a question | `index.html: selectDomain` |
| FR9 | Nightly auto-organise | `automation/organize.py` |
| FR10 | Weekly digest note | `automation/digest.py` |
| FR11 | Weekly conflict check | `automation/conflicts.py` |

## What the UI does

- **Orbit** - domains circling a central note count, each sized by how many
  notes it holds. Click one to focus it.
- **Links** - the wikilink graph laid out with a small deterministic force
  simulation. Node size is its number of connections; broken links are dashed
  red stubs pointing at nothing.
- **Notes** - filter as you type, with matches highlighted. Click any note to
  read it.
- **Ask** - answers cite their sources, and every source is clickable, so a
  claim is one tap from the note it came from.

The dashboard re-checks the vault every 10 seconds, so edits made in Obsidian
appear without a reload.

## The demo vault

`vault/` holds a worked example: the notes of a CS student planning to become
an AI engineer in six months (Sep 2026 - Feb 2027). 54 notes across 10 domains,
201 wikilinks.

| Domain | What it holds |
|---|---|
| `roadmap/` | The six-month plan and one note per month |
| `foundations/` | Maths and Python prerequisites |
| `ml/` | Classical ML - regression, trees, evaluation |
| `deep-learning/` | Networks, backprop, CNNs, transformers |
| `llm/` | LLMs, RAG, embeddings, prompting, agents |
| `mlops/` | Docker, serving, tracking, monitoring |
| `projects/` | Four portfolio projects |
| `career/` | Job descriptions, resume, interview prep |
| `inbox/` | Rough captures, for FR9 to file |
| `digests/` | Written by `digest.py` |

It deliberately contains two links to notes that were never written, so FR4's
broken-link detection has something real to find, and one genuine contradiction
between the Month 4 plan and a conclusion reached later in `llm/`.

The previous sample vault is kept at `docs/sample-vault-v1/`.

## Automation (FR9-FR11)

Three maintenance tasks that write back into the vault. The requirement
document specifies these "via Cowork", which needs a paid Claude plan; they are
implemented here as plain scripts on Windows Task Scheduler instead, so the
whole system stays free and the scheduler is swappable.

```bash
python automation/organize.py             # dry run - shows the plan
python automation/organize.py --apply     # actually do it

automation\schedule.bat test              # dry-run all three
automation\schedule.bat install           # register the scheduled tasks
automation\schedule.bat status            # see what is registered
automation\schedule.bat remove            # unregister
```

| Task | Runs | What it does |
|---|---|---|
| `organize.py` | nightly 02:00 | Files each `inbox/` capture into an existing domain with tags and links |
| `digest.py` | Mondays 07:00 | Writes `digests/YYYY-Wnn.md` summarising the week |
| `conflicts.py` | Sundays 20:00 | Writes `reviews/conflicts-DATE.md` for notes that contradict each other |

`organize.py` files a capture the way the vault already organises itself: into
a folder if the vault uses folders, or into the root with frontmatter tags if
it is flat. New notes inherit any tag every existing note carries, so they do
not look foreign next to the ones written by hand.

**Safety rules**, because these are the only parts of Nautilus that write:

- **Dry run by default.** Nothing is written without `--apply`.
- **Never clobber.** An existing file is never overwritten; names get `-2`, `-3`.
- **Never invent.** Links and domains the model makes up are dropped, not
  written. A reply that cannot be parsed means the task does nothing.
- **Always auditable.** Every run appends to `automation/history.log`.

Dry-run each task yourself before scheduling it. The literature review is right
that an agent moving files needs supervision first.

### Known limitations

- **Free-tier token limits.** Groq's free tier caps tokens per minute, so batch
  tasks retry on 429 and split large groups across requests. Where a group is
  split, pairs separated across requests are not compared, and that is printed.
  Local Ollama has no such cap and is the better choice for batch runs.
- **A failed check is reported as failed.** If the provider cannot be reached,
  the task says so and exits non-zero rather than reporting a clean result.
- **FR11 recall is not deterministic.** The same vault checked twice can return
  different findings, because batch composition changes what the model compares
  in one request. It is a review aid, not a guarantee - treat a clean run as
  "nothing obvious", not "nothing there".

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | provider, model, readiness, vault path |
| `GET /api/stats` | totals, per-domain counts, link counts |
| `GET /api/notes?domain=` | note list, newest first |
| `GET /api/graph` | nodes, edges, broken links, orphans |
| `GET /api/note/{slug}` | one note including its body |
| `POST /api/ask` | `{question, domain?}` -> `{answer, sources[]}` |
