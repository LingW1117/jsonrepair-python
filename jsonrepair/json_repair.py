import json
import re

from .error import JSONRepairError
from .string_utils import (
    ends_with_comma_or_newline,
    insert_before_last_whitespace,
    is_control_character,
    is_delimiter,
    is_digit,
    is_double_quote,
    is_double_quote_like,
    is_function_name_char,
    is_function_name_char_start,
    is_hex,
    is_quote,
    is_single_quote,
    is_single_quote_like,
    is_special_whitespace_at,
    is_start_of_value,
    is_unquoted_string_delimiter,
    is_valid_string_character,
    is_whitespace_at,
    is_whitespace_except_newline_at,
    remove_at_index,
    strip_last_occurrence,
)
from .string_utils import _regex_url_char
from .string_utils import _regex_url_start

_control_characters = {
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}

_escape_characters = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def jsonrepair(text: str) -> str:
    """Repair a string containing an invalid JSON document."""
    return _jsonrepair_inner(text)


def extract_json(text: str) -> str:
    """Extract and repair a JSON structure from text with extra content.

    Strips any text before the first '{' or '[', and any text after
    the JSON structure closes. Useful for parsing LLM outputs that
    contain JSON embedded in natural language.
    """
    # Find first JSON structure start
    first_brace = text.find("{")
    first_bracket = text.find("[")
    candidates = [i for i in (first_brace, first_bracket) if i != -1]
    if not candidates:
        raise JSONRepairError("No JSON structure found in text", 0)

    start = min(candidates)
    return _jsonrepair_inner(text[start:], allow_trailing=True)


