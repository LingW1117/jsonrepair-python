# jsonrepair

Repair invalid JSON documents. A Python port of [jsonrepair](https://github.com/josdejong/jsonrepair) (TypeScript).

## Features

- Fixes 30+ common JSON formatting errors (missing quotes, single quotes, comments, trailing commas, etc.)
- Auto-extracts JSON embedded in LLM outputs (filters surrounding text before/after JSON)
- Streaming API for large files or real-time data
- Zero dependencies — stdlib only
- No installation required — copy the `jsonrepair/` directory and `import` directly
- Clean, well-tested codebase (116 parameterized tests)

## Installation

```bash
pip install jsonrepair
```

Or simply copy the `jsonrepair/` directory into your project — it has no external dependencies.

## Quick Start

```python
from jsonrepair import extract_json, jsonrepair

# Basic repair
jsonrepair("{name: 'John'}")        # -> {"name": "John"}

# Extract JSON from LLM output
llm = "Here's the data:\n{\n  name: 'Alice'\n}"
extract_json(llm)                   # -> {"name": "Alice"}
```

## API

### `jsonrepair(text: str) -> str`

Repair an invalid JSON string. Throws `JSONRepairError` for unrepairable inputs.

```python
from jsonrepair import jsonrepair, JSONRepairError

try:
    result = jsonrepair("{name: 'John'}")
    print(result)  # {"name": "John"}
except JSONRepairError as e:
    print(e)           # Error message with position
    print(e.position)  # Character position where the error occurred
```

### `extract_json(text: str) -> str`

Extract and repair a JSON structure from text that contains extra content (e.g. LLM outputs). Skips text before the first `{` or `[` and ignores trailing text after the JSON structure closes.

```python
from jsonrepair import extract_json

llm_output = "Here's your data:\n{name: 'test'}\nHope this helps"
result = extract_json(llm_output)  # {"name": "test"}
```

### Streaming API

For large files or real-time data streams.

**Core interface:**

```python
from jsonrepair.streaming.core import JsonRepairCore

output_parts = []

def on_data(chunk: str):
    output_parts.append(chunk)

repair = JsonRepairCore(on_data=on_data, buffer_size=65536, chunk_size=65536)
repair.transform('{"a":2')
repair.transform(',"b":3}')
repair.flush()

print("".join(output_parts))  # {"a":2,"b":3}
```

**Generator wrapper:**

```python
from jsonrepair.streaming.stream import jsonrepair_stream

chunks = ['{"a":2', ',"b":3}']
for chunk in jsonrepair_stream(chunks):
    print(chunk, end="")
```

### CLI

```bash
python -m jsonrepair.cli broken.json                    # Output to stdout
python -m jsonrepair.cli broken.json -o repaired.json   # Output to file
python -m jsonrepair.cli broken.json --overwrite        # Replace file in-place
python -m jsonrepair.cli --help                         # Help message
```

## Supported Repairs

| Category | Example |
|----------|---------|
| Missing quotes | `{name: "John"}` → `{"name": "John"}` |
| Single/special quotes | `{'a':2}` → `{"a":2}` |
| Trailing/leading commas | `[1,2,]` → `[1,2]` |
| Missing colons | `{"a" "b"}` → `{"a": "b"}` |
| Missing commas | `{1 2}` → `{1, 2}` |
| Missing object values | `{"a":}` → `{"a":null}` |
| Missing closing brackets | `{"a":2` → `{"a":2}` |
| Redundant brackets | `{"a":1}}` → `{"a":1}` |
| Block / line comments | `{/*c*/"a":1}` → `{"a":1}` |
| Markdown code blocks | `` ```json\n{}\n``` `` → `{}` |
| JSONP callbacks | `callback({});` → `{}` |
| MongoDB types | `ObjectId("123")` → `"123"` |
| Python constants | `True/False/None` → `true/false/null` |
| `undefined` | `undefined` → `null` |
| Control char escaping | `\n` `\t` `\b` `\r` `\f` |
| Unescaped double quotes | `"say "hi""` → `"say \"hi\""` |
| Special Unicode whitespace | Fullwidth space → regular space |
| Ellipsis | `[1,2,...]` → `[1,2]` |
| Newline-delimited JSON | `{a:1}\n{b:2}` → `[{a:1},{b:2}]` |
| String concatenation | `"a"+"b"` → `"ab"` |
| Regular expressions | `/pattern/` → `"/pattern/"` |
| Leading-zero numbers | `00789` → `"00789"` |
| Truncated numbers | `2.` → `2.0` |
| Truncated JSON | `["foo` → `["foo"]` |
| Escaped strings | `\"hello\"` → `"hello"` |

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Project Structure

```
jsonrepair-python/
├── demo.py                     # Feature demo (English)
├── demo_CH.py                  # Feature demo (Chinese)
├── README.md                   # English documentation
├── README_CH.md                # 中文文档
├── pyproject.toml
├── jsonrepair/
│   ├── __init__.py             # exports: jsonrepair, extract_json, JSONRepairError
│   ├── json_repair.py          # Regular (non-streaming) implementation
│   ├── string_utils.py         # Character classification helpers
│   ├── error.py                # JSONRepairError exception
│   ├── cli.py                  # CLI entry point
│   └── streaming/
│       ├── __init__.py
│       ├── core.py             # Streaming state machine
│       ├── stack.py            # Stack / caret state management
│       ├── stream.py           # Generator-based streaming wrapper
│       └── buffer/
│           ├── input_buffer.py  # Sliding window input buffer
│           └── output_buffer.py # Sliding window output buffer
└── tests/
    └── test_json_repair.py     # 116 tests (regular + streaming)
```

## License

ISC — same as the original project.
