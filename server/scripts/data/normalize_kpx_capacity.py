#!/usr/bin/env python3
"""
Normalize KPX regional renewable/ESS capacity CSV files.

The source data changed its column layout in July 2024. This script accepts
both layouts and writes a compact monthly regional capacity table that PV
backtests can join by region and timestamp month.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "kpx_capacity_20260519" / "kpx_renewable_ess_capacity_20250531.csv"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "pv"
    / "capacity_20260519"
    / "kpx_regional_solar_capacity_monthly_202210_202505.csv"
)
REGION_ALIASES = {
    "서울특별시": "서울시",
    "부산광역시": "부산시",
    "대구광역시": "대구시",
    "인천광역시": "인천시",
    "광주광역시": "광주시",
    "대전광역시": "대전시",
    "울산광역시": "울산시",
    "세종특별자치시": "세종시",
    "제주특별자치도": "제주도",
    "서울": "서울시",
    "부산": "부산시",
    "대구": "대구시",
    "인천": "인천시",
    "광주": "광주시",
    "대전": "대전시",
    "울산": "울산시",
    "세종": "세종시",
    "제주": "제주도",
}


def read_csv_auto(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")
    raise UnicodeDecodeError("csv", b"", 0, 1, "; ".join(errors))


def extract_zip_members(path: Path, work_dir: Path) -> list[Path]:
    if not zipfile_is_valid(path):
        return [path]
    work_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with ZipFile(path) as archive:
        for index, member in enumerate(archive.infolist(), start=1):
            if member.is_dir():
                continue
            target = work_dir / f"kpx_renewable_ess_capacity_part{index}.csv"
            target.write_bytes(archive.read(member))
            extracted.append(target)
    return extracted


def zipfile_is_valid(path: Path) -> bool:
    try:
        with ZipFile(path):
            return True
    except Exception:
        return False


def normalize_source_frame(frame: pd.DataFrame, source_file: str) -> pd.DataFrame:
    if "태양광 전체 설비용량" in frame.columns:
        solar_col = "태양광 전체 설비용량"
        wind_col = "풍력 전체 설비용량"
        solar_ess_col = "태양광 연계 전기저장장치 설비용량"
        wind_ess_col = "풍력 연계 전기저장장치 설비용량"
    else:
        solar_col = "태양광"
        wind_col = "풍력"
        solar_ess_col = "전기저장장치(태양광)"
        wind_ess_col = "전기저장장치(풍력)"

    out = pd.DataFrame(
        {
            "year": pd.to_numeric(frame["연도"], errors="raise").astype(int),
            "month": pd.to_numeric(frame["월"], errors="raise").astype(int),
            "region": frame["지역"].astype(str).str.strip().replace(REGION_ALIASES),
            "solar_capacity_mw": pd.to_numeric(frame[solar_col], errors="raise"),
            "wind_capacity_mw": pd.to_numeric(frame[wind_col], errors="coerce").fillna(0.0),
            "solar_ess_capacity_mw": pd.to_numeric(frame[solar_ess_col], errors="coerce").fillna(0.0),
            "wind_ess_capacity_mw": pd.to_numeric(frame[wind_ess_col], errors="coerce").fillna(0.0),
            "source_file": source_file,
        }
    )
    out["month_start"] = pd.to_datetime(
        out["year"].astype(str) + "-" + out["month"].astype(str).str.zfill(2) + "-01",
        errors="raise",
    )
    return out


def normalize_capacity(input_path: Path, output_path: Path, work_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in extract_zip_members(input_path, work_dir):
        frames.append(normalize_source_frame(read_csv_auto(path), path.name))
    out = pd.concat(frames, ignore_index=True)
    out = (
        out.sort_values(["region", "month_start", "source_file"])
        .drop_duplicates(["region", "month_start"], keep="last")
        .sort_values(["region", "month_start"])
        .reset_index(drop=True)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    summary_path = output_path.with_suffix(".summary.csv")
    summary = (
        out.groupby("region", as_index=False)
        .agg(
            rows=("month_start", "size"),
            start=("month_start", "min"),
            end=("month_start", "max"),
            first_solar_capacity_mw=("solar_capacity_mw", "first"),
            last_solar_capacity_mw=("solar_capacity_mw", "last"),
        )
        .sort_values("region")
    )
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_INPUT.parent / "extracted")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = normalize_capacity(args.input, args.output, args.work_dir)
    print(f"saved: {args.output}")
    print(f"rows={len(frame)} regions={frame['region'].nunique()} range={frame['month_start'].min()}..{frame['month_start'].max()}")


if __name__ == "__main__":
    main()