def _jsonrepair_inner(text: str, allow_trailing: bool = False) -> str:
    """Internal repair implementation."""
    i = 0
    output = ""

    # ---- helper functions that need nonlocal ----

    def parse_value() -> bool:
        nonlocal i
        parse_whitespace_and_skip_comments()
        processed = (
            parse_object()
            or parse_array()
            or parse_string()
            or parse_number()
            or parse_keywords()
            or parse_regex()
            or parse_unquoted_string(False)
        )
        parse_whitespace_and_skip_comments()
        return processed

    def parse_whitespace_and_skip_comments(skip_newline: bool = True) -> bool:
        nonlocal i
        start = i
        changed = parse_whitespace(skip_newline)
        while True:
            changed = parse_comment()
            if changed:
                changed = parse_whitespace(skip_newline)
            else:
                break
        return i > start

    def parse_whitespace(skip_newline: bool) -> bool:
        nonlocal i, output
        _is_ws = (
            is_whitespace_at if skip_newline else is_whitespace_except_newline_at
        )
        whitespace = ""

        while True:
            if _is_ws(text, i):
                whitespace += text[i]
                i += 1
            elif is_special_whitespace_at(text, i):
                whitespace += " "
                i += 1
            else:
                break

        if whitespace:
            output += whitespace
            return True
        return False

    def parse_comment() -> bool:
        nonlocal i
        if (
            i < len(text) - 1
            and text[i] == "/"
            and text[i + 1] == "*"
        ):
            while i < len(text) and not _at_end_of_block_comment(i):
                i += 1
            i += 2
            return True

        if (
            i < len(text) - 1
            and text[i] == "/"
            and text[i + 1] == "/"
        ):
            while i < len(text) and text[i] != "\n":
                i += 1
            return True

        return False

    def _at_end_of_block_comment(idx: int) -> bool:
        return (
            idx + 1 < len(text)
            and text[idx] == "*"
            and text[idx + 1] == "/"
        )

    def parse_markdown_code_block(blocks: list) -> bool:
        nonlocal i
        if _skip_markdown_code_block(blocks):
            if i < len(text) and is_function_name_char_start(text[i]):
                while i < len(text) and is_function_name_char(text[i]):
                    i += 1
            parse_whitespace_and_skip_comments()
            return True
        return False

    def _skip_markdown_code_block(blocks: list) -> bool:
        nonlocal i
        parse_whitespace(True)

        for block in blocks:
            end = i + len(block)
            if text[i:end] == block:
                i = end
                return True
        return False

    def parse_character(char: str) -> bool:
        nonlocal i, output
        if i < len(text) and text[i] == char:
            output += text[i]
            i += 1
            return True
        return False

    def skip_character(char: str) -> bool:
        nonlocal i
        if i < len(text) and text[i] == char:
            i += 1
            return True
        return False

    def skip_escape_character() -> bool:
        return skip_character("\\")

    def skip_ellipsis() -> bool:
        nonlocal i
        parse_whitespace_and_skip_comments()

        if (
            i + 2 < len(text)
            and text[i] == "."
            and text[i + 1] == "."
            and text[i + 2] == "."
        ):
            i += 3
            parse_whitespace_and_skip_comments()
            skip_character(",")
            return True
        return False

    def parse_object() -> bool:
        nonlocal i, output
        if i < len(text) and text[i] == "{":
            output += "{"
            i += 1
            parse_whitespace_and_skip_comments()

            if skip_character(","):
                parse_whitespace_and_skip_comments()

            initial = True
            while i < len(text) and text[i] != "}":
                if not initial:
                    processed_comma = parse_character(",")
                    if not processed_comma:
                        output = insert_before_last_whitespace(output, ",")
                    parse_whitespace_and_skip_comments()
                else:
                    initial = False

                skip_ellipsis()

                processed_key = parse_string() or parse_unquoted_string(True)
                if not processed_key:
                    if (
                        i >= len(text)
                        or text[i] == "}"
                        or text[i] == "{"
                        or text[i] == "]"
                        or text[i] == "["
                    ):
                        output = strip_last_occurrence(output, ",")
                    else:
                        _throw_object_key_expected()
                    break

                parse_whitespace_and_skip_comments()
                processed_colon = parse_character(":")
                truncated_text = i >= len(text)
                if not processed_colon:
                    if truncated_text or (
                        i < len(text) and is_start_of_value(text[i])
                    ):
                        output = insert_before_last_whitespace(output, ":")
                    else:
                        _throw_colon_expected()

                processed_value = parse_value()
                if not processed_value:
                    if processed_colon or truncated_text:
                        output += "null"
                    else:
                        _throw_colon_expected()

            if i < len(text) and text[i] == "}":
                output += "}"
                i += 1
            else:
                output = insert_before_last_whitespace(output, "}")

            return True
        return False

    def parse_array() -> bool:
        nonlocal i, output
        if i < len(text) and text[i] == "[":
            output += "["
            i += 1
            parse_whitespace_and_skip_comments()

            if skip_character(","):
                parse_whitespace_and_skip_comments()

            initial = True
            while i < len(text) and text[i] != "]":
                if not initial:
                    processed_comma = parse_character(",")
                    if not processed_comma:
                        output = insert_before_last_whitespace(output, ",")
                else:
                    initial = False

                skip_ellipsis()

                processed_value = parse_value()
                if not processed_value:
                    output = strip_last_occurrence(output, ",")
                    break

            if i < len(text) and text[i] == "]":
                output += "]"
                i += 1
            else:
                output = insert_before_last_whitespace(output, "]")

            return True
        return False

    def parse_newline_delimited_json() -> None:
        nonlocal i, output
        initial = True
        processed_value = True
        while processed_value:
            if not initial:
                processed_comma = parse_character(",")
                if not processed_comma:
                    output = insert_before_last_whitespace(output, ",")
            else:
                initial = False

            processed_value = parse_value()

        if not processed_value:
            output = strip_last_occurrence(output, ",")

        output = f"[\n{output}\n]"

    def parse_string(
        stop_at_delimiter: bool = False, stop_at_index: int = -1
    ) -> bool:
        nonlocal i, output
        skip_escape_chars = i < len(text) and text[i] == "\\"
        if skip_escape_chars:
            i += 1

        if i < len(text) and is_quote(text[i]):
            is_end_quote = (
                is_double_quote
                if is_double_quote(text[i])
                else (
                    is_single_quote
                    if is_single_quote(text[i])
                    else (
                        is_single_quote_like
                        if is_single_quote_like(text[i])
                        else is_double_quote_like
                    )
                )
            )

            i_before = i
            o_before = len(output)

            s = '"'
            i += 1

            while True:
                if i >= len(text):
                    i_prev = _prev_non_whitespace_index(i - 1)
                    if (
                        not stop_at_delimiter
                        and i_prev >= 0
                        and i_prev < len(text)
                        and is_delimiter(text[i_prev])
                    ):
                        i = i_before
                        output = output[:o_before]
                        return parse_string(True)

                    s = insert_before_last_whitespace(s, '"')
                    output += s
                    return True

                if i == stop_at_index:
                    s = insert_before_last_whitespace(s, '"')
                    output += s
                    return True

                if i < len(text) and is_end_quote(text[i]):
                    i_quote = i
                    o_quote = len(s)
                    s += '"'
                    i += 1
                    output += s

                    parse_whitespace_and_skip_comments(False)

                    if (
                        stop_at_delimiter
                        or i >= len(text)
                        or is_delimiter(text[i])
                        or (i < len(text) and is_quote(text[i]))
                        or (i < len(text) and is_digit(text[i]))
                    ):
                        parse_concatenated_string()
                        return True

                    i_prev_char = _prev_non_whitespace_index(i_quote - 1)
                    prev_char = text[i_prev_char] if i_prev_char >= 0 else ""

                    if prev_char == ",":
                        i = i_before
                        output = output[:o_before]
                        return parse_string(False, i_prev_char)

                    if is_delimiter(prev_char):
                        i = i_before
                        output = output[:o_before]
                        return parse_string(True)

                    output = output[:o_before]
                    i = i_quote + 1
                    s = s[:o_quote] + "\\" + s[o_quote:]

                elif (
                    stop_at_delimiter
                    and i < len(text)
                    and is_unquoted_string_delimiter(text[i])
                ):
                    if (
                        i > 0
                        and text[i - 1] == ":"
                        and _regex_url_start.match(
                            text[i_before + 1 : i + 2]
                        )
                    ):
                        while i < len(text) and _regex_url_char.match(text[i]):
                            s += text[i]
                            i += 1

                    s = insert_before_last_whitespace(s, '"')
                    output += s
                    parse_concatenated_string()
                    return True

                elif i < len(text) and text[i] == "\\":
                    if i + 1 >= len(text):
                        s += "\\"
                        i += 1
                        continue

                    char = text[i + 1]
                    escape_char = _escape_characters.get(char)
                    if escape_char is not None:
                        s += text[i : i + 2]
                        i += 2
                    elif char == "u":
                        j = 2
                        while j < 6 and i + j < len(text) and is_hex(text[i + j]):
                            j += 1

                        if j == 6:
                            s += text[i : i + 6]
                            i += 6
                        elif i + j >= len(text):
                            i = len(text)
                        else:
                            _throw_invalid_unicode_character()
                    elif char == "\n":
                        s += "\\n"
                        i += 2
                    else:
                        s += char
                        i += 2
                else:
                    char = text[i]

                    if char == '"' and i > 0 and text[i - 1] != "\\":
                        s += f"\\{char}"
                        i += 1
                    elif is_control_character(char):
                        s += _control_characters.get(char, char)
                        i += 1
                    else:
                        if not is_valid_string_character(char):
                            _throw_invalid_character(char)
                        s += char
                        i += 1

                if skip_escape_chars:
                    skip_escape_character()

        return False

    def parse_concatenated_string() -> bool:
        nonlocal i, output
        processed = False

        parse_whitespace_and_skip_comments()
        while i < len(text) and text[i] == "+":
            processed = True
            i += 1
            parse_whitespace_and_skip_comments()

            output = strip_last_occurrence(output, '"', True)
            start = len(output)
            parsed_str = parse_string()
            if parsed_str:
                output = remove_at_index(output, start, 1)
            else:
                output = insert_before_last_whitespace(output, '"')

        return processed

    def parse_number() -> bool:
        nonlocal i, output
        start = i
        if i < len(text) and text[i] == "-":
            i += 1
            if _at_end_of_number():
                _repair_number_ending_with_numeric_symbol(start)
                return True
            if i >= len(text) or not is_digit(text[i]):
                i = start
                return False

        while i < len(text) and is_digit(text[i]):
            i += 1

        if i < len(text) and text[i] == ".":
            i += 1
            if _at_end_of_number():
                _repair_number_ending_with_numeric_symbol(start)
                return True
            if i >= len(text) or not is_digit(text[i]):
                i = start
                return False
            while i < len(text) and is_digit(text[i]):
                i += 1

        if i < len(text) and text[i] in ("e", "E"):
            i += 1
            if i < len(text) and text[i] in ("-", "+"):
                i += 1
            if _at_end_of_number():
                _repair_number_ending_with_numeric_symbol(start)
                return True
            if i >= len(text) or not is_digit(text[i]):
                i = start
                return False
            while i < len(text) and is_digit(text[i]):
                i += 1

        if not _at_end_of_number():
            i = start
            return False

        if i > start:
            num = text[start:i]
            has_invalid_leading_zero = bool(re.match(r"^0\d", num))
            output += f'"{num}"' if has_invalid_leading_zero else num
            return True

        return False

    def parse_keywords() -> bool:
        return (
            _parse_keyword("true", "true")
            or _parse_keyword("false", "false")
            or _parse_keyword("null", "null")
            or _parse_keyword("True", "true")
            or _parse_keyword("False", "false")
            or _parse_keyword("None", "null")
        )

    def _parse_keyword(name: str, value: str) -> bool:
        nonlocal i, output
        if text[i : i + len(name)] == name:
            output += value
            i += len(name)
            return True
        return False

    def parse_unquoted_string(is_key: bool) -> bool:
        nonlocal i, output
        start = i

        if i < len(text) and is_function_name_char_start(text[i]):
            while i < len(text) and is_function_name_char(text[i]):
                i += 1

            j = i
            while j < len(text) and is_whitespace_at(text, j):
                j += 1

            if j < len(text) and text[j] == "(":
                i = j + 1
                parse_value()

                if i < len(text) and text[i] == ")":
                    i += 1
                    if i < len(text) and text[i] == ";":
                        i += 1

                return True

        while (
            i < len(text)
            and not is_unquoted_string_delimiter(text[i])
            and not is_quote(text[i])
            and (not is_key or text[i] != ":")
        ):
            i += 1

        if (
            i > 0
            and text[i - 1] == ":"
            and _regex_url_start.match(text[start : i + 2])
        ):
            while i < len(text) and _regex_url_char.match(text[i]):
                i += 1

        if i > start:
            while i > 0 and is_whitespace_at(text, i - 1):
                i -= 1

            symbol = text[start:i]
            output += "null" if symbol == "undefined" else json.dumps(symbol, ensure_ascii=False)

            if i < len(text) and text[i] == '"':
                i += 1

            return True

        return False

    def parse_regex() -> bool:
        nonlocal i, output
        if i < len(text) and text[i] == "/":
            start = i
            i += 1

            while i < len(text) and (text[i] != "/" or text[i - 1] == "\\"):
                i += 1
            i += 1

            output += json.dumps(text[start:i], ensure_ascii=False)
            return True

        return False

    # ---- helpers that only read outer scope ----

    def _prev_non_whitespace_index(start: int) -> int:
        prev = start
        while prev > 0 and is_whitespace_at(text, prev):
            prev -= 1
        return prev

    def _at_end_of_number() -> bool:
        return (
            i >= len(text)
            or is_delimiter(text[i])
            or is_whitespace_at(text, i)
        )

    def _repair_number_ending_with_numeric_symbol(start: int) -> None:
        nonlocal output
        output += f"{text[start:i]}0"

    def _throw_invalid_character(char: str) -> None:
        raise JSONRepairError(f"Invalid character {json.dumps(char)}", i)

    def _throw_unexpected_character() -> None:
        raise JSONRepairError(
            f"Unexpected character {json.dumps(text[i]) if i < len(text) else 'undefined'}", i
        )

    def _throw_unexpected_end() -> None:
        raise JSONRepairError("Unexpected end of json string", len(text))

    def _throw_object_key_expected() -> None:
        raise JSONRepairError("Object key expected", i)

    def _throw_colon_expected() -> None:
        raise JSONRepairError("Colon expected", i)

    def _throw_invalid_unicode_character() -> None:
        chars = text[i : i + 6]
        raise JSONRepairError(f'Invalid unicode character "{chars}"', i)

    # ---- main flow ----

    parse_markdown_code_block(["```", "[```", "{```"])

    processed = parse_value()
    if not processed:
        _throw_unexpected_end()

    parse_markdown_code_block(["```", "```]", "```}"])

    processed_comma = parse_character(",")
    if processed_comma:
        parse_whitespace_and_skip_comments()

    if allow_trailing:
        # extract mode: strip trailing comma, skip extra brackets, ignore rest
        if processed_comma:
            output = strip_last_occurrence(output, ",")
        while i < len(text) and text[i] in ("}", "]"):
            i += 1
            parse_whitespace_and_skip_comments()
        return output

    if (
        i < len(text)
        and is_start_of_value(text[i])
        and ends_with_comma_or_newline(output)
    ):
        if not processed_comma:
            output = insert_before_last_whitespace(output, ",")
        parse_newline_delimited_json()
    elif processed_comma:
        output = strip_last_occurrence(output, ",")

    while i < len(text) and text[i] in ("}", "]"):
        i += 1
        parse_whitespace_and_skip_comments()

    if i >= len(text):
        return output

    _throw_unexpected_character()
