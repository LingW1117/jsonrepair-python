"""
异常LLM输出修复演示（中文版）
================================
展示 jsonrepair 从各种畸形 LLM 输出中提取和修复 JSON 的能力 —
缺失花括号、错误括号类型、无结构的键值对、嵌入的 markdown 等等。

用法：
    python ExceptLLmOutputRepair_Demo_CH.py
"""
import json

from jsonrepair import jsonrepair, JSONRepairError

SEP = "=" * 65


# ============================================================
# 1. 自然语言中嵌入的 JSON（经典 LLM 输出）
# ============================================================
print(SEP)
print("1. 自然语言中嵌入的 JSON")
print(SEP)

cases = [
    (
        "JSON 前面有文字",
        '查询结果如下：{"name": "张三", "age": 28}',
    ),
    (
        "JSON 后面有文字（同行）",
        '{"name": "张三", "age": 28}  如需修改请告知。',
    ),
    (
        "JSON 前后都有文字（含换行）",
        "分析结果如下：\n\n{\n  name: '李四',\n  score: 95\n}\n\n以上仅供参考。",
    ),
    (
        "说明文字后紧跟 JSON",
        '根据您的查询，匹配记录为：\n{"id": 42, "status": "active"}',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    输入:  {raw!r}")
    print(f"    输出:  {result}")


# ============================================================
# 2. 缺失花括号 — 裸键值对
# ============================================================
print("\n" + SEP)
print("2. 缺失花括号 — 裸键值对")
print(SEP)

cases = [
    (
        "单行键值对",
        'name: Alice, age: 28, city: Shanghai',
    ),
    (
        "中文键值对",
        '姓名: 张三, 年龄: 30, 职位: 工程师',
    ),
    (
        "多行键值对（换行分隔）",
        '产品: 笔记本电脑\n价格: 999.99\n库存: true',
    ),
    (
        "单个键值对",
        '状态: 正常',
    ),
    (
        "包含特殊字符的值",
        '路径: usr/local/bin, 端口: 8080',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    输入:  {raw!r}")
    print(f"    输出:  {result}")


# ============================================================
# 3. 错误括号类型 — [...] 用作 {...}
# ============================================================
print("\n" + SEP)
print("3. 错误括号类型 — [...] 被当作 {...} 使用")
print(SEP)

cases = [
    (
        "对象被包在数组括号里",
        '[姓名: 张三, 年龄: 30, 状态: 在职]',
    ),
    (
        "方括号前有文字",
        '结果: [标题: 工程师, 级别: 高级]',
    ),
    (
        "嵌套对象在方括号中（保持数组）",
        '[{id: 1, name: A}, {id: 2, name: B}]',
    ),
    (
        "普通字符串数组（保持数组）",
        '[苹果, 香蕉, 橘子]',
    ),
    (
        "数字数组（保持数组）",
        '[1, 2, 3, 4]',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    输入:  {raw!r}")
    print(f"    输出:  {result}")


# ============================================================
# 4. Markdown 代码块
# ============================================================
print("\n" + SEP)
print("4. Markdown 代码块")
print(SEP)

cases = [
    (
        "```json 代码块夹在文字中间",
        '以下是数据：\n```json\n{\n  "name": "张三",\n  "age": 28\n}\n```\n完毕。',
    ),
    (
        "纯 ``` 代码块",
        '```\n{"a": 1, "b": 2}\n```',
    ),
    (
        "```json 代码块（行内）",
        '```json\n{"status": "ok"}\n```',
    ),
    (
        "只有开头标记的代码块",
        '```json\n{"x": 1}\n',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    输入:  {raw!r}")
    print(f"    输出:  {result}")


# ============================================================
# 5. JSONP 回调
# ============================================================
print("\n" + SEP)
print("5. JSONP 回调")
print(SEP)

cases = [
    (
        "标准 JSONP",
        'callback({"姓名": "张三", "年龄": 28});',
    ),
    (
        "带注释前缀的 JSONP",
        '/* 查询结果 */ jsonp_cb({"data": [1,2,3]});',
    ),
    (
        "不带分号的 JSONP",
        'callback({"ok": true})',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    输入:  {raw!r}")
    print(f"    输出:  {result}")


# ============================================================
# 6. LLM 常见 JSON 错误
# ============================================================
print("\n" + SEP)
print("6. LLM 常见 JSON 错误")
print(SEP)

cases = [
    (
        "末尾多余逗号",
        '{"姓名": "张三", "年龄": 28,}',
    ),
    (
        "字段之间缺少逗号",
        '{"姓名": "张三"\n"年龄": 28}',
    ),
    (
        "单引号字符串",
        "{'姓名': '张三', '城市': '北京'}",
    ),
    (
        "Python 风格布尔值",
        '{"活跃": True, "删除": False, "额外": None}',
    ),
    (
        "JSON 内部有注释",
        '{\n  "姓名": "张三",  // 用户名\n  "年龄": 28  /* 年龄 */\n}',
    ),
    (
        "缺失闭合花括号（截断）",
        '{"users": [{"id": 1, "name": "张三"}',
    ),
    (
        "有效 JSON 后有尾随文字",
        '{"result": "ok"} 这是一些额外说明',
    ),
    (
        "无引号键名和单引号值",
        "{name: '张三', status: 'active'}",
    ),
    (
        "undefined 和 MongoDB 类型",
        '{"a": undefined, "b": NumberLong("123")}',
    ),
    (
        "缺失冒号",
        '{"姓名" "张三"}',
    ),
    (
        "省略号",
        '[1, 2, 3, ...]',
    ),
]

for name, raw in cases:
    result = jsonrepair(raw)
    print(f"\n  [{name}]")
    print(f"    输入:  {raw!r}")
    print(f"    输出:  {result}")


# ============================================================
# 7. 真实 LLM 响应场景
# ============================================================
print("\n" + SEP)
print("7. 真实 LLM 响应场景")
print(SEP)

# 场景A：中文银行客户数据（markdown 包裹）
print("\n  [场景A: 中文银行客户数据 (markdown 包裹)]")
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
    print(f"    输出: {json.dumps(data_a, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    原始输出: {result_a}")

# 场景B：JSON 混在日志输出中
print("\n  [场景B: JSON 混在日志行中]")
raw_b = (
    "INFO 2024-01-15 10:30:00 请求已处理\n"
    "DEBUG 响应体:\n"
    '{\n  "status": "success",\n  "data": {\n'
    '    "user_id": 12345,\n    "items": ["book", "pen"],\n'
    '    "total": 42.99\n  }\n}\n'
    "INFO 2024-01-15 10:30:01 响应已发送"
)

result_b = jsonrepair(raw_b)
try:
    data_b = json.loads(result_b)
    print(f"    输出: {json.dumps(data_b, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    原始输出: {result_b}")

# 场景C：无结构裸键值对
print("\n  [场景C: 自然语言中的键值事实]")
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
    print(f"    输出: {json.dumps(data_c, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    原始输出: {result_c}")

# 场景D：医疗报告数据（混合中文和特殊字符）
print("\n  [场景D: 医疗报告数据]")
raw_d = (
    "患者姓名: 王小明\n"
    "性别: 男\n"
    "年龄: 45\n"
    "血压收缩压: 120\n"
    "血压舒张压: 80\n"
    "心率: 72\n"
    "确诊: true\n"
    "备注: 需定期复查"
)

result_d = jsonrepair(raw_d)
try:
    data_d = json.loads(result_d)
    print(f"    输出: {json.dumps(data_d, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    原始输出: {result_d}")

# 场景E：电商订单（方括号误用）
print("\n  [场景E: 电商订单 (方括号误用)]")
raw_e = (
    "您的订单信息如下：\n"
    "[订单号: 20250115001, "
    "商品: iPhone 15, "
    "数量: 1, "
    "金额: 6999.00, "
    "状态: 已发货]"
)

result_e = jsonrepair(raw_e)
try:
    data_e = json.loads(result_e)
    print(f"    输出: {json.dumps(data_e, ensure_ascii=False, indent=2)}")
except json.JSONDecodeError:
    print(f"    原始输出: {result_e}")


# ============================================================
# 8. 无法修复的输入（错误处理）
# ============================================================
print("\n" + SEP)
print("8. 无法修复的输入（错误处理）")
print(SEP)

unrepairable = [
    ("空字符串", ""),
    ("缺少冒号的对象", '{"a",'),
    ("冒号在键名前", '{:2}'),
    ("键名后跟括号而非冒号", '{"a" ]'),
]

for name, raw in unrepairable:
    try:
        jsonrepair(raw)
        print(f"  [{name}] {raw!r:35s} -> 意外成功!")
    except JSONRepairError as e:
        print(f"  [{name}] {raw!r:35s} -> JSONRepairError: {e}")


# ============================================================
# 9. 往返验证 — 所有输出必须是合法 JSON
# ============================================================
print("\n" + SEP)
print("9. 往返验证（所有输出必须能通过 json.loads）")
print(SEP)

test_inputs = [
    ('合法JSON对象', '{"name": "ok"}'),
    ('合法JSON数组', '[1, 2, 3]'),
    ('布尔值', "true"),
    ('数字', "42"),
    ('字符串', '"hello"'),
    ('裸键值对', 'name: Alice'),
    ('方括号转花括号', '[key: value]'),
    ('键值后跟嵌套JSON', 'data: {"nested": 1}'),
    ('Markdown代码块', '```json\n{"a":1}\n```'),
    ('JSONP回调', 'callback({"x": 1});'),
]

all_ok = True
for name, raw in test_inputs:
    try:
        result = jsonrepair(raw)
        json.loads(result)
        print(f"  OK  [{name}] {raw!r:35s} -> {result}")
    except Exception as e:
        all_ok = False
        print(f"  FAIL [{name}] {raw!r:35s} -> {e}")

print()
if all_ok:
    print(f"  全部 {len(test_inputs)} 个输出均为合法 JSON。")
else:
    print("  部分输出不是合法 JSON!")


print("\n" + SEP)
print("演示完毕")
print(SEP)
