"""
Exceptional LLM Output Repair Demo
===================================
Demonstrates jsonrepair's ability to extract and repair JSON from
various malformed LLM outputs — missing brackets, wrong bracket types,
key-value pairs without structure, embedded markdown, and more.

Usage:
    python ExceptLLmOutputRepair_Demo.py
"""
import json

import jsonrepair

SEP = "=" * 65


# ============================================================
# 1. JSON embedded in natural language (classic LLM output)
# ============================================================
print(SEP)
print("1. JSON embedded in natural language")
print(SEP)

cases = [
    (
        "Text before JSON",
        'The data is: {"name": "Alice", "age": 28}',
    ),
    (
        "Text after JSON (same line)",
        '{"name": "Alice", "age": 28}  Let me know if you need changes.',
    ),
    (
        "Text around JSON with newlines",
        "Here is the result:\n\n{\n  name: 'Bob',\n  score: 95\n}\n\nHope that helps!",
    ),
    (
        "JSON preceded by explanatory sentence",
        'Based on your query, the matching record is:\n{"id": 42, "status": "active"}',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    Input:  {raw!r}")
    print(f"    Output: {result}")


# ============================================================
# 2. Missing braces — key:value pairs in the wild
# ============================================================
print("\n" + SEP)
print("2. Missing braces — bare key:value pairs")
print(SEP)

cases = [
    (
        "Simple key:value on one line",
        'name: Alice, age: 28, city: Shanghai',
    ),
    (
        "Key:value with Chinese characters",
        '姓名: 张三, 年龄: 30, 职位: 工程师',
    ),
    (
        "Multi-line key:value pairs (newline separated)",
        'product: Laptop\nprice: 999.99\nin_stock: true',
    ),
    (
        "Single key:value pair",
        'status: OK',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    Input:  {raw!r}")
    print(f"    Output: {result}")


# ============================================================
# 3. Wrong bracket type — [...] used as {...}
# ============================================================
print("\n" + SEP)
print("3. Wrong bracket type — [...] instead of {...}")
print(SEP)

cases = [
    (
        "Object-in-array brackets",
        '[name: John, age: 30, active: true]',
    ),
    (
        "Brackets with leading text",
        'output: [title: Engineer, level: senior]',
    ),
    (
        "Nested objects in brackets stay as array",
        '[{id: 1, name: A}, {id: 2, name: B}]',
    ),
    (
        "Plain array stays as array",
        '[apple, banana, cherry]',
    ),
    (
        "Numeric array stays as array",
        '[1, 2, 3, 4]',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    Input:  {raw!r}")
    print(f"    Output: {result}")


# ============================================================
# 4. Markdown fenced code blocks
# ============================================================
print("\n" + SEP)
print("4. Markdown fenced code blocks")
print(SEP)

cases = [
    (
        "JSON in ```json block with surrounding text",
        'Here is the data:\n```json\n{\n  "name": "Alice",\n  "age": 28\n}\n```\nDone.',
    ),
    (
        "JSON in bare ``` block",
        '```\n{"a": 1, "b": 2}\n```',
    ),
    (
        "JSON in ```json block (inline)",
        '```json\n{"status": "ok"}\n```',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    Input:  {raw!r}")
    print(f"    Output: {result}")


# ============================================================
# 5. JSONP callbacks
# ============================================================
print("\n" + SEP)
print("5. JSONP callbacks")
print(SEP)

cases = [
    (
        "Standard JSONP",
        'callback({"name": "Alice", "age": 28});',
    ),
    (
        "JSONP with comment prefix",
        '/* result */ jsonp_cb({"data": [1,2,3]});',
    ),
    (
        "JSONP without semicolon",
        'callback({"ok": true})',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    Input:  {raw!r}")
    print(f"    Output: {result}")


# ============================================================
# 6. Common LLM JSON errors
# ============================================================
print("\n" + SEP)
print("6. Common LLM JSON errors")
print(SEP)

cases = [
    (
        "Trailing comma after last field",
        '{"name": "Alice", "age": 28,}',
    ),
    (
        "Missing comma between fields",
        '{"name": "Alice"\n"age": 28}',
    ),
    (
        "Single-quoted strings",
        "{'name': 'Alice', 'city': 'Paris'}",
    ),
    (
        "Python booleans",
        '{"active": True, "deleted": False, "extra": None}',
    ),
    (
        "Comments inside JSON",
        '{\n  "name": "Alice",  // user name\n  "age": 28  /* age in years */\n}',
    ),
    (
        "Missing closing brace (truncated)",
        '{"users": [{"id": 1, "name": "Alice"}',
    ),
    (
        "Trailing text after valid JSON",
        '{"result": "ok"} some extra note here',
    ),
    (
        "Unquoted keys and single-quoted values",
        "{name: 'Alice', status: 'active'}",
    ),
    (
        "undefined and MongoDB types",
        '{"a": undefined, "b": NumberLong("123")}',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    Input:  {raw!r}")
    print(f"    Output: {result}")


# ============================================================
# 7. Realistic LLM response scenarios
# ============================================================
print("\n" + SEP)
print("7. Realistic LLM response scenarios")
print(SEP)

# Scenario A: Customer info with Chinese + markdown
print("\n  [Scenario A: Chinese banking customer data in markdown]")
raw_a = (
    "好的，根据您的要求，查询到以下客户信息：\n\n"
    "```json\n"
    "{\n"
    '  客户名称: "徐美玲",\n'
    "  借款金额: 150000.00,\n"
    '  合同编号: "GD-2025-40193",\n'
    '  "担保方式": "房产抵押",\n'
    '  "贷款期限": "36个月",\n'
    '  审批状态: "已通过",\n'
    "  ...\n"
    "}\n"
    "```\n\n"
    "如需进一步信息，请告知。"
)

result_a = jsonrepair(raw_a)
try:
    data_a = json.loads(result_a)
    print(f"    Output: {json.dumps(data_a, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    Raw output: {result_a}")

# Scenario B: JSON mixed with log output
print("\n  [Scenario B: JSON mixed with log lines]")
raw_b = (
    "INFO 2024-01-15 10:30:00 Request processed\n"
    "DEBUG Response body:\n"
    '{\n  "status": "success",\n  "data": {\n'
    '    "user_id": 12345,\n    "items": ["book", "pen"],\n'
    '    "total": 42.99\n  }\n}\n'
    "INFO 2024-01-15 10:30:01 Response sent"
)

result_b = jsonrepair(raw_b)
try:
    data_b = json.loads(result_b)
    print(f"    Output: {json.dumps(data_b, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    Raw output: {result_b}")

# Scenario C: Completely unstructured (bare key:value in prose)
print("\n  [Scenario C: Key-value facts in natural language]")
raw_c = (
    "年龄: 34\n"
    "收入水平: 高\n"
    "信用评分: 720\n"
    "是否有房: true\n"
    "是否有车: false"
)

result_c = jsonrepair(raw_c)
try:
    data_c = json.loads(result_c)
    print(f"    Output: {json.dumps(data_c, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    Raw output: {result_c}")


# ============================================================
# 8. Error handling — inputs that cannot be repaired
# ============================================================
print("\n" + SEP)
print("8. Unrepairable inputs (error handling)")
print(SEP)

unrepairable = [
    "",
    '{"a",',
    '{:2}',
]

for raw in unrepairable:
    try:
        jsonrepair(raw)
        print(f"  {raw!r:20s} -> unexpectedly succeeded!")
    except jsonrepair.JSONRepairError as e:
        print(f"  {raw!r:20s} -> JSONRepairError: {e}")


# ============================================================
# 9. Round-trip verification
# ============================================================
print("\n" + SEP)
print("9. Round-trip verification (all outputs must be valid JSON)")
print(SEP)

test_inputs = [
    '{"name": "ok"}',
    '[1, 2, 3]',
    "true",
    "42",
    '"hello"',
    'name: Alice',
    '[key: value]',
    'data: {"nested": 1}',
    '```json\n{"a":1}\n```',
    'callback({"x": 1});',
]

all_ok = True
for raw in test_inputs:
    try:
        result = jsonrepair(raw)
        json.loads(result)
        print(f"  OK  {raw!r:40s} -> {result}")
    except Exception as e:
        all_ok = False
        print(f"  FAIL {raw!r:40s} -> {e}")

print()
if all_ok:
    print(f"  All {len(test_inputs)} outputs are valid JSON.")
else:
    print("  Some outputs are NOT valid JSON!")


print("\n" + SEP)
print("Demo complete")
print(SEP)
