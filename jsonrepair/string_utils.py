import re

# Character code constants
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


def is_hex(char: str) -> bool:
    return char in "0123456789ABCDEFabcdef"


def is_digit(char: str) -> bool:
    return "0" <= char <= "9"


def is_valid_string_character(char: str) -> bool:
    return char >= " "


def is_delimiter(char: str) -> bool:
    return char in ",:[]/{}()\n+"


def is_function_name_char_start(char: str) -> bool:
    return ("a" <= char <= "z") or ("A" <= char <= "Z") or char == "_" or char == "$"


def is_function_name_char(char: str) -> bool:
    return is_function_name_char_start(char) or is_digit(char)


# matches "https://" and other schemas
_regex_url_start = re.compile(r"^(http|https|ftp|mailto|file|data|irc)://$")

# matches all valid URL characters EXCEPT "[", "]", and ","
_regex_url_char = re.compile(r"^[A-Za-z0-9\-._~:/?#@!$&'()*+;=]$")


def is_unquoted_string_delimiter(char: str) -> bool:
    return char in ",[]{}\n+"


def is_start_of_value(char: str) -> bool:
    if not char:
        return False
    return is_quote(char) or bool(_regex_start_of_value.match(char))


_regex_start_of_value = re.compile(r"^[\[{\w\-]$")


def is_control_character(char: str) -> bool:
    return char in ("\n", "\r", "\t", "\b", "\f")


def is_whitespace_at(text: str, index: int) -> bool:
    """Check if the character at index is a whitespace character like space, tab, or newline."""
    if index < 0 or index >= len(text):
        return False
    code = ord(text[index])
    return code in (_CODE_SPACE, _CODE_NEWLINE, _CODE_TAB, _CODE_RETURN)


def is_whitespace_except_newline_at(text: str, index: int) -> bool:
    """Check if the character at index is whitespace like space or tab, but NOT newline."""
    if index < 0 or index >= len(text):
        return False
    code = ord(text[index])
    return code in (_CODE_SPACE, _CODE_TAB, _CODE_RETURN)


def is_special_whitespace_at(text: str, index: int) -> bool:
    """Check if the character at index is a special unicode whitespace variant."""
    if index < 0 or index >= len(text):
        return False
    code = ord(text[index])
    return (
        code == _CODE_NON_BREAKING_SPACE
        or code == _CODE_MONGOLIAN_VOWEL_SEPARATOR
        or (_CODE_EN_QUAD <= code <= _CODE_ZERO_WIDTH_SPACE)
        or code == _CODE_NARROW_NO_BREAK_SPACE
        or code == _CODE_MEDIUM_MATHEMATICAL_SPACE
        or code == _CODE_IDEOGRAPHIC_SPACE
        or code == _CODE_ZERO_WIDTH_NO_BREAK_SPACE
    )


def is_quote(char: str) -> bool:
    return is_double_quote_like(char) or is_single_quote_like(char)


def is_double_quote_like(char: str) -> bool:
    return char == '"' or char == "“" or char == "”"


def is_double_quote(char: str) -> bool:
    return char == '"'


def is_single_quote_like(char: str) -> bool:
    return (
        char == "'"
        or char == "‘"
        or char == "’"
        or char == "`"
        or char == "´"
    )


def is_single_quote(char: str) -> bool:
    return char == "'"


def strip_last_occurrence(text: str, text_to_strip: str, strip_remaining_text: bool = False) -> str:
    index = text.rfind(text_to_strip)
    if index != -1:
        if strip_remaining_text:
            return text[:index]
        else:
            return text[:index] + text[index + len(text_to_strip):]
    return text


def insert_before_last_whitespace(text: str, text_to_insert: str) -> str:
    if not text:
        return text + text_to_insert

    index = len(text)
    if not is_whitespace_at(text, index - 1):
        return text + text_to_insert

    while index > 0 and is_whitespace_at(text, index - 1):
        index -= 1

    return text[:index] + text_to_insert + text[index:]


def remove_at_index(text: str, start: int, count: int) -> str:
    return text[:start] + text[start + count:]


def ends_with_comma_or_newline(text: str) -> bool:
    return bool(re.search(r"[,\n][ \t\r]*$", text))
