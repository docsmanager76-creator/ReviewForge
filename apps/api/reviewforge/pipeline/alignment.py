"""
Aligns the user's script sentences (exact wording, source of truth) to the timing produced by
Whisper (source of truth for *when* words were spoken, not what they say). The spoken audio
often diverges from the written script (numerals vs. spelled-out numbers, ad-libbed words,
etc.), so this cannot assume a 1:1 mapping between script sentences and Whisper segments.

Strategy: tokenize both the full script and the full Whisper transcript into normalized word
sequences, run Python's stdlib difflib.SequenceMatcher (Ratcliff/Obershelt) to find matching
runs between the two sequences, then use the matched token pairs as timing anchors. Every
script token's approximate spoken time is interpolated between its nearest anchors. This is a
deterministic, local, dependency-free algorithm — no LLM involved, per architecture rule.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import List, Tuple

from .transcript_schema import Transcript

_TOKEN_RE = re.compile(r"[A-Za-z0-9']+")

# A sentence whose matched-token fraction falls below this is flagged needsReview.
LOW_CONFIDENCE_THRESHOLD = 0.5


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text)


def _normalize(token: str) -> str:
    return token.lower().strip("'")


@dataclass
class _WhisperWordTiming:
    token: str
    start: float
    end: float


@dataclass
class SentenceAlignment:
    startTime: float
    endTime: float
    confidence: float
    needsReview: bool


def _flatten_whisper_words(transcript: Transcript) -> List[_WhisperWordTiming]:
    """Word-level timing when available; otherwise approximate by evenly dividing the
    segment's duration across its tokens."""
    flat: List[_WhisperWordTiming] = []
    for seg in transcript.segments:
        if seg.words:
            for w in seg.words:
                for tok in _tokenize(w.word):
                    flat.append(_WhisperWordTiming(token=_normalize(tok), start=w.startTime, end=w.endTime))
        else:
            toks = _tokenize(seg.text)
            if not toks:
                continue
            span = (seg.endTime - seg.startTime) / len(toks)
            for i, tok in enumerate(toks):
                start = seg.startTime + i * span
                flat.append(_WhisperWordTiming(token=_normalize(tok), start=start, end=start + span))
    return flat


def align_sentences(sentences: List[str], transcript: Transcript) -> List[SentenceAlignment]:
    whisper_words = _flatten_whisper_words(transcript)
    whisper_tokens = [w.token for w in whisper_words]

    sentence_spans: List[Tuple[int, int]] = []
    script_tokens: List[str] = []
    for sentence in sentences:
        start_idx = len(script_tokens)
        script_tokens.extend(_normalize(t) for t in _tokenize(sentence))
        sentence_spans.append((start_idx, len(script_tokens)))

    if not whisper_tokens or not script_tokens:
        return [SentenceAlignment(0.0, 0.0, 0.0, True) for _ in sentences]

    matcher = SequenceMatcher(None, script_tokens, whisper_tokens, autojunk=False)
    matching_blocks = matcher.get_matching_blocks()

    # anchors: sorted (script_index, whisper_index) pairs for every exactly-matched token.
    anchors: List[Tuple[int, int]] = []
    matched_script_indices = set()
    anchor_by_script_index: dict[int, int] = {}
    for block in matching_blocks:
        for offset in range(block.size):
            a_idx, b_idx = block.a + offset, block.b + offset
            anchors.append((a_idx, b_idx))
            matched_script_indices.add(a_idx)
            anchor_by_script_index[a_idx] = b_idx

    last_whisper_idx = len(whisper_words) - 1

    def whisper_time_for_script_index(idx: int, *, use_end: bool) -> float:
        """Nearest-anchor interpolation: exact match uses that word's own timing; otherwise
        interpolate proportionally between the closest matched anchors on either side."""
        if idx in anchor_by_script_index:
            w = whisper_words[min(anchor_by_script_index[idx], last_whisper_idx)]
            return w.end if use_end else w.start

        before = max((a for a in anchors if a[0] <= idx), key=lambda a: a[0], default=None)
        after = min((a for a in anchors if a[0] >= idx), key=lambda a: a[0], default=None)

        if before and after and before[0] != after[0]:
            frac = (idx - before[0]) / (after[0] - before[0])
            b_start = whisper_words[min(before[1], last_whisper_idx)].start
            b_end = whisper_words[min(after[1], last_whisper_idx)].start
            return b_start + frac * (b_end - b_start)
        if before:
            return whisper_words[min(before[1], last_whisper_idx)].end
        if after:
            return whisper_words[min(after[1], last_whisper_idx)].start
        return 0.0

    audio_duration = transcript.audioDuration
    results: List[SentenceAlignment] = []

    for start_idx, end_idx in sentence_spans:
        if end_idx <= start_idx:
            results.append(SentenceAlignment(0.0, 0.0, 0.0, True))
            continue

        token_range = range(start_idx, end_idx)
        matched_count = sum(1 for i in token_range if i in matched_script_indices)
        confidence = round(matched_count / (end_idx - start_idx), 3)

        start_time = whisper_time_for_script_index(start_idx, use_end=False)
        end_time = whisper_time_for_script_index(end_idx - 1, use_end=True)

        start_time = max(0.0, min(start_time, audio_duration))
        end_time = max(start_time + 0.01, min(max(end_time, start_time + 0.01), audio_duration if audio_duration > 0 else end_time))

        results.append(
            SentenceAlignment(
                startTime=round(start_time, 3),
                endTime=round(end_time, 3),
                confidence=confidence,
                needsReview=confidence < LOW_CONFIDENCE_THRESHOLD,
            )
        )

    _enforce_monotonic(results)
    return results


def _enforce_monotonic(results: List[SentenceAlignment]) -> None:
    """Alignment interpolation can occasionally produce out-of-order or overlapping
    timestamps for badly-matched sentences; nudge them into a valid, chronological sequence
    and flag anything adjusted for human review rather than silently keeping bad timings."""
    prev_end = 0.0
    for r in results:
        if r.startTime < prev_end:
            r.startTime = prev_end
            r.needsReview = True
        if r.endTime <= r.startTime:
            r.endTime = round(r.startTime + 0.05, 3)
            r.needsReview = True
        prev_end = r.endTime
