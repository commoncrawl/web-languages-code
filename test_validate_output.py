from validate_output import validate_markdown_file
import os

def test_missing_title(tmp_path):
    test_file = tmp_path / "test1.md"
    test_file.write_text("Summary: This is a test.")
    errors = validate_markdown_file(str(test_file))
    assert "Missing title" in errors

def test_missing_summary(tmp_path):
    test_file = tmp_path / "test2.md"
    test_file.write_text("# Test Title")
    errors = validate_markdown_file(str(test_file))
    assert "Missing summary section" in errors

def test_valid_markdown(tmp_path):
    test_file = tmp_path / "test3.md"
    test_file.write_text("# Test Title\nSummary: All good.")
    errors = validate_markdown_file(str(test_file))
    assert not errors