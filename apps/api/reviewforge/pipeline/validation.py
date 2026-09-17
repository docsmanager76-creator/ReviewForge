"""
Sanity checks on aligned sentence timings. Nothing here fabricates or silently discards bad
timings — every problem found either clamps a timestamp to a valid, ordered range (recording
that adjustment via needsReview) or flags a sentence for human review; the checks never raise
in normal operation, since a single misaligned sentence should not fail an entire analysis run.
"""
from __future__ import annotations

from typing import List

from .sentence_schema import Sentence

# "Near the beginning/end of the audio" tolerance: the larger of an absolute floor and a
# fraction of the total audio duration, so short and long voice-overs both get a sane window.
_EDGE_TOLERANCE_FLOOR_SECONDS = 2.0
_EDGE_TOLERANCE_FRACTION = 0.1

# Alignment rounds timestamps to milliseconds while audioDuration stays unrounded, so a
# sentence legitimately ending "at" the audio's end can appear a few float-epsilons past it.
_FLOAT_SLACK_SECONDS = 0.01


def _edge_tolerance(audio_duration: float) -> float:
    return max(_EDGE_TOLERANCE_FLOOR_SECONDS, _EDGE_TOLERANCE_FRACTION * audio_duration)


def validate_sentences(sentences: List[Sentence], audio_duration: float) -> List[str]:
    """Mutates `needsReview` in place where a check fails; returns a list of human-readable
    issue descriptions for logging/job diagnostics (informational, not fatal)."""
    issues: List[str] = []
    if not sentences:
        return issues

    prev_end = 0.0
    for sentence in sentences:
        if sentence.startTime < 0:
            issues.append(f"{sentence.id}: negative startTime {sentence.startTime}")
            sentence.startTime = 0.0
            sentence.needsReview = True

        if sentence.endTime <= sentence.startTime:
            issues.append(f"{sentence.id}: endTime <= startTime")
            sentence.endTime = sentence.startTime + 0.05
            sentence.needsReview = True

        if sentence.startTime < prev_end:
            issues.append(f"{sentence.id}: overlaps previous sentence")
            sentence.needsReview = True

        if sentence.endTime > audio_duration + _FLOAT_SLACK_SECONDS:
            issues.append(f"{sentence.id}: endTime exceeds audio duration")
            sentence.needsReview = True

        prev_end = max(prev_end, sentence.endTime)

    first, last = sentences[0], sentences[-1]
    tolerance = _edge_tolerance(audio_duration)

    if first.startTime > tolerance:
        issues.append(
            f"{first.id}: starts at {first.startTime}s, more than {tolerance:.2f}s into the audio"
        )
        first.needsReview = True

    if last.endTime < audio_duration - tolerance:
        issues.append(
            f"{last.id}: ends at {last.endTime}s, more than {tolerance:.2f}s before audio ends"
        )
        last.needsReview = True

    total_duration = sum(s.endTime - s.startTime for s in sentences)
    if total_duration > audio_duration + 0.5:
        issues.append(
            f"total sentence duration {total_duration:.2f}s exceeds audio duration {audio_duration:.2f}s"
        )
        for s in sentences:
            s.needsReview = True

    return issues
