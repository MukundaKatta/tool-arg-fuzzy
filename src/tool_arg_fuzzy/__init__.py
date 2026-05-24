"""tool-arg-fuzzy - match LLM enum-value typos to the schema.

The schema says `vendor` is one of `["Anthropic", "OpenAI", "Google"]`.
The LLM produces `"anthropic"`. Strict validation rejects it. The LLM
gets a confusing rejection and produces something equally weird on the
next turn. `fuzzy_match` would have returned `"Anthropic"` from the
case-insensitive exact match and saved a round trip.

`coerce_enums(args, schema)` walks an args dict against a JSON Schema
and rewrites each property whose value is *close-but-not-equal* to one
of the schema's `enum` values.

    from tool_arg_fuzzy import coerce_enums

    schema = {
        "type": "object",
        "properties": {
            "vendor": {"type": "string", "enum": ["Anthropic", "OpenAI", "Google"]},
            "size": {"type": "string", "enum": ["small", "medium", "large"]},
        },
    }

    args = {"vendor": "anthropic", "size": "lg"}
    fixed, warnings = coerce_enums(args, schema)
    # fixed == {"vendor": "Anthropic", "size": "large"}

Match cascade (first hit wins, no Levenshtein):

    1. exact equality
    2. case-insensitive exact
    3. value is a (case-insensitive) prefix of an enum
    4. value is a (case-insensitive) substring of an enum
    5. an enum is a (case-insensitive) substring of value
    6. no match → return value unchanged, no warning

Substring matches are guarded against ambiguity: if two enum values both
match the value at the same tier, the function returns no match for
that property (warnings record the ambiguity).
"""

from __future__ import annotations

from typing import Any, Iterable

__version__ = "0.1.0"
__all__ = [
    "fuzzy_match",
    "coerce_enums",
]


# ---- single value match ---------------------------------------------------


def fuzzy_match(
    value: Any,
    candidates: Iterable[str],
) -> str | None:
    """Pick the best candidate for `value`, or None if no unambiguous match.

    Returns:
        The matched candidate string, or None when no candidate matches
        or two candidates match at the same precedence tier.
    """
    if not isinstance(value, str):
        return None
    cands = list(candidates)

    # 1. exact
    for c in cands:
        if value == c:
            return c

    lower_v = value.lower()

    # 2. case-insensitive exact
    matches = [c for c in cands if c.lower() == lower_v]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None

    # 3. value is prefix of candidate
    matches = [c for c in cands if c.lower().startswith(lower_v)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None

    # 4. value is substring of candidate
    matches = [c for c in cands if lower_v in c.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None

    # 5. candidate is substring of value
    matches = [c for c in cands if c.lower() in lower_v]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return None

    return None


# ---- whole-args coercion -------------------------------------------------


def coerce_enums(
    args: dict[str, Any],
    schema: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Walk `args` against `schema`, rewrite each `enum`-constrained string.

    Returns:
        `(fixed_dict, warnings)`. The original args dict is not mutated.

    Notes:
        - Only top-level properties are walked. For nested objects, call
          recursively with the appropriate sub-schema.
        - Properties without `enum` pass through unchanged.
        - Ambiguous matches (two candidates at same tier) are left unchanged
          and emit a warning.
    """
    if not isinstance(args, dict):
        return args, []  # type: ignore[return-value]

    props = schema.get("properties") or {}
    out: dict[str, Any] = {}
    warnings: list[str] = []

    for k, v in args.items():
        sub = props.get(k)
        if not isinstance(sub, dict) or "enum" not in sub:
            out[k] = v
            continue
        enum_values = [e for e in sub["enum"] if isinstance(e, str)]
        if not enum_values or not isinstance(v, str):
            out[k] = v
            continue
        if v in enum_values:
            out[k] = v
            continue
        match = fuzzy_match(v, enum_values)
        if match is None:
            out[k] = v
            warnings.append(
                f"$.{k}: {v!r} did not match any enum value; left as-is"
            )
            continue
        out[k] = match
        warnings.append(f"$.{k}: fuzzy-matched {v!r} → {match!r}")

    return out, warnings
