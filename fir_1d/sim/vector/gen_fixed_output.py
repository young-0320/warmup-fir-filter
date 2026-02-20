# File: gen_fixed_output.py
# Role: 입력 이미지와 계수 맵을 사용해 fixed FIR 출력 벡터(.npy)를 생성한다.
from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import numpy as np

from fir_1d.model.python.fir_1d_fixed_ref import fir_1d_fixed_golden
from fir_1d.sim.vector.h_coeff import h_coeff_3tap_map, h_coeff_5tap_map


THIS_FILE = Path(__file__).resolve()
DEFAULT_INPUT_DIR = THIS_FILE.parent / "input"
DEFAULT_OUTPUT_DIR = THIS_FILE.parent / "output"


def _iter_input_npy_files(input_dir: Path) -> list[Path]:
    files = [p for p in input_dir.glob("*.npy") if p.name.endswith("_x_u8.npy")]
    return sorted(files, key=lambda p: p.name.lower())


def _load_input_image_u8(path: Path) -> np.ndarray:
    x = np.load(path)
    if x.ndim != 2:
        raise ValueError(f"{path.name}: expected 2D array, got shape={x.shape}")
    if x.dtype != np.uint8:
        x = x.astype(np.uint8)
    return x


def _run_fixed_rowwise(
    x_u8: np.ndarray,
    h: list[float],
    *,
    frac_bits: int,
    acc_bits: int,
    coeff_bits: int,
) -> np.ndarray:
    height, width = x_u8.shape
    y = np.zeros((height, width), dtype=np.uint8)
    for r in range(height):
        row = x_u8[r, :]
        y_row = fir_1d_fixed_golden(
            row.tolist(),
            h,
            frac_bits=frac_bits,
            acc_bits=acc_bits,
            coeff_bits=coeff_bits,
        )
        y_arr = np.asarray(y_row, dtype=np.uint8)
        if y_arr.shape != (width,):
            raise ValueError(
                f"Row output length mismatch at row={r}: expected {width}, got {y_arr.shape}. "
                "Check fir_1d_fixed_golden same-mode output length."
            )
        y[r, :] = y_arr
    return y


def _case_stem_from_input(path: Path) -> str:
    suffix = "_x_u8.npy"
    if path.name.endswith(suffix):
        return path.name[: -len(suffix)]
    return path.stem


def _generate_fixed_outputs_for_tap_map(
    *,
    input_dir: Path,
    out_dir: Path,
    coeff_map: dict[str, list[float]],
    tap_label: str,
    frac_bits: int,
    acc_bits: int,
    coeff_bits: int,
    overwrite: bool = False,
) -> int:
    input_files = _iter_input_npy_files(input_dir)
    if not input_files:
        raise FileNotFoundError(f"No input .npy files found in {input_dir}")

    out_dir.mkdir(parents=True, exist_ok=True)
    generated = 0

    for in_path in input_files:
        x_u8 = _load_input_image_u8(in_path)
        case_stem = _case_stem_from_input(in_path)

        for coeff_name, h in coeff_map.items():
            out_name = f"{case_stem}__{coeff_name}_fixed_{tap_label}_y_u8.npy"
            out_path = out_dir / out_name
            if out_path.exists() and not overwrite:
                continue
            y = _run_fixed_rowwise(
                x_u8,
                h,
                frac_bits=frac_bits,
                acc_bits=acc_bits,
                coeff_bits=coeff_bits,
            )
            np.save(out_path, y)
            generated += 1

    return generated


def generate_fixed_3tap_output_vector(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    frac_bits: int = 12,
    acc_bits: int = 32,
    coeff_bits: int = 16,
    overwrite: bool = False,
) -> int:
    return _generate_fixed_outputs_for_tap_map(
        input_dir=input_dir.resolve(),
        out_dir=(output_dir.resolve() / "fixed_3tap"),
        coeff_map=h_coeff_3tap_map,
        tap_label="3tap",
        frac_bits=frac_bits,
        acc_bits=acc_bits,
        coeff_bits=coeff_bits,
        overwrite=overwrite,
    )


def generate_fixed_5tap_output_vector(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    frac_bits: int = 12,
    acc_bits: int = 32,
    coeff_bits: int = 16,
    overwrite: bool = False,
) -> int:
    return _generate_fixed_outputs_for_tap_map(
        input_dir=input_dir.resolve(),
        out_dir=(output_dir.resolve() / "fixed_5tap"),
        coeff_map=h_coeff_5tap_map,
        tap_label="5tap",
        frac_bits=frac_bits,
        acc_bits=acc_bits,
        coeff_bits=coeff_bits,
        overwrite=overwrite,
    )


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate FIR 1D fixed output vectors for 3tap/5tap filters."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Input vector directory (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output root directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--tap",
        choices=("all", "3", "5"),
        default="all",
        help="Tap-size to generate (default: all).",
    )
    parser.add_argument(
        "--frac-bits",
        type=int,
        default=12,
        help="Fraction bits for coefficient quantization (default: 12).",
    )
    parser.add_argument(
        "--acc-bits",
        type=int,
        default=32,
        help="Accumulator bit width (default: 32).",
    )
    parser.add_argument(
        "--coeff-bits",
        type=int,
        default=16,
        help="Coefficient bit width (default: 16).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output vectors instead of skipping duplicates.",
    )
    return parser


def _expected_num_outputs(input_dir: Path, coeff_count: int) -> int:
    return len(_iter_input_npy_files(input_dir)) * coeff_count


if __name__ == "__main__":
    _t0 = perf_counter()
    try:
        _args = _build_argparser().parse_args()
        _input_dir = _args.input_dir.resolve()
        _output_dir = _args.output_dir.resolve()

        c3 = 0
        c5 = 0
        e3 = 0
        e5 = 0
        if _args.tap in ("all", "3"):
            e3 = _expected_num_outputs(_input_dir, len(h_coeff_3tap_map))
            c3 = generate_fixed_3tap_output_vector(
                input_dir=_input_dir,
                output_dir=_output_dir,
                frac_bits=_args.frac_bits,
                acc_bits=_args.acc_bits,
                coeff_bits=_args.coeff_bits,
                overwrite=_args.overwrite,
            )
        if _args.tap in ("all", "5"):
            e5 = _expected_num_outputs(_input_dir, len(h_coeff_5tap_map))
            c5 = generate_fixed_5tap_output_vector(
                input_dir=_input_dir,
                output_dir=_output_dir,
                frac_bits=_args.frac_bits,
                acc_bits=_args.acc_bits,
                coeff_bits=_args.coeff_bits,
                overwrite=_args.overwrite,
            )
        total = c3 + c5
        expected_total = e3 + e5
        skipped_total = max(expected_total - total, 0)
        _elapsed = perf_counter() - _t0
        print(
            "[OK] gen_fixed_output "
            "file=gen_fixed_output.py "
            f"generated={total} skipped={skipped_total} failed=0 "
            f"elapsed={_elapsed:.2f}s out={_output_dir} "
            f"fixed_3tap={c3} fixed_5tap={c5}"
        )
    except Exception as exc:
        _elapsed = perf_counter() - _t0
        print(
            "[FAIL] gen_fixed_output "
            "file=gen_fixed_output.py "
            f"generated=0 skipped=0 failed=1 "
            f"elapsed={_elapsed:.2f}s out={DEFAULT_OUTPUT_DIR.resolve()} "
            f'error="{exc}"'
        )
        raise
