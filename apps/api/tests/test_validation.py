from reviewforge.pipeline.sentence_schema import Sentence
from reviewforge.pipeline.validation import validate_sentences


def make_sentence(**overrides) -> Sentence:
    defaults = dict(
        id="sentence_001",
        index=0,
        text="Some text.",
        startTime=0.0,
        endTime=1.0,
        alignmentConfidence=1.0,
        needsReview=False,
    )
    defaults.update(overrides)
    return Sentence(**defaults)


def test_valid_sentences_pass_without_flags():
    sentences = [
        make_sentence(id="sentence_001", index=0, startTime=0.0, endTime=2.0),
        make_sentence(id="sentence_002", index=1, startTime=2.0, endTime=4.0),
        make_sentence(id="sentence_003", index=2, startTime=4.0, endTime=10.0),
    ]
    issues = validate_sentences(sentences, audio_duration=10.0)
    assert issues == []
    assert all(not s.needsReview for s in sentences)


def test_negative_start_time_is_clamped_and_flagged():
    sentences = [make_sentence(startTime=-5.0, endTime=1.0)]
    issues = validate_sentences(sentences, audio_duration=5.0)
    assert sentences[0].startTime == 0.0
    assert sentences[0].needsReview is True
    assert any("negative" in i for i in issues)


def test_end_before_start_is_fixed_and_flagged():
    sentences = [make_sentence(startTime=2.0, endTime=1.0)]
    validate_sentences(sentences, audio_duration=5.0)
    assert sentences[0].endTime > sentences[0].startTime
    assert sentences[0].needsReview is True


def test_overlap_between_sentences_is_flagged():
    sentences = [
        make_sentence(id="sentence_001", index=0, startTime=0.0, endTime=3.0),
        make_sentence(id="sentence_002", index=1, startTime=2.0, endTime=5.0),
    ]
    issues = validate_sentences(sentences, audio_duration=5.0)
    assert sentences[1].needsReview is True
    assert any("overlaps" in i for i in issues)


def test_first_sentence_far_from_start_is_flagged():
    sentences = [
        make_sentence(id="sentence_001", index=0, startTime=8.0, endTime=9.0),
        make_sentence(id="sentence_002", index=1, startTime=9.0, endTime=10.0),
    ]
    validate_sentences(sentences, audio_duration=10.0)
    assert sentences[0].needsReview is True


def test_last_sentence_far_from_end_is_flagged():
    sentences = [
        make_sentence(id="sentence_001", index=0, startTime=0.0, endTime=1.0),
        make_sentence(id="sentence_002", index=1, startTime=1.0, endTime=2.0),
    ]
    validate_sentences(sentences, audio_duration=10.0)
    assert sentences[1].needsReview is True


def test_endtime_exceeding_audio_duration_is_flagged():
    sentences = [make_sentence(startTime=0.0, endTime=20.0)]
    issues = validate_sentences(sentences, audio_duration=10.0)
    assert sentences[0].needsReview is True
    assert any("exceeds audio duration" in i for i in issues)


def test_empty_sentence_list_is_a_noop():
    assert validate_sentences([], audio_duration=10.0) == []


def test_endtime_within_float_epsilon_of_audio_duration_is_not_flagged():
    # Alignment rounds timestamps to milliseconds while audioDuration itself is unrounded, so
    # a sentence legitimately ending at the audio's end can appear a hair past it in floats.
    audio_duration = 11.199999999999994
    sentences = [
        make_sentence(id="sentence_001", index=0, startTime=0.0, endTime=9.45),
        make_sentence(id="sentence_002", index=1, startTime=9.45, endTime=11.2),
    ]
    issues = validate_sentences(sentences, audio_duration=audio_duration)
    assert issues == []
    assert all(not s.needsReview for s in sentences)
