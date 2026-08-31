"""Keyword retrieval - the first half of FR5.

Deliberately simple: no embeddings, no vector store, no model. Scoring is
explainable, instant, and free. Swapping in semantic search later means
replacing this one module.
"""
from __future__ import annotations

import re
from math import log

import config
from vault import Note

TOKEN_RE = re.compile(r"[a-z0-9']+")

# Crude suffix stripping so "hallucinating" matches "hallucination". Not a real
# stemmer - just enough to survive the plural/gerund mismatches that otherwise
# make an obviously relevant note score zero.
SUFFIXES = ("ations", "ation", "ating", "ising", "izing", "ings", "ing", "ies",
            "ers", "er", "ed", "es", "s")

# Words too common to carry signal in a question.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "did", "do",
    "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "is", "it",
    "its", "me", "my", "no", "not", "of", "on", "or", "so", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "to", "was", "we", "were",
    "what", "when", "where", "which", "who", "why", "will", "with", "you", "your",
    "about", "tell", "know", "notes", "note",
}

# Where a term appears matters more than how often. Titles are the strongest
# signal; without this weighting, long notes win simply by being long.
W_TITLE, W_DOMAIN, W_BODY = 6.0, 3.0, 1.0


def stem(token: str) -> str:
    for suffix in SUFFIXES:
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            base = token[: -len(suffix)]
            return base[:-1] if base.endswith("i") else base
    return token


def tokenize(text: str) -> list[str]:
    return [
        stem(t)
        for t in TOKEN_RE.findall(text.lower())
        if t not in STOPWORDS and len(t) > 1
    ]


def _idf(notes: list[Note]) -> dict[str, float]:
    """Rare terms discriminate; terms in every note do not."""
    total = len(notes) or 1
    seen: dict[str, int] = {}
    for note in notes:
        for term in set(tokenize(note.body) + tokenize(note.title)):
            seen[term] = seen.get(term, 0) + 1
    return {term: log(1 + total / (1 + count)) for term, count in seen.items()}


def score_note(note: Note, terms: list[str], idf: dict[str, float]) -> float:
    title_tokens = tokenize(note.title)
    body_tokens = tokenize(note.body)
    domain_tokens = tokenize(note.domain)
    if not body_tokens and not title_tokens:
        return 0.0

    score = 0.0
    for term in set(terms):
        weight = idf.get(term, 1.0)
        hits = (
            W_TITLE * title_tokens.count(term)
            + W_DOMAIN * domain_tokens.count(term)
            + W_BODY * body_tokens.count(term)
        )
        if hits:
            # Saturating: the 10th mention of a word adds less than the 2nd.
            score += weight * (1 + log(hits))

    # Reward notes that cover more of the question rather than one word loudly.
    covered = sum(1 for t in set(terms) if t in title_tokens or t in body_tokens)
    if terms:
        score *= 0.5 + 0.5 * (covered / len(set(terms)))
    return score


def search(question: str, notes: list[Note], top_k: int | None = None) -> list[tuple[Note, float]]:
    """Return the best-matching notes, highest score first."""
    top_k = top_k or config.TOP_K
    terms = tokenize(question)
    if not terms:
        return []
    idf = _idf(notes)
    ranked = [(n, score_note(n, terms, idf)) for n in notes]
    ranked = [(n, s) for n, s in ranked if s > 0]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked[:top_k]
