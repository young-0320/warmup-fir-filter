# File: gen_ideal_output.py
# Role: 입력 이미지와 계수 맵을 사용해 ideal FIR 출력 벡터(.npy)를 생성한다.
from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import numpy as np

from fir_1d.model.python.fir_1d_ref import fir_1d_ideal
from fir_1d.sim.vector.h_coeff import h_coeff_3tap_map, h_coeff_5tap_map


THIS_FILE = Path(__file__).resolve()
DEFAULT_INPUT_DIR = THIS_FILE.parent / "input"
DEFAULT_OUTPUT_DIR = THIS_FILE.parent / "output"

# 입력 : 처리 대상 파일 경로
# 출력 : 처리 대상 파일 리스트
def _iter_input_npy_files(input_dir: Path) -> list[Path]:
    files = [p for p in input_dir.glob("*.npy") if p.name.endswith("_x_u8.npy")]
    return sorted(files, key=lambda p: p.name.lower())

# 데이터 유효성 검토
# 입력 : u8이미지 데이터 경로 
# 출력 : 해당 데이터
def _load_input_image_u8(path: Path) -> np.ndarray:
    x = np.load(path)
    if x.ndim != 2:
        raise ValueError(f"{path.name}: expected 2D array, got shape={x.shape}")
    if x.dtype != np.uint8:
        x = x.astype(np.uint8)
    return x

# Fir 행 단위 실행
def _run_ideal_rowwise(x_u8: np.ndarray, h: list[float]) -> np.ndarray:
    height, width = x_u8.shape
    y = np.zeros((height, width), dtype=np.float64)
    for r in range(height):
        row = x_u8[r, :]
        y_row = fir_1d_ideal(row.tolist(), h)
        y_arr = np.asarray(y_row, dtype=np.float64)
        if y_arr.shape != (width,):
            raise ValueError(
                f"Row output length mismatch at row={r}: expected {width}, got {y_arr.shape}. "
                "Check fir_1d_ideal same-mode output length."
            )
        y[r, :] = y_arr
    return y

# 파일 명에서 공통 prefix 추출
def _case_stem_from_input(path: Path) -> str:
    suffix = "_x_u8.npy"
    if path.name.endswith(suffix):
        return path.name[: -len(suffix)]
    return path.stem


def _generate_ideal_outputs_for_tap_map(
    *,
    input_dir: Path,
    out_dir: Path,
    coeff_map: dict[str, list[float]],
    tap_label: str,
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
            out_name = f"{case_stem}__{coeff_name}_ideal_{tap_label}_y_f64.npy"
            out_path = out_dir / out_name
            if out_path.exists() and not overwrite:
                continue
            y = _run_ideal_rowwise(x_u8, h)
            np.save(out_path, y)
            generated += 1

    return generated


def generate_ideal_3tap_output_vector(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    overwrite: bool = False,
) -> int:
    return _generate_ideal_outputs_for_tap_map(
        input_dir=input_dir.resolve(),
        out_dir=(output_dir.resolve() / "ideal_3tap"),
        coeff_map=h_coeff_3tap_map,
        tap_label="3tap",
        overwrite=overwrite,
    )


def generate_ideal_5tap_output_vector(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    overwrite: bool = False,
) -> int:
    return _generate_ideal_outputs_for_tap_map(
        input_dir=input_dir.resolve(),
        out_dir=(output_dir.resolve() / "ideal_5tap"),
        coeff_map=h_coeff_5tap_map,
        tap_label="5tap",
        overwrite=overwrite,
    )


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate FIR 1D ideal output vectors for 3tap/5tap filters."
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
            c3 = generate_ideal_3tap_output_vector(
                input_dir=_input_dir,
                output_dir=_output_dir,
                overwrite=_args.overwrite,
            )
        if _args.tap in ("all", "5"):
            e5 = _expected_num_outputs(_input_dir, len(h_coeff_5tap_map))
            c5 = generate_ideal_5tap_output_vector(
                input_dir=_input_dir,
                output_dir=_output_dir,
                overwrite=_args.overwrite,
            )
        total = c3 + c5
        expected_total = e3 + e5
        skipped_total = max(expected_total - total, 0)
        _elapsed = perf_counter() - _t0
        print(
            "[OK] gen_ideal_output "
            "file=gen_ideal_output.py "
            f"generated={total} skipped={skipped_total} failed=0 "
            f"elapsed={_elapsed:.2f}s out={_output_dir} "
            f"ideal_3tap={c3} ideal_5tap={c5}"
        )
    except Exception as exc:
        _elapsed = perf_counter() - _t0
        print(
            "[FAIL] gen_ideal_output "
            "file=gen_ideal_output.py "
            f"generated=0 skipped=0 failed=1 "
            f"elapsed={_elapsed:.2f}s out={DEFAULT_OUTPUT_DIR.resolve()} "
            f'error="{exc}"'
        )
        raise
