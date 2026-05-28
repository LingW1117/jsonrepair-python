from __future__ import annotations

import json
import re
from typing import Callable

from ..error import JSONRepairError
from ..string_utils import (
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
    is_start_of_value,
    is_unquoted_string_delimiter,
    is_valid_string_character,
)
from ..string_utils import _regex_url_char
from ..string_utils import _regex_url_start
from .buffer.input_buffer import InputBuffer
from .buffer.output_buffer import OutputBuffer
from .stack import Caret, Stack, StackType

# Character codes for whitespace checks
_CODE_SPACE = 0x20
_CODE_NEWLINE = 0xA
_CODE_TAB = 0x9
_CODE_RETURN = 0xD
_CODE_NON_BREAKING_SPACE = 0x00A0
_CODE_MONGOLIAN_VOWEL_SEPARATOR = 0x180E
_CODE_EN_QUAD = 0x2000
_CODE_ZERO_WIDTH_SPACE = 0x200B
_CODE_NARROW_NO_BREAK_SPACE = 0x202F
_CODE_MEDIUM_MATHEMATICAL_SPACE = 0x205F
_CODE_IDEOGRAPHIC_SPACE = 0x3000
_CODE_ZERO_WIDTH_NO_BREAK_SPACE = 0xFEFF

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


