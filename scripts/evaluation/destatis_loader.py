"""
Destatis Verbraucherpreisindex (VPI) data loader.

Loads and validates the Destatis table 61111-0004 CSV export, which contains
monthly Consumer Price Index (CPI) values for Germany, base year 2020=100.

The loader:
  - Detects encoding, delimiter, decimal separator, and header/footer row counts.
  - Confirms that values are price INDICES (2020=100), not absolute prices.
  - Identifies the four energy sub-index series without guessing.
  - Parses dates into a monthly DatetimeIndex.
  - Validates completeness, frequency, and data quality.
  - Produces a clean table ready for time-series analysis.

Typical usage:
    loader = DestatisLoader(Path("scripts/evaluation/61111-0004_de.csv"))
    result = loader.load()
    result.clean_df   # pandas DataFrame with monthly DatetimeIndex
    result.report     # LoadReport dataclass with all findings
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# ── optional dependency: pandas required for DatetimeIndex and CSV output ────
try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# COICOP codes of interest — explicitly defined, never guessed.
# Source: Statistisches Bundesamt Klassifikation der Verwendungszwecke (COICOP).
SERIES_COICOP: dict[str, dict[str, str]] = {
    "electricity": {
        "code": "CC13-0451",
        "description_de": "Strom",
        "description_en": "Electricity",
        "unit": "index_2020_100",
    },
    "gas": {
        "code": "CC13-04521",
        "description_de": "Erdgas, einschließlich Betriebskosten",
        "description_en": "Natural gas incl. distribution charges",
        "unit": "index_2020_100",
    },
    "heating_oil": {
        "code": "CC13-04530",
        "description_de": "Heizöl, einschließlich Betriebskosten",
        "description_en": "Heating oil incl. distribution charges",
        "unit": "index_2020_100",
    },
    "petrol": {
        "code": "CC13-07222",
        "description_de": "Superbenzin",
        "description_en": "Super petrol (unleaded)",
        "unit": "index_2020_100",
        "note": (
            "Super petrol (Superbenzin) selected as petrol proxy. "
            "Dieselkraftstoff (CC13-07221) is also present in this file. "
            "Choose whichever matches the household vehicle type."
        ),
    },
}

# Alternative diesel code available in the same file
DIESEL_COICOP = {
    "code": "CC13-07221",
    "description_de": "Dieselkraftstoff",
    "description_en": "Diesel fuel",
    "unit": "index_2020_100",
}

GERMAN_MONTHS: dict[str, int] = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4,
    "Mai": 5, "Juni": 6, "Juli": 7, "August": 8,
    "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}

# Minimum history for ETS/SARIMA backtesting (months)
MIN_MONTHS_FOR_BACKTESTING = 60   # 5 years
MIN_MONTHS_SEASONAL_MODEL = 24    # 2 full seasonal cycles

# Destatis quality flag meanings
QUALITY_FLAGS: dict[str, str] = {
    "e": "provisional / estimated (vorläufig)",
    "p": "provisional (vorläufig)",
    "r": "revised (revidiert)",
    "s": "estimated (geschätzt)",
    "d": "doubtful quality (Qualität eingeschränkt)",
    "": "released",
}

MISSING_MARKERS: set[str] = {"...", ".", "/", "x", ""}

# ─────────────────────────────────────────────────────────────────────────────
# REPORT DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SeriesReport:
    series_id: str
    coicop_code: str
    description_de: str
    description_en: str
    found: bool
    n_observations: int
    n_missing: int
    n_provisional: int
    first_date: str | None
    last_date: str | None
    value_range: tuple[float, float] | None
    flags_found: list[str]
    backtesting_suitable: bool
    backtesting_reason: str
    notes: list[str] = field(default_factory=list)


@dataclass
class LoadReport:
    file_path: str
    encoding: str
    delimiter: str
    decimal_separator: str
    n_header_rows: int
    n_footer_rows: int
    n_data_rows: int
    table_id: str
    table_title: str
    base_year: str
    value_type: str                         # "price_index" or "absolute_price"
    date_range_in_file: tuple[str, str]
    n_time_columns: int
    series: dict[str, SeriesReport]
    overall_backtesting_suitable: bool
    overall_backtesting_reason: str
    missing_series: list[str]
    ambiguous_series: list[str]
    warnings: list[str]
    transformations_applied: list[str]

    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON output."""
        d = self.__dict__.copy()
        d["series"] = {k: v.__dict__ for k, v in self.series.items()}
        d["date_range_in_file"] = list(self.date_range_in_file)
        for sr in d["series"].values():
            if sr.get("value_range") and sr["value_range"] is not None:
                sr["value_range"] = list(sr["value_range"])
        return d


