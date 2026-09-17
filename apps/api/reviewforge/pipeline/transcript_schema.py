"""Strict transcript schema written to work/transcript.json. Segment/word timestamps come
straight from the local Whisper backend; nothing here is derived from the user's script."""
from __future__ import annotations

import math
from typing import List, Optional

from pydantic import BaseModel

from .whisper_backend import RawTranscript

TRANSCRIPT_SCHEMA_VERSION = "1.0"


class TranscriptWord(BaseModel):
    word: str
    startTime: float
    endTime: float
    confidence: Optional[float] = None


class TranscriptSegment(BaseModel):
    id: str
    startTime: float
    endTime: float
    text: str
    words: Optional[List[TranscriptWord]] = None
    confidence: Optional[float] = None


class Transcript(BaseModel):
    version: str = TRANSCRIPT_SCHEMA_VERSION
    audioDuration: float
    segments: List[TranscriptSegment]


def _logprob_to_confidence(avg_logprob: Optional[float]) -> Optional[float]:
    """Rough proxy: exp(avg log-probability) as a 0-1-ish confidence. Whisper's avg_logprob is
    not a true probability, so this is only ever used as an approximate signal for the UI,
    never as an exact metric."""
    if avg_logprob is None:
        return None
    return max(0.0, min(1.0, math.exp(avg_logprob)))


def transcript_from_raw(raw: RawTranscript) -> Transcript:
    segments: List[TranscriptSegment] = []
    for i, seg in enumerate(raw.segments):
        words = (
            [
                TranscriptWord(
                    word=w.word,
                    startTime=w.start,
                    endTime=w.end,
                    confidence=w.probability,
                )
                for w in seg.words
            ]
            if seg.words
            else None
        )
        segments.append(
            TranscriptSegment(
                id=f"seg_{i + 1:03d}",
                startTime=seg.start,
                endTime=seg.end,
                text=seg.text,
                words=words,
                confidence=_logprob_to_confidence(seg.avg_logprob),
            )
        )
    return Transcript(audioDuration=raw.audio_duration, segments=segments)
