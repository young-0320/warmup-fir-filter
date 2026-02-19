# File: output_test_common.py
# Role: output vector 테스트에서 공용으로 쓰는 입력 준비/검증 유틸리티를 제공한다.
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np


def prepare_single_input_case(input_dir: Path) -> Path:
    input_dir.mkdir(parents=True, exist_ok=True)
    x = np.array(
        [
            [10, 20, 30, 40, 50, 60, 70, 80],
            [80, 70, 60, 50, 40, 30, 20, 10],
            [0, 10, 0, 10, 0, 10, 0, 10],
            [255, 200, 150, 100, 50, 0, 25, 75],
        ],
        dtype=np.uint8,
    )
    input_file = input_dir / "case_000_small_x_u8.npy"
    np.save(input_file, x)
    return input_file


def assert_output_files(
    *,
    output_dir: Path,
    subdir: str,
    expected_count: int,
    expected_suffix: str,
) -> list[Path]:
    files = sorted((output_dir / subdir).glob("*.npy"))
    assert len(files) == expected_count
    assert all("__" in p.name and expected_suffix in p.name for p in files)
    return files


def generate_and_assert_output_sets(
    *,
    input_dir: Path,
    output_dir: Path,
    generate_3tap: Callable[..., int],
    generate_5tap: Callable[..., int],
    count_3tap: int,
    count_5tap: int,
    subdir_3tap: str,
    subdir_5tap: str,
    suffix_3tap: str,
    suffix_5tap: str,
) -> tuple[int, int, list[Path], list[Path]]:
    c3 = generate_3tap(input_dir=input_dir, output_dir=output_dir)
    c5 = generate_5tap(input_dir=input_dir, output_dir=output_dir)

    files3 = assert_output_files(
        output_dir=output_dir,
        subdir=subdir_3tap,
        expected_count=count_3tap,
        expected_suffix=suffix_3tap,
    )
    files5 = assert_output_files(
        output_dir=output_dir,
        subdir=subdir_5tap,
        expected_count=count_5tap,
        expected_suffix=suffix_5tap,
    )
    return c3, c5, files3, files5


def load_first_output_pair(
    files3: list[Path],
    files5: list[Path],
) -> tuple[np.ndarray, np.ndarray]:
    return np.load(files3[0]), np.load(files5[0])


def assert_shape_dtype_and_range(
    y: np.ndarray,
    *,
    x_shape: tuple[int, ...],
    expected_dtype: Any,
    value_min: int | None = None,
    value_max: int | None = None,
) -> None:
    assert y.shape == x_shape
    assert y.dtype == expected_dtype
    if value_min is not None and value_max is not None:
        assert np.all((y >= value_min) & (y <= value_max))
