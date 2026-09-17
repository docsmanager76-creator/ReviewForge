"""
Splits the user-provided script.md into sentences, preserving the exact wording. This text is
the source of truth for sentence content — Whisper's transcription text is only ever used for
timing (see alignment.py), never for sentence wording.

Strategy: protect periods that are NOT sentence boundaries (abbreviations, decimal numbers,
ellipses) with a placeholder character, split on the remaining genuine [.!?] boundaries, then
restore the placeholder back to '.'. Bullet/numbered list lines are each treated as their own
paragraph before splitting, since a list item's wording should not merge with the next line.
"""
from __future__ import annotations

import re
from typing import List

_PLACEHOLDER = chr(0)

_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")

# Abbreviations whose trailing period must not be treated as a sentence boundary.
_SIMPLE_ABBREVIATIONS = (
    "Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Mt|vs|etc|approx|No|Inc|Ltd|Co|Corp|Fig|Vol|Ave|Rd|Jan|Feb|"
    "Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
_SIMPLE_ABBREVIATION_RE = re.compile(rf"\b(?:{_SIMPLE_ABBREVIATIONS})\.", re.IGNORECASE)

# Multi-period abbreviations, e.g. "e.g.", "i.e.", "U.S.", "U.K.", "a.m.", "p.m."
_DOTTED_ABBREVIATION_RE = re.compile(r"\b(?:[A-Za-z]\.){1,4}[A-Za-z]?\.", re.IGNORECASE)

_DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")
_ELLIPSIS_RE = re.compile(r"\.\.\.")

# A genuine sentence boundary: one or more terminators, optionally followed by a closing
# quote/paren, followed by whitespace or end-of-string. Anything caught here is real, because
# abbreviation/decimal/ellipsis periods were already replaced with the placeholder above.
_BOUNDARY_RE = re.compile(r"[.!?]+[\"'’”)]*(?:\s+|$)")


def _protect(text: str) -> str:
    text = _ELLIPSIS_RE.sub(_PLACEHOLDER * 3, text)
    text = _DECIMAL_RE.sub(_PLACEHOLDER, text)
    text = _DOTTED_ABBREVIATION_RE.sub(lambda m: m.group(0).replace(".", _PLACEHOLDER), text)
    text = _SIMPLE_ABBREVIATION_RE.sub(lambda m: m.group(0).replace(".", _PLACEHOLDER), text)
    return text


def _restore(text: str) -> str:
    return text.replace(_PLACEHOLDER, ".")


def _split_into_paragraphs(script_text: str) -> List[str]:
    """Blank-line-separated runs of text become one paragraph (soft-wrapped lines are
    joined with a space); a bullet/numbered list line is always its own paragraph."""
    paragraphs: List[str] = []
    current: List[str] = []

    for line in script_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if _BULLET_RE.match(line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(_BULLET_RE.sub("", line).strip())
        else:
            current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    return [p for p in paragraphs if p]


def _split_paragraph_into_sentences(paragraph: str) -> List[str]:
    protected = _protect(paragraph)
    sentences: List[str] = []
    last_end = 0

    for match in _BOUNDARY_RE.finditer(protected):
        end = match.end()
        candidate = protected[last_end:end].strip()
        if candidate:
            sentences.append(_restore(candidate))
        last_end = end

    remainder = protected[last_end:].strip()
    if remainder:
        sentences.append(_restore(remainder))

    return sentences


def parse_script_sentences(script_text: str) -> List[str]:
    """Never raises — a malformed or empty script simply yields an empty/best-effort list.
    The caller (analyze_voice) decides whether an empty result is fatal."""
    sentences: List[str] = []
    for paragraph in _split_into_paragraphs(script_text):
        sentences.extend(_split_paragraph_into_sentences(paragraph))
    return sentences
