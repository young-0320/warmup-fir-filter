# File: test_ideal_ output.py
# Role: ideal output vector 생성 스크립트의 파일 규약과 값 정합성을 검증한다.
from __future__ import annotations

from pathlib import Path

import numpy as np

from fir_1d.model.python.fir_1d_ref import fir_1d_ideal
from fir_1d.sim.vector.gen_ideal_output import (
    generate_ideal_3tap_output_vector,
    generate_ideal_5tap_output_vector,
)
from fir_1d.sim.vector.h_coeff import h_coeff_3tap_map, h_coeff_5tap_map
from fir_1d.sim.tests.output_test_common import (
    assert_shape_dtype_and_range,
    generate_and_assert_output_sets,
    load_first_output_pair,
    prepare_single_input_case,
)


def test_output_count_and_filename_convention(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    prepare_single_input_case(input_dir)

    c3, c5, _, _ = generate_and_assert_output_sets(
        input_dir=input_dir,
        output_dir=output_dir,
        generate_3tap=generate_ideal_3tap_output_vector,
        generate_5tap=generate_ideal_5tap_output_vector,
        count_3tap=len(h_coeff_3tap_map),
        count_5tap=len(h_coeff_5tap_map),
        subdir_3tap="ideal_3tap",
        subdir_5tap="ideal_5tap",
        suffix_3tap="_ideal_3tap_y_f64.npy",
        suffix_5tap="_ideal_5tap_y_f64.npy",
    )

    assert c3 == len(h_coeff_3tap_map)
    assert c5 == len(h_coeff_5tap_map)


def test_output_shape_and_dtype_match_input(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_file = prepare_single_input_case(input_dir)
    x = np.load(input_file)

    _, _, files3, files5 = generate_and_assert_output_sets(
        input_dir=input_dir,
        output_dir=output_dir,
        generate_3tap=generate_ideal_3tap_output_vector,
        generate_5tap=generate_ideal_5tap_output_vector,
        count_3tap=len(h_coeff_3tap_map),
        count_5tap=len(h_coeff_5tap_map),
        subdir_3tap="ideal_3tap",
        subdir_5tap="ideal_5tap",
        suffix_3tap="_ideal_3tap_y_f64.npy",
        suffix_5tap="_ideal_5tap_y_f64.npy",
    )
    y3, y5 = load_first_output_pair(files3, files5)

    assert_shape_dtype_and_range(y3, x_shape=x.shape, expected_dtype=np.float64)
    assert_shape_dtype_and_range(y5, x_shape=x.shape, expected_dtype=np.float64)


def test_spot_check_against_direct_ideal_row_result(tmp_path: Path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_file = prepare_single_input_case(input_dir)
    x = np.load(input_file)

    generate_ideal_3tap_output_vector(input_dir=input_dir, output_dir=output_dir)

    out_file = output_dir / "ideal_3tap" / "case_000_small__simple_lp_ideal_3tap_y_f64.npy"
    y = np.load(out_file)

    expected_row0 = np.array(
        fir_1d_ideal(x[0, :].tolist(), h_coeff_3tap_map["simple_lp"]),
        dtype=np.float64,
    )
    expected_row2 = np.array(
        fir_1d_ideal(x[2, :].tolist(), h_coeff_3tap_map["simple_lp"]),
        dtype=np.float64,
    )

    assert np.allclose(y[0, :], expected_row0)
    assert np.allclose(y[2, :], expected_row2)
