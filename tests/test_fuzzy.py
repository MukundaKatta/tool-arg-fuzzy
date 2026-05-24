"""Tests for tool_arg_fuzzy."""

from __future__ import annotations

import pytest

from tool_arg_fuzzy import coerce_enums, fuzzy_match


# ---- fuzzy_match: exact + case ------------------------------------------


def test_exact_match_wins():
    assert fuzzy_match("Anthropic", ["Anthropic", "OpenAI"]) == "Anthropic"


def test_case_insensitive_exact():
    assert fuzzy_match("anthropic", ["Anthropic", "OpenAI"]) == "Anthropic"


def test_case_insensitive_exact_returns_canonical():
    # Canonical form from the candidate list, not the user input form
    assert fuzzy_match("ANTHROPIC", ["Anthropic"]) == "Anthropic"


# ---- prefix matching ---------------------------------------------------


def test_value_is_prefix_of_candidate():
    assert fuzzy_match("ant", ["Anthropic", "OpenAI"]) == "Anthropic"


def test_prefix_match_ambiguous_returns_none():
    # "an" matches both Anthropic and Andromeda
    assert fuzzy_match("an", ["Anthropic", "Andromeda"]) is None


# ---- substring matching ------------------------------------------------


def test_value_is_substring_of_candidate():
    assert fuzzy_match("thropic", ["Anthropic"]) == "Anthropic"


def test_candidate_is_substring_of_value():
    assert fuzzy_match("large-size", ["large", "small"]) == "large"


def test_substring_ambiguous_returns_none():
    # "ai" is substring of both OpenAI and ClaudeAI; not a prefix of either
    assert fuzzy_match("ai", ["OpenAI", "ClaudeAI", "Cohere"]) is None


# ---- non-string + edge cases -------------------------------------------


def test_non_string_value_returns_none():
    assert fuzzy_match(42, ["a", "b"]) is None
    assert fuzzy_match(None, ["a", "b"]) is None


def test_empty_candidates_returns_none():
    assert fuzzy_match("x", []) is None


def test_no_match_returns_none():
    assert fuzzy_match("xyz", ["abc", "def"]) is None


# ---- coerce_enums (whole args) ----------------------------------------


SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string", "enum": ["Anthropic", "OpenAI", "Google"]},
        "size": {"type": "string", "enum": ["small", "medium", "large"]},
        "q": {"type": "string"},  # no enum
    },
}


def test_coerce_basic():
    # "med" matches "medium" by prefix; "anthropic" matches "Anthropic" by case
    args = {"vendor": "anthropic", "size": "med"}
    fixed, w = coerce_enums(args, SCHEMA)
    assert fixed == {"vendor": "Anthropic", "size": "medium"}
    assert len(w) == 2


def test_coerce_passes_through_non_enum_prop():
    args = {"q": "hi"}
    fixed, w = coerce_enums(args, SCHEMA)
    assert fixed == {"q": "hi"}
    assert w == []


def test_coerce_passes_through_unknown_prop():
    args = {"random": "yes"}
    fixed, _ = coerce_enums(args, SCHEMA)
    assert fixed == {"random": "yes"}


def test_coerce_exact_match_no_warning():
    args = {"vendor": "Anthropic"}
    fixed, w = coerce_enums(args, SCHEMA)
    assert fixed == {"vendor": "Anthropic"}
    assert w == []


def test_coerce_unmatchable_value_left_as_is_and_warned():
    args = {"vendor": "xyz"}
    fixed, w = coerce_enums(args, SCHEMA)
    assert fixed == {"vendor": "xyz"}
    assert any("did not match" in msg for msg in w)


def test_coerce_does_not_mutate_input():
    args = {"vendor": "anthropic"}
    snap = dict(args)
    coerce_enums(args, SCHEMA)
    assert args == snap


def test_coerce_non_dict_args_passthrough():
    out, w = coerce_enums("not a dict", SCHEMA)  # type: ignore[arg-type]
    assert out == "not a dict"


def test_coerce_skips_non_string_enum_values():
    schema = {"type": "object", "properties": {
        "k": {"type": "integer", "enum": [1, 2, 3]},
    }}
    args = {"k": 2}
    fixed, w = coerce_enums(args, schema)
    assert fixed == {"k": 2}  # non-string enums skipped, value passes through


def test_coerce_ambiguous_left_as_is_with_warning():
    schema = {"type": "object", "properties": {
        "v": {"type": "string", "enum": ["Anthropic", "Andromeda"]},
    }}
    args = {"v": "an"}
    fixed, w = coerce_enums(args, schema)
    assert fixed["v"] == "an"
    assert any("did not match" in msg for msg in w)
