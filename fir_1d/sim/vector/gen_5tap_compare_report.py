# File: gen_5tap_compare_report.py
# Role: 5탭 기준 ideal/fixed 출력 벡터 비교 리포트 생성을 위한 모듈이다.
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


THIS_FILE = Path(__file__).resolve()
DEFAULT_OUTPUT_DIR = THIS_FILE.parent / "output"
DEFAULT_IDEAL_5TAP_DIR = DEFAULT_OUTPUT_DIR / "ideal_5tap"
DEFAULT_FIXED_5TAP_DIR = DEFAULT_OUTPUT_DIR / "fixed_5tap"
DEFAULT_REPORT_DIR = DEFAULT_OUTPUT_DIR / "report_5tap"

# 파일 이름 검증 및 파싱
IDEAL_NAME_RE = re.compile(r"^(?P<case_stem>.+?)__(?P<coeff_name>.+)_ideal_5tap_y_f64\.npy$")
FIXED_NAME_RE = re.compile(r"^(?P<case_stem>.+?)__(?P<coeff_name>.+)_fixed_5tap_y_u8\.npy$")

PairKey = tuple[str, str]


def _key_to_str(key: PairKey) -> str:
    case_stem, coeff_name = key
    return f"{case_stem}__{coeff_name}"


def _safe_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _iter_npy_files(directory: Path) -> list[Path]:
    return sorted([p for p in directory.glob("*.npy") if p.is_file()], key=lambda p: p.name.lower())


def _collect_keyed_files(
    directory: Path,
    *,
    pattern: re.Pattern[str],
) -> tuple[dict[PairKey, Path], list[str], list[str]]:
    key_to_path: dict[PairKey, Path] = {}
    invalid_names: list[str] = []
    duplicate_keys: list[str] = []

    for path in _iter_npy_files(directory):
        m = pattern.match(path.name)
        if m is None:
            invalid_names.append(path.name)
            continue

        key = (m.group("case_stem"), m.group("coeff_name"))
        if key in key_to_path:
            duplicate_keys.append(_key_to_str(key))
            continue
        key_to_path[key] = path

    return key_to_path, invalid_names, sorted(duplicate_keys)


def _compute_metrics(y_ideal: np.ndarray, y_fixed: np.ndarray) -> dict[str, float | int]:
    if y_ideal.shape != y_fixed.shape:
        raise ValueError(f"Shape mismatch: ideal={y_ideal.shape}, fixed={y_fixed.shape}")

    ideal_f64 = y_ideal.astype(np.float64, copy=False)
    fixed_f64 = y_fixed.astype(np.float64, copy=False)
    diff = fixed_f64 - ideal_f64
    abs_diff = np.abs(diff)

    max_abs_err = float(abs_diff.max()) if abs_diff.size else 0.0
    mae = float(abs_diff.mean()) if abs_diff.size else 0.0
    rmse = float(np.sqrt(np.mean(np.square(diff)))) if diff.size else 0.0
    mean_err = float(diff.mean()) if diff.size else 0.0

    flat_fixed = y_fixed.reshape(-1)
    sat_low_ratio = float(np.mean(flat_fixed == 0)) if flat_fixed.size else 0.0
    sat_high_ratio = float(np.mean(flat_fixed == 255)) if flat_fixed.size else 0.0
    sat_ratio = sat_low_ratio + sat_high_ratio

    ideal_clip_needed = (ideal_f64 < 0.0) | (ideal_f64 > 255.0)
    clip_needed_ratio = float(np.mean(ideal_clip_needed)) if ideal_clip_needed.size else 0.0

    return {
        "num_samples": int(ideal_f64.size),
        "max_abs_err": max_abs_err,
        "mae": mae,
        "rmse": rmse,
        "mean_err": mean_err,
        "sat_low_ratio": sat_low_ratio,
        "sat_high_ratio": sat_high_ratio,
        "sat_ratio": sat_ratio,
        "clip_needed_ratio": clip_needed_ratio,
    }