class JsonRepairCore:
    """Streaming JSON repair state machine.

    Usage:
        repair = JsonRepairCore(on_data=handler)
        repair.transform(chunk1)
        repair.transform(chunk2)
        repair.flush()
    """

    def __init__(
        self,
        on_data: Callable[[str], None],
        buffer_size: int = 65536,
        chunk_size: int = 65536,
    ):
        self._input = InputBuffer()
        self._output = OutputBuffer(
            write=on_data, chunk_size=chunk_size, buffer_size=buffer_size
        )
        self._buffer_size = buffer_size
        self._chunk_size = chunk_size
        self._i = 0
        self._i_flushed = 0
        self._stack = Stack()

    def _char(self, index: int) -> str:
        return self._input.char_at(index)

    def _char_code(self, index: int) -> int:
        return self._input.char_code_at(index)

    def _substr(self, start: int, end: int) -> str:
        return self._input.substring(start, end)

    def _is_end(self, index: int) -> bool:
        return self._input.is_end(index)

    def _is_whitespace_code(self, code: int, skip_newline: bool) -> bool:
        if skip_newline:
            return code in (_CODE_SPACE, _CODE_NEWLINE, _CODE_TAB, _CODE_RETURN)
        return code in (_CODE_SPACE, _CODE_TAB, _CODE_RETURN)

    def _is_special_whitespace_code(self, code: int) -> bool:
        return (
            code == _CODE_NON_BREAKING_SPACE
            or code == _CODE_MONGOLIAN_VOWEL_SEPARATOR
            or (_CODE_EN_QUAD <= code <= _CODE_ZERO_WIDTH_SPACE)
            or code == _CODE_NARROW_NO_BREAK_SPACE
            or code == _CODE_MEDIUM_MATHEMATICAL_SPACE
            or code == _CODE_IDEOGRAPHIC_SPACE
            or code == _CODE_ZERO_WIDTH_NO_BREAK_SPACE
        )

    def _is_ws_at(self, index: int, skip_newline: bool) -> bool:
        if self._is_end(index):
            return False
        return self._is_whitespace_code(self._char_code(index), skip_newline)

    def _is_special_ws_at(self, index: int) -> bool:
        if self._is_end(index):
            return False
        return self._is_special_whitespace_code(self._char_code(index))

    def _flush_input_buffer(self) -> None:
        while self._i_flushed < self._i - self._buffer_size - self._chunk_size:
            self._i_flushed += self._chunk_size
            self._input.flush(self._i_flushed)

    def transform(self, chunk: str) -> None:
        self._input.push(chunk)

        while (
            self._i < self._input.current_length() - self._buffer_size
            and self._parse()
        ):
            pass

        self._flush_input_buffer()

    def flush(self) -> None:
        self._input.close()

        while self._parse():
            pass

        self._output.flush()

    def _parse(self) -> bool:
        self._parse_whitespace_and_skip_comments()

        st = self._stack.type
        caret = self._stack.caret

        if st == StackType.OBJECT:
            if caret == Caret.BEFORE_KEY:
                return (
                    self._skip_ellipsis()
                    or self._parse_object_key()
                    or self._parse_unexpected_colon()
                    or self._parse_repair_trailing_comma()
                    or self._parse_repair_object_end_or_comma()
                )
            elif caret == Caret.BEFORE_VALUE:
                return self._parse_value() or self._parse_repair_missing_object_value()
            elif caret == Caret.AFTER_VALUE:
                return (
                    self._parse_object_comma()
                    or self._parse_object_end()
                    or self._parse_repair_object_end_or_comma()
                )
        elif st == StackType.ARRAY:
            if caret == Caret.BEFORE_VALUE:
                return (
                    self._skip_ellipsis()
                    or self._parse_value()
                    or self._parse_repair_trailing_comma()
                    or self._parse_repair_array_end()
                )
            elif caret == Caret.AFTER_VALUE:
                return (
                    self._parse_array_comma()
                    or self._parse_array_end()
                    or self._parse_repair_missing_comma()
                    or self._parse_repair_array_end()
                )
        elif st == StackType.ND_JSON:
            if caret == Caret.BEFORE_VALUE:
                return self._parse_value() or self._parse_repair_trailing_comma()
            elif caret == Caret.AFTER_VALUE:
                return (
                    self._parse_array_comma()
                    or self._parse_repair_missing_comma()
                    or self._parse_repair_ndjson_end()
                )
        elif st == StackType.FUNCTION_CALL:
            if caret == Caret.BEFORE_VALUE:
                return self._parse_value()
            elif caret == Caret.AFTER_VALUE:
                return self._parse_function_call_end()
        elif st == StackType.ROOT:
            if caret == Caret.BEFORE_VALUE:
                return self._parse_root_start()
            elif caret == Caret.AFTER_VALUE:
                return self._parse_root_end()

        return False

    def _parse_value(self) -> bool:
        return (
            self._parse_object_start()
            or self._parse_array_start()
            or self._parse_string()
            or self._parse_number()
            or self._parse_keywords()
            or self._parse_repair_regex()
            or self._parse_repair_unquoted_string()
        )

    def _parse_object_start(self) -> bool:
        if self._parse_character("{"):
            self._parse_whitespace_and_skip_comments()
            self._skip_ellipsis()
            if self._skip_character(","):
                self._parse_whitespace_and_skip_comments()
            if self._parse_character("}"):
                return self._stack.update(Caret.AFTER_VALUE)
            return self._stack.push(StackType.OBJECT, Caret.BEFORE_KEY)
        return False

    def _parse_array_start(self) -> bool:
        if self._parse_character("["):
            self._parse_whitespace_and_skip_comments()
            self._skip_ellipsis()
            if self._skip_character(","):
                self._parse_whitespace_and_skip_comments()
            if self._parse_character("]"):
                return self._stack.update(Caret.AFTER_VALUE)
            return self._stack.push(StackType.ARRAY, Caret.BEFORE_VALUE)
        return False

    def _parse_repair_unquoted_string(self) -> bool:
        j = self._i

        if not self._is_end(j) and is_function_name_char_start(self._char(j)):
            while not self._is_end(j) and is_function_name_char(self._char(j)):
                j += 1

            k = j
            while not self._is_end(k) and self._is_ws_at(k, True):
                k += 1

            if not self._is_end(k) and self._char(k) == "(":
                k += 1
                self._i = k
                return self._stack.push(StackType.FUNCTION_CALL, Caret.BEFORE_VALUE)

        j = self._find_next_delimiter(False, j)
        if j is not None:
            if (
                j > 0
                and self._char(j - 1) == ":"
                and _regex_url_start.match(self._substr(self._i, j + 2))
            ):
                while not self._is_end(j) and _regex_url_char.match(self._char(j)):
                    j += 1

            symbol = self._substr(self._i, j)
            self._i = j

            self._output.push("null" if symbol == "undefined" else json.dumps(symbol, ensure_ascii=False))

            if not self._is_end(self._i) and self._char(self._i) == '"':
                self._i += 1

            return self._stack.update(Caret.AFTER_VALUE)

        return False

    def _parse_repair_regex(self) -> bool:
        if not self._is_end(self._i) and self._char(self._i) == "/":
            start = self._i
            self._i += 1

            while not self._is_end(self._i) and (
                self._char(self._i) != "/" or self._char(self._i - 1) == "\\"
            ):
                self._i += 1
            self._i += 1

            self._output.push(json.dumps(self._substr(start, self._i), ensure_ascii=False))
            return self._stack.update(Caret.AFTER_VALUE)
        return False

    def _parse_repair_missing_object_value(self) -> bool:
        self._output.push("null")
        return self._stack.update(Caret.AFTER_VALUE)

    def _parse_repair_trailing_comma(self) -> bool:
        if self._output.ends_with_ignoring_whitespace(","):
            self._output.strip_last_occurrence(",")
            return self._stack.update(Caret.AFTER_VALUE)
        return False

    def _parse_unexpected_colon(self) -> bool:
        if not self._is_end(self._i) and self._char(self._i) == ":":
            self._throw_object_key_expected()
        return False

    def _parse_unexpected_end(self) -> bool:
        if self._is_end(self._i):
            self._throw_unexpected_end()
        else:
            self._throw_unexpected_character()
        return False

    def _parse_object_key(self) -> bool:
        parsed_key = self._parse_string() or self._parse_unquoted_key()
        if parsed_key:
            self._parse_whitespace_and_skip_comments()

            if self._parse_character(":"):
                return self._stack.update(Caret.BEFORE_VALUE)

            truncated_text = self._is_end(self._i)
            if truncated_text or (
                not self._is_end(self._i) and is_start_of_value(self._char(self._i))
            ):
                self._output.insert_before_last_whitespace(":")
                return self._stack.update(Caret.BEFORE_VALUE)

            self._throw_colon_expected()
        return False

    def _parse_object_comma(self) -> bool:
        if self._parse_character(","):
            return self._stack.update(Caret.BEFORE_KEY)
        return False

    def _parse_object_end(self) -> bool:
        if self._parse_character("}"):
            return self._stack.pop()
        return False

    def _parse_repair_object_end_or_comma(self) -> bool:
        if not self._is_end(self._i) and self._char(self._i) == "{":
            self._output.strip_last_occurrence(",")
            self._output.insert_before_last_whitespace("}")
            return self._stack.pop()

        if not self._is_end(self._i) and is_start_of_value(self._char(self._i)):
            self._output.insert_before_last_whitespace(",")
            return self._stack.update(Caret.BEFORE_KEY)

        self._output.insert_before_last_whitespace("}")
        return self._stack.pop()

    def _parse_array_comma(self) -> bool:
        if self._parse_character(","):
            return self._stack.update(Caret.BEFORE_VALUE)
        return False

    def _parse_array_end(self) -> bool:
        if self._parse_character("]"):
            return self._stack.pop()
        return False

    def _parse_repair_missing_comma(self) -> bool:
        if not self._is_end(self._i) and is_start_of_value(self._char(self._i)):
            self._output.insert_before_last_whitespace(",")
            return self._stack.update(Caret.BEFORE_VALUE)
        return False

    def _parse_repair_array_end(self) -> bool:
        self._output.insert_before_last_whitespace("]")
        return self._stack.pop()

    def _parse_repair_ndjson_end(self) -> bool:
        if self._is_end(self._i):
            self._output.push("\n]")
            return self._stack.pop()
        self._throw_unexpected_end()
        return False

    def _parse_function_call_end(self) -> bool:
        if self._skip_character(")"):
            self._skip_character(";")
        return self._stack.pop()

    def _parse_root_start(self) -> bool:
        self._parse_markdown_code_block(["```", "[```", "{```"])
        return self._parse_value() or self._parse_unexpected_end()

    def _parse_root_end(self) -> bool:
        self._parse_markdown_code_block(["```", "```]", "```}"])

        parsed_comma = self._parse_character(",")
        self._parse_whitespace_and_skip_comments()

        if (
            not self._is_end(self._i)
            and is_start_of_value(self._char(self._i))
            and (
                self._output.ends_with_ignoring_whitespace(",")
                or self._output.ends_with_ignoring_whitespace("\n")
            )
        ):
            if not parsed_comma:
                self._output.insert_before_last_whitespace(",")

            self._output.unshift("[\n")
            return self._stack.push(StackType.ND_JSON, Caret.BEFORE_VALUE)

        if parsed_comma:
            self._output.strip_last_occurrence(",")
            return self._stack.update(Caret.AFTER_VALUE)

        while (
            not self._is_end(self._i)
            and self._char(self._i) in ("}", "]")
        ):
            self._i += 1
            self._parse_whitespace_and_skip_comments()

        if not self._is_end(self._i):
            self._throw_unexpected_character()

        return False

    def _parse_whitespace_and_skip_comments(
        self, skip_newline: bool = True
    ) -> bool:
        start = self._i
        changed = self._parse_whitespace(skip_newline)
        while True:
            changed = self._parse_comment()
            if changed:
                changed = self._parse_whitespace(skip_newline)
            else:
                break
        return self._i > start

    def _parse_whitespace(self, skip_newline: bool) -> bool:
        whitespace = ""

        while True:
            if self._is_ws_at(self._i, skip_newline):
                whitespace += self._char(self._i)
                self._i += 1
            elif self._is_special_ws_at(self._i):
                whitespace += " "
                self._i += 1
            else:
                break

        if whitespace:
            self._output.push(whitespace)
            return True
        return False

    def _parse_comment(self) -> bool:
        if (
            not self._is_end(self._i + 1)
            and self._char(self._i) == "/"
            and self._char(self._i + 1) == "*"
        ):
            while (
                not self._is_end(self._i)
                and not self._at_end_of_block_comment()
            ):
                self._i += 1
            self._i += 2
            return True

        if (
            not self._is_end(self._i + 1)
            and self._char(self._i) == "/"
            and self._char(self._i + 1) == "/"
        ):
            while (
                not self._is_end(self._i)
                and self._char(self._i) != "\n"
            ):
                self._i += 1
            return True

        return False

    def _at_end_of_block_comment(self) -> bool:
        return (
            not self._is_end(self._i + 1)
            and self._char(self._i) == "*"
            and self._char(self._i + 1) == "/"
        )

    def _parse_markdown_code_block(self, blocks: list) -> bool:
        if self._skip_markdown_code_block(blocks):
            if (
                not self._is_end(self._i)
                and is_function_name_char_start(self._char(self._i))
            ):
                while (
                    not self._is_end(self._i)
                    and is_function_name_char(self._char(self._i))
                ):
                    self._i += 1
            self._parse_whitespace_and_skip_comments()
            return True
        return False

    def _skip_markdown_code_block(self, blocks: list) -> bool:
        for block in blocks:
            end = self._i + len(block)
            if (
                not self._is_end(end - 1)
                and self._substr(self._i, end) == block
            ):
                self._i = end
                return True
        return False

    def _parse_character(self, char: str) -> bool:
        if not self._is_end(self._i) and self._char(self._i) == char:
            self._output.push(self._char(self._i))
            self._i += 1
            return True
        return False

    def _skip_character(self, char: str) -> bool:
        if not self._is_end(self._i) and self._char(self._i) == char:
            self._i += 1
            return True
        return False

    def _skip_escape_character(self) -> bool:
        return self._skip_character("\\")

    def _skip_ellipsis(self) -> bool:
        self._parse_whitespace_and_skip_comments()

        if (
            not self._is_end(self._i + 2)
            and self._char(self._i) == "."
            and self._char(self._i + 1) == "."
            and self._char(self._i + 2) == "."
        ):
            self._i += 3
            self._parse_whitespace_and_skip_comments()
            self._skip_character(",")
            return True

        return False

    def _parse_string(
        self, stop_at_delimiter: bool = False, stop_at_index: int = -1
    ) -> bool:
        skip_escape_chars = (
            not self._is_end(self._i) and self._char(self._i) == "\\"
        )
        if skip_escape_chars:
            self._i += 1

        if not self._is_end(self._i) and is_quote(self._char(self._i)):
            is_end_quote = (
                is_double_quote
                if is_double_quote(self._char(self._i))
                else (
                    is_single_quote
                    if is_single_quote(self._char(self._i))
                    else (
                        is_single_quote_like
                        if is_single_quote_like(self._char(self._i))
                        else is_double_quote_like
                    )
                )
            )

            i_before = self._i
            o_before = self._output.length()

            self._output.push('"')
            self._i += 1

            while True:
                if self._is_end(self._i):
                    i_prev = self._prev_non_whitespace_index(self._i - 1)
                    if (
                        not stop_at_delimiter
                        and i_prev >= 0
                        and is_delimiter(self._char(i_prev))
                    ):
                        self._i = i_before
                        self._output.remove(o_before)
                        return self._parse_string(True)

                    self._output.insert_before_last_whitespace('"')
                    return self._stack.update(Caret.AFTER_VALUE)

                if self._i == stop_at_index:
                    self._output.insert_before_last_whitespace('"')
                    return self._stack.update(Caret.AFTER_VALUE)

                if is_end_quote(self._char(self._i)):
                    i_quote = self._i
                    o_quote = self._output.length()
                    self._output.push('"')
                    self._i += 1

                    self._parse_whitespace_and_skip_comments(False)

                    if (
                        stop_at_delimiter
                        or self._is_end(self._i)
                        or (not self._is_end(self._i) and is_delimiter(self._char(self._i)))
                        or (not self._is_end(self._i) and is_quote(self._char(self._i)))
                        or (not self._is_end(self._i) and is_digit(self._char(self._i)))
                    ):
                        self._parse_concatenated_string()
                        return self._stack.update(Caret.AFTER_VALUE)

                    i_prev_char = self._prev_non_whitespace_index(i_quote - 1)
                    prev_char = (
                        self._char(i_prev_char) if i_prev_char >= 0 else ""
                    )

                    if prev_char == ",":
                        self._i = i_before
                        self._output.remove(o_before)
                        return self._parse_string(False, i_prev_char)

                    if is_delimiter(prev_char):
                        self._i = i_before
                        self._output.remove(o_before)
                        return self._parse_string(True)

                    self._output.remove(o_quote + 1)
                    self._i = i_quote + 1
                    self._output.insert_at(o_quote, "\\")

                elif (
                    stop_at_delimiter
                    and not self._is_end(self._i)
                    and is_unquoted_string_delimiter(self._char(self._i))
                ):
                    if (
                        self._i > 0
                        and self._char(self._i - 1) == ":"
                        and _regex_url_start.match(
                            self._substr(i_before + 1, self._i + 2)
                        )
                    ):
                        while not self._is_end(self._i) and _regex_url_char.match(
                            self._char(self._i)
                        ):
                            self._output.push(self._char(self._i))
                            self._i += 1

                    self._output.insert_before_last_whitespace('"')
                    self._parse_concatenated_string()
                    return self._stack.update(Caret.AFTER_VALUE)

                elif (
                    not self._is_end(self._i)
                    and self._char(self._i) == "\\"
                ):
                    if self._is_end(self._i + 1):
                        self._output.push("\\")
                        self._i += 1
                        continue

                    char = self._char(self._i + 1)
                    escape_char = _escape_characters.get(char)
                    if escape_char is not None:
                        self._output.push(self._substr(self._i, self._i + 2))
                        self._i += 2
                    elif char == "u":
                        j = 2
                        while (
                            j < 6
                            and not self._is_end(self._i + j)
                            and is_hex(self._char(self._i + j))
                        ):
                            j += 1

                        if j == 6:
                            self._output.push(self._substr(self._i, self._i + 6))
                            self._i += 6
                        elif self._is_end(self._i + j):
                            self._i += j
                        else:
                            self._throw_invalid_unicode_character()
                    elif char == "\n":
                        self._output.push("\\n")
                        self._i += 2
                    else:
                        self._output.push(char)
                        self._i += 2
                else:
                    char = self._char(self._i)

                    if (
                        char == '"'
                        and self._i > 0
                        and self._char(self._i - 1) != "\\"
                    ):
                        self._output.push(f"\\{char}")
                        self._i += 1
                    elif is_control_character(char):
                        self._output.push(_control_characters.get(char, char))
                        self._i += 1
                    else:
                        if not is_valid_string_character(char):
                            self._throw_invalid_character(char)
                        self._output.push(char)
                        self._i += 1

                if skip_escape_chars:
                    self._skip_escape_character()

        return False

    def _parse_concatenated_string(self) -> bool:
        parsed = False

        self._parse_whitespace_and_skip_comments()
        while (
            not self._is_end(self._i) and self._char(self._i) == "+"
        ):
            parsed = True
            self._i += 1
            self._parse_whitespace_and_skip_comments()

            self._output.strip_last_occurrence('"', True)
            start = self._output.length()
            parsed_str = self._parse_string()
            if parsed_str:
                self._output.remove(start, start + 1)
            else:
                self._output.insert_before_last_whitespace('"')

        return parsed

    def _parse_number(self) -> bool:
        start = self._i
        if not self._is_end(self._i) and self._char(self._i) == "-":
            self._i += 1
            if self._at_end_of_number():
                self._repair_number_ending_with_numeric_symbol(start)
                return self._stack.update(Caret.AFTER_VALUE)
            if self._is_end(self._i) or not is_digit(self._char(self._i)):
                self._i = start
                return False

        while not self._is_end(self._i) and is_digit(self._char(self._i)):
            self._i += 1

        if (
            not self._is_end(self._i)
            and self._char(self._i) == "."
        ):
            self._i += 1
            if self._at_end_of_number():
                self._repair_number_ending_with_numeric_symbol(start)
                return self._stack.update(Caret.AFTER_VALUE)
            if self._is_end(self._i) or not is_digit(self._char(self._i)):
                self._i = start
                return False
            while not self._is_end(self._i) and is_digit(self._char(self._i)):
                self._i += 1

        if (
            not self._is_end(self._i)
            and self._char(self._i) in ("e", "E")
        ):
            self._i += 1
            if (
                not self._is_end(self._i)
                and self._char(self._i) in ("-", "+")
            ):
                self._i += 1
            if self._at_end_of_number():
                self._repair_number_ending_with_numeric_symbol(start)
                return self._stack.update(Caret.AFTER_VALUE)
            if self._is_end(self._i) or not is_digit(self._char(self._i)):
                self._i = start
                return False
            while not self._is_end(self._i) and is_digit(self._char(self._i)):
                self._i += 1

        if not self._at_end_of_number():
            self._i = start
            return False

        if self._i > start:
            num = self._substr(start, self._i)
            has_invalid_leading_zero = bool(re.match(r"^0\d", num))
            self._output.push(f'"{num}"' if has_invalid_leading_zero else num)
            return self._stack.update(Caret.AFTER_VALUE)

        return False

    def _parse_keywords(self) -> bool:
        return (
            self._parse_keyword("true", "true")
            or self._parse_keyword("false", "false")
            or self._parse_keyword("null", "null")
            or self._parse_keyword("True", "true")
            or self._parse_keyword("False", "false")
            or self._parse_keyword("None", "null")
        )

    def _parse_keyword(self, name: str, value: str) -> bool:
        if (
            not self._is_end(self._i + len(name) - 1)
            and self._substr(self._i, self._i + len(name)) == name
        ):
            self._output.push(value)
            self._i += len(name)
            return self._stack.update(Caret.AFTER_VALUE)
        return False

    def _parse_unquoted_key(self) -> bool:
        end = self._find_next_delimiter(True, self._i)

        if end is not None:
            while end > self._i and self._is_ws_at(end - 1, True):
                end -= 1

            symbol = self._substr(self._i, end)
            self._output.push(json.dumps(symbol, ensure_ascii=False))
            self._i = end

            if (
                not self._is_end(self._i)
                and self._char(self._i) == '"'
            ):
                self._i += 1

            return self._stack.update(Caret.AFTER_VALUE)

        return False

    def _find_next_delimiter(self, is_key: bool, start: int) -> int | None:
        j = start
        while (
            not self._is_end(j)
            and not is_unquoted_string_delimiter(self._char(j))
            and not is_quote(self._char(j))
            and (not is_key or self._char(j) != ":")
        ):
            j += 1

        return j if j > self._i else None

    def _prev_non_whitespace_index(self, start: int) -> int:
        prev = start
        while prev > 0 and self._is_ws_at(prev, True):
            prev -= 1
        return prev

    def _at_end_of_number(self) -> bool:
        return (
            self._is_end(self._i)
            or (not self._is_end(self._i) and is_delimiter(self._char(self._i)))
            or self._is_ws_at(self._i, True)
        )

    def _repair_number_ending_with_numeric_symbol(self, start: int) -> None:
        self._output.push(f"{self._substr(start, self._i)}0")

    def _throw_invalid_character(self, char: str) -> None:
        raise JSONRepairError(f"Invalid character {json.dumps(char)}", self._i)

    def _throw_unexpected_character(self) -> None:
        ch = self._char(self._i) if not self._is_end(self._i) else "undefined"
        raise JSONRepairError(f"Unexpected character {json.dumps(ch)}", self._i)

    def _throw_unexpected_end(self) -> None:
        raise JSONRepairError("Unexpected end of json string", self._i)

    def _throw_object_key_expected(self) -> None:
        raise JSONRepairError("Object key expected", self._i)

    def _throw_colon_expected(self) -> None:
        raise JSONRepairError("Colon expected", self._i)

    def _throw_invalid_unicode_character(self) -> None:
        chars = self._substr(self._i, self._i + 6)
        raise JSONRepairError(f'Invalid unicode character "{chars}"', self._i)
