"""Tests for jsonrepair - runs against both regular and streaming implementations."""

import pytest

from jsonrepair import JSONRepairError, jsonrepair as jsonrepair_regular
from jsonrepair.streaming.core import JsonRepairCore


def _streaming_wrapper(text: str) -> str:
    """Wrap streaming core to act like the regular jsonrepair function."""
    output_parts: list[str] = []

    def on_data(chunk: str) -> None:
        output_parts.append(chunk)

    repair = JsonRepairCore(
        on_data=on_data,
        buffer_size=float("inf"),  # type: ignore[arg-type]
        chunk_size=float("inf"),  # type: ignore[arg-type]
    )
    repair.transform(text)
    repair.flush()
    return "".join(output_parts)


implementations = [
    ("regular", jsonrepair_regular),
    ("streaming", _streaming_wrapper),
]


@pytest.mark.parametrize("name,jsonrepair", implementations)
class TestJsonRepair:
    """Test jsonrepair with both regular and streaming implementations."""

    # -- helpers --

    def assert_repair(self, jsonrepair, text: str) -> None:
        assert jsonrepair(text) == text

    # -- valid JSON parsing --

    def test_parse_full_json_object(self, name, jsonrepair):
        text = '{"a":2.3e100,"b":"str","c":null,"d":false,"e":[1,2,3]}'
        assert jsonrepair(text) == text

    def test_parse_whitespace(self, name, jsonrepair):
        self.assert_repair(jsonrepair, "  { \n } \t ")

    def test_parse_object(self, name, jsonrepair):
        self.assert_repair(jsonrepair, "{}")
        self.assert_repair(jsonrepair, '{  }')
        self.assert_repair(jsonrepair, '{"a": {}}')
        self.assert_repair(jsonrepair, '{"a": "b"}')
        self.assert_repair(jsonrepair, '{"a": 2}')

    def test_parse_array(self, name, jsonrepair):
        self.assert_repair(jsonrepair, "[]")
        self.assert_repair(jsonrepair, "[  ]")
        self.assert_repair(jsonrepair, "[1,2,3]")
        self.assert_repair(jsonrepair, "[ 1 , 2 , 3 ]")
        self.assert_repair(jsonrepair, "[1,2,[3,4,5]]")
        self.assert_repair(jsonrepair, "[{}]")
        self.assert_repair(jsonrepair, '{"a":[]}')
        self.assert_repair(jsonrepair, '[1, "hi", true, false, null, {}, []]')

    def test_parse_number(self, name, jsonrepair):
        for num in [
            "23", "0", "0e+2", "0.0", "-0", "2.3", "2300e3",
            "2300e+3", "2300e-3", "-2", "2e-3", "2.3e-3",
        ]:
            self.assert_repair(jsonrepair, num)

    def test_parse_string(self, name, jsonrepair):
        self.assert_repair(jsonrepair, '"str"')
        self.assert_repair(jsonrepair, '"\\"\\\\\\/\\b\\f\\n\\r\\t"')
        self.assert_repair(jsonrepair, '"\\u260E"')

    def test_parse_keywords(self, name, jsonrepair):
        self.assert_repair(jsonrepair, "true")
        self.assert_repair(jsonrepair, "false")
        self.assert_repair(jsonrepair, "null")

    def test_strings_equaling_json_delimiter(self, name, jsonrepair):
        self.assert_repair(jsonrepair, '""')
        self.assert_repair(jsonrepair, '"["')
        self.assert_repair(jsonrepair, '"]"')
        self.assert_repair(jsonrepair, '"{"')
        self.assert_repair(jsonrepair, '"}"')
        self.assert_repair(jsonrepair, '":"')
        self.assert_repair(jsonrepair, '","')

    def test_unicode_characters_in_string(self, name, jsonrepair):
        assert jsonrepair('"★"') == '"★"'
        assert jsonrepair('"★"') == '"★"'
        assert jsonrepair('"😀"') == '"😀"'
        assert jsonrepair('"йнформация"') == '"йнформация"'

    def test_escaped_unicode_in_string(self, name, jsonrepair):
        assert jsonrepair('"\\u2605"') == '"\\u2605"'
        assert jsonrepair('"\\u2605A"') == '"\\u2605A"'
        assert (
            jsonrepair(
                '"\\u0439\\u043d\\u0444\\u043e\\u0440\\u043c\\u0430\\u0446\\u0438\\u044f"'
            )
            == '"\\u0439\\u043d\\u0444\\u043e\\u0440\\u043c\\u0430\\u0446\\u0438\\u044f"'
        )

    def test_unicode_in_key(self, name, jsonrepair):
        assert jsonrepair('{"★":true}') == '{"★":true}'
        assert jsonrepair('{"😀":true}') == '{"😀":true}'

    # -- repair invalid JSON --

    def test_add_missing_quotes(self, name, jsonrepair):
        assert jsonrepair("abc") == '"abc"'
        assert jsonrepair("hello   world") == '"hello   world"'
        assert (
            jsonrepair("{\nmessage: hello world\n}")
            == '{\n"message": "hello world"\n}'
        )
        assert jsonrepair("{a:2}") == '{"a":2}'
        assert jsonrepair("{a: 2}") == '{"a": 2}'
        assert jsonrepair("{2: 2}") == '{"2": 2}'
        assert jsonrepair("{true: 2}") == '{"true": 2}'
        assert jsonrepair("{\n  a: 2\n}") == '{\n  "a": 2\n}'
        assert jsonrepair("[a,b]") == '["a","b"]'
        assert jsonrepair('[\na,\nb\n]') == '[\n"a",\n"b"\n]'

    def test_repair_unquoted_url(self, name, jsonrepair):
        assert jsonrepair("https://www.bible.com/") == '"https://www.bible.com/"'
        assert (
            jsonrepair("{url:https://www.bible.com/}")
            == '{"url":"https://www.bible.com/"}'
        )
        assert (
            jsonrepair('{url:https://www.bible.com/,"id":2}')
            == '{"url":"https://www.bible.com/","id":2}'
        )
        assert jsonrepair("[https://www.bible.com/]") == '["https://www.bible.com/"]'

    def test_repair_url_with_missing_end_quote(self, name, jsonrepair):
        assert jsonrepair('"https://www.bible.com/') == '"https://www.bible.com/"'
        assert (
            jsonrepair('{"url":"https://www.bible.com/}')
            == '{"url":"https://www.bible.com/"}'
        )
        assert (
            jsonrepair('{"url":"https://www.bible.com/,"id":2}')
            == '{"url":"https://www.bible.com/","id":2}'
        )

    def test_add_missing_end_quote(self, name, jsonrepair):
        assert jsonrepair('"abc') == '"abc"'
        assert jsonrepair("'abc") == '"abc"'
        assert jsonrepair('"12:20') == '"12:20"'
        assert jsonrepair('{"time":"12:20}') == '{"time":"12:20"}'
        assert (
            jsonrepair('{"date":2024-10-18T18:35:22.229Z}')
            == '{"date":"2024-10-18T18:35:22.229Z"}'
        )
        assert jsonrepair('"She said:') == '"She said:"'
        assert jsonrepair('{"text": "She said:') == '{"text": "She said:"}'
        assert jsonrepair('["hello, world]') == '["hello", "world"]'
        assert jsonrepair('["hello,"world"]') == '["hello","world"]'
        assert jsonrepair('{"a":"b}') == '{"a":"b"}'
        assert jsonrepair('{"a":"b,"c":"d"}') == '{"a":"b","c":"d"}'
        assert jsonrepair('{"a":"b,c,"d":"e"}') == '{"a":"b,c","d":"e"}'
        assert jsonrepair('{a:"b,c,"d":"e"}') == '{"a":"b,c","d":"e"}'
        assert jsonrepair('["b,c,]') == '["b","c"]'
        assert jsonrepair("'abc") == '"abc"'

    def test_repair_truncated_json(self, name, jsonrepair):
        assert jsonrepair('"foo') == '"foo"'
        assert jsonrepair("[") == "[]"
        assert jsonrepair('["foo') == '["foo"]'
        assert jsonrepair('["foo"') == '["foo"]'
        assert jsonrepair('["foo",') == '["foo"]'
        assert jsonrepair('{"foo":"bar"') == '{"foo":"bar"}'
        assert jsonrepair('{"foo":"bar') == '{"foo":"bar"}'
        assert jsonrepair('{"foo":') == '{"foo":null}'
        assert jsonrepair('{"foo"') == '{"foo":null}'
        assert jsonrepair('{"foo') == '{"foo":null}'
        assert jsonrepair("{") == "{}"
        assert jsonrepair("2.") == "2.0"
        assert jsonrepair("2e") == "2e0"
        assert jsonrepair("2e+") == "2e+0"
        assert jsonrepair("2e-") == "2e-0"

    def test_repair_ellipsis_in_array(self, name, jsonrepair):
        assert jsonrepair("[1,2,3,...]") == "[1,2,3]"
        assert jsonrepair("[1, 2, 3, ... ]") == "[1, 2, 3  ]"
        assert (
            jsonrepair("[1,2,3,/*comment1*/.../*comment2*/]") == "[1,2,3]"
        )
        assert jsonrepair("[1,2,3,...,9]") == "[1,2,3,9]"
        assert jsonrepair("[...,7,8,9]") == "[7,8,9]"
        assert jsonrepair("[...]") == "[]"
        assert jsonrepair("[ ... ]") == "[  ]"

    def test_repair_ellipsis_in_object(self, name, jsonrepair):
        assert jsonrepair('{"a":2,"b":3,...}') == '{"a":2,"b":3}'
        assert (
            jsonrepair('{"a":2,"b":3,/*comment1*/.../*comment2*/}')
            == '{"a":2,"b":3}'
        )
        assert jsonrepair('{"a":2,"b":3, ... }') == '{"a":2,"b":3  }'
        assert jsonrepair('{"a":2,"b":3,...,"z":26}') == '{"a":2,"b":3,"z":26}'
        assert jsonrepair("{...}") == "{}"

    def test_add_missing_start_quote(self, name, jsonrepair):
        assert jsonrepair('abc"') == '"abc"'
        assert jsonrepair('[a","b"]') == '["a","b"]'
        assert jsonrepair('[a",b"]') == '["a","b"]'
        assert jsonrepair('{"a":"foo","b":"bar"}') == '{"a":"foo","b":"bar"}'
        assert jsonrepair('{a":"foo","b":"bar"}') == '{"a":"foo","b":"bar"}'
        assert jsonrepair('{"a":"foo",b":"bar"}') == '{"a":"foo","b":"bar"}'
        assert jsonrepair('{"a":foo","b":"bar"}') == '{"a":"foo","b":"bar"}'

    def test_replace_single_quotes(self, name, jsonrepair):
        assert jsonrepair("{'a':2}") == '{"a":2}'
        assert jsonrepair("{'a':'foo'}") == '{"a":"foo"}'
        assert jsonrepair('{"a":\'foo\'}') == '{"a":"foo"}'
        assert jsonrepair("{a:'foo',b:'bar'}") == '{"a":"foo","b":"bar"}'

    def test_replace_special_quotes(self, name, jsonrepair):
        assert jsonrepair('{"a":"b"}') == '{"a":"b"}'
        assert jsonrepair('{"a":"b"}') == '{"a":"b"}'

    def test_not_replace_special_quotes_inside_string(self, name, jsonrepair):
        assert jsonrepair('"Rounded “ quote"') == '"Rounded “ quote"'
        assert jsonrepair("'Rounded “ quote'") == '"Rounded “ quote"'
        assert jsonrepair('"Rounded ’ quote"') == '"Rounded ’ quote"'
        assert jsonrepair("'Rounded ’ quote'") == '"Rounded ’ quote"'
        assert jsonrepair("'Double \" quote'") == '"Double \\" quote"'
    def test_add_remove_escape_characters(self, name, jsonrepair):
        assert jsonrepair('"foo\'bar"') == '"foo\'bar"'
        assert jsonrepair('"foo\\"bar"') == '"foo\\"bar"'
        assert jsonrepair("'foo\"bar'") == '"foo\\"bar"'
        assert jsonrepair("'foo\\'bar'") == '"foo\'bar"'
        assert jsonrepair('"foo\\\\\'bar"') == '"foo\\\\\'bar"'
        assert jsonrepair('"\\a"') == '"a"'

    def test_repair_missing_object_value(self, name, jsonrepair):
        assert jsonrepair('{"a":}') == '{"a":null}'
        assert jsonrepair('{"a":,"b":2}') == '{"a":null,"b":2}'
        assert jsonrepair('{"a":') == '{"a":null}'

    def test_repair_undefined(self, name, jsonrepair):
        assert jsonrepair('{"a":undefined}') == '{"a":null}'
        assert jsonrepair("[undefined]") == "[null]"
        assert jsonrepair("undefined") == "null"

    def test_escape_unescaped_control_characters(self, name, jsonrepair):
        assert jsonrepair('"hello\bworld"') == '"hello\\bworld"'
        assert jsonrepair('"hello\fworld"') == '"hello\\fworld"'
        assert jsonrepair('"hello\nworld"') == '"hello\\nworld"'
        assert jsonrepair('"hello\rworld"') == '"hello\\rworld"'
        assert jsonrepair('"hello\tworld"') == '"hello\\tworld"'

    def test_escape_unescaped_double_quotes(self, name, jsonrepair):
        assert jsonrepair('"The TV has a 24" screen"') == '"The TV has a 24\\" screen"'

    def test_replace_special_whitespace(self, name, jsonrepair):
        assert jsonrepair('{"a": "foo bar"}') == '{"a": "foo bar"}'
        assert jsonrepair('{"a": "foo"}') == '{"a": "foo"}'
        assert jsonrepair('{"a":​"foo"}') == '{"a": "foo"}'
        assert jsonrepair('{"a":　"foo"}') == '{"a": "foo"}'
        assert jsonrepair('{"a":﻿"foo"}') == '{"a": "foo"}'

    def test_replace_non_normalized_quotes(self, name, jsonrepair):
        assert jsonrepair("‘foo’") == '"foo"'
        assert jsonrepair("“foo”") == '"foo"'

    def test_remove_block_comments(self, name, jsonrepair):
        assert jsonrepair("/* foo */ {}") == " {}"
        assert jsonrepair("{} /* foo */ ") == "{}  "
        assert jsonrepair("{} /* foo ") == "{} "
        assert jsonrepair('\n/* foo */\n{}') == "\n\n{}"
        assert (
            jsonrepair('{"a":"foo",/*hello*/"b":"bar"}')
            == '{"a":"foo","b":"bar"}'
        )
        assert jsonrepair('{"flag":/*boolean*/true}') == '{"flag":true}'

    def test_remove_line_comments(self, name, jsonrepair):
        assert jsonrepair("{} // comment") == "{} "
        assert (
            jsonrepair('{\n"a":"foo",//hello\n"b":"bar"\n}')
            == '{\n"a":"foo",\n"b":"bar"\n}'
        )

    def test_not_remove_comments_inside_string(self, name, jsonrepair):
        assert jsonrepair('"/* foo */"') == '"/* foo */"'

    def test_strip_jsonp_notation(self, name, jsonrepair):
        assert jsonrepair("callback_123({});") == "{}"
        assert jsonrepair("callback_123([]);") == "[]"
        assert jsonrepair("callback_123(2);") == "2"
        assert jsonrepair('callback_123("foo");') == '"foo"'
        assert jsonrepair("callback_123(null);") == "null"
        assert jsonrepair("callback_123(true);") == "true"
        assert jsonrepair("callback_123(false);") == "false"
        assert jsonrepair("callback({}") == "{}"
        assert jsonrepair("/* foo bar */ callback_123 ({})") == " {}"

    def test_strip_markdown_fenced_code_blocks(self, name, jsonrepair):
        assert jsonrepair('```\n{"a":"b"}\n```') == '\n{"a":"b"}\n'
        assert jsonrepair('```json\n{"a":"b"}\n```') == '\n{"a":"b"}\n'
        assert jsonrepair('```\n{"a":"b"}\n') == '\n{"a":"b"}\n'
        assert jsonrepair('\n{"a":"b"}\n```') == '\n{"a":"b"}\n'
        assert jsonrepair('```{"a":"b"}```') == '{"a":"b"}'

    def test_repair_escaped_string_contents(self, name, jsonrepair):
        assert jsonrepair('\\"hello world\\"') == '"hello world"'
        assert jsonrepair('\\"hello world\\') == '"hello world"'
        assert jsonrepair('\\"hello \\\\"world\\\\"\\"') == '"hello \\"world\\""'
        assert jsonrepair('\\"hello"') == '"hello"'

    def test_strip_leading_comma_array(self, name, jsonrepair):
        assert jsonrepair("[,1,2,3]") == "[1,2,3]"
        assert jsonrepair("[/* a */,/* b */1,2,3]") == "[1,2,3]"
        assert jsonrepair("[, 1,2,3]") == "[ 1,2,3]"

    def test_strip_leading_comma_object(self, name, jsonrepair):
        assert jsonrepair('{,"message": "hi"}') == '{"message": "hi"}'
        assert (
            jsonrepair('{/* a */,/* b */"message": "hi"}')
            == '{"message": "hi"}'
        )
        assert jsonrepair('{ ,"message": "hi"}') == '{ "message": "hi"}'

    def test_strip_trailing_commas_array(self, name, jsonrepair):
        assert jsonrepair("[1,2,3,]") == "[1,2,3]"
        assert jsonrepair("[1,2,3,\n]") == "[1,2,3\n]"
        assert jsonrepair("[1,2,3,/*foo*/]") == "[1,2,3]"
        assert jsonrepair('{"array":[1,2,3,]}') == '{"array":[1,2,3]}'
        assert jsonrepair('"[1,2,3,]"') == '"[1,2,3,]"'

    def test_strip_trailing_commas_object(self, name, jsonrepair):
        assert jsonrepair('{"a":2,}') == '{"a":2}'
        assert jsonrepair('{"a":2  ,  }') == '{"a":2    }'
        assert jsonrepair('{"a":2/*foo*/,/*foo*/}') == '{"a":2}'
        assert jsonrepair('{},') == '{}'
        assert jsonrepair('"{a:2,}"') == '"{a:2,}"'

    def test_strip_trailing_comma_at_end(self, name, jsonrepair):
        assert jsonrepair("4,") == "4"
        assert jsonrepair("4 ,") == "4 "
        assert jsonrepair('{"a":2},') == '{"a":2}'
        assert jsonrepair("[1,2,3],") == "[1,2,3]"

    def test_add_missing_closing_brace_object(self, name, jsonrepair):
        assert jsonrepair("{") == "{}"
        assert jsonrepair('{"a":2') == '{"a":2}'
        assert jsonrepair('{"a":2,') == '{"a":2}'
        assert jsonrepair('{"a":{"b":2}') == '{"a":{"b":2}}'
        assert jsonrepair('[{"b":2]') == '[{"b":2}]'
        assert jsonrepair('[{"i":1{"i":2}]') == '[{"i":1},{"i":2}]'

    def test_remove_redundant_closing_bracket(self, name, jsonrepair):
        assert jsonrepair('{"a": 1}}') == '{"a": 1}'
        assert jsonrepair('{"a": 1}}]}') == '{"a": 1}'
        assert jsonrepair('{"a":2]') == '{"a":2}'
        assert jsonrepair("{}}") == "{}"
        assert jsonrepair("[2,}") == "[2]"
        assert jsonrepair("[}") == "[]"

    def test_add_missing_closing_bracket_array(self, name, jsonrepair):
        assert jsonrepair("[") == "[]"
        assert jsonrepair("[1,2,3") == "[1,2,3]"
        assert jsonrepair("[1,2,3,") == "[1,2,3]"
        assert jsonrepair("[[1,2,3,") == "[[1,2,3]]"

    def test_strip_mongodb_data_types(self, name, jsonrepair):
        assert jsonrepair('NumberLong("2")') == '"2"'
        assert jsonrepair('{"_id":ObjectId("123")}') == '{"_id":"123"}'

        mongo_doc = (
            '{\n'
            '   "_id" : ObjectId("123"),\n'
            '   "isoDate" : ISODate("2012-12-19T06:01:17.171Z"),\n'
            '   "regularNumber" : 67,\n'
            '   "long" : NumberLong("2"),\n'
            '   "long2" : NumberLong(2),\n'
            '   "int" : NumberInt("3"),\n'
            '   "int2" : NumberInt(3),\n'
            '   "decimal" : NumberDecimal("4"),\n'
            '   "decimal2" : NumberDecimal(4)\n'
            '}'
        )
        expected = (
            '{\n'
            '   "_id" : "123",\n'
            '   "isoDate" : "2012-12-19T06:01:17.171Z",\n'
            '   "regularNumber" : 67,\n'
            '   "long" : "2",\n'
            '   "long2" : 2,\n'
            '   "int" : "3",\n'
            '   "int2" : 3,\n'
            '   "decimal" : "4",\n'
            '   "decimal2" : 4\n'
            '}'
        )
        assert jsonrepair(mongo_doc) == expected

    def test_replace_python_constants(self, name, jsonrepair):
        assert jsonrepair("True") == "true"
        assert jsonrepair("False") == "false"
        assert jsonrepair("None") == "null"

    def test_unknown_symbols_to_string(self, name, jsonrepair):
        assert jsonrepair("foo") == '"foo"'
        assert jsonrepair("[1,foo,4]") == '[1,"foo",4]'
        assert jsonrepair("{foo: bar}") == '{"foo": "bar"}'
        assert jsonrepair("foo 2 bar") == '"foo 2 bar"'
        assert (
            jsonrepair("{greeting: hello world}")
            == '{"greeting": "hello world"}'
        )

    def test_invalid_numbers_to_strings(self, name, jsonrepair):
        assert jsonrepair("ES2020") == '"ES2020"'
        assert jsonrepair("0.0.1") == '"0.0.1"'
        assert (
            jsonrepair("746de9ad-d4ff-4c66-97d7-00a92ad46967")
            == '"746de9ad-d4ff-4c66-97d7-00a92ad46967"'
        )
        assert jsonrepair("234..5") == '"234..5"'
        assert jsonrepair("[0.0.1,2]") == '["0.0.1",2]'

    def test_repair_regular_expressions(self, name, jsonrepair):
        assert (
            jsonrepair("{regex: /standalone-styles.css/}")
            == '{"regex": "/standalone-styles.css/"}'
        )
        assert jsonrepair("/[a-z]_/") == '"/[a-z]_/"'

    def test_concatenate_strings(self, name, jsonrepair):
        assert jsonrepair('"hello" + " world"') == '"hello world"'
        assert jsonrepair('"hello" +\n " world"') == '"hello world"'
        assert jsonrepair('"a"+"b"+"c"') == '"abc"'
        assert jsonrepair('"hello" + /*comment*/ " world"') == '"hello world"'

    def test_repair_missing_comma_between_array_items(self, name, jsonrepair):
        assert jsonrepair('{"array": [{}{}]}') == '{"array": [{},{}]}'
        assert jsonrepair('{"array": [{}\n{}]}') == '{"array": [{},\n{}]}'
        assert jsonrepair('{"array": [\n"a"\n"b"\n]}') == '{"array": [\n"a",\n"b"\n]}'

    def test_repair_missing_comma_between_object_properties(self, name, jsonrepair):
        assert jsonrepair('{"a":2\n"b":3\n}') == '{"a":2,\n"b":3\n}'
        assert jsonrepair('{"a":2\n"b":3\nc:4}') == '{"a":2,\n"b":3,\n"c":4}'

    def test_repair_numbers_at_end(self, name, jsonrepair):
        assert jsonrepair('{"a":2.') == '{"a":2.0}'
        assert jsonrepair('{"a":2e') == '{"a":2e0}'
        assert jsonrepair('{"a":2e-') == '{"a":2e-0}'
        assert jsonrepair('{"a":-') == '{"a":-0}'

    def test_repair_missing_colon(self, name, jsonrepair):
        assert jsonrepair('{"a" "b"}') == '{"a": "b"}'
        assert jsonrepair('{"a" 2}') == '{"a": 2}'
        assert jsonrepair('{"a" true}') == '{"a": true}'
        assert jsonrepair('{"a" false}') == '{"a": false}'
        assert jsonrepair('{"a" null}') == '{"a": null}'
        assert jsonrepair('{"a"2}') == '{"a":2}'
        assert jsonrepair('{\n"a" "b"\n}') == '{\n"a": "b"\n}'
        assert jsonrepair('{"a" \'b\'}') == '{"a": "b"}'
        assert jsonrepair("{'a' 'b'}") == '{"a": "b"}'
        assert jsonrepair("{a 'b'}") == '{"a": "b"}'

    def test_repair_combination(self, name, jsonrepair):
        assert jsonrepair('{"array": [\na\nb\n]}') == '{"array": [\n"a",\n"b"\n]}'
        assert jsonrepair("1\n2") == '[\n1,\n2\n]'
        assert jsonrepair("[a,b\nc]") == '["a","b",\n"c"]'

    def test_repair_newline_separated_json(self, name, jsonrepair):
        text = (
            "/* 1 */\n{}\n\n/* 2 */\n{}\n\n/* 3 */\n{}\n"
        )
        expected = '[\n\n{},\n\n\n{},\n\n\n{}\n\n]'
        assert jsonrepair(text) == expected

    def test_repair_comma_separated_list(self, name, jsonrepair):
        assert jsonrepair("1,2,3") == '[\n1,2,3\n]'
        assert jsonrepair("1,2,3,") == '[\n1,2,3\n]'
        assert jsonrepair("1\n2\n3") == '[\n1,\n2,\n3\n]'
        assert jsonrepair("a\nb") == '[\n"a",\n"b"\n]'
        assert jsonrepair("a,b") == '[\n"a","b"\n]'

    def test_repair_number_with_leading_zero(self, name, jsonrepair):
        assert jsonrepair("0789") == '"0789"'
        assert jsonrepair("000789") == '"000789"'
        assert jsonrepair("001.2") == '"001.2"'
        assert jsonrepair("002e3") == '"002e3"'
        assert jsonrepair("[0789]") == '["0789"]'
        assert jsonrepair("{value:0789}") == '{"value":"0789"}'

    # -- error cases --

    def test_throw_on_non_repairable(self, name, jsonrepair):
        with pytest.raises(JSONRepairError, match="Unexpected end of json string"):
            jsonrepair("")

        with pytest.raises(JSONRepairError, match="Colon expected"):
            jsonrepair('{"a",')

        with pytest.raises(JSONRepairError, match="Object key expected"):
            jsonrepair('{:2}')

        with pytest.raises(JSONRepairError, match="Unexpected character"):
            jsonrepair('{"a":2}{}')

        with pytest.raises(JSONRepairError, match="Colon expected"):
            jsonrepair('{"a" ]')

        with pytest.raises(JSONRepairError, match="Unexpected character"):
            jsonrepair('{"a":2}foo')

        with pytest.raises(JSONRepairError, match="Unexpected character"):
            jsonrepair("foo [")

        with pytest.raises(JSONRepairError, match="Invalid unicode character"):
            jsonrepair('"\\u26"')

        with pytest.raises(JSONRepairError, match="Invalid unicode character"):
            jsonrepair('"\\uZ000"')

        with pytest.raises(JSONRepairError, match="Invalid character"):
            jsonrepair('"abc' + chr(0) + '"')
