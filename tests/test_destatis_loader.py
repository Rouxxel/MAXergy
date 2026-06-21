"""
Unit tests for scripts/evaluation/destatis_loader.py.

Run with:
    python -m pytest tests/test_destatis_loader.py -v
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "evaluation"))

from destatis_loader import (
    GERMAN_MONTHS,
    MIN_MONTHS_FOR_BACKTESTING,
    MIN_MONTHS_SEASONAL_MODEL,
    MISSING_MARKERS,
    SERIES_COICOP,
    DestatisLoader,
    _fmt,
    write_csv,
    write_json,
)

_REAL_CSV = Path(__file__).parent.parent / "scripts" / "evaluation" / "61111-0004_de.csv"
_REAL_CSV_EXISTS = _REAL_CSV.exists()

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — synthetic minimal CSV that mimics the Destatis layout
# ─────────────────────────────────────────────────────────────────────────────

def _make_synthetic_csv(
    tmp_path: Path,
    n_months: int = 17,
    electricity_vals: list[str] | None = None,
    gas_vals: list[str] | None = None,
    heating_oil_vals: list[str] | None = None,
    petrol_vals: list[str] | None = None,
    include_electricity: bool = True,
    include_gas: bool = True,
    include_heating_oil: bool = True,
    include_petrol: bool = True,
) -> Path:
    """Write a minimal Destatis-format CSV for testing."""
    # Build month sequence starting 2025-01
    months_de_inv = {v: k for k, v in GERMAN_MONTHS.items()}
    time_slots = []
    y, m = 2025, 1
    for _ in range(n_months):
        time_slots.append((str(y), months_de_inv[m]))
        m += 1
        if m > 12:
            m, y = 1, y + 1

    def make_val_row(code: str, desc: str, vals: list[str] | None) -> str:
        if vals is None:
            vals = [f"{100 + i},0" for i in range(n_months)]
        pairs = "".join(f";{v};e" for v in vals)
        return f"{code};{desc}{pairs}\n"

    # Year header row
    year_row = ";;" + ";".join(f"{yr};{yr}" for yr, _ in time_slots) + "\n"
    # "Wait, each month occupies 2 columns" - actually value+flag interleaved
    # Build: col0=code, col1=desc, then pairs (value, flag) per month
    yr_cells = ";;".join("") + ";"  # placeholder
    yr_parts = [yr for yr, _ in time_slots]
    mo_parts = [mo for _, mo in time_slots]

    year_header = ";;" + ";".join(f"{yr};{yr}" for yr in yr_parts) + "\n"
    month_header = ";;" + ";".join(f"{mo};{mo}" for mo in mo_parts) + "\n"

    elec_row = make_val_row("CC13-0451", "Strom", electricity_vals) if include_electricity else ""
    gas_row = make_val_row("CC13-04521", "Erdgas, einschließlich Betriebskosten", gas_vals) if include_gas else ""
    oil_row = make_val_row("CC13-04530", "Heizöl, einschließlich Betriebskosten", heating_oil_vals) if include_heating_oil else ""
    petrol_row = make_val_row("CC13-07222", "Superbenzin", petrol_vals) if include_petrol else ""

    content = (
        "Tabelle: 61111-0004\n"
        "Verbraucherpreisindex: Deutschland, Monate,\n"
        "Klassifikation der Verwendungszwecke des Individualkonsums\n"
        "(COICOP 2-5-Steller Hierarchie)\n"
        "Verbraucherpreisindex für Deutschland\n"
        "Deutschland\n"
        "Verbraucherpreisindex (2020=100)\n"
        + year_header
        + month_header
        + "CC13-01;Nahrungsmittel;120,0;e;121,0;e\n"  # irrelevant row
        + elec_row
        + gas_row
        + oil_row
        + petrol_row
        + "__________\n"
        "© Statistisches Bundesamt (Destatis), 2026\n"
    )

    p = tmp_path / "test_61111-0004.csv"
    p.write_text(content, encoding="utf-8-sig")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# 1. Format detection
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatDetection:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_encoding_detected_as_utf8_sig(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        fmt = loader._detect_format(lines)
        assert fmt["encoding"] == "utf-8-sig"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_delimiter_is_semicolon(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        fmt = loader._detect_format(lines)
        assert fmt["delimiter"] == ";"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_decimal_is_comma(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        fmt = loader._detect_format(lines)
        assert fmt["decimal"] == ","

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_nine_header_rows(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        fmt = loader._detect_format(lines)
        assert fmt["n_header_rows"] == 9

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_footer_rows_detected(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        fmt = loader._detect_format(lines)
        assert fmt["n_footer_rows"] > 0

    def test_synthetic_format_detection(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=6)
        loader = DestatisLoader(p)
        lines = loader._read_raw()
        fmt = loader._detect_format(lines)
        assert fmt["delimiter"] == ";"
        assert fmt["decimal"] == ","


# ─────────────────────────────────────────────────────────────────────────────
# 2. Header parsing
# ─────────────────────────────────────────────────────────────────────────────

class TestHeaderParsing:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_table_id_extracted(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        header = loader._parse_header(lines)
        assert header["table_id"] == "61111-0004"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_base_year_is_2020(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        header = loader._parse_header(lines)
        assert header["base_year"] == "2020"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_title_non_empty(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        header = loader._parse_header(lines)
        assert header["title"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Time column parsing
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeColumnParsing:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_24_time_columns(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        time_cols = loader._parse_time_columns(lines)
        assert len(time_cols) == 24

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_first_date_is_2025_01(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        time_cols = loader._parse_time_columns(lines)
        assert time_cols[0]["label"] == "2025-01"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_last_date_is_2026_12(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        time_cols = loader._parse_time_columns(lines)
        assert time_cols[-1]["label"] == "2026-12"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_dates_monotonically_increasing(self):
        loader = DestatisLoader(_REAL_CSV)
        lines = loader._read_raw()
        time_cols = loader._parse_time_columns(lines)
        labels = [tc["label"] for tc in time_cols]
        assert labels == sorted(labels)

    def test_synthetic_time_columns(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=6)
        loader = DestatisLoader(p)
        lines = loader._read_raw()
        time_cols = loader._parse_time_columns(lines)
        assert len(time_cols) == 6
        assert time_cols[0]["label"] == "2025-01"
        assert time_cols[-1]["label"] == "2025-06"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Values are indices, not absolute prices
# ─────────────────────────────────────────────────────────────────────────────

class TestValueType:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_report_states_price_index(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.value_type == "price_index"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_base_year_2020_in_report(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.base_year == "2020"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_electricity_index_plausible_range(self):
        """Electricity index 2020=100; values in the range 80–200 are plausible."""
        result = DestatisLoader(_REAL_CSV).load()
        sr = result.report.series["electricity"]
        assert sr.found
        lo, hi = sr.value_range
        assert 50 < lo < 200
        assert 50 < hi < 300


# ─────────────────────────────────────────────────────────────────────────────
# 5. All four energy series found
# ─────────────────────────────────────────────────────────────────────────────

class TestSeriesIdentification:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_electricity_found(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.series["electricity"].found

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_gas_found(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.series["gas"].found

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_heating_oil_found(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.series["heating_oil"].found

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_petrol_found(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.series["petrol"].found

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_no_missing_series(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.missing_series == []

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_no_ambiguous_series(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.ambiguous_series == []

    def test_missing_series_reported_clearly(self, tmp_path):
        """When electricity row is absent, the report must say so."""
        p = _make_synthetic_csv(tmp_path, n_months=6, include_electricity=False)
        result = DestatisLoader(p).load()
        assert "electricity" in result.report.missing_series
        assert not result.report.series["electricity"].found

    def test_present_series_still_found(self, tmp_path):
        """Gas/heating_oil/petrol are found even when electricity is absent."""
        p = _make_synthetic_csv(tmp_path, n_months=6, include_electricity=False)
        result = DestatisLoader(p).load()
        assert result.report.series["gas"].found
        assert result.report.series["heating_oil"].found
        assert result.report.series["petrol"].found


# ─────────────────────────────────────────────────────────────────────────────
# 6. Date range and frequency
# ─────────────────────────────────────────────────────────────────────────────

class TestDateRange:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_date_range_starts_2025_01(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.date_range_in_file[0] == "2025-01"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_date_range_ends_2026_12(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.date_range_in_file[1] == "2026-12"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_no_frequency_gaps(self):
        result = DestatisLoader(_REAL_CSV).load()
        issues = DestatisLoader(_REAL_CSV).validate_clean_table(result.clean_csv_rows)
        gap_issues = [i for i in issues if "Gap in monthly frequency" in i]
        assert gap_issues == [], f"Unexpected frequency gaps: {gap_issues}"

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_no_duplicate_dates(self):
        result = DestatisLoader(_REAL_CSV).load()
        issues = DestatisLoader(_REAL_CSV).validate_clean_table(result.clean_csv_rows)
        dup_issues = [i for i in issues if "Duplicate" in i]
        assert dup_issues == [], f"Unexpected duplicates: {dup_issues}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Missing values
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingValues:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_missing_values_reported_per_series(self):
        result = DestatisLoader(_REAL_CSV).load()
        # The file has "..." for future months not yet published
        # At least one series should have n_missing > 0
        total_missing = sum(sr.n_missing for sr in result.report.series.values() if sr.found)
        assert total_missing > 0, "Expected some missing (not yet published) months"

    def test_missing_marker_dot_dot_dot_becomes_none(self, tmp_path):
        """Rows with '...' must produce None, not a parse error."""
        vals = ["120,0"] * 3 + ["..."] * 3
        p = _make_synthetic_csv(tmp_path, n_months=6, electricity_vals=vals)
        result = DestatisLoader(p).load()
        sr = result.report.series["electricity"]
        assert sr.n_missing == 3
        assert sr.n_observations == 3

    def test_missing_not_counted_as_observation(self, tmp_path):
        vals = ["..."] * 6
        p = _make_synthetic_csv(tmp_path, n_months=6, electricity_vals=vals)
        result = DestatisLoader(p).load()
        assert result.report.series["electricity"].n_observations == 0


# ─────────────────────────────────────────────────────────────────────────────
# 8. Numeric parsing
# ─────────────────────────────────────────────────────────────────────────────

class TestNumericParsing:
    def test_comma_decimal_converted(self, tmp_path):
        """Values like '124,8' must be parsed as 124.8."""
        vals = ["124,8"] * 6
        p = _make_synthetic_csv(tmp_path, n_months=6, electricity_vals=vals)
        result = DestatisLoader(p).load()
        sr = result.report.series["electricity"]
        assert sr.value_range == (124.8, 124.8)

    def test_clean_csv_uses_dot_decimal(self, tmp_path):
        vals = ["185,3"] * 4
        p = _make_synthetic_csv(tmp_path, n_months=4, gas_vals=vals)
        result = DestatisLoader(p).load()
        rows = result.clean_csv_rows[1:]
        for row in rows:
            if row[2]:  # gas_index column
                assert "," not in row[2]
                assert float(row[2]) == 185.3


# ─────────────────────────────────────────────────────────────────────────────
# 9. Clean table structure
# ─────────────────────────────────────────────────────────────────────────────

class TestCleanTable:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_clean_table_has_five_columns(self):
        result = DestatisLoader(_REAL_CSV).load()
        header = result.clean_csv_rows[0]
        assert header == ["date", "electricity_index", "gas_index",
                          "heating_oil_index", "petrol_index"]

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_clean_table_row_count_equals_time_columns(self):
        result = DestatisLoader(_REAL_CSV).load()
        # Header + one row per time column
        assert len(result.clean_csv_rows) == result.report.n_time_columns + 1

    def test_synthetic_clean_table_structure(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=6)
        result = DestatisLoader(p).load()
        rows = result.clean_csv_rows
        assert rows[0] == ["date", "electricity_index", "gas_index",
                            "heating_oil_index", "petrol_index"]
        assert len(rows) == 7  # header + 6 months

    def test_clean_table_dates_are_yyyy_mm(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=4)
        result = DestatisLoader(p).load()
        for row in result.clean_csv_rows[1:]:
            assert len(row[0]) == 7
            assert row[0][4] == "-"


# ─────────────────────────────────────────────────────────────────────────────
# 10. Backtesting suitability
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestingSuitability:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_real_file_not_suitable_for_backtesting(self):
        """17 months is far below the 60-month minimum for ETS/SARIMA."""
        result = DestatisLoader(_REAL_CSV).load()
        assert not result.report.overall_backtesting_suitable

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_reason_mentions_minimum_months(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert str(MIN_MONTHS_FOR_BACKTESTING) in result.report.overall_backtesting_reason

    def test_short_series_not_suitable(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=17)
        result = DestatisLoader(p).load()
        assert not result.report.overall_backtesting_suitable

    def test_long_enough_series_is_suitable(self, tmp_path):
        """Simulate 65 months of data — must report suitable."""
        p = _make_synthetic_csv(tmp_path, n_months=MIN_MONTHS_FOR_BACKTESTING + 5)
        result = DestatisLoader(p).load()
        assert result.report.overall_backtesting_suitable

    def test_each_series_has_suitability_flag(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=6)
        result = DestatisLoader(p).load()
        for sid, sr in result.report.series.items():
            if sr.found:
                assert isinstance(sr.backtesting_suitable, bool)
                assert sr.backtesting_reason

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_reason_mentions_genesis_alternative(self):
        """Report must point users to the longer Destatis GENESIS series."""
        result = DestatisLoader(_REAL_CSV).load()
        reason = result.report.overall_backtesting_reason
        # Should mention GENESIS or a longer table
        assert any(
            kw.lower() in reason.lower()
            for kw in ["GENESIS", "61111-0001", "historical", "longer"]
        )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Report completeness
# ─────────────────────────────────────────────────────────────────────────────

class TestReportCompleteness:
    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_report_serialises_to_json(self):
        result = DestatisLoader(_REAL_CSV).load()
        d = result.report.to_dict()
        json_str = json.dumps(d)
        assert json_str  # must not be empty

    def test_transformations_list_non_empty(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=4)
        result = DestatisLoader(p).load()
        assert len(result.report.transformations_applied) > 0

    def test_report_has_all_required_fields(self, tmp_path):
        p = _make_synthetic_csv(tmp_path, n_months=4)
        result = DestatisLoader(p).load()
        r = result.report
        assert r.encoding
        assert r.delimiter
        assert r.decimal_separator
        assert r.base_year
        assert r.value_type == "price_index"
        assert r.date_range_in_file
        assert r.series
        assert isinstance(r.overall_backtesting_suitable, bool)
        assert r.overall_backtesting_reason

    @pytest.mark.skipif(not _REAL_CSV_EXISTS, reason="real CSV not available")
    def test_no_ambiguous_series_in_real_file(self):
        result = DestatisLoader(_REAL_CSV).load()
        assert result.report.ambiguous_series == []


# ─────────────────────────────────────────────────────────────────────────────
# 12. Output file helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestOutputHelpers:
    def test_write_json(self, tmp_path):
        write_json({"key": "value"}, tmp_path / "out.json")
        d = json.loads((tmp_path / "out.json").read_text())
        assert d == {"key": "value"}

    def test_write_csv(self, tmp_path):
        rows = [["date", "val"], ["2025-01", "120.0"]]
        write_csv(rows, tmp_path / "out.csv")
        text = (tmp_path / "out.csv").read_text()
        assert "date,val" in text
        assert "2025-01,120.0" in text

    def test_fmt_none_is_empty_string(self):
        assert _fmt(None) == ""

    def test_fmt_float_one_decimal(self):
        assert _fmt(124.8) == "124.8"
        assert _fmt(100.0) == "100.0"
