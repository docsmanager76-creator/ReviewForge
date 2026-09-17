"""Deterministic transcript fixtures shared by alignment/pipeline tests. Never touches a real
Whisper model — these build a Transcript directly from hand-authored word timings."""
from __future__ import annotations

from typing import List, Sequence, Tuple

from reviewforge.pipeline.transcript_schema import Transcript, TranscriptSegment, TranscriptWord


def build_transcript_from_words(word_texts: Sequence[str], word_duration: float = 0.4) -> Transcript:
    """One segment containing every word, each `word_duration` seconds long, back to back."""
    words: List[TranscriptWord] = []
    t = 0.0
    for text in word_texts:
        words.append(TranscriptWord(word=text, startTime=t, endTime=t + word_duration))
        t += word_duration

    segment = TranscriptSegment(
        id="seg_001",
        startTime=0.0,
        endTime=t,
        text=" ".join(word_texts),
        words=words,
    )
    return Transcript(audioDuration=t, segments=[segment])


def build_fake_raw_transcript_wav_bytes() -> bytes:
    """Minimal (silent, near-empty) valid WAV file bytes, for tests that only need a file to
    exist on disk and be readable — never fed to a real Whisper model."""
    import struct

    sample_rate = 16000
    num_samples = 1600  # 0.1s of silence
    data = b"\x00\x00" * num_samples
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data
