"""Regression tests for legacy agent CSV Boolean parsing."""
import pytest
from cli import parse_bool

@pytest.mark.parametrize("value,expected", [("true", True), ("TRUE", True), ("yes", True), ("1", True), ("false", False), ("FALSE", False), ("no", False), ("0", False), ("", False), (False, False), (True, True)])
def test_parse_bool(value, expected):
    assert parse_bool(value) is expected

def test_parse_bool_rejects_ambiguous_value():
    with pytest.raises(ValueError):
        parse_bool("unknown")
