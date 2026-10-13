"""Regression tests for actual SAM/BAM FLAG decoding."""
import csv
import pytest
import sam_flag

@pytest.mark.parametrize("raw,names", [
    (0, []),
    (99, ["Multiple segments", "Properly aligned", "Next segment reverse complemented", "First segment"]),
    ("147", ["Multiple segments", "Properly aligned", "Reverse complemented", "Last segment"]),
    ("0x810", ["Reverse complemented", "Supplementary alignment"]),
    (4, ["Segment unmapped"]),
    (0x1000, []),
])
def test_flag_decode(raw, names):
    assert [b["name"] for b in sam_flag.decode_flag(raw)["set_bits"]] == names

@pytest.mark.parametrize("bad", [None, "", "creatinine", "1.0", "0xZZ", -1, 65536, 1.2, True, "0b11"])
def test_bad_flag(bad):
    with pytest.raises(ValueError):
        sam_flag.parse_flag(bad)
    assert "error" in sam_flag.lookup(bad)

def test_reserved_bits_not_invented():
    flag = sam_flag.decode_flag(0x1000)
    assert flag["unknown_bits"] == 0x1000
    assert flag["warnings"] and not flag["set_bits"]

def test_mate_flags_explanation():
    assert any("0x1 is unset" in msg for msg in sam_flag.decode_flag(64)["warnings"])
    assert not sam_flag.decode_flag(193)["warnings"]
    assert any("unmapped" in msg for msg in sam_flag.decode_flag(6)["warnings"])

def test_csv_mixed_rows(tmp_path):
    source, target = tmp_path / "source.csv", tmp_path / "sub" / "out.csv"
    source.write_text("id,FLAG\nA,99\nB,0x93\nC,bad\n", encoding="utf-8")
    rows = sam_flag.process_csv(source, target)
    assert len(rows) == 3
    assert rows[0]["flag_decimal"] == 99
    assert rows[1]["flag_decimal"] == 147
    assert rows[2]["error"]
    with target.open() as stream:
        exported = list(csv.DictReader(stream))
    assert exported[1]["flag_hex"] == "0x0093"

def test_duplicate_columns_not_written_twice(tmp_path):
    src, dest = tmp_path / "source.csv", tmp_path / "dest.csv"
    src.write_text("FLAG,top_hit\n4,old\n")
    sam_flag.process_csv(src, dest)
    assert dest.read_text().splitlines()[0].split(",").count("top_hit") == 1

def test_extra_fields_rejected(tmp_path):
    src = tmp_path / "bad.csv"
    src.write_text("FLAG\n4,5\n")
    with pytest.raises(ValueError, match="more values"):
        sam_flag.process_csv(src, tmp_path / "out.csv")

def test_cli_exit_codes(tmp_path):
    assert sam_flag.main(["single", "99"]) == 0
    assert sam_flag.main(["single", "creatinine"]) == 2
    src, dest = tmp_path / "input.csv", tmp_path / "output.csv"
    src.write_text("FLAG\n4\ninvalid\n")
    assert sam_flag.main(["batch", "--input", str(src), "--output", str(dest)]) == 1
    assert dest.exists()
