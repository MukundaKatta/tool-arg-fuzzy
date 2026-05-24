# tool-arg-fuzzy

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tool-arg-fuzzy.svg)](https://pypi.org/project/tool-arg-fuzzy/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Fuzzy-match LLM-generated args to JSON Schema enum values.** Zero deps, no Levenshtein. Just a sensible cascade of exact / case-insensitive / prefix / substring matches.

```python
from tool_arg_fuzzy import coerce_enums

schema = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string", "enum": ["Anthropic", "OpenAI", "Google"]},
        "size": {"type": "string", "enum": ["small", "medium", "large"]},
    },
}

args = {"vendor": "anthropic", "size": "med"}
fixed, warnings = coerce_enums(args, schema)
# fixed == {"vendor": "Anthropic", "size": "medium"}
# warnings == ["$.vendor: fuzzy-matched 'anthropic' → 'Anthropic'", ...]
```

## Why

The schema says `vendor ∈ {Anthropic, OpenAI, Google}`. The LLM emits `"anthropic"`. Strict validation rejects it. The agent loses a turn round-tripping a casing typo.

`tool-arg-fuzzy` fills the most common gap: case typos and abbreviated forms. It's intentionally conservative — ambiguous matches return `None` rather than guessing, and any non-match leaves the value alone with a warning so downstream validation can surface a real error.

Pair with [`tool-arg-coerce-py`](https://github.com/MukundaKatta/tool-arg-coerce-py) (type coercion) for the full LLM-args repair pipeline before strict validation.

## Match cascade (first hit wins)

1. Exact equality
2. Case-insensitive exact
3. Value is a (case-insensitive) prefix of a candidate
4. Value is a (case-insensitive) substring of a candidate
5. A candidate is a (case-insensitive) substring of the value
6. No match → value unchanged, warning emitted

If two candidates match at the same tier, the result is `None` (ambiguous — caller can deal with it).

## Install

```bash
pip install tool-arg-fuzzy
```

## API

```python
from tool_arg_fuzzy import fuzzy_match, coerce_enums

fuzzy_match(value: str, candidates: Iterable[str]) -> str | None
coerce_enums(args: dict, schema: dict) -> (dict, list[str])
```

`coerce_enums` walks only top-level properties. For nested objects, recurse with the appropriate sub-schema.

## Companion libraries

- [`tool-arg-coerce-py`](https://github.com/MukundaKatta/tool-arg-coerce-py) — type coercion ("5" → 5).
- [`tool-arg-defaults`](https://github.com/MukundaKatta/tool-arg-defaults) — fill in missing kwargs.
- [`agentvet`](https://github.com/MukundaKatta/agentvet) — strict validation after these three.

Full LLM-args repair pipeline:

```
LLM args
  ↓ tool-arg-defaults.apply       fill missing kwargs
  ↓ tool-arg-coerce-py.coerce     fix type mistakes
  ↓ tool-arg-fuzzy.coerce_enums   fix enum typos
  ↓ agentvet.validate             strict schema check
  ↓ tool(...)
```

## License

MIT