def _summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "num_cases": 0,
            "num_samples_total": 0,
            "avg_max_abs_err": 0.0,
            "avg_mae": 0.0,
            "avg_rmse": 0.0,
            "avg_mean_err": 0.0,
            "avg_sat_low_ratio": 0.0,
            "avg_sat_high_ratio": 0.0,
            "avg_sat_ratio": 0.0,
            "avg_clip_needed_ratio": 0.0,
            "max_max_abs_err": 0.0,
            "max_mae": 0.0,
            "max_rmse": 0.0,
            "max_sat_ratio": 0.0,
        }

    def _avg(col: str) -> float:
        return float(np.mean([_safe_float(r[col]) for r in rows]))

    def _max(col: str) -> float:
        return float(np.max([_safe_float(r[col]) for r in rows]))

    return {
        "num_cases": len(rows),
        "num_samples_total": int(sum(int(r["num_samples"]) for r in rows)),
        "avg_max_abs_err": _avg("max_abs_err"),
        "avg_mae": _avg("mae"),
        "avg_rmse": _avg("rmse"),
        "avg_mean_err": _avg("mean_err"),
        "avg_sat_low_ratio": _avg("sat_low_ratio"),
        "avg_sat_high_ratio": _avg("sat_high_ratio"),
        "avg_sat_ratio": _avg("sat_ratio"),
        "avg_clip_needed_ratio": _avg("clip_needed_ratio"),
        "max_max_abs_err": _max("max_abs_err"),
        "max_mae": _max("mae"),
        "max_rmse": _max("rmse"),
        "max_sat_ratio": _max("sat_ratio"),
    }


