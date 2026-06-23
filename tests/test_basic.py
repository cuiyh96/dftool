"""Basic tests for dftool package."""

import pytest
import pandas as pd
import json
from pathlib import Path

from dftool import (
    ColumnProcessor,
    JsonUtils,
    CommonUtils,
    PathUtils,
    TimeUtils,
    __version__,
)


def test_version():
    """Test that version is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)


class TestColumnProcessor:
    """Tests for ColumnProcessor."""

    def test_df_select_columns(self):
        """Test column selection."""
        df = pd.DataFrame({"name": ["a", "b"], "age": [1, 2], "city": ["x", "y"]})
        fn = ColumnProcessor.df_select_columns(["name", "age"])
        result = fn(df)
        assert list(result.columns) == ["name", "age"]
        assert len(result) == 2

    def test_check_columns_exist(self):
        """Test column existence check."""
        df = pd.DataFrame({"name": ["a"], "age": [1]})
        assert ColumnProcessor.check_columns_exist(df, ["name"]) is True
        assert ColumnProcessor.check_columns_exist(df, ["name", "age"]) is True

        with pytest.raises(ValueError):
            ColumnProcessor.check_columns_exist(df, ["nonexistent"])

    def test_df_fillna_column(self):
        """Test fillna operation."""
        df = pd.DataFrame({"col1": [1, None, 3], "col2": ["a", None, "c"]})
        fn = ColumnProcessor.df_fillna_column(["col1", "col2"], [0, "unknown"])
        result = fn(df)
        assert result["col1"].iloc[1] == 0
        assert result["col2"].iloc[1] == "unknown"


class TestJsonUtils:
    """Tests for JsonUtils."""

    def test_safe_json_loads_valid(self):
        """Test parsing valid JSON."""
        result = JsonUtils.safe_json_loads('{"key": "value"}')
        assert result == {"key": "value"}

        result = JsonUtils.safe_json_loads("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_safe_json_loads_invalid(self):
        """Test parsing invalid JSON returns None."""
        result = JsonUtils.safe_json_loads("not json")
        assert result is None

        result = JsonUtils.safe_json_loads(None)
        assert result is None

    def test_extract_json_from_text(self):
        """Test extracting JSON from text."""
        text = "Here is some text ```json\n{\"key\": \"value\"}\n``` and more text"
        result = JsonUtils.extract_json_from_text(text)
        assert result == {"key": "value"}

    def test_extract_json_from_text_inline(self):
        """Test extracting inline JSON."""
        text = 'The config is {"host": "localhost", "port": 8080}'
        result = JsonUtils.extract_json_from_text(text)
        assert result == {"host": "localhost", "port": 8080}


class TestCommonUtils:
    """Tests for CommonUtils."""

    def test_seq_truncate_or_pad(self):
        """Test sequence truncation and padding."""
        # Test truncation
        result = CommonUtils.seq_truncate_or_pad([1, 2, 3, 4, 5], 3)
        assert result == [1, 2, 3]

        # Test padding
        result = CommonUtils.seq_truncate_or_pad([1, 2], 5, fill_value=0)
        assert result == [1, 2, 0, 0, 0]

        # Test exact length
        result = CommonUtils.seq_truncate_or_pad([1, 2, 3], 3)
        assert result == [1, 2, 3]

    def test_read_write_file(self, tmp_path):
        """Test file read/write operations."""
        test_file = tmp_path / "test.json"
        data = {"test": "data", "nested": {"key": "value"}}

        # Write
        CommonUtils.write_file(str(test_file), data)

        # Read
        read_data = CommonUtils.read_file(str(test_file))
        assert read_data == data

    def test_get_hashcode(self):
        """Test hashcode generation."""
        text = "test_text"
        hash1 = CommonUtils.get_hashcode(text, digit_num=8)
        hash2 = CommonUtils.get_hashcode(text, digit_num=8)
        assert hash1 == hash2
        assert len(hash1) == 8


class TestPathUtils:
    """Tests for PathUtils."""

    def test_trans_abs_path(self):
        """Test absolute path conversion."""
        # Should return same for absolute path
        abs_path = "/tmp/test"
        result = PathUtils.trans_abs_path(abs_path)
        assert result == abs_path

    def test_get_path_depth(self):
        """Test path depth calculation."""
        depth = PathUtils.get_path_depth("/a/b/c")
        assert depth >= 3

    def test_set_dir(self, tmp_path):
        """Test directory creation."""
        test_dir = tmp_path / "test_dir"
        PathUtils.setDir(str(test_dir))
        assert test_dir.exists()


class TestTimeUtils:
    """Tests for TimeUtils."""

    def test_get_current_time(self):
        """Test getting current time."""
        time_str = TimeUtils.get_current_time()
        assert isinstance(time_str, str)
        assert len(time_str) == 19  # YYYY-MM-DD HH:MM:SS

    def test_trans_timeStr2timeStamp(self):
        """Test time string to timestamp conversion."""
        timestamp = TimeUtils.trans_timeStr2timeStamp("2024-01-01 00:00:00")
        assert isinstance(timestamp, int)
        assert timestamp == 1704067200