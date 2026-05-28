"""
jsonrepair feature demo

Run directly without installation:
    python demo.py
"""
import json

from jsonrepair import jsonrepair, JSONRepairError

# ============================================================
# 1. Basic Repair
# ============================================================
print("=" * 60)
print("1. Basic Repair")
print("=" * 60)

cases = [
    ("Missing quotes on key/value",  '{name: John}'),
    ("Single quotes",                 "{'age': 30}"),
    ("Trailing comma",                '[1, 2, 3,]'),
    ("Missing colon",                 '{"name" "John"}'),
    ("Block comment",                 '{"name": /* name */ "John"}'),
    ("Line comment",                  '{\n"a": 1 // comment\n}'),
    ("Python constants",              '[True, False, None]'),
    ("undefined -> null",             '{"a": undefined}'),
    ("MongoDB type",                  'NumberLong("12345")'),
    ("JSONP callback",                'callback({"a": 1});'),
    ("Markdown code block",           '```json\n{"a": 1}\n```'),
    ("Array ellipsis",                '[1, 2, 3, ...]'),
    ("Newline-delimited JSON -> array", '{"a":1}\n{"b":2}'),
    ("Truncated number",              '{"a": 2.}'),
    ("Special Unicode whitespace",    '{"a":　"foo"}'),
    ("Unescaped control character",   '"hello\\nworld"'),
    ("Leading zero -> string",        '0789'),
    ("String concatenation",          '"hello" + " world"'),
    ("Regular expression",            '/[a-z]_/'),
    ("Missing object value",          '{"a":}'),
]

for name, raw in cases:
    result = jsonrepair(raw)
    status = "PASS" if json.loads(result) else "FAIL"
    print(f"  [{name}]")
    print(f"    {raw!r:45s} -> {result}")

# ============================================================
# 2. Complex Nested JSON
# ============================================================
print("\n" + "=" * 60)
print("2. Complex Nested JSON")
print("=" * 60)

broken = """{
  name: 'Alice',
  age: 28,
  hobbies: ['reading', 'coding', ...],
  address: {
    city: 'Shanghai',
    zip: 200000,
  },
  /* this is a comment */
  active: True,
}"""

print(jsonrepair(broken))

# ============================================================
# 3. Error Handling
# ============================================================
print("=" * 60)
print("3. Error Handling")
print("=" * 60)

for bad in ["", '{"a",', '{:2}']:
    try:
        jsonrepair(bad)
    except JSONRepairError as e:
        print(f"  {bad!r:20s} -> {e}")

# ============================================================
# 4. Auto-extract JSON from LLM Output
# ============================================================
print("\n" + "=" * 60)
print("4. Auto-extract JSON from LLM Output")
print("=" * 60)
print("  jsonrepair now auto-extracts JSON from surrounding text:")
print()

# Simulate LLM response with JSON wrapped in natural language
raw_llm = """Sure, here is the customer info you requested:

```json
{
  name: "Alice Smith",
  amount: 15.32,
  contract_id: "ABC-2025-40193",
  "start_date": "2026-01-09"
  "end_date": "2027-06-03",
  "collateral_type": "mortgage",
  ...
}
```

Let me know if you need any adjustments."""

print("Raw LLM output (with extra text):")
print(raw_llm)

result = jsonrepair(raw_llm)
data = json.loads(result)
print("Extracted result:")
print(json.dumps(data, ensure_ascii=False, indent=2))

# ============================================================
# 5. Auto-extract: More Scenarios
# ============================================================
print("\n" + "=" * 60)
print("5. Auto-extract - More Scenarios")
print("=" * 60)

scenarios = [
    ("Text before JSON",  "json\n{\"a\": 1}"),
    ("Text around JSON",  "Here you go:\n{\"a\": 1}\nDone."),
    ("JSON with comment", "/* info */ {\"a\": 1}"),
    ("JSON only",         "{\"a\": 1}"),
    ("Missing braces",    "name: Alice, age: 28"),
    ("Bracket convert",   "[name: John, active: true]"),
]

for name, raw in scenarios:
    result = jsonrepair(raw)
    print(f"  [{name}] {raw!r:40s} -> {result}")

# ============================================================
# 6. Streaming
# ============================================================
print("\n" + "=" * 60)
print("6. Streaming")
print("=" * 60)

from jsonrepair.streaming.stream import jsonrepair_stream

chunks = ['{"name": ', "'Alice', ", '"age": 30}']
result = "".join(jsonrepair_stream(chunks))
print(f"  chunks: {chunks}")
print(f"  result: {result}")

print("\n" + "=" * 60)
print("Demo complete")
print("=" * 60)
