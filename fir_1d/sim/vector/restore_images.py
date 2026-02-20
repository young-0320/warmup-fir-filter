"""
Restore image files from FIR output vectors (.npy).

Supported input sets:
- ideal_3tap, ideal_5tap
- fixed_3tap, fixed_5tap

Default behavior:
- Load vectors from this directory's `output/` subfolder.
- Save restored images under ../output_img.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np


THIS_FILE = Path(__file__).resolve()
DEFAULT_VECTOR_OUTPUT_DIR = THIS_FILE.parent / "output"
DEFAULT_OUTPUT_IMG_DIR = THIS_FILE.parent.parent / "output_img"

VALID_KINDS = ("ideal", "fixed")
VALID_TAPS = ("3", "5")
IDEAL_POLICIES = ("clip", "normalize")

FILENAME_RE = re.compile(
    r"^(?P<case_stem>.+?)__(?P<coeff_name>.+)_(?P<kind>ideal|fixed)_(?P<tap>[35])tap_y_(?P<dtype_tag>f64|u8)\.npy$"
)


def _load_gray_u8_image_backend():
    try:
        from PIL import Image  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required. Install with: `uv add pillow`.") from exc
    return Image


def _iter_npy_files(directory: Path) -> list[Path]:
    return sorted((p for p in directory.glob("*.npy") if p.is_file()), key=lambda p: p.name.lower())


def _to_u8_clip(arr: np.ndarray) -> np.ndarray:
    rounded = np.rint(arr)
    clipped = np.clip(rounded, 0, 255)
    return clipped.astype(np.uint8)


def _to_u8_normalized(arr: np.ndarray) -> np.ndarray:
    arr_f64 = arr.astype(np.float64, copy=False)
    arr_min = float(arr_f64.min())
    arr_max = float(arr_f64.max())
    if arr_max <= arr_min:
        return np.zeros(arr_f64.shape, dtype=np.uint8)
    scaled = (arr_f64 - arr_min) * (255.0 / (arr_max - arr_min))
    return np.rint(np.clip(scaled, 0, 255)).astype(np.uint8)


def _convert_array_to_image_u8(
    arr: np.ndarray,
    *,
    kind: str,
    ideal_policy: str,
) -> np.ndarray:
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array for image restore, got shape={arr.shape}")

    if kind == "fixed":
        if arr.dtype == np.uint8:
            return arr
        return _to_u8_clip(arr.astype(np.float64, copy=False))

    if kind == "ideal":
        arr_f64 = arr.astype(np.float64, copy=False)
        if ideal_policy == "clip":
            return _to_u8_clip(arr_f64)
        if ideal_policy == "normalize":
            return _to_u8_normalized(arr_f64)
        raise ValueError(f"Unsupported ideal_policy={ideal_policy}")

    raise ValueError(f"Unsupported kind={kind}")


def _selected_values(value: str, valid: tuple[str, ...]) -> list[str]:
    if value == "all":
        return list(valid)
    return [value]


def _subdir_name(kind: str, tap: str, *, ideal_policy: str) -> str:
    if kind == "ideal" and ideal_policy != "clip":
        return f"{kind}_{tap}tap_{ideal_policy}"
    return f"{kind}_{tap}tap"


def restore_images(
    *,
    vector_output_dir: Path = DEFAULT_VECTOR_OUTPUT_DIR,
    output_img_dir: Path = DEFAULT_OUTPUT_IMG_DIR,
    kind: str = "all",
    tap: str = "all",
    ideal_policy: str = "clip",
    overwrite: bool = False,
    strict: bool = False,
) -> dict[str, Any]:
    vector_output_dir = vector_output_dir.resolve()
    output_img_dir = output_img_dir.resolve()

    if not vector_output_dir.exists():
        raise FileNotFoundError(f"Vector output directory not found: {vector_output_dir}")

    selected_kinds = _selected_values(kind, VALID_KINDS)
    selected_taps = _selected_values(tap, VALID_TAPS)

    Image = _load_gray_u8_image_backend()

    converted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for sel_kind in selected_kinds:
        for sel_tap in selected_taps:
            input_subdir = vector_output_dir / f"{sel_kind}_{sel_tap}tap"
            if not input_subdir.exists():
                skipped.append(
                    {
                        "reason": "missing_input_subdir",
                        "kind": sel_kind,
                        "tap": f"{sel_tap}tap",
                        "path": str(input_subdir),
                    }
                )
                if strict:
                    raise FileNotFoundError(f"Expected input subdir not found: {input_subdir}")
                continue

            output_subdir = output_img_dir / _subdir_name(sel_kind, sel_tap, ideal_policy=ideal_policy)
            output_subdir.mkdir(parents=True, exist_ok=True)

            for npy_path in _iter_npy_files(input_subdir):
                match = FILENAME_RE.match(npy_path.name)
                if match is None:
                    skipped.append(
                        {
                            "reason": "invalid_filename",
                            "path": str(npy_path),
                        }
                    )
                    if strict:
                        raise ValueError(f"Invalid vector filename: {npy_path.name}")
                    continue

                file_kind = match.group("kind")
                file_tap = match.group("tap")
                if file_kind != sel_kind or file_tap != sel_tap:
                    skipped.append(
                        {
                            "reason": "kind_tap_mismatch",
                            "path": str(npy_path),
                            "expected_kind": sel_kind,
                            "expected_tap": sel_tap,
                            "file_kind": file_kind,
                            "file_tap": file_tap,
                        }
                    )
                    if strict:
                        raise ValueError(
                            f"Kind/tap mismatch in filename={npy_path.name}, "
                            f"expected {sel_kind}_{sel_tap}tap"
                        )
                    continue

                arr = np.load(npy_path)
                img_u8 = _convert_array_to_image_u8(arr, kind=sel_kind, ideal_policy=ideal_policy)

                out_name = f"{npy_path.stem}.png"
                out_path = output_subdir / out_name
                if out_path.exists() and not overwrite:
                    skipped.append(
                        {
                            "reason": "exists",
                            "path": str(out_path),
                        }
                    )
                    continue

                img = Image.fromarray(img_u8, mode="L")
                img.save(out_path)

                converted.append(
                    {
                        "input_npy": str(npy_path),
                        "output_img": str(out_path),
                        "kind": sel_kind,
                        "tap": f"{sel_tap}tap",
                        "ideal_policy": ideal_policy if sel_kind == "ideal" else "n/a",
                        "height": int(img_u8.shape[0]),
                        "width": int(img_u8.shape[1]),
                        "dtype": str(img_u8.dtype),
                        "pixel_min": int(img_u8.min()),
                        "pixel_max": int(img_u8.max()),
                    }
                )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {
            "vector_output_dir": str(vector_output_dir),
            "output_img_dir": str(output_img_dir),
            "kind": kind,
            "tap": tap,
            "ideal_policy": ideal_policy,
            "overwrite": bool(overwrite),
            "strict": bool(strict),
        },
        "num_converted": len(converted),
        "num_skipped": len(skipped),
        "converted": converted,
        "skipped": skipped,
    }
    return summary


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore output images from FIR ideal/fixed vector .npy files."
    )
    parser.add_argument(
        "--vector-output-dir",
        type=Path,
        default=DEFAULT_VECTOR_OUTPUT_DIR,
        help=f"Vector output root containing ideal_*/fixed_* dirs (default: {DEFAULT_VECTOR_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--output-img-dir",
        type=Path,
        default=DEFAULT_OUTPUT_IMG_DIR,
        help=f"Output directory for restored images (default: {DEFAULT_OUTPUT_IMG_DIR})",
    )
    parser.add_argument(
        "--kind",
        choices=("all", "ideal", "fixed"),
        default="all",
        help="Which vector kind to restore (default: all).",
    )
    parser.add_argument(
        "--tap",
        choices=("all", "3", "5"),
        default="all",
        help="Which tap-size to restore (default: all).",
    )
    parser.add_argument(
        "--ideal-policy",
        choices=IDEAL_POLICIES,
        default="clip",
        help="How to map ideal(float) vectors to uint8 images (default: clip).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing image files if present.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Raise errors on missing subdirs or invalid filenames.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=None,
        help="Optional path to write JSON summary. If omitted, summary is not written.",
    )
    return parser


def main() -> None:
    parser = _build_argparser()
    args = parser.parse_args()
    _t0 = perf_counter()
    try:
        result = restore_images(
            vector_output_dir=args.vector_output_dir,
            output_img_dir=args.output_img_dir,
            kind=args.kind,
            tap=args.tap,
            ideal_policy=args.ideal_policy,
            overwrite=args.overwrite,
            strict=args.strict,
        )

        if args.summary_json is not None:
            _write_json(args.summary_json.resolve(), result)

        _elapsed = perf_counter() - _t0
        extra = (
            f" summary_json={args.summary_json.resolve()}"
            if args.summary_json is not None
            else ""
        )
        print(
            "[OK] restore_images "
            "file=restore_images.py "
            f"generated={result['num_converted']} skipped={result['num_skipped']} failed=0 "
            f"elapsed={_elapsed:.2f}s out={args.output_img_dir.resolve()}{extra}"
        )
    except Exception as exc:
        _elapsed = perf_counter() - _t0
        print(
            "[FAIL] restore_images "
            "file=restore_images.py "
            f"generated=0 skipped=0 failed=1 "
            f"elapsed={_elapsed:.2f}s out={args.output_img_dir.resolve()} "
            f'error="{exc}"'
        )
        raise


if __name__ == "__main__":
    main()
