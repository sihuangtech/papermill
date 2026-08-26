"""extract_json 与 _repair_truncated_json 的单元测试。"""

import json

import pytest

from backend.infrastructure.llm import (
    FakeLlmClient,
    _repair_truncated_json,
    extract_json,
    extract_json_with_retry,
)

# ---------------------------------------------------------------------------
# extract_json: 基本场景
# ---------------------------------------------------------------------------


class TestExtractJsonBasic:
    def test_plain_json_object(self) -> None:
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_plain_json_array(self) -> None:
        assert extract_json('[1, 2, 3]') == [1, 2, 3]

    def test_json_with_surrounding_text(self) -> None:
        result = extract_json('Here is the result: {"key": "value"} done.')
        assert result == {"key": "value"}

    def test_json_in_fenced_code_block(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert extract_json(text) == {"key": "value"}

    def test_json_in_fenced_block_no_lang(self) -> None:
        text = '```\n[1, 2]\n```'
        assert extract_json(text) == [1, 2]

    def test_no_json_raises(self) -> None:
        with pytest.raises(ValueError, match="没有.*JSON"):
            extract_json("This is just plain text without any json")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="没有.*JSON"):
            extract_json("")

    def test_nested_json(self) -> None:
        data = {"outer": {"inner": [1, 2, {"deep": True}]}}
        assert extract_json(json.dumps(data)) == data


# ---------------------------------------------------------------------------
# _repair_truncated_json: 截断修复
# ---------------------------------------------------------------------------


class TestRepairTruncatedJson:
    def test_unterminated_string(self) -> None:
        # 字符串在中途被截断
        truncated = '{"title": "some long text that was cut'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert parsed["title"].startswith("some long text")

    def test_missing_closing_brace(self) -> None:
        truncated = '{"a": 1, "b": 2'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert parsed == {"a": 1, "b": 2}

    def test_missing_closing_bracket(self) -> None:
        truncated = '[{"a": 1}, {"b": 2}'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert len(parsed) == 2

    def test_nested_truncation(self) -> None:
        truncated = '[{"title": "test", "items": [1, 2'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert parsed[0]["items"] == [1, 2]

    def test_trailing_comma(self) -> None:
        truncated = '{"a": 1, "b": 2,'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert parsed == {"a": 1, "b": 2}

    def test_empty_returns_none(self) -> None:
        assert _repair_truncated_json("") is None
        assert _repair_truncated_json("   ") is None

    def test_already_valid_json(self) -> None:
        valid = '{"a": 1}'
        repaired = _repair_truncated_json(valid)
        assert repaired is not None
        assert json.loads(repaired) == {"a": 1}

    def test_string_with_escaped_quotes(self) -> None:
        truncated = '{"text": "He said \\"hello\\" and'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert "hello" in parsed["text"]

    def test_complex_truncation_like_real_error(self) -> None:
        """模拟日志中实际出现的截断场景：数组中第二个对象的字符串被截断"""
        truncated = (
            '[{"title": "Hypothesis A", "hypothesis": "Method A improves X"}, '
            '{"title": "Hypothesis B", "hypothesis": "Method B shows promise in'
        )
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        parsed = json.loads(repaired)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "Hypothesis A"


# ---------------------------------------------------------------------------
# extract_json: 截断修复集成
# ---------------------------------------------------------------------------


class TestExtractJsonWithRepair:
    def test_truncated_json_auto_repaired(self) -> None:
        truncated = '{"title": "test", "value": 42, "desc": "a long description that'
        result = extract_json(truncated)
        assert result["title"] == "test"
        assert result["value"] == 42

    def test_truncated_array_auto_repaired(self) -> None:
        truncated = '[{"id": 1}, {"id": 2'
        result = extract_json(truncated)
        assert len(result) == 2

    def test_text_prefix_with_truncated_json(self) -> None:
        text = 'Here is the output:\n[{"key": "val'
        result = extract_json(text)
        assert result[0]["key"].startswith("val")


# ---------------------------------------------------------------------------
# extract_json_with_retry
# ---------------------------------------------------------------------------


class TestExtractJsonWithRetry:
    def test_success_on_first_try(self) -> None:
        client = FakeLlmClient(['{"result": "ok"}'])
        result = extract_json_with_retry(client, "test prompt", max_retries=2)
        assert result == {"result": "ok"}
        assert len(client.prompts) == 1

    def test_success_on_retry(self) -> None:
        client = FakeLlmClient([
            "This is not json at all",
            '{"result": "fixed"}',
        ])
        result = extract_json_with_retry(client, "test prompt", max_retries=2)
        assert result == {"result": "fixed"}
        assert len(client.prompts) == 2
        # 第二次 prompt 应该包含错误反馈
        assert "纠正" in client.prompts[1]

    def test_all_retries_exhausted(self) -> None:
        client = FakeLlmClient([
            "not json 1",
            "not json 2",
            "not json 3",
        ])
        with pytest.raises(ValueError, match="3 次尝试"):
            extract_json_with_retry(client, "test prompt", max_retries=2)
        assert len(client.prompts) == 3

    def test_zero_retries(self) -> None:
        client = FakeLlmClient(["not json"])
        with pytest.raises(ValueError):
            extract_json_with_retry(client, "test prompt", max_retries=0)
        assert len(client.prompts) == 1

    def test_truncated_repaired_no_retry_needed(self) -> None:
        """截断 JSON 能被 extract_json 内部修复，不需要重试"""
        client = FakeLlmClient(['{"key": "value that is truncated'])
        result = extract_json_with_retry(client, "test prompt", max_retries=2)
        assert result["key"].startswith("value")
        assert len(client.prompts) == 1  # 只调用了一次

    def test_max_tokens_passed_through(self) -> None:
        client = FakeLlmClient(['{"ok": true}'])
        extract_json_with_retry(client, "prompt", max_retries=0, max_tokens=1234)
        # FakeLlmClient doesn't check max_tokens but we verify it was called
        assert len(client.prompts) == 1
