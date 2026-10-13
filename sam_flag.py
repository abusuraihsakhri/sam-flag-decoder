#!/usr/bin/env python3
"""Decode SAM/BAM FLAG values (SAM specification v1.6), individually or from CSV."""
import argparse
import csv
import json
import pathlib
import re
import sys

# SAMv1 specification, section 1.4: bits not listed here are reserved.
FLAG_DEFINITIONS = (
    (0x001, "Multiple segments", "Template has multiple segments"),
    (0x002, "Properly aligned", "Each segment properly aligned according to the aligner"),
    (0x004, "Segment unmapped", "This segment is unmapped"),
    (0x008, "Next segment unmapped", "Next segment in the template is unmapped"),
    (0x010, "Reverse complemented", "SEQ is reverse complemented"),
    (0x020, "Next segment reverse complemented", "SEQ of the next segment is reverse complemented"),
    (0x040, "First segment", "First segment in the template"),
    (0x080, "Last segment", "Last segment in the template"),
    (0x100, "Secondary alignment", "Secondary alignment"),
    (0x200, "Failed quality checks", "Not passing platform/vendor quality checks"),
    (0x400, "Duplicate", "PCR or optical duplicate"),
    (0x800, "Supplementary alignment", "Supplementary alignment"),
)
KNOWN_MASK = sum(bit for bit, _, _ in FLAG_DEFINITIONS)


def parse_flag(value):
    """Return a 16-bit FLAG integer; accept decimal, 0x-prefixed hex, or int."""
    if isinstance(value, bool):
        raise ValueError("FLAG must be an integer, not a Boolean")
    if isinstance(value, int):
        flag = value
    elif isinstance(value, str):
        raw = value.strip()
        if re.fullmatch(r"[0-9]+", raw):
            flag = int(raw, 10)
        elif re.fullmatch(r"0[xX][0-9a-fA-F]+", raw):
            flag = int(raw, 16)
        else:
            raise ValueError("FLAG must be an unsigned decimal integer or 0x-prefixed hex")
    else:
        raise ValueError("FLAG must be an unsigned decimal integer or 0x-prefixed hex")
    if not 0 <= flag <= 65535:
        raise ValueError("FLAG must be in the range 0–65535 (16 bits)")
    return flag


def decode_flag(value):
    """Return an interpretation without inferring alignment fields not in FLAG."""
    flag = parse_flag(value)
    active = [
        {"bit": bit, "hex": f"0x{bit:03X}", "name": name, "description": desc}
        for bit, name, desc in FLAG_DEFINITIONS if flag & bit
    ]
    reserved = flag & ~KNOWN_MASK
    warnings = []
    if reserved:
        warnings.append(f"Reserved bit(s) 0x{reserved:X} set; ignore when interpreting current SAM flags.")
    if not flag & 0x1 and flag & (0x2 | 0x8 | 0x20 | 0x40 | 0x80):
        warnings.append("0x1 is unset: SAM does not define the interpretation of mate/template bits.")
    if flag & 0x4 and flag & 0x2:
        warnings.append("0x4 denotes an unmapped segment; do not infer mapped status from 0x2.")
    return {
        "flag": flag,
        "hex": f"0x{flag:04X}",
        "binary": f"{flag:016b}",
        "set_bits": active,
        "unknown_bits": reserved,
        "warnings": warnings,
        "summary": ", ".join(a["name"] for a in active) or "No SAM FLAG bits set",
    }


def lookup(query, extra=None):
    """Compatibility entry point for one numeric SAM FLAG (extra is ignored)."""
    try:
        result = decode_flag(query)
    except ValueError as exc:
        return {"query": query, "top_hit": "Invalid SAM FLAG", "score": 0,
                "all": [], "error": str(exc), "flag": None, "warnings": []}
    return {
        "query": query,
        "top_hit": result["summary"],
        "score": len(result["set_bits"]),
        "all": [(v["bit"], v["name"]) for v in result["set_bits"]],
        **result,
    }


def _resolve_query_column(fieldnames):
    """Prefer a specifically named FLAG column; retain legacy query support."""
    if not fieldnames:
        return None
    for candidate in ("flag", "sam_flag", "query", "test", "drug", "code", "variant", "hla", "lab", "name"):
        for col in fieldnames:
            if col and col.strip().lower() == candidate:
                return col
    return fieldnames[0]


def process_csv(inp, out):
    """Decode every CSV row, preserving columns and reporting row-level errors."""
    inp_path = pathlib.Path(inp)
    if not inp_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {inp}")
    if not inp_path.is_file():
        raise ValueError(f"Input path is not a file: {inp}")
    with inp_path.open(newline="", encoding="utf-8-sig") as src:
        reader = csv.DictReader(src)
        columns = reader.fieldnames or []
        if not columns or any(not c for c in columns):
            raise ValueError("Input CSV needs nonempty column headers")
        query_column = _resolve_query_column(columns)
        rows = []
        for index, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Row {index} has more values than CSV headers")
            result = lookup(row.get(query_column, ""))
            rows.append({**row,
                         "top_hit": result["top_hit"],
                         "lookup_score": result["score"],
                         "flag_decimal": result.get("flag") if result.get("flag") is not None else "",
                         "flag_hex": result.get("hex", ""),
                         "decoded_flags": "; ".join(name for _, name in result["all"]),
                         "warnings": "; ".join(result["warnings"]),
                         "error": result.get("error", "")})
    out_path = pathlib.Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output_columns = list(dict.fromkeys([*columns, "top_hit", "lookup_score", "flag_decimal",
                                         "flag_hex", "decoded_flags", "warnings", "error"]))
    with out_path.open("w", newline="", encoding="utf-8") as dest:
        writer = csv.DictWriter(dest, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def build_parser():
    parser = argparse.ArgumentParser(prog="sam_flag", description="Decode SAM/BAM bitwise FLAG values")
    commands = parser.add_subparsers(dest="cmd", required=True)
    single = commands.add_parser("single", help="Decode one decimal or hexadecimal FLAG")
    single.add_argument("query", nargs="?", default="99")
    single.add_argument("--query", dest="q2")
    batch = commands.add_parser("batch", help="Decode the FLAG column in CSV")
    batch.add_argument("--input", required=True)
    batch.add_argument("--output", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "single":
            result = lookup(args.q2 if args.q2 is not None else args.query)
            if "error" in result:
                print(f"Error: {result['error']}", file=sys.stderr)
                return 2
            print(json.dumps(result, indent=2))
            return 0
        rows = process_csv(args.input, args.output)
        errors = sum(bool(row["error"]) for row in rows)
        print(f"Processed {len(rows)} rows ({errors} invalid) -> {args.output}")
        return 1 if errors else 0
    except (FileNotFoundError, ValueError, csv.Error, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