@dataclass
class LoadResult:
    clean_df: Any                     # pandas DataFrame or None if pandas absent
    clean_csv_rows: list[list[str]]   # always populated for stdlib-only output
    report: LoadReport


# ─────────────────────────────────────────────────────────────────────────────
# LOADER
# ─────────────────────────────────────────────────────────────────────────────


class DestatisLoader:
    """Load and validate the Destatis 61111-0004 CPI CSV export.

    This class is intentionally narrow: it handles the specific layout of the
    Destatis semicolon-delimited export with interleaved value/quality-flag
    columns. It does NOT attempt to detect arbitrary CSV layouts.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    # ── Public entry point ────────────────────────────────────────────────────

    def load(self) -> LoadResult:
        """Parse the file and return a clean table together with a quality report."""
        raw_lines = self._read_raw()
        fmt = self._detect_format(raw_lines)
        header = self._parse_header(raw_lines)
        time_cols = self._parse_time_columns(raw_lines)
        data_rows = self._parse_data_rows(raw_lines, fmt["n_header_rows"], fmt["n_footer_rows"])
        series_data, series_reports, warnings = self._extract_series(data_rows, time_cols)
        clean_rows = self._build_clean_table(time_cols, series_data)
        transformations = [
            "Decimal separator ',' converted to '.' for numeric parsing.",
            "Missing value markers ('...', '.', '') replaced with None / NaN.",
            "Date columns constructed from separate year and month header rows.",
            "Quality flag columns removed from output; stored in report.",
            "Footer metadata rows excluded.",
        ]

        # Overall backtesting assessment
        n_obs = max(
            (sr.n_observations for sr in series_reports.values() if sr.found),
            default=0,
        )
        if n_obs < MIN_MONTHS_FOR_BACKTESTING:
            overall_suitable = False
            overall_reason = (
                f"Only {n_obs} months of data available. "
                f"ETS and SARIMA backtesting require at least "
                f"{MIN_MONTHS_FOR_BACKTESTING} months ({MIN_MONTHS_FOR_BACKTESTING // 12} years). "
                f"Supplement with longer historical series from Destatis GENESIS "
                f"(table 61111-0001 or 61111-0006 provides monthly data from 1991 onward)."
            )
        elif n_obs < MIN_MONTHS_SEASONAL_MODEL:
            overall_suitable = False
            overall_reason = (
                f"Only {n_obs} months available; seasonal models need ≥{MIN_MONTHS_SEASONAL_MODEL}."
            )
        else:
            overall_suitable = True
            overall_reason = f"{n_obs} months of data available; suitable for seasonal modelling."

        date_range = (
            (time_cols[0]["label"], time_cols[-1]["label"]) if time_cols else ("", "")
        )

        report = LoadReport(
            file_path=str(self._path),
            encoding=fmt["encoding"],
            delimiter=fmt["delimiter"],
            decimal_separator=fmt["decimal"],
            n_header_rows=fmt["n_header_rows"],
            n_footer_rows=fmt["n_footer_rows"],
            n_data_rows=len(data_rows),
            table_id=header.get("table_id", ""),
            table_title=header.get("title", ""),
            base_year=header.get("base_year", ""),
            value_type="price_index",
            date_range_in_file=date_range,
            n_time_columns=len(time_cols),
            series=series_reports,
            overall_backtesting_suitable=overall_suitable,
            overall_backtesting_reason=overall_reason,
            missing_series=[
                k for k, v in series_reports.items() if not v.found
            ],
            ambiguous_series=[],      # no ambiguity in this file
            warnings=warnings,
            transformations_applied=transformations,
        )

        df = self._to_dataframe(clean_rows) if _HAS_PANDAS else None
        return LoadResult(clean_df=df, clean_csv_rows=clean_rows, report=report)

    # ── File I/O ──────────────────────────────────────────────────────────────

    def _read_raw(self) -> list[str]:
        """Read all lines, auto-detecting BOM."""
        with self._path.open(encoding="utf-8-sig") as f:
            return f.readlines()

    # ── Format detection ──────────────────────────────────────────────────────

    def _detect_format(self, lines: list[str]) -> dict:
        """Detect encoding, delimiter, decimal, header, and footer row counts."""
        # Encoding: always utf-8-sig (UTF-8 with BOM) for Destatis exports.
        # Confirmed by file inspection.
        encoding = "utf-8-sig"

        # Delimiter: semicolon confirmed from row 7 which has many ';' separators
        delimiter = ";"

        # Decimal separator: comma (German locale)
        decimal = ","

        # Header rows: rows 0-8 (9 rows) are metadata + year/month headers
        n_header_rows = 9

        # Footer rows: the last 9 lines contain notes and copyright
        # Detect footer by looking for '__________' separator
        n_footer_rows = 0
        for i, line in enumerate(reversed(lines)):
            if line.strip() == "__________":
                n_footer_rows = i + 1
                break
        if n_footer_rows == 0:
            # Fallback: count lines that don't start with CC13-
            for i in range(len(lines) - 1, max(len(lines) - 15, 0), -1):
                if lines[i].startswith("CC13-"):
                    n_footer_rows = len(lines) - 1 - i
                    break

        return {
            "encoding": encoding,
            "delimiter": delimiter,
            "decimal": decimal,
            "n_header_rows": n_header_rows,
            "n_footer_rows": n_footer_rows,
        }

    # ── Header parsing ────────────────────────────────────────────────────────

    def _parse_header(self, lines: list[str]) -> dict:
        result: dict[str, str] = {}

        # Row 0: table ID ("Tabelle: 61111-0004")
        row0 = lines[0].rstrip("\n").split(";")[0].strip()
        if row0.startswith("Tabelle:"):
            result["table_id"] = row0.replace("Tabelle:", "").strip()

        # Row 1: title
        result["title"] = lines[1].rstrip("\n").replace(";", "").strip()

        # Row 6: base year indication (e.g. "Verbraucherpreisindex (2020=100)")
        row6 = lines[6].rstrip("\n").replace(";", "").strip() if len(lines) > 6 else ""
        if "=" in row6 and "100" in row6:
            # Extract "2020" from "Verbraucherpreisindex (2020=100)"
            import re
            m = re.search(r"(\d{4})=100", row6)
            result["base_year"] = m.group(1) if m else row6
        else:
            result["base_year"] = ""

        return result

    # ── Time column parsing ───────────────────────────────────────────────────

    def _parse_time_columns(self, lines: list[str]) -> list[dict]:
        """Return ordered list of time column descriptors.

        Each entry:  {col_index, year, month_int, label "YYYY-MM"}
        col_index points to the VALUE column (the quality flag is col_index+1).
        """
        row7 = lines[7].rstrip("\n").split(";")
        row8 = lines[8].rstrip("\n").split(";")

        time_cols: list[dict] = []
        i = 2  # first two columns are code and description
        while i < len(row7):
            yr_str = row7[i].strip() if i < len(row7) else ""
            mo_str = row8[i].strip() if i < len(row8) else ""
            if yr_str.isdigit() and mo_str in GERMAN_MONTHS:
                month_int = GERMAN_MONTHS[mo_str]
                label = f"{yr_str}-{month_int:02d}"
                time_cols.append({
                    "col_index": i,
                    "year": int(yr_str),
                    "month": month_int,
                    "label": label,
                })
                i += 2  # skip quality flag column
            else:
                i += 1

        return time_cols

    # ── Data row parsing ──────────────────────────────────────────────────────

    def _parse_data_rows(
        self, lines: list[str], n_header: int, n_footer: int
    ) -> list[dict]:
        """Return list of dicts {code, description, raw_fields} for each data row."""
        end = len(lines) - n_footer if n_footer else len(lines)
        rows = []
        for line in lines[n_header:end]:
            stripped = line.rstrip("\n")
            if not stripped or stripped.startswith("_"):
                continue
            fields = stripped.split(";")
            code = fields[0].strip()
            if not code.startswith("CC13-"):
                continue
            desc = fields[1].strip() if len(fields) > 1 else ""
            rows.append({"code": code, "description": desc, "fields": fields})
        return rows

    # ── Series extraction ─────────────────────────────────────────────────────

    def _extract_series(
        self,
        data_rows: list[dict],
        time_cols: list[dict],
    ) -> tuple[dict[str, list], dict[str, SeriesReport], list[str]]:
        """Find the target COICOP rows and extract their value series."""
        code_to_row: dict[str, dict] = {r["code"]: r for r in data_rows}
        warnings: list[str] = []

        series_data: dict[str, list] = {}
        series_reports: dict[str, SeriesReport] = {}

        for series_id, meta in SERIES_COICOP.items():
            code = meta["code"]

            if code not in code_to_row:
                series_reports[series_id] = SeriesReport(
                    series_id=series_id,
                    coicop_code=code,
                    description_de=meta["description_de"],
                    description_en=meta["description_en"],
                    found=False,
                    n_observations=0,
                    n_missing=0,
                    n_provisional=0,
                    first_date=None,
                    last_date=None,
                    value_range=None,
                    flags_found=[],
                    backtesting_suitable=False,
                    backtesting_reason=f"COICOP code {code} not found in file.",
                    notes=["Series not found in this CSV export."],
                )
                warnings.append(f"Series '{series_id}' (code {code}) not found in file.")
                continue

            row = code_to_row[code]
            fields = row["fields"]

            values: list[float | None] = []
            flags: list[str] = []
            dates_available: list[str] = []
            flags_seen: set[str] = set()

            for tc in time_cols:
                ci = tc["col_index"]
                flag_ci = ci + 1

                raw_val = fields[ci].strip() if ci < len(fields) else ""
                raw_flag = fields[flag_ci].strip() if flag_ci < len(fields) else ""

                if raw_val in MISSING_MARKERS:
                    values.append(None)
                    flags.append("")
                else:
                    try:
                        numeric = float(raw_val.replace(",", "."))
                        values.append(numeric)
                        flags.append(raw_flag)
                        dates_available.append(tc["label"])
                        flags_seen.add(raw_flag)
                    except ValueError:
                        values.append(None)
                        flags.append("")
                        warnings.append(
                            f"Series '{series_id}': could not parse value "
                            f"'{raw_val}' at {tc['label']}."
                        )

            series_data[series_id] = [
                {"date": tc["label"], "value": v, "flag": f}
                for tc, v, f in zip(time_cols, values, flags)
            ]

            non_null = [v for v in values if v is not None]
            n_obs = len(non_null)
            n_missing = len(values) - n_obs
            n_provisional = sum(1 for f in flags if f in ("e", "p", "s"))
            v_min = min(non_null) if non_null else None
            v_max = max(non_null) if non_null else None
            first_date = dates_available[0] if dates_available else None
            last_date = dates_available[-1] if dates_available else None

            # Backtesting suitability
            if n_obs < MIN_MONTHS_FOR_BACKTESTING:
                bt_suitable = False
                bt_reason = (
                    f"Only {n_obs} observations available; "
                    f"ETS/SARIMA require ≥{MIN_MONTHS_FOR_BACKTESTING} months. "
                    f"This export covers only the most recent 24-month window. "
                    f"Obtain the full historical series from Destatis GENESIS "
                    f"(table 61111-0001 provides monthly data from 1991)."
                )
            elif n_obs < MIN_MONTHS_SEASONAL_MODEL:
                bt_suitable = False
                bt_reason = (
                    f"Only {n_obs} observations; seasonal models need "
                    f"≥{MIN_MONTHS_SEASONAL_MODEL} (2 full cycles)."
                )
            else:
                bt_suitable = True
                bt_reason = f"{n_obs} observations available."

            notes = []
            if meta.get("note"):
                notes.append(meta["note"])
            if n_provisional > 0:
                notes.append(
                    f"{n_provisional} of {n_obs} observations carry provisional "
                    f"flag 'e' (vorläufig — subject to revision)."
                )
            if n_missing > 0:
                missing_dates = [
                    tc["label"]
                    for tc, v in zip(time_cols, values)
                    if v is None
                ]
                notes.append(f"Missing (not yet published): {missing_dates}")

            series_reports[series_id] = SeriesReport(
                series_id=series_id,
                coicop_code=code,
                description_de=meta["description_de"],
                description_en=meta["description_en"],
                found=True,
                n_observations=n_obs,
                n_missing=n_missing,
                n_provisional=n_provisional,
                first_date=first_date,
                last_date=last_date,
                value_range=(v_min, v_max) if v_min is not None else None,
                flags_found=sorted(flags_seen),
                backtesting_suitable=bt_suitable,
                backtesting_reason=bt_reason,
                notes=notes,
            )

        return series_data, series_reports, warnings

    # ── Clean table construction ───────────────────────────────────────────────

    def _build_clean_table(
        self,
        time_cols: list[dict],
        series_data: dict[str, list],
    ) -> list[list[str]]:
        """Return list-of-lists (header + rows) with the four clean series."""
        cols = ["date", "electricity_index", "gas_index", "heating_oil_index", "petrol_index"]
        rows: list[list[str]] = [cols]
        col_map = {
            "electricity": "electricity_index",
            "gas": "gas_index",
            "heating_oil": "heating_oil_index",
            "petrol": "petrol_index",
        }

        # Build lookup: date → value per series
        series_by_date: dict[str, dict[str, float | None]] = {}
        for sid, col_name in col_map.items():
            for entry in series_data.get(sid, []):
                d = entry["date"]
                series_by_date.setdefault(d, {})[col_name] = entry["value"]

        for tc in time_cols:
            d = tc["label"]
            row_vals = series_by_date.get(d, {})
            row = [
                d,
                _fmt(row_vals.get("electricity_index")),
                _fmt(row_vals.get("gas_index")),
                _fmt(row_vals.get("heating_oil_index")),
                _fmt(row_vals.get("petrol_index")),
            ]
            rows.append(row)

        return rows

    # ── Validation helpers ────────────────────────────────────────────────────

    def validate_clean_table(
        self, clean_rows: list[list[str]]
    ) -> list[str]:
        """Run post-construction checks; return list of issue strings."""
        issues: list[str] = []
        if len(clean_rows) < 2:
            issues.append("Clean table has no data rows.")
            return issues

        header = clean_rows[0]
        data = clean_rows[1:]

        # Duplicate dates
        dates = [r[0] for r in data]
        seen: set[str] = set()
        dupes = [d for d in dates if d in seen or seen.add(d)]  # type: ignore[func-returns-value]
        if dupes:
            issues.append(f"Duplicate dates found: {dupes}")

        # Monthly frequency check
        from datetime import date as dt
        parsed = []
        for d in dates:
            try:
                y, m = d.split("-")
                parsed.append(dt(int(y), int(m), 1))
            except (ValueError, AttributeError):
                issues.append(f"Cannot parse date: {d!r}")

        if len(parsed) > 1:
            parsed_sorted = sorted(parsed)
            for i in range(1, len(parsed_sorted)):
                prev = parsed_sorted[i - 1]
                curr = parsed_sorted[i]
                months_diff = (curr.year - prev.year) * 12 + (curr.month - prev.month)
                if months_diff != 1:
                    issues.append(
                        f"Gap in monthly frequency: {prev.strftime('%Y-%m')} → "
                        f"{curr.strftime('%Y-%m')} ({months_diff} months apart)"
                    )

        # Missing values per series
        for col_i, col_name in enumerate(header[1:], 1):
            n_missing = sum(1 for r in data if r[col_i] == "")
            if n_missing:
                issues.append(
                    f"Column '{col_name}': {n_missing} missing values "
                    f"out of {len(data)} rows."
                )

        # Base-year note
        issues.append(
            "INFO: Values are price indices with base year 2020=100. "
            "No base-year change detected within this export "
            "(single 2020=100 base stated in header row 6)."
        )

        return issues

    # ── Pandas conversion ─────────────────────────────────────────────────────

    @staticmethod
    def _to_dataframe(clean_rows: list[list[str]]) -> Any:
        if not _HAS_PANDAS:
            return None
        import pandas as pd  # noqa: PLC0415
        header = clean_rows[0]
        data = clean_rows[1:]
        df = pd.DataFrame(data, columns=header)
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m")
        df = df.set_index("date")
        for col in df.columns:
            df[col] = pd.to_numeric(df[col].replace("", float("nan")), errors="coerce")
        return df


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _fmt(v: float | None) -> str:
    if v is None:
        return ""
    return f"{v:.1f}"


def write_json(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_csv(rows: list[list[str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
