"""
Focused tests for sam_flag.py core functions and security features.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sam_flag


class TestLookup:
    """Tests for the lookup() function."""

    def test_basic_lookup_returns_dict(self):
        result = sam_flag.lookup("creatinine")
        assert isinstance(result, dict)
        assert "top_hit" in result
        assert "score" in result
        assert "query" in result
        assert "all" in result

    def test_lookup_returns_all_field(self):
        result = sam_flag.lookup("hemoglobin")
        assert len(result["all"]) > 0

    def test_lookup_empty_string(self):
        result = sam_flag.lookup("")
        assert isinstance(result, dict)
        assert "top_hit" in result

    def test_lookup_none_input(self):
        result = sam_flag.lookup(None)
        assert isinstance(result, dict)

    def test_lookup_case_insensitive(self):
        r1 = sam_flag.lookup("CREATININE")
        r2 = sam_flag.lookup("creatinine")
        assert r1["top_hit"] == r2["top_hit"]

    def test_lookup_with_extra_param(self):
        result = sam_flag.lookup("wbc", extra={"source": "lab"})
        assert isinstance(result, dict)


class TestProcessCsv:
    """Tests for the process_csv() function."""

    def test_process_csv_basic(self, tmp_path):
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("query,name\nQ1,creatinine\nQ2,hemoglobin\n", encoding="utf-8")
        output_csv = tmp_path / "output.csv"

        results = sam_flag.process_csv(str(input_csv), str(output_csv))

        assert len(results) == 2
        assert output_csv.exists()
        for row in results:
            assert "top_hit" in row
            assert "lookup_score" in row

    def test_process_csv_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            sam_flag.process_csv(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))

    def test_process_csv_directory_raises(self, tmp_path):
        with pytest.raises(ValueError):
            sam_flag.process_csv(str(tmp_path), str(tmp_path / "out.csv"))

    def test_process_csv_creates_parent_dirs(self, tmp_path):
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("query\nQ1\n", encoding="utf-8")
        output_csv = tmp_path / "subdir" / "nested" / "output.csv"

        sam_flag.process_csv(str(input_csv), str(output_csv))
        assert output_csv.exists()


class TestBuildParser:
    """Tests for build_parser() and main()."""

    def test_single_command(self):
        assert sam_flag.main(["single", "creatinine"]) == 0

    def test_single_with_flag_query(self):
        assert sam_flag.main(["single", "--query", "hemoglobin"]) == 0

    def test_batch_command(self, tmp_path):
        input_csv = tmp_path / "input.csv"
        input_csv.write_text("query\nQ1\n", encoding="utf-8")
        output_csv = tmp_path / "output.csv"

        result = sam_flag.main(["batch", "--input", str(input_csv), "--output", str(output_csv)])
        assert result == 0
        assert output_csv.exists()

    def test_batch_missing_file_returns_error(self):
        result = sam_flag.main(["batch", "--input", "/nonexistent/path.csv", "--output", "/tmp/out.csv"])
        assert result == 1


class TestResolveQueryColumn:
    """Tests for the _resolve_query_column helper."""

    def test_exact_match(self):
        assert sam_flag._resolve_query_column(["query", "name"]) == "query"

    def test_case_insensitive_match(self):
        assert sam_flag._resolve_query_column(["Query", "Name"]) == "Query"

    def test_fallback_to_first(self):
        assert sam_flag._resolve_query_column(["foo", "bar"]) == "foo"

    def test_empty_fieldnames(self):
        assert sam_flag._resolve_query_column([]) is None

    def test_none_fieldnames(self):
        assert sam_flag._resolve_query_column(None) is None