def _summarize_by_coeff(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        coeff = str(row["coeff_name"])
        grouped.setdefault(coeff, []).append(row)

    out: dict[str, dict[str, Any]] = {}
    for coeff, coeff_rows in sorted(grouped.items(), key=lambda kv: kv[0]):
        out[coeff] = _summarize_rows(coeff_rows)
    return out


def _build_worst_cases(rows: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    if top_k <= 0:
        return []
    ordered = sorted(rows, key=lambda r: (-_safe_float(r["rmse"]), str(r["key"])))
    return ordered[: min(top_k, len(ordered))]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "key",
        "case_stem",
        "coeff_name",
        "height",
        "width",
        "num_samples",
        "max_abs_err",
        "mae",
        "rmse",
        "mean_err",
        "sat_low_ratio",
        "sat_high_ratio",
        "sat_ratio",
        "clip_needed_ratio",
        "ideal_file",
        "fixed_file",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _has_validation_issue(validation: dict[str, Any]) -> bool:
    return any(
        len(validation[name]) > 0
        for name in (
            "invalid_ideal_filenames",
            "invalid_fixed_filenames",
            "duplicate_ideal_keys",
            "duplicate_fixed_keys",
            "missing_ideal_keys",
            "missing_fixed_keys",
            "shape_mismatch_cases",
        )
    )


def _print_console_summary(
    *,
    overall: dict[str, Any],
    worst_cases: list[dict[str, Any]],
    validation: dict[str, Any],
    csv_path: Path,
    json_path: Path,
) -> None:
    print("[5tap compare summary]")
    print(f"- num_cases: {overall['num_cases']}")
    print(f"- num_samples_total: {overall['num_samples_total']}")
    print(f"- avg_mae: {overall['avg_mae']:.6f}")
    print(f"- avg_rmse: {overall['avg_rmse']:.6f}")
    print(f"- max_max_abs_err: {overall['max_max_abs_err']:.6f}")
    print(f"- avg_sat_ratio: {overall['avg_sat_ratio']:.6f}")

    print("[validation]")
    print(f"- invalid_ideal_filenames: {len(validation['invalid_ideal_filenames'])}")
    print(f"- invalid_fixed_filenames: {len(validation['invalid_fixed_filenames'])}")
    print(f"- duplicate_ideal_keys: {len(validation['duplicate_ideal_keys'])}")
    print(f"- duplicate_fixed_keys: {len(validation['duplicate_fixed_keys'])}")
    print(f"- missing_ideal_keys: {len(validation['missing_ideal_keys'])}")
    print(f"- missing_fixed_keys: {len(validation['missing_fixed_keys'])}")
    print(f"- shape_mismatch_cases: {len(validation['shape_mismatch_cases'])}")

    if worst_cases:
        print("[worst cases by rmse]")
        for idx, row in enumerate(worst_cases, start=1):
            print(
                f"{idx}. key={row['key']}, rmse={row['rmse']:.6f}, "
                f"mae={row['mae']:.6f}, max_abs_err={row['max_abs_err']:.6f}"
            )

    print("[reports]")
    print(f"- csv: {csv_path}")
    print(f"- json: {json_path}")


def generate_5tap_compare_report(
    *,
    ideal_dir: Path = DEFAULT_IDEAL_5TAP_DIR,
    fixed_dir: Path = DEFAULT_FIXED_5TAP_DIR,
    report_dir: Path = DEFAULT_REPORT_DIR,
    top_k: int = 5,
    strict: bool = False,
) -> dict[str, Any]:
    ideal_dir = ideal_dir.resolve()
    fixed_dir = fixed_dir.resolve()
    report_dir = report_dir.resolve()

    if not ideal_dir.exists():
        raise FileNotFoundError(f"Ideal output directory not found: {ideal_dir}")
    if not fixed_dir.exists():
        raise FileNotFoundError(f"Fixed output directory not found: {fixed_dir}")

    ideal_map, invalid_ideal_names, duplicate_ideal_keys = _collect_keyed_files(
        ideal_dir, pattern=IDEAL_NAME_RE
    )
    fixed_map, invalid_fixed_names, duplicate_fixed_keys = _collect_keyed_files(
        fixed_dir, pattern=FIXED_NAME_RE
    )

    shared_keys = sorted(set(ideal_map) & set(fixed_map), key=lambda k: (k[0], k[1]))
    missing_ideal_keys = sorted(set(fixed_map) - set(ideal_map), key=lambda k: (k[0], k[1]))
    missing_fixed_keys = sorted(set(ideal_map) - set(fixed_map), key=lambda k: (k[0], k[1]))

    if not shared_keys:
        raise ValueError(
            "No matched 5tap ideal/fixed pairs found. "
            f"ideal_dir={ideal_dir}, fixed_dir={fixed_dir}"
        )

    rows: list[dict[str, Any]] = []
    shape_mismatch_cases: list[dict[str, Any]] = []
    for key in shared_keys:
        ideal_path = ideal_map[key]
        fixed_path = fixed_map[key]

        y_ideal = np.load(ideal_path)
        y_fixed = np.load(fixed_path)
        if y_ideal.shape != y_fixed.shape:
            shape_mismatch_cases.append(
                {
                    "key": _key_to_str(key),
                    "ideal_shape": list(y_ideal.shape),
                    "fixed_shape": list(y_fixed.shape),
                    "ideal_file": ideal_path.name,
                    "fixed_file": fixed_path.name,
                }
            )
            continue

        metrics = _compute_metrics(y_ideal, y_fixed)
        case_stem, coeff_name = key
        height = int(y_ideal.shape[0]) if y_ideal.ndim >= 2 else 1
        width = int(y_ideal.shape[1]) if y_ideal.ndim >= 2 else int(y_ideal.shape[0])

        rows.append(
            {
                "key": _key_to_str(key),
                "case_stem": case_stem,
                "coeff_name": coeff_name,
                "height": height,
                "width": width,
                "num_samples": metrics["num_samples"],
                "max_abs_err": metrics["max_abs_err"],
                "mae": metrics["mae"],
                "rmse": metrics["rmse"],
                "mean_err": metrics["mean_err"],
                "sat_low_ratio": metrics["sat_low_ratio"],
                "sat_high_ratio": metrics["sat_high_ratio"],
                "sat_ratio": metrics["sat_ratio"],
                "clip_needed_ratio": metrics["clip_needed_ratio"],
                "ideal_file": ideal_path.name,
                "fixed_file": fixed_path.name,
            }
        )

    rows = sorted(rows, key=lambda r: (str(r["case_stem"]), str(r["coeff_name"])))
    overall = _summarize_rows(rows)
    by_coeff = _summarize_by_coeff(rows)
    worst_cases = _build_worst_cases(rows, top_k=top_k)

    validation = {
        "invalid_ideal_filenames": sorted(invalid_ideal_names),
        "invalid_fixed_filenames": sorted(invalid_fixed_names),
        "duplicate_ideal_keys": duplicate_ideal_keys,
        "duplicate_fixed_keys": duplicate_fixed_keys,
        "missing_ideal_keys": [_key_to_str(key) for key in missing_ideal_keys],
        "missing_fixed_keys": [_key_to_str(key) for key in missing_fixed_keys],
        "shape_mismatch_cases": shape_mismatch_cases,
    }

    if strict and _has_validation_issue(validation):
        raise ValueError(
            "Validation failed in strict mode. "
            f"missing_ideal={len(validation['missing_ideal_keys'])}, "
            f"missing_fixed={len(validation['missing_fixed_keys'])}, "
            f"shape_mismatch={len(validation['shape_mismatch_cases'])}, "
            f"invalid_ideal_names={len(validation['invalid_ideal_filenames'])}, "
            f"invalid_fixed_names={len(validation['invalid_fixed_filenames'])}, "
            f"duplicate_ideal_keys={len(validation['duplicate_ideal_keys'])}, "
            f"duplicate_fixed_keys={len(validation['duplicate_fixed_keys'])}"
        )

    csv_path = report_dir / "compare_5tap_cases.csv"
    json_path = report_dir / "compare_5tap_summary.json"
    _write_csv(csv_path, rows)

    summary_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "ideal_dir": str(ideal_dir),
            "fixed_dir": str(fixed_dir),
            "report_dir": str(report_dir),
            "top_k": int(top_k),
            "strict": bool(strict),
            "comparison_note": "Metrics are computed on fixed(uint8 clipped) - ideal(float64 raw).",
        },
        "validation": validation,
        "overall": overall,
        "by_coeff": by_coeff,
        "worst_cases_by_rmse": worst_cases,
        "cases": rows,
    }
    _write_json(json_path, summary_payload)

    _print_console_summary(
        overall=overall,
        worst_cases=worst_cases,
        validation=validation,
        csv_path=csv_path,
        json_path=json_path,
    )

    return {
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "num_cases": overall["num_cases"],
        "num_samples_total": overall["num_samples_total"],
        "validation_has_issue": _has_validation_issue(validation),
    }


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate 5tap ideal/fixed comparison report (CSV/JSON + console summary)."
    )
    parser.add_argument(
        "--ideal-dir",
        type=Path,
        default=DEFAULT_IDEAL_5TAP_DIR,
        help=f"Directory containing ideal 5tap outputs (default: {DEFAULT_IDEAL_5TAP_DIR})",
    )
    parser.add_argument(
        "--fixed-dir",
        type=Path,
        default=DEFAULT_FIXED_5TAP_DIR,
        help=f"Directory containing fixed 5tap outputs (default: {DEFAULT_FIXED_5TAP_DIR})",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help=f"Directory to store report files (default: {DEFAULT_REPORT_DIR})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of worst cases shown in console/JSON summary (default: 5)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when there are validation issues (missing/invalid/duplicate/shape mismatch).",
    )
    return parser


def main() -> None:
    parser = _build_argparser()
    args = parser.parse_args()

    result = generate_5tap_compare_report(
        ideal_dir=args.ideal_dir,
        fixed_dir=args.fixed_dir,
        report_dir=args.report_dir,
        top_k=args.top_k,
        strict=args.strict,
    )
    print(
        "[done] "
        f"num_cases={result['num_cases']}, "
        f"num_samples_total={result['num_samples_total']}, "
        f"validation_has_issue={result['validation_has_issue']}"
    )


if __name__ == "__main__":
    main()
