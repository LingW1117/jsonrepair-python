# jsonrepair

修复无效 JSON 文档的 Python 库，是 [jsonrepair](https://github.com/josdejong/jsonrepair) (TypeScript) 的 Python 移植版。

由Claude code + Deepseek v4 pro完成
## 特性

- 修复 30+ 种常见 JSON 格式错误（缺引号、单引号、注释、末尾逗号等）
- 自动提取 LLM 输出中嵌入的 JSON（过滤前后多余文字）
- 流式处理大文件或实时数据流
- 零依赖，仅需 Python 标准库
- 无需 pip 安装，将 `jsonrepair/` 目录复制到项目中即可直接 `import` 使用
- 代码整洁，测试覆盖充分（116 组参数化测试）

## 快速开始

```python
from jsonrepair import extract_json, jsonrepair

# 基本修复
jsonrepair("{name: 'John'}")        # -> {"name": "John"}

# 从 LLM 输出中提取 JSON
llm = "好的，数据如下：\n{\n  name: 'Alice'\n}"
extract_json(llm)                   # -> {"name": "Alice"}
```

## API

### `jsonrepair(text: str) -> str`

修复无效 JSON 字符串，返回合法 JSON。遇到无法修复的错误时抛出 `JSONRepairError`。

```python
from jsonrepair import jsonrepair, JSONRepairError

try:
    result = jsonrepair("{name: 'John'}")
    print(result)  # {"name": "John"}
except JSONRepairError as e:
    print(e)          # 错误信息（含位置）
    print(e.position)  # 出错字符位置
```

### `extract_json(text: str) -> str`

从包含多余文字（如 LLM 输出）的文本中自动提取并修复 JSON 结构。跳过第一个 `{` 或 `[` 之前的内容，忽略 JSON 闭合后的尾部文字。

```python
from jsonrepair import extract_json

llm_output = "这是数据：\n{name: 'test'}\n请查收"
result = extract_json(llm_output)  # {"name": "test"}
```

### 流式 API

适用于大文件或实时数据流。

**核心接口：**

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

**生成器式接口：**

```python
from jsonrepair.streaming.stream import jsonrepair_stream

chunks = ['{"a":2', ',"b":3}']
for chunk in jsonrepair_stream(chunks):
    print(chunk, end="")
```

### CLI

```bash
python -m jsonrepair.cli broken.json                    # 输出到控制台
python -m jsonrepair.cli broken.json -o repaired.json   # 输出到文件
python -m jsonrepair.cli broken.json --overwrite        # 原地替换文件
python -m jsonrepair.cli --help                         # 帮助信息
```

## 支持的修复类型

| 类别 | 示例 |
|------|------|
| 补全引号 | `{name: "John"}` → `{"name": "John"}` |
| 单引号/特殊引号 | `{'a':2}` → `{"a":2}` |
| 末尾/开头多余逗号 | `[1,2,]` → `[1,2]` |
| 缺失冒号 | `{"a" "b"}` → `{"a": "b"}` |
| 缺失逗号 | `{1 2}` → `{1, 2}` |
| 缺失对象值 | `{"a":}` → `{"a":null}` |
| 缺失闭合括号 | `{"a":2` → `{"a":2}` |
| 多余闭合括号 | `{"a":1}}` → `{"a":1}` |
| 块注释 / 行注释 | `{/*c*/"a":1}` → `{"a":1}` |
| Markdown 代码块 | `` ```json\n{}\n``` `` → `{}` |
| JSONP 回调 | `callback({});` → `{}` |
| MongoDB 类型 | `ObjectId("123")` → `"123"` |
| Python 常量 | `True/False/None` → `true/false/null` |
| undefined | `undefined` → `null` |
| 控制字符转义 | `\n` `\t` `\b` `\r` `\f` |
| 未转义双引号 | `"say "hi""` → `"say \"hi\""` |
| 特殊 Unicode 空白 | 全角空格等 → 普通空格 |
| 省略号 | `[1,2,...]` → `[1,2]` |
| 换行分隔 JSON | `{a:1}\n{b:2}` → `[{a:1},{b:2}]` |
| 字符串拼接 | `"a"+"b"` → `"ab"` |
| 正则表达式 | `/pattern/` → `"/pattern/"` |
| 前导零数字 | `00789` → `"00789"` |
| 截断数字 | `2.` → `2.0` |
| 截断 JSON | `["foo` → `["foo"]` |
| 转义字符串 | `\"hello\"` → `"hello"` |

## 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## 项目结构

```
jsonrepair-python/
├── demo.py                     # 功能演示（英文）
├── demo_CH.py                  # 功能演示（中文）
├── README.md                   # 英文文档
├── README_CH.md                # 中文文档
├── pyproject.toml
├── jsonrepair/
│   ├── __init__.py             # 导出: jsonrepair, extract_json, JSONRepairError
│   ├── json_repair.py          # 常规（非流式）实现
│   ├── string_utils.py         # 字符分类辅助函数
│   ├── error.py                # JSONRepairError 异常
│   ├── cli.py                  # CLI 入口
│   └── streaming/
│       ├── __init__.py
│       ├── core.py             # 流式状态机
│       ├── stack.py            # 栈/插入位置状态管理
│       ├── stream.py           # 生成器式流式封装
│       └── buffer/
│           ├── input_buffer.py  # 滑动窗口输入缓冲
│           └── output_buffer.py # 滑动窗口输出缓冲
└── tests/
    └── test_json_repair.py     # 116 组测试（常规 + 流式）
```

## 开源协议

ISC — 与原项目一致。
