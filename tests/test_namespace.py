# dftool/tests/test_namespace.py
"""Tests for namespace tools."""

import pytest
from argparse import Namespace

from dftool import (
    dict_to_namespace,
    namespace_to_dict,
    deep_update,
    get_nested_attr,
    set_nested_attr,
    filter_namespace_keys,
    to_json,
    from_json,
    is_namespace,
    get_all_keys,
)


class TestDictToNamespace:
    """Tests for dict_to_namespace function."""

    def test_basic_conversion(self):
        """Test basic dict to namespace conversion."""
        data = {"name": "test", "age": 24}
        ns = dict_to_namespace(data)
        assert ns.name == "test"
        assert ns.age == 24

    def test_nested_conversion(self):
        """Test nested dict conversion."""
        data = {"info": {"name": "test", "address": {"city": "Beijing"}}}
        ns = dict_to_namespace(data)
        assert ns.info.name == "test"
        assert ns.info.address.city == "Beijing"

    def test_list_conversion(self):
        """Test list conversion."""
        data = [{"id": 1}, {"id": 2}]
        result = dict_to_namespace(data)
        assert result[0].id == 1
        assert result[1].id == 2


class TestNamespaceToDict:
    """Tests for namespace_to_dict function."""

    def test_basic_conversion(self):
        """Test basic namespace to dict conversion."""
        ns = Namespace(name="test", age=24)
        result = namespace_to_dict(ns)
        assert result == {"name": "test", "age": 24}

    def test_skip_private(self):
        """Test skipping private attributes."""
        ns = Namespace(name="test", _internal="secret", __private__="hidden")
        result = namespace_to_dict(ns)
        assert "name" in result
        assert "_internal" not in result
        assert "__private__" not in result

    def test_nested_conversion(self):
        """Test nested conversion."""
        ns = Namespace(info=Namespace(name="test", address=Namespace(city="Beijing")))
        result = namespace_to_dict(ns)
        assert result["info"]["name"] == "test"
        assert result["info"]["address"]["city"] == "Beijing"


class TestDeepUpdate:
    """Tests for deep_update function."""

    def test_basic_merge(self):
        """Test basic merge operation."""
        target = Namespace(a=1, b=2)
        source = Namespace(b=3, c=4)
        result = deep_update(target, source)
        assert result.a == 1
        assert result.b == 3
        assert result.c == 4

    def test_nested_merge(self):
        """Test nested merge."""
        target = Namespace(a=1, b=Namespace(c=2))
        source = Namespace(b=Namespace(d=3), e=4)
        result = deep_update(target, source)
        assert result.a == 1
        assert result.b.c == 2
        assert result.b.d == 3
        assert result.e == 4


class TestNestedAttr:
    """Tests for nested attribute access."""

    def test_get_nested_attr(self):
        """Test getting nested attributes."""
        ns = dict_to_namespace({"info": {"address": {"city": "Beijing"}}})
        city = get_nested_attr(ns, "info.address.city")
        assert city == "Beijing"

    def test_get_nested_attr_default(self):
        """Test getting nested attributes with default."""
        ns = dict_to_namespace({"info": {"name": "test"}})
        result = get_nested_attr(ns, "info.address.city", default="Unknown")
        assert result == "Unknown"

    def test_set_nested_attr(self):
        """Test setting nested attributes."""
        ns = Namespace()
        result = set_nested_attr(ns, "info.address.city", "Beijing")
        assert result is True
        assert ns.info.address.city == "Beijing"


class TestFilterNamespaceKeys:
    """Tests for filter_namespace_keys function."""

    def test_keep_keys(self):
        """Test keeping specific keys."""
        ns = Namespace(a=1, b=2, c=3, d=4)
        result = filter_namespace_keys(ns, keep_keys=["a", "c"])
        assert vars(result) == {"a": 1, "c": 3}

    def test_remove_keys(self):
        """Test removing specific keys."""
        ns = Namespace(a=1, b=2, c=3, d=4)
        result = filter_namespace_keys(ns, remove_keys=["b", "d"])
        assert vars(result) == {"a": 1, "c": 3}


class TestJSONSerialization:
    """Tests for JSON serialization."""

    def test_to_json(self):
        """Test converting to JSON."""
        ns = Namespace(name="test", info=Namespace(age=24))
        json_str = to_json(ns)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"
        assert parsed["info"]["age"] == 24

    def test_from_json(self):
        """Test parsing from JSON."""
        json_str = '{"name": "test", "info": {"age": 24}}'
        ns = from_json(json_str)
        assert ns.name == "test"
        assert ns.info.age == 24


class TestUtilities:
    """Tests for utility functions."""

    def test_is_namespace(self):
        """Test is_namespace function."""
        ns = Namespace()
        assert is_namespace(ns) is True
        assert is_namespace({}) is False
        assert is_namespace([]) is False

    def test_get_all_keys(self):
        """Test getting all keys."""
        ns = Namespace(a=1, b=Namespace(c=2, d=Namespace(e=3)))
        keys = get_all_keys(ns)
        assert "a" in keys
        assert "b.c" in keys
        assert "b.d.e" in keys