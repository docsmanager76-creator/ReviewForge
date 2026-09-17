from reviewforge.pipeline.script_parser import parse_script_sentences


def test_basic_periods():
    assert parse_script_sentences("This is one sentence. This is another.") == [
        "This is one sentence.",
        "This is another.",
    ]


def test_question_and_exclamation_marks():
    assert parse_script_sentences("Is this the best drill? Yes, absolutely!") == [
        "Is this the best drill?",
        "Yes, absolutely!",
    ]


def test_abbreviations_not_split():
    result = parse_script_sentences("Dr. Smith reviewed the drill. He said it was great.")
    assert result == [
        "Dr. Smith reviewed the drill.",
        "He said it was great.",
    ]


def test_dotted_abbreviations_not_split():
    result = parse_script_sentences(
        "This uses e.g. a 20V battery and i.e. lithium-ion cells. It ships in the U.S. today."
    )
    assert result == [
        "This uses e.g. a 20V battery and i.e. lithium-ion cells.",
        "It ships in the U.S. today.",
    ]


def test_decimal_numbers_not_split():
    result = parse_script_sentences("The chuck is 3.5 millimeters wide. It fits most bits.")
    assert result == [
        "The chuck is 3.5 millimeters wide.",
        "It fits most bits.",
    ]


def test_product_names_and_model_numbers_preserved():
    result = parse_script_sentences("The Widget Pro WP-2000 is our top pick. It has 2,000 RPM.")
    assert result == [
        "The Widget Pro WP-2000 is our top pick.",
        "It has 2,000 RPM.",
    ]


def test_quoted_phrases():
    result = parse_script_sentences('He said "Stop now." Then he left the room.')
    assert result == [
        'He said "Stop now."',
        "Then he left the room.",
    ]


def test_bullet_list_items_become_separate_sentences():
    script = "- Long battery life\n- Compact design\n- Great for the jobsite"
    assert parse_script_sentences(script) == [
        "Long battery life",
        "Compact design",
        "Great for the jobsite",
    ]


def test_numbered_list_items():
    script = "1. First feature.\n2. Second feature."
    assert parse_script_sentences(script) == [
        "First feature.",
        "Second feature.",
    ]


def test_ellipsis_not_treated_as_sentence_boundary_alone():
    result = parse_script_sentences("Wait... this is amazing! Really?")
    assert result == [
        "Wait... this is amazing!",
        "Really?",
    ]


def test_empty_script_returns_empty_list():
    assert parse_script_sentences("") == []
    assert parse_script_sentences("   \n\n   ") == []


def test_malformed_script_does_not_raise():
    # No terminal punctuation at all, stray symbols, etc. — should not raise, best effort.
    weird_inputs = [
        "no punctuation at all just words",
        "!!!???...",
        "\t\t\n\n---\n\n",
        "a" * 5000,
    ]
    for text in weird_inputs:
        result = parse_script_sentences(text)
        assert isinstance(result, list)
