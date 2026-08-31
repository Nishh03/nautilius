"""Tests for the parts that must not silently break.

Run with:  python backend/test_nautilus.py

No pytest dependency and no network: every test builds a throwaway vault in a
temp folder, so these run in under a second and never touch the real notes or
the LLM. The LLM is the one thing not tested here - it is non-deterministic and
slow, and llm.py is deliberately thin enough to read.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import retrieve
import vault

PASSED, FAILED = 0, 0


def check(label: str, got, want):
    global PASSED, FAILED
    if got == want:
        PASSED += 1
        print(f"  PASS  {label}")
    else:
        FAILED += 1
        print(f"  FAIL  {label}\n          got:  {got!r}\n          want: {want!r}")


def check_true(label: str, condition):
    check(label, bool(condition), True)


def make_vault(files: dict[str, str]) -> Path:
    """Build a temporary vault from {relative path: contents}."""
    root = Path(tempfile.mkdtemp(prefix="nautilus-test-"))
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return root


# --------------------------------------------------------------------------
def test_reading():
    print("\nFR1/FR2 - reading notes and inferring domains")
    root = make_vault({
        "ai/alpha.md": "# Alpha\nAbout alpha.",
        "ai/beta.md": "No heading here, so the filename becomes the title.",
        "coursework/gamma.md": "# Gamma\nAbout gamma.",
        "loose-note.md": "# Loose\nSits in the vault root.",
        ".obsidian/config.md": "# Hidden\nShould be ignored.",
        "notes.txt": "Not markdown, should be ignored.",
    })
    try:
        notes = vault.load_notes(root)
        by_slug = {n.slug: n for n in notes}

        check("only markdown files are read", len(notes), 4)
        check_true("dot-folders are skipped", ".obsidian/config" not in by_slug)
        check("folder becomes the domain", by_slug["ai/alpha"].domain, "ai")
        check("root notes are unfiled", by_slug["loose-note"].domain, "unfiled")
        check("H1 becomes the title", by_slug["ai/alpha"].title, "Alpha")
        check("filename is the fallback title", by_slug["ai/beta"].title, "Beta")
        check_true("notes are newest first",
                   all(notes[i].modified >= notes[i + 1].modified
                       for i in range(len(notes) - 1)))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_frontmatter():
    print("\nFR1 - Obsidian YAML frontmatter and tag-derived domains")
    root = make_vault({
        "push.md": "---\ntags: [nautilus, fitness]\n---\n\n# Push\nBench and press.",
        "pull.md": "---\ntags: [nautilus, fitness]\nstatus: ongoing\n---\n\n# Pull\nRows.",
        "plan.md": "---\ntags: [nautilus, planning, meta]\n---\n\n# Plan\nThe plan.",
        "plain.md": "# Plain\nNo frontmatter at all.",
    })
    try:
        notes = {n.slug: n for n in vault.load_notes(root)}

        check("frontmatter is stripped from the body",
              notes["push"].body.lstrip().startswith("# Push"), True)
        check("tags are parsed from a YAML list",
              notes["push"].tags, ["nautilus", "fitness"])
        check("other frontmatter keys are kept",
              notes["pull"].meta.get("status"), "ongoing")
        check("the raw file is preserved for writing back",
              notes["push"].raw.startswith("---"), True)
        check("a note without frontmatter still works",
              notes["plain"].tags, [])

        # "nautilus" is on every tagged note, so it groups nothing.
        check("a universal tag is not used as a domain",
              notes["push"].domain, "fitness")
        check("the first distinguishing tag wins",
              notes["plan"].domain, "planning")
        check("an untagged note stays unfiled",
              notes["plain"].domain, "unfiled")

        counts = {d["domain"]: d["count"] for d in vault.domain_counts(vault.load_notes(root))}
        check("a flat vault still produces real domains",
              counts, {"fitness": 2, "planning": 1, "unfiled": 1})

        # A frontmatter-only tag must not be searchable as body text.
        check("frontmatter text does not pollute retrieval",
              retrieve.search("nautilus", vault.load_notes(root)), [])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_counts_and_graph():
    print("\nFR3/FR4 - domain counts and the wikilink graph")
    root = make_vault({
        "ai/one.md": "# One\nLinks to [[Two]] and to [[ai/three]].",
        "ai/two.md": "# Two\nLinks back to [[One]].",
        "ai/three.md": "# Three\nPoints at [[Nowhere At All]].",
        "misc/four.md": "# Four\nLinks to [[Two|an alias]] and [[One#a-heading]].",
        "misc/five.md": "# Five\nLinks to nothing and nothing links here.",
    })
    try:
        notes = vault.load_notes(root)
        counts = {d["domain"]: d["count"] for d in vault.domain_counts(notes)}
        check("counts per domain", counts, {"ai": 3, "misc": 2})

        graph = vault.build_graph(notes)
        edges = {(e["source"], e["target"]) for e in graph["edges"]}

        check("links resolve by title", ("ai/one", "ai/two") in edges, True)
        check("links resolve by slug", ("ai/one", "ai/three") in edges, True)
        check("aliased [[X|y]] links resolve", ("misc/four", "ai/two") in edges, True)
        check("heading [[X#h]] links resolve", ("misc/four", "ai/one") in edges, True)
        check("broken links are reported",
              [b["target"] for b in graph["broken"]], ["Nowhere At All"])
        check("orphans are reported", graph["orphans"], ["misc/five"])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_retrieval():
    print("\nFR5 - keyword retrieval")
    root = make_vault({
        "a/embeddings.md": "# Vector Embeddings\nSemantic search by meaning.",
        "a/keywords.md": "# Keyword Retrieval\nScoring by term overlap. Cheap and explainable.",
        "a/unrelated.md": "# Baking Bread\nFlour, water, salt, yeast, an oven.",
    })
    try:
        notes = vault.load_notes(root)

        ranked = retrieve.search("what are vector embeddings?", notes, top_k=3)
        check("best match ranks first", ranked[0][0].slug, "a/embeddings")
        check_true("irrelevant notes score zero and are dropped",
                   all(n.slug != "a/unrelated" for n, _ in ranked))

        check("title matches outrank body matches",
              retrieve.search("keyword retrieval", notes, top_k=1)[0][0].slug,
              "a/keywords")
        check("a question of only stopwords returns nothing",
              retrieve.search("what is it about the", notes), [])
        check("top_k is respected", len(retrieve.search("search", notes, top_k=1)), 1)

        check("stemming links singular and plural",
              retrieve.stem("embeddings"), retrieve.stem("embedding"))
        check("stemming links noun and gerund",
              retrieve.stem("hallucinating"), retrieve.stem("hallucination"))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_edges():
    print("\nEdge cases - the things that crash a demo")
    empty = Path(tempfile.mkdtemp(prefix="nautilus-empty-"))
    try:
        check("an empty vault returns no notes", vault.load_notes(empty), [])
        check("an empty vault has no domains", vault.domain_counts([]), [])
        check("an empty vault has an empty graph",
              vault.build_graph([])["edges"], [])
        check("a missing vault folder does not crash",
              vault.load_notes(empty / "nope"), [])
    finally:
        shutil.rmtree(empty, ignore_errors=True)

    odd = make_vault({
        "x/blank.md": "",
        "x/unicode.md": "# Café ☕\nAccents and emoji must survive the round trip.",
    })
    try:
        notes = {n.slug: n for n in vault.load_notes(odd)}
        check("an empty note does not crash", notes["x/blank"].title, "Blank")
        check("unicode titles survive", notes["x/unicode"].title, "Café ☕")
        check("scoring an empty note returns zero",
              retrieve.score_note(notes["x/blank"], ["anything"], {}), 0.0)
    finally:
        shutil.rmtree(odd, ignore_errors=True)


def test_automation():
    print("\nFR9-FR11 - automation safety rules")
    sys.path.insert(0, str(Path(__file__).parent.parent / "automation"))
    import common
    import organize

    check("slugify makes safe filenames",
          organize.slugify("Why RAG? (a note!)"), "why-rag-a-note")
    check("slugify never returns empty", organize.slugify("!!!"), "untitled")

    root = Path(tempfile.mkdtemp(prefix="nautilus-auto-"))
    try:
        a = root / "note.md"
        a.write_text("first", encoding="utf-8")
        check("unique_path avoids clobbering an existing file",
              common.unique_path(a).name, "note-2.md")
        check("unique_path leaves a free name alone",
              common.unique_path(root / "free.md").name, "free.md")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # A task that cannot parse the model's reply must do nothing, not guess.
    # Swap the real LLM call for canned replies to test the parsing directly.
    import llm as llm_mod
    real_complete = llm_mod.complete
    try:
        def canned(reply):
            common.llm.complete = lambda *a, **k: reply
            return common.ask_json("ignored", fallback="FELLBACK")

        check("plain JSON parses", canned('{"a": 1}'), {"a": 1})
        check("fenced JSON is recovered",
              canned('```json\n{"a": 2}\n```'), {"a": 2})
        check("JSON wrapped in prose is recovered",
              canned('Sure! Here you go:\n[{"a": 3}]\nHope that helps.'), [{"a": 3}])
        check("unparseable output falls back rather than guessing",
              canned("I could not do that."), "FELLBACK")

        def raiser(*a, **k):
            raise llm_mod.LLMError("provider down")
        common.llm.complete = raiser
        result = common.ask_json("ignored", fallback=[])
        check_true("an unreachable provider does not crash", result is not None)
        # The distinction that matters: "I checked and found nothing" must not
        # be confused with "I could not check", or a failed review reads clean.
        check("an unreachable provider is reported as unchecked, not empty",
              isinstance(result, common.Unchecked), True)
        check_true("unchecked is not an empty list", result != [])
    finally:
        common.llm.complete = real_complete

    body = organize.build_body(
        {"title": "T", "tags": ["x"], "links": ["Real Note", "Made Up"]},
        "# Old Heading\n\nbody text",
        {"Real Note"},
    )
    check_true("invented links are dropped", "[[Made Up]]" not in body)
    check_true("valid links are kept", "[[Real Note]]" in body)
    check_true("the original text is preserved", "body text" in body)
    check("the old heading is not duplicated", body.count("# "), 1)

    # A capture must be filed the way the vault already organises itself.
    folder_vault = make_vault({
        "ai/one.md": "# One\nx",
        "ai/two.md": "# Two\ny",
    })
    flat_vault = make_vault({
        "push.md": "---\ntags: [nautilus, fitness]\n---\n# Push\nx",
        "plan.md": "---\ntags: [nautilus, planning]\n---\n# Plan\ny",
    })
    try:
        uses, universal = organize.vault_style(vault.load_notes(folder_vault))
        check("a foldered vault is detected", uses, True)
        check("a foldered vault has no universal tags", universal, [])

        uses, universal = organize.vault_style(vault.load_notes(flat_vault))
        check("a flat vault is detected", uses, False)
        check("the vault's shared tag is detected", universal, ["nautilus"])

        tagged = organize.build_body(
            {"title": "T", "tags": ["shoulder"], "links": []}, "text", set(),
            frontmatter_tags=universal + ["fitness"],
        )
        check_true("a flat vault gets frontmatter",
                   tagged.startswith("---\ntags: [nautilus, fitness, shoulder]\n---"))
        check_true("a foldered vault gets no frontmatter",
                   not body.startswith("---"))
    finally:
        shutil.rmtree(folder_vault, ignore_errors=True)
        shutil.rmtree(flat_vault, ignore_errors=True)


if __name__ == "__main__":
    print("Nautilus test suite")
    test_reading()
    test_frontmatter()
    test_counts_and_graph()
    test_retrieval()
    test_edges()
    test_automation()
    print(f"\n{PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)
