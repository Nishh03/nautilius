"""The only module that knows an AI provider exists - satisfies the
'swappable AI' non-functional requirement.

Every provider implements one thing: text in, text out. Switching models is a
one-line change in .env, not a rewrite. Three providers ship by default:

    ollama  - local, free, notes never leave the machine (default)
    groq    - free cloud tier, very fast, needs GROQ_API_KEY
    gemini  - free cloud tier, needs GEMINI_API_KEY
"""
from __future__ import annotations

import time

import httpx

import config
from vault import Note

TIMEOUT = 300.0         # a cold 7B model on CPU can take minutes to load
GROQ_RETRIES = 3        # free tier is capped per minute; waiting usually clears it

SYSTEM_PROMPT = """You are Nautilus, a research assistant that answers strictly from a user's personal notes.

Rules:
- Answer using ONLY the notes provided. Never use outside knowledge, and never guess.
- Write 2 to 5 complete sentences. A bare word or phrase is not an acceptable answer.
- Explain the reasoning the notes give, not just the conclusion.
- Refer to notes by their title when you draw on them, in plain prose.
- Do not copy [[wikilink]] brackets into your answer; write the plain words.
- If the notes genuinely do not cover the question, say exactly which topic is
  missing, in one sentence, and stop. Do not invent anything."""


class LLMError(RuntimeError):
    """Provider unreachable, unauthenticated, or refusing to answer."""


# --- Providers: each takes a prompt, returns text ---------------------------

def _ollama(prompt: str) -> str:
    try:
        r = httpx.post(
            f"{config.OLLAMA_HOST}/api/chat",
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                # Keep the model resident so the next question is not paying
                # the cold-load cost again.
                "keep_alive": "30m",
                "options": {"temperature": 0.2},
            },
            timeout=TIMEOUT,
        )
    except httpx.TimeoutException as exc:
        raise LLMError(
            f"Ollama did not respond within {TIMEOUT:.0f}s. The model may still be "
            f"loading - try again, or use a smaller model (e.g. llama3.2:3b)."
        ) from exc
    except httpx.RequestError as exc:
        raise LLMError(
            f"Cannot reach Ollama at {config.OLLAMA_HOST}. Is `ollama serve` running?"
        ) from exc
    if r.status_code != 200:
        raise LLMError(f"Ollama returned {r.status_code}: {r.text[:200]}")
    return r.json()["message"]["content"].strip()


def _groq(prompt: str, _attempt: int = 0) -> str:
    if not config.GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY is not set in .env")
    try:
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": config.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=TIMEOUT,
        )
    except httpx.RequestError as exc:
        raise LLMError(f"Cannot reach Groq: {exc}") from exc

    # The free tier is capped per minute, so a batch job hits 429 routinely.
    # Waiting is the correct response, not failing - but only a few times, or a
    # genuinely exhausted quota turns into an unbounded stall.
    if r.status_code == 429 and _attempt < GROQ_RETRIES:
        wait = _retry_after(r)
        print(f"    (rate limited, waiting {wait:.0f}s then retrying)")
        time.sleep(wait)
        return _groq(prompt, _attempt + 1)

    if r.status_code == 413:
        raise LLMError(
            "Groq rejected the request as too large for the free tier's "
            "per-minute token limit. Send fewer or shorter notes per call."
        )
    if r.status_code != 200:
        raise LLMError(f"Groq returned {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"].strip()


def _retry_after(response: httpx.Response) -> float:
    """How long to wait after a 429, from the header when the API supplies one."""
    header = response.headers.get("retry-after")
    if header:
        try:
            return min(float(header) + 1.0, 65.0)
        except ValueError:
            pass
    return 20.0


def _gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set in .env")
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{config.GEMINI_MODEL}:generateContent",
            headers={"x-goog-api-key": config.GEMINI_API_KEY},
            json={
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            },
            timeout=TIMEOUT,
        )
    except httpx.RequestError as exc:
        raise LLMError(f"Cannot reach Gemini: {exc}") from exc
    if r.status_code != 200:
        raise LLMError(f"Gemini returned {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


PROVIDERS = {"ollama": _ollama, "groq": _groq, "gemini": _gemini}


def complete(prompt: str, provider: str | None = None) -> str:
    """Raw text-in text-out. Used by the chat endpoint and the automations."""
    name = (provider or config.LLM_PROVIDER).lower()
    if name not in PROVIDERS:
        raise LLMError(f"Unknown provider '{name}'. Choose one of {list(PROVIDERS)}.")
    return PROVIDERS[name](prompt)


def active_model() -> str:
    return {
        "ollama": config.OLLAMA_MODEL,
        "groq": config.GROQ_MODEL,
        "gemini": config.GEMINI_MODEL,
    }.get(config.LLM_PROVIDER, "unknown")


def health() -> dict:
    """Is the configured provider usable right now? Shown in the UI header."""
    provider = config.LLM_PROVIDER
    info = {"provider": provider, "model": active_model()}
    if provider == "ollama":
        try:
            r = httpx.get(f"{config.OLLAMA_HOST}/api/tags", timeout=5.0)
            installed = [m["name"] for m in r.json().get("models", [])]
            info["ready"] = config.OLLAMA_MODEL in installed
            info["detail"] = (
                "ready" if info["ready"]
                else f"model not pulled - run: ollama pull {config.OLLAMA_MODEL}"
            )
        except httpx.RequestError:
            info["ready"] = False
            info["detail"] = "ollama not running - run: ollama serve"
    else:
        key = config.GROQ_API_KEY if provider == "groq" else config.GEMINI_API_KEY
        info["ready"] = bool(key)
        info["detail"] = "ready" if key else f"missing API key for {provider}"
    return info


# --- FR5 + FR6: grounded answer with named sources --------------------------

def build_prompt(question: str, notes: list[Note]) -> str:
    blocks = []
    for note in notes:
        body = note.body[: config.MAX_NOTE_CHARS]
        # Deliberately unnumbered: given "NOTE 1", a small model cites "Note 1"
        # back at the user instead of the note's actual title.
        blocks.append(f'--- NOTE "{note.title}" (domain: {note.domain}) ---\n{body}')
    context = "\n\n".join(blocks) if blocks else "(no notes matched this question)"
    return f"{context}\n\n--- QUESTION ---\n{question}"


def ask(question: str, notes: list[Note]) -> dict:
    """Answer a question from the given notes and name every source used."""
    if not notes:
        return {
            "answer": "Nothing in the vault matches that question.",
            "sources": [],
            "model": active_model(),
            "provider": config.LLM_PROVIDER,
        }
    answer = complete(build_prompt(question, notes))
    return {
        "answer": answer,
        # FR6 - the user can always verify where an answer came from.
        "sources": [
            {"slug": n.slug, "title": n.title, "domain": n.domain} for n in notes
        ],
        "model": active_model(),
        "provider": config.LLM_PROVIDER,
    }
