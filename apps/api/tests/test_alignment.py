from reviewforge.pipeline.alignment import align_sentences
from reviewforge.pipeline.transcript_schema import Transcript, TranscriptSegment, TranscriptWord

from .fixtures import build_transcript_from_words


def test_alignment_with_matching_words_is_high_confidence():
    words = "this drill delivers up to two thousand rpm it also has a compact grip".split()
    transcript = build_transcript_from_words(words)

    sentences = [
        "This drill delivers up to two thousand RPM.",
        "It also has a compact grip.",
    ]
    results = align_sentences(sentences, transcript)

    assert len(results) == 2
    assert results[0].confidence == 1.0
    assert results[1].confidence == 1.0
    for r in results:
        assert r.startTime < r.endTime
        assert not r.needsReview


def test_alignment_handles_spoken_vs_written_number_divergence():
    # Spoken: "two thousand"; written: "2,000" — different tokens, but the rest of the
    # sentence matches, so confidence should be partial, not zero, and timing still sane.
    words = "this drill delivers up to two thousand rpm".split()
    transcript = build_transcript_from_words(words)

    sentences = ["This drill delivers up to 2,000 RPM."]
    results = align_sentences(sentences, transcript)

    assert len(results) == 1
    result = results[0]
    assert 0.0 < result.confidence < 1.0
    assert result.startTime == 0.0
    assert result.endTime > result.startTime


def test_alignment_orders_sentences_chronologically():
    words = "first sentence here second sentence here third sentence here".split()
    transcript = build_transcript_from_words(words)
    sentences = ["First sentence here.", "Second sentence here.", "Third sentence here."]

    results = align_sentences(sentences, transcript)

    prev_end = 0.0
    for r in results:
        assert r.startTime >= prev_end
        assert r.endTime > r.startTime
        prev_end = r.endTime


def test_alignment_flags_low_confidence_when_mostly_unmatched():
    transcript = build_transcript_from_words(["completely", "unrelated", "audio", "content"])
    sentences = ["This sentence shares no words with that recording whatsoever."]

    results = align_sentences(sentences, transcript)

    assert len(results) == 1
    assert results[0].confidence == 0.0
    assert results[0].needsReview is True
    # Still a valid, non-negative, ordered timestamp pair — never silently bad.
    assert results[0].startTime >= 0.0
    assert results[0].endTime > results[0].startTime


def test_alignment_with_no_whisper_words_flags_all_sentences():
    transcript = Transcript(audioDuration=0.0, segments=[])
    sentences = ["Some sentence.", "Another sentence."]

    results = align_sentences(sentences, transcript)

    assert len(results) == 2
    assert all(r.needsReview for r in results)
    assert all(r.confidence == 0.0 for r in results)


def test_alignment_with_no_word_level_timestamps_falls_back_to_even_split():
    segment = TranscriptSegment(
        id="seg_001",
        startTime=0.0,
        endTime=4.0,
        text="hello world this works",
        words=None,
    )
    transcript = Transcript(audioDuration=4.0, segments=[segment])

    results = align_sentences(["Hello world this works."], transcript)

    assert len(results) == 1
    assert results[0].confidence == 1.0
    assert 0.0 <= results[0].startTime < results[0].endTime <= 4.0
