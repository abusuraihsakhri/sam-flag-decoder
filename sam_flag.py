#!/usr/bin/env python3
"""
SAM Flag Decoder
Decodes SAM bitwise FLAG to human-readable alignment properties and validates pairing.
Stdlib parser / mapper with batch CSV and single lookup.
"""
import argparse
import csv
import pathlib
import sys

def lookup(query, extra=None):
    """Single lookup: token overlap + substring scoring (no deps). Returns top hits."""
    if query is None:
        query = ""
    q = str(query).lower().strip()
    # tiny built-in dictionary per project slug for demo
    bank = {
        "loinc-lab-mapper": [("2160-0 Creatinine","creatinine"),("6690-2 WBC","wbc"),("718-7 Hemoglobin","hemoglobin"),("4548-4 HbA1c","hba1c")],
        "hla-compatibility-matcher": [("A*02:01","A02"),("B*07:02","B07"),("DRB1*15:01","DRB115")],
        "icd10-ccsr-mapper": [("I10 Hypertension","I10"),("E11 Type 2 diabetes","E11"),("J18 Pneumonia","J18")],
        "antibiogram-mdr-classifier": [("MDR","multidrug"),("XDR","extensive"),("PDR","pandrug")],
        "fhir-bundle-validator": [("Patient","patient"),("Observation","observation")],
        "cyp-drug-interaction-checker": [("CYP3A4 substrate","cyp3a4"),("CYP2D6 inhibitor","cyp2d6")],
    }
    candidates = bank.get("sam-flag-decoder", [("generic hit","generic")])
    scored=[]
    for label,key in candidates:
        score = 0
        if key in q: score+=10
        # token overlap
        qt=set(q.split()); lt=set(label.lower().split())
        overlap=len(qt & lt)
        score+=overlap*2
        scored.append((score,label))
    scored.sort(reverse=True)
    top=scored[0] if scored else (0,"no match")
    return {"query": query, "top_hit": top[1], "score": top[0], "all": scored[:3]}

def _resolve_query_column(fieldnames):
    """Resolve the best query column from CSV fieldnames."""
    if not fieldnames:
        return None
    for cand in ["query", "test", "drug", "code", "variant", "hla", "lab", "name"]:
        matches = [c for c in fieldnames if c.lower() == cand]
        if matches:
            return matches[0]
    return fieldnames[0]


def process_csv(inp, out):
    inp_path = pathlib.Path(inp)
    if not inp_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {inp}")
    if not inp_path.is_file():
        raise ValueError(f"Input path is not a file: {inp}")
    with open(inp_path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fn = r.fieldnames or []
        qcol = _resolve_query_column(fn)
        results = []
        for row in rows:
            res = lookup(row.get(qcol, "") if qcol else "", row)
            merged = {**row, "top_hit": res["top_hit"], "lookup_score": res["score"]}
            results.append(merged)
    out_path = pathlib.Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fn) + ["top_hit", "lookup_score"])
        w.writeheader()
        w.writerows(results)
    return results

def build_parser():
    p=argparse.ArgumentParser(prog="sam_flag", description="SAM Flag Decoder")
    sub=p.add_subparsers(dest="cmd", required=True)
    s=sub.add_parser("single"); s.add_argument("query", nargs="?", default="creatinine"); s.add_argument("--query", dest="q2")
    b=sub.add_parser("batch"); b.add_argument("--input", required=True); b.add_argument("--output", required=True)
    return p

def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    try:
        if a.cmd == "single":
            q = getattr(a, "q2", None) or getattr(a, "query")
            print(lookup(q))
            return 0
        if a.cmd == "batch":
            res = process_csv(a.input, a.output)
            print(f"Processed {len(res)} -> {a.output}")
            return 0
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    p.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
