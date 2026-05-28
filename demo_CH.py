"""
jsonrepair 功能演示

直接运行即可，无需安装：
    python demo_CH.py
"""
import json

from jsonrepair import extract_json, jsonrepair, JSONRepairError

# ============================================================
# 1. 基本修复
# ============================================================
print("=" * 60)
print("1. 基本修复")
print("=" * 60)

cases = [
    ("缺引号的键名/值",       '{name: John}'),
    ("单引号",                "{'age': 30}"),
    ("末尾多余逗号",          '[1, 2, 3,]'),
    ("缺冒号",                '{"name" "John"}'),
    ("块注释",                '{"name": /* name */ "John"}'),
    ("行注释",                '{\n"a": 1 // comment\n}'),
    ("Python 常量",           '[True, False, None]'),
    ("undefined -> null",     '{"a": undefined}'),
    ("MongoDB 类型",          'NumberLong("12345")'),
    ("JSONP 回调",            'callback({"a": 1});'),
    ("Markdown 代码块",       '```json\n{"a": 1}\n```'),
    ("数组省略号",            '[1, 2, 3, ...]'),
    ("换行分隔 JSON -> 数组",  '{"a":1}\n{"b":2}'),
    ("截断的数字",            '{"a": 2.}'),
    ("特殊 Unicode 空白",     '{"a":　"foo"}'),
    ("未转义控制字符",        '"hello\\nworld"'),
    ("前导零数字 -> 字符串",  '0789'),
    ("字符串拼接",            '"hello" + " world"'),
    ("正则表达式",            '/[a-z]_/'),
    ("缺少对象值",            '{"a":}'),
]

for name, raw in cases:
    result = jsonrepair(raw)
    status = "PASS" if json.loads(result) else "FAIL"
    print(f"  [{name}]")
    print(f"    {raw!r:45s} -> {result}")

# ============================================================
# 2. 复杂嵌套 JSON
# ============================================================
print("\n" + "=" * 60)
print("2. 复杂嵌套 JSON")
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
# 3. 错误处理
# ============================================================
print("=" * 60)
print("3. 错误处理")
print("=" * 60)

for bad in ["", '{"a",', '{:2}']:
    try:
        jsonrepair(bad)
    except JSONRepairError as e:
        print(f"  {bad!r:20s} -> {e}")

# ============================================================
# 4. extract_json: LLM 输出提取
# ============================================================
print("\n" + "=" * 60)
print("4. extract_json - 从 LLM 输出中提取 JSON")
print("=" * 60)

# 模拟 LLM 在 JSON 前后夹杂自然语言
raw_llm = """好的，根据您的要求，以下是客户信息：

```json
{
  客户名称: "徐美玲",
  金额: 15.32元,
  借款合同号/合同号: 广东银行最高额度生意贷2025第40193,
  "起始日": "2026-01-09"
  "终止日": "2027.06.03",
  "担保方式": "抵押",
  ...
}
```

如需调整请告诉我。"""

print("原始 LLM 输出 (含多余文字):")
print(raw_llm)

result = extract_json(raw_llm)
data = json.loads(result)
print("提取结果:")
print(json.dumps(data, ensure_ascii=False, indent=2))

# ============================================================
# 5. extract_json 更多场景
# ============================================================
print("\n" + "=" * 60)
print("5. extract_json 更多场景")
print("=" * 60)

scenarios = [
    ("前面有文字",     "json\n{\"a\": 1}"),
    ("后面有文字",     "{\"a\": 1}\nHope this helps!"),
    ("前后都有文字",   "Here you go:\n{\"a\": 1}\nDone."),
    ("只有 JSON",      "{\"a\": 1}"),
]

for name, raw in scenarios:
    result = extract_json(raw)
    print(f"  [{name}] {raw!r:40s} -> {result}")

# ============================================================
# 6. 流式处理
# ============================================================
print("\n" + "=" * 60)
print("6. 流式处理")
print("=" * 60)

from jsonrepair.streaming.stream import jsonrepair_stream

chunks = ['{"name": ', "'Alice', ", '"age": 30}']
result = "".join(jsonrepair_stream(chunks))
print(f"  chunks: {chunks}")
print(f"  result: {result}")

print("\n" + "=" * 60)
print("演示完毕")
print("=" * 60)
