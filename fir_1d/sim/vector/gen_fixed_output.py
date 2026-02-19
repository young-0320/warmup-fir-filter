from __future__ import annotations

from pathlib import Path

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
            y = _run_fixed_rowwise(
                x_u8,
                h,
                frac_bits=frac_bits,
                acc_bits=acc_bits,
                coeff_bits=coeff_bits,
            )
            out_name = f"{case_stem}__{coeff_name}_fixed_{tap_label}_y_u8.npy"
            np.save(out_dir / out_name, y)
            generated += 1

    return generated


def generate_fixed_3tap_output_vector(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    frac_bits: int = 12,
    acc_bits: int = 32,
    coeff_bits: int = 16,
) -> int:
    return _generate_fixed_outputs_for_tap_map(
        input_dir=input_dir.resolve(),
        out_dir=(output_dir.resolve() / "fixed_3tap"),
        coeff_map=h_coeff_3tap_map,
        tap_label="3tap",
        frac_bits=frac_bits,
        acc_bits=acc_bits,
        coeff_bits=coeff_bits,
    )


def generate_fixed_5tap_output_vector(
    input_dir: Path = DEFAULT_INPUT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    frac_bits: int = 12,
    acc_bits: int = 32,
    coeff_bits: int = 16,
) -> int:
    return _generate_fixed_outputs_for_tap_map(
        input_dir=input_dir.resolve(),
        out_dir=(output_dir.resolve() / "fixed_5tap"),
        coeff_map=h_coeff_5tap_map,
        tap_label="5tap",
        frac_bits=frac_bits,
        acc_bits=acc_bits,
        coeff_bits=coeff_bits,
    )


if __name__ == "__main__":
    c3 = generate_fixed_3tap_output_vector()
    c5 = generate_fixed_5tap_output_vector()
    print(f"Generated fixed outputs: 3tap={c3}, 5tap={c5}, total={c3 + c5}")
