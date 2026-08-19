"""Unit tests for apply_transformation — the engine-side half of the
preset contract defined in frontend/src/lib/transformations.ts."""

import pytest

from app.features.mappings.transform import apply_transformation


class TestPassthrough:
    @pytest.mark.parametrize("transformation", ["", None])
    def test_no_preset_returns_value_unchanged(self, transformation):
        assert apply_transformation("Hello", transformation) == "Hello"

    @pytest.mark.parametrize(
        "transformation", ["lowercase", "uppercase", "trim", "to_string", "to_number"]
    )
    def test_none_value_always_passes_through(self, transformation):
        assert apply_transformation(None, transformation) is None

    def test_unrecognized_preset_is_a_noop_not_an_error(self):
        assert apply_transformation("Hello", "some_future_preset") == "Hello"

    def test_free_form_custom_text_is_a_noop(self):
        assert apply_transformation("Hello", "concat(first, last)") == "Hello"


class TestCasing:
    def test_lowercase(self):
        assert apply_transformation("HELLO", "lowercase") == "hello"

    def test_uppercase(self):
        assert apply_transformation("hello", "uppercase") == "HELLO"

    def test_trim(self):
        assert apply_transformation("  hello  ", "trim") == "hello"


class TestToString:
    def test_converts_an_int(self):
        assert apply_transformation(42, "to_string") == "42"

    def test_converts_a_bool(self):
        assert apply_transformation(True, "to_string") == "True"


class TestToNumber:
    def test_parses_an_integer_string(self):
        result = apply_transformation("42", "to_number")
        assert result == 42
        assert isinstance(result, int)

    def test_parses_a_float_string(self):
        result = apply_transformation("3.14", "to_number")
        assert result == 3.14
        assert isinstance(result, float)

    def test_unparseable_text_passes_through(self):
        assert apply_transformation("not a number", "to_number") == "not a number"


class TestParseDate:
    def test_parses_iso_date(self):
        assert apply_transformation("2026-08-19", "parse_date") == "2026-08-19T00:00:00"

    def test_parses_dd_mm_yyyy(self):
        assert apply_transformation("19.08.2026", "parse_date") == "2026-08-19T00:00:00"

    def test_datetime_object_is_converted_to_isoformat(self):
        from datetime import datetime

        value = datetime(2026, 8, 19, 12, 30)
        assert apply_transformation(value, "parse_date") == "2026-08-19T12:30:00"

    def test_unparseable_text_passes_through(self):
        assert apply_transformation("not a date", "parse_date") == "not a date"
