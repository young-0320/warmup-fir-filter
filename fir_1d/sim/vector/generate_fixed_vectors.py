#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


THIS_FILE = Path(__file__).resolve()
# NOTE:
# Run this script as a module from the project root:
# `uv run -m fir_1d.sim.vector.generate_fixed_vectors`
from fir_1d.model.python.fir_1d_fixed_ref import fir_1d_fixed_golden  # noqa: E402

# 상수 정의
FRAC_BITS = 7   # 소수 부분
ACC_BITS = 16   # 누산기 비트 폭
COEFF_BITS = 8  # 필터 계수 비트 폭


# 양자화된 h 출력
def _quantize_coefficients(h: list[float], frac_bits: int, coeff_bits: int) -> list[int]:
    scale = 1 << frac_bits
    min_coeff = -(1 << (coeff_bits - 1))
    max_coeff = (1 << (coeff_bits - 1)) - 1
    q = np.rint(np.array(h, dtype=np.float64) * scale)
    q = np.clip(q, min_coeff, max_coeff).astype(np.int64)
    return [int(v) for v in q.tolist()]


def _preprocess_x(x: list[float | int]) -> list[int]:
    out: list[int] = []
    for sample in x:
        if not np.isfinite(sample):
            raise ValueError("Vector generation input x must not contain NaN/Inf.")
        rounded = int(np.rint(sample))
        if rounded < 0:
            out.append(0)
        elif rounded > 255:
            out.append(255)
        else:
            out.append(rounded)
    return out


def _write_u8_mem(path: Path, values: list[int]) -> None:
    path.write_text("\n".join(f"{v & 0xFF:02X}" for v in values) + "\n", encoding="ascii")


def _write_s8_mem(path: Path, values: list[int]) -> None:
    path.write_text("\n".join(f"{v & 0xFF:02X}" for v in values) + "\n", encoding="ascii")


def generate_vectors() -> list[dict]:
    vector_dir = THIS_FILE.parent

    cases = [
        {
            "name": "case00_full_scale_impulse",
            "x": [255, 0, 0, 0],
            "h": [0.1, 0.5, 0.3, 0.1],
        },
        {
            "name": "case01_bankers_rounding_and_saturation",
            "x": [-1.2, 0.5, 1.5, 2.5, 300.1],
            "h": [0.5],
        },
        {
            "name": "case02_q17_boundary_taps",
            "x": [255, 255, 255, 255],
            "h": [-1.0, 127 / 128],
        },
        {
            "name": "case03_general_nominal",
            "x": [10, 20, 30, 40, 50, 60],
            "h": [0.1, 0.5, 0.3, 0.1],
        },
    ]

    manifest: list[dict] = []
    for case in cases:
        name = case["name"]
        x_in = case["x"]
        h_real = case["h"]

        y = fir_1d_fixed_golden(
            x=x_in,
            h=h_real,
            frac_bits=FRAC_BITS,
            acc_bits=ACC_BITS,
            coeff_bits=COEFF_BITS,
        )
        y_list = [int(v) for v in y.tolist()]
        x_proc = _preprocess_x(x_in)
        h_q = _quantize_coefficients(h_real, FRAC_BITS, COEFF_BITS)

        x_mem = f"{name}_x_u8.mem"
        h_mem = f"{name}_h_s8.mem"
        y_mem = f"{name}_y_u8.mem"

        _write_u8_mem(vector_dir / x_mem, x_proc)
        _write_s8_mem(vector_dir / h_mem, h_q)
        _write_u8_mem(vector_dir / y_mem, y_list)

        manifest.append(
            {
                "name": name,
                "params": {
                    "frac_bits": FRAC_BITS,
                    "acc_bits": ACC_BITS,
                    "coeff_bits": COEFF_BITS,
                },
                "x_input": x_in,
                "x_preprocessed_u8": x_proc,
                "h_real": h_real,
                "h_quantized_s8": h_q,
                "y_output_u8": y_list,
                "files": {"x_mem": x_mem, "h_mem": h_mem, "y_mem": y_mem},
            }
        )

    manifest_path = vector_dir / "fixed_vector_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "model": "fir_1d_fixed_golden",
                "note": "Generated from Python fixed reference model.",
                "cases": manifest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    generated = generate_vectors()
    print(f"Generated {len(generated)} fixed-vector cases in {THIS_FILE.parent}")
