"""
Validate the Destatis 61111-0004 CPI CSV export and write outputs.

Usage:
    python scripts/evaluation/validate_destatis_data.py

Writes:
    scripts/evaluation/output/destatis_validation_report.json
    scripts/evaluation/output/destatis_price_indices.csv
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from destatis_loader import DestatisLoader, write_csv, write_json

_CSV_IN = Path(__file__).parent / "61111-0004_de.csv"
_REPORT_OUT = Path(__file__).parent / "output" / "destatis_validation_report.json"
_CSV_OUT = Path(__file__).parent / "output" / "destatis_price_indices.csv"


def main() -> None:
    print(f"Loading: {_CSV_IN}")

    loader = DestatisLoader(_CSV_IN)
    result = loader.load()
    report = result.report
    clean_rows = result.clean_csv_rows

    # Run additional post-load validation checks
    validation_issues = loader.validate_clean_table(clean_rows)

    # Augment the report dict with post-load checks
    report_dict = report.to_dict()
    report_dict["post_load_validation"] = validation_issues

    # Write outputs
    write_json(report_dict, _REPORT_OUT)
    print(f"Wrote report: {_REPORT_OUT}")

    write_csv(clean_rows, _CSV_OUT)
    print(f"Wrote clean CSV: {_CSV_OUT}")

    # Print summary to console
    print()
    print("=" * 70)
    print("DESTATIS VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Table: {report.table_id}")
    print(f"Title: {report.table_title}")
    print(f"Encoding: {report.encoding}  |  Delimiter: '{report.delimiter}'  "
          f"|  Decimal: '{report.decimal_separator}'")
    print(f"Base year: {report.base_year}  |  Value type: {report.value_type}")
    print(f"Date range in file: {report.date_range_in_file[0]} – {report.date_range_in_file[1]}")
    print(f"Time columns: {report.n_time_columns}  |  Data rows: {report.n_data_rows}")
    print()
    print("SERIES FOUND:")
    for sid, sr in report.series.items():
        status = "✓" if sr.found else "✗ NOT FOUND"
        print(f"  {status}  {sid:15s}  [{sr.coicop_code}]  {sr.description_de}")
        if sr.found:
            print(f"             {sr.n_observations} obs  "
                  f"({sr.first_date} – {sr.last_date})  "
                  f"range: {sr.value_range}  "
                  f"missing: {sr.n_missing}  provisional: {sr.n_provisional}")
        for note in sr.notes:
            print(f"             NOTE: {note}")

    if report.missing_series:
        print()
        print(f"MISSING SERIES: {report.missing_series}")

    if report.warnings:
        print()
        print("WARNINGS:")
        for w in report.warnings:
            print(f"  ! {w}")

    print()
    print("BACKTESTING SUITABILITY:")
    print(f"  Overall: {'SUITABLE' if report.overall_backtesting_suitable else 'NOT SUITABLE'}")
    print(f"  Reason: {report.overall_backtesting_reason}")

    print()
    print("POST-LOAD VALIDATION CHECKS:")
    for issue in validation_issues:
        prefix = "  INFO" if issue.startswith("INFO") else "  CHECK"
        print(f"{prefix}: {issue}")

    print()
    print("TRANSFORMATIONS APPLIED:")
    for t in report.transformations_applied:
        print(f"  - {t}")

    print()
    print(f"Clean CSV preview (first 5 data rows):")
    for row in clean_rows[:6]:
        print(f"  {row}")


if __name__ == "__main__":
    main()
